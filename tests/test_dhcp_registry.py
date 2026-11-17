"""Bounded multi-client DHCP sessions with real HTTP, concurrency and no writes."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.dhcp_registry import DhcpSessionRegistry
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_dhcp import topology
from test_ethernet import link, node


def clients(count=3):
    p = topology()
    sw = p["nodes"][1]
    for i in range(2, count+1):
        name = "client-" + str(i)
        port_name = "p-" + str(i)
        client = node(name, "host", ["eth0"])
        client["ports"][0]["mac"] = f"02:00:00:00:00:{i+10:02X}"
        p["nodes"].append(client)
        sw["ports"].append(node("spare", "switch", [port_name])["ports"][0])
        p["links"].append(link("wire-" + str(i), name, "eth0", "sw", port_name))
    return p


def start(registry, project=None, *, begin="192.0.2.70", end="192.0.2.71"):
    return registry.start(
        clients() if project is None else project,
        "server", "eth0", begin, end)


def run(registry, session_id, project, client, xid):
    return registry.run(session_id, project, client, "eth0", xid, 3600)


class MultiClientRegistryTests(unittest.TestCase):
    def test_two_clients_unique_leases_pool_exhaustion_reset_and_stop(self):
        p = clients()
        before = copy.deepcopy(p)
        registry = DhcpSessionRegistry()
        state = start(registry, p)
        sid = state["sessionId"]
        self.assertEqual(state["leaseCount"], 0)
        self.assertEqual(state["poolStart"], "192.0.2.70")
        self.assertEqual(state["poolEnd"], "192.0.2.71")
        self.assertTrue(state["ephemeral"])
        self.assertEqual(state["operationCount"], 0)
        first = run(registry, sid, p, "client", 101)
        self.assertEqual(first["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(first["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(first["leaseCount"], 1)
        second = run(registry, sid, p, "client-2", 102)
        self.assertEqual(second["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(second["result"]["lease"]["ipv4"], "192.0.2.71")
        self.assertEqual(second["operationCount"], 2)
        self.assertEqual(second["leaseCount"], 2)
        self.assertEqual([x["ipv4"] for x in second["leases"]],
                         ["192.0.2.70", "192.0.2.71"])
        self.assertEqual({x["clientNode"] for x in second["leases"]},
                         {"client", "client-2"})
        for message, name in (("already owns", "client"), ("pool exhausted", "client-3")):
            with self.subTest(name=name), self.assertRaisesRegex(ProjectValidationError, message):
                run(registry, sid, p, name, 103)
        self.assertEqual(registry._get(sid).state()["operationCount"], 2)
        self.assertEqual(registry._get(sid).state()["leaseCount"], 2)
        self.assertEqual(p, before)
        self.assertIsNone(p["nodes"][0]["ports"][0]["ipv4"])
        self.assertEqual(registry.reset(sid, p)["leaseCount"], 0)
        self.assertEqual(run(registry, sid, p, "client-3", 104)["result"]["lease"]["ipv4"],
                         "192.0.2.70")
        self.assertEqual(registry.stop(sid), {"status": "STOPPED"})
        with self.assertRaisesRegex(ProjectValidationError, "unknown or expired"):
            run(registry, sid, p, "client", 105)

    def test_project_lock_mutation_rejected_before_lease_mutation(self):
        p = clients()
        registry = DhcpSessionRegistry()
        sid = start(registry, p)["sessionId"]
        run(registry, sid, p, "client", 101)
        altered = copy.deepcopy(p)
        altered["links"][1]["enabled"] = False
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            run(registry, sid, altered, "client-2", 102)
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            registry.reset(sid, altered)
        self.assertEqual(registry._get(sid).state()["leaseCount"], 1)
        self.assertEqual(registry._get(sid).state()["operationCount"], 1)
        self.assertEqual(registry.stop(sid), {"status": "STOPPED"})

    def test_wrong_pool_and_server_rejected_at_start_without_allocation(self):
        p = clients()
        registry = DhcpSessionRegistry()
        for address_a, address_b in (
            ("192.0.2.0", "192.0.2.2"),
            ("192.0.2.71", "192.0.2.70"),
            ("192.0.2.71", "198.51.100.1"),
            ("junk", "192.0.2.72"),
            ("192.0.2.1", "192.0.3.1"),
        ):
            with self.subTest(start=address_a), self.assertRaises(ProjectValidationError):
                registry.start(p, "server", "eth0", address_a, address_b)
        with self.assertRaises(ProjectValidationError):
            registry.start(p, "sw", "s", "192.0.2.70", "192.0.2.71")
        with self.assertRaises(ProjectValidationError):
            registry.start(p, "server", "nope", "192.0.2.70", "192.0.2.71")
        self.assertEqual(len(registry._sessions), 0)

    def test_sessions_separated_and_racing_clients_get_distinct_ips(self):
        p = clients()
        registry = DhcpSessionRegistry()
        sid = start(registry, p)["sessionId"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(run, registry, sid, p, "client", 111)
            b = pool.submit(run, registry, sid, p, "client-2", 112)
            values = (a.result()["result"]["lease"]["ipv4"],
                      b.result()["result"]["lease"]["ipv4"])
        self.assertEqual(set(values), {"192.0.2.70", "192.0.2.71"})
        self.assertEqual(registry._get(sid).state()["leaseCount"], 2)
        another = start(registry, p)
        self.assertNotEqual(another["sessionId"], sid)
        self.assertEqual(another["leaseCount"], 0)
        self.assertEqual(run(registry, another["sessionId"], p, "client", 113)
                         ["result"]["lease"]["ipv4"], "192.0.2.70")

    def test_registry_session_limit(self):
        p = clients()
        registry = DhcpSessionRegistry()
        for _ in range(16):
            start(registry, p)
        with self.assertRaisesRegex(ProjectValidationError, "too many active"):
            start(registry, p)
        self.assertEqual(len(registry._sessions), 16)

    def test_failed_l2_exchange_counts_attempt_not_lease(self):
        p = clients()
        p["links"][1]["enabled"] = False
        registry = DhcpSessionRegistry()
        sid = start(registry, p)["sessionId"]
        result = run(registry, sid, p, "client", 101)
        self.assertEqual(result["result"]["status"], "DISCOVER_NOT_RECEIVED")
        self.assertEqual(result["leaseCount"], 0)
        self.assertEqual(result["operationCount"], 1)
        self.assertFalse(result["result"]["leaseCommitted"])
        self.assertEqual(result["leases"], [])


class MultiClientHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root)
        self.server = LabHTTPServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        request = Request(self.url + path, data=data,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_real_http_multiplex_lease_table_reset_stop_and_disk_checksum(self):
        p = clients()
        self.store.save("baseline", p)
        saved = self.root / "baseline.yadilab"
        disk_hash = hashlib.sha256(saved.read_bytes()).hexdigest()
        start_payload = {"project": p, "serverNode": "server", "serverPort": "eth0",
                         "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"}
        status, state = self.post("/api/dhcp/session/start", start_payload)
        self.assertEqual(status, 200)
        sid = state["sessionId"]
        self.assertEqual(state["leaseCount"], 0)
        for client_name, xid, address in (
            ("client", 1, "192.0.2.70"), ("client-2", 2, "192.0.2.71")
        ):
            status, value = self.post("/api/dhcp/session/run", {
                "project": p, "sessionId": sid,
                "clientNode": client_name, "clientPort": "eth0",
                "transactionId": xid, "leaseSeconds": 3600})
            self.assertEqual(status, 200)
            self.assertEqual(value["result"]["status"], "ACK_RECEIVED")
            self.assertEqual(value["result"]["lease"]["ipv4"], address)
        self.assertEqual(value["leaseCount"], 2)
        self.assertEqual(value["operationCount"], 2)
        status, exhausted = self.post("/api/dhcp/session/run", {
            "project": p, "sessionId": sid,
            "clientNode": "client-3", "clientPort": "eth0",
            "transactionId": 3, "leaseSeconds": 3600})
        self.assertEqual(status, 422)
        self.assertEqual(exhausted["error"], "INVALID_PROJECT")
        self.assertIn("pool exhausted", exhausted["message"])
        status, reset = self.post("/api/dhcp/session/reset",
                                  {"project": p, "sessionId": sid})
        self.assertEqual(status, 200)
        self.assertEqual(reset["leaseCount"], 0)
        self.assertEqual(reset["operationCount"], 0)
        self.assertEqual(reset["macTables"], [])
        status, again = self.post("/api/dhcp/session/run", {
            "project": p, "sessionId": sid,
            "clientNode": "client-3", "clientPort": "eth0",
            "transactionId": 4, "leaseSeconds": 3600})
        self.assertEqual(status, 200)
        self.assertEqual(again["result"]["lease"]["ipv4"], "192.0.2.70")
        status, stopped = self.post("/api/dhcp/session/stop", {"sessionId": sid})
        self.assertEqual(status, 200)
        self.assertEqual(stopped, {"status": "STOPPED"})
        self.assertEqual(self.post("/api/dhcp/session/reset",
                                  {"project": p, "sessionId": sid})[0], 422)
        self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), disk_hash)
        self.assertIsNone(ProjectStore(self.root).read("baseline")
                          ["project"]["nodes"][0]["ports"][0]["ipv4"])
        self.assertEqual(sorted(x.name for x in self.root.glob("*.yadilab")),
                         ["baseline.yadilab"])

    def test_malformed_requests_and_changed_project_fail_closed(self):
        p = clients()
        self.store.save("baseline", p)
        saved = self.root / "baseline.yadilab"
        before = saved.read_bytes()
        good_start = {"project": p, "serverNode": "server", "serverPort": "eth0",
                      "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"}
        for body in (
            {k:v for k,v in good_start.items() if k != "poolEnd"},
            {**good_start, "unexpected": True},
            {**good_start, "poolStart": "junk"},
        ):
            self.assertEqual(self.post("/api/dhcp/session/start", body)[0], 422)
        status, value = self.post("/api/dhcp/session/start", good_start)
        self.assertEqual(status, 200)
        sid = value["sessionId"]
        changed = copy.deepcopy(p)
        changed["links"][0]["enabled"] = False
        good_run = {"sessionId": sid, "project": p, "clientNode": "client",
                    "clientPort": "eth0", "transactionId": 1, "leaseSeconds": 3600}
        for path, body in (
            ("/api/dhcp/session/run", {**good_run, "project": changed}),
            ("/api/dhcp/session/run", {**good_run, "bad": 1}),
            ("/api/dhcp/session/run", {**good_run, "transactionId": 0}),
            ("/api/dhcp/session/run", {**good_run, "leaseSeconds": True}),
            ("/api/dhcp/session/run", {**good_run, "sessionId": "invalid"}),
            ("/api/dhcp/session/reset", {"sessionId": sid, "project": changed}),
            ("/api/dhcp/session/stop", {"sessionId": "unknown"}),
        ):
            with self.subTest(path=path):
                status, body = self.post(path, body)
                self.assertEqual(status, 422)
                self.assertEqual(body["error"], "INVALID_PROJECT")
                self.assertEqual(saved.read_bytes(), before)
        self.assertEqual(self.server.dhcp_sessions._get(sid).state()["leaseCount"], 0)
