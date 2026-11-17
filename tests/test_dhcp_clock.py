"""Deterministic DHCP lease expiry: exact boundaries, no real-time clock."""
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

from network_core.dhcp import DhcpSession
from network_core.dhcp_registry import (
    DhcpSessionRegistry, MAX_ADVANCE_SECONDS, MAX_VIRTUAL_SECONDS,
)
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_dhcp_registry import clients, run, start


class ClockModelTests(unittest.TestCase):
    def test_exact_boundary_retention_then_expiry_and_address_reuse(self):
        project = clients()
        original = copy.deepcopy(project)
        registry = DhcpSessionRegistry()
        state = start(registry, project)
        sid = state["sessionId"]
        self.assertEqual(state["clockSeconds"], 0)
        first = registry.run(sid, project, "client", "eth0", 101, 60)
        self.assertEqual(first["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(first["result"]["lease"]["startedAtSeconds"], 0)
        self.assertEqual(first["result"]["lease"]["expiresAtSeconds"], 60)
        self.assertEqual(first["result"]["lease"]["remainingSeconds"], 60)
        self.assertEqual(first["leases"][0]["remainingSeconds"], 60)
        self.assertEqual(first["clockSeconds"], 0)
        t59 = registry.advance(sid, project, 59)
        self.assertEqual(t59["clockSeconds"], 59)
        self.assertEqual(t59["advancedSeconds"], 59)
        self.assertEqual(t59["operationCount"], 2)
        self.assertEqual(t59["expiredLeases"], [])
        self.assertEqual(t59["leases"][0]["remainingSeconds"], 1)
        self.assertEqual(t59["leases"][0]["state"], "BOUND")
        other = registry.run(sid, project, "client-2", "eth0", 102, 120)
        self.assertEqual(other["result"]["lease"]["ipv4"], "192.0.2.71")
        self.assertEqual(other["result"]["lease"]["startedAtSeconds"], 59)
        self.assertEqual(other["result"]["lease"]["expiresAtSeconds"], 179)
        self.assertEqual(other["leaseCount"], 2)
        t60 = registry.advance(sid, project, 1)
        self.assertEqual(t60["clockSeconds"], 60)
        self.assertEqual(t60["leaseCount"], 1)
        self.assertEqual(len(t60["expiredLeases"]), 1)
        self.assertEqual(t60["expiredLeases"][0]["ipv4"], "192.0.2.70")
        self.assertEqual(t60["expiredLeases"][0]["state"], "EXPIRED")
        self.assertEqual(t60["expiredLeases"][0]["remainingSeconds"], 0)
        self.assertEqual(t60["leases"][0]["ipv4"], "192.0.2.71")
        self.assertEqual(t60["leases"][0]["remainingSeconds"], 119)
        reused = registry.run(sid, project, "client-3", "eth0", 103, 60)
        self.assertEqual(reused["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(reused["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(reused["result"]["lease"]["startedAtSeconds"], 60)
        self.assertEqual(reused["result"]["lease"]["expiresAtSeconds"], 120)
        self.assertEqual(reused["leaseCount"], 2)
        self.assertEqual(project, original)
        self.assertTrue(all(
            p["ipv4"] is None
            for n in project["nodes"] if n["kind"] == "host" and n["id"].startswith("client")
            for p in n["ports"]))

    def test_all_expire_at_later_boundary_and_prior_client_can_request_again(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 101, 60)
        reg.advance(sid, p, 15)
        reg.run(sid, p, "client-2", "eth0", 102, 60)
        still = reg.advance(sid, p, 44)
        self.assertEqual(still["clockSeconds"], 59)
        self.assertEqual(still["leaseCount"], 2)
        expire_first = reg.advance(sid, p, 1)
        self.assertEqual(expire_first["leaseCount"], 1)
        self.assertEqual(expire_first["expiredLeases"][0]["clientNode"], "client")
        self.assertEqual(expire_first["leases"][0]["expiresAtSeconds"], 75)
        expire_second = reg.advance(sid, p, 15)
        self.assertEqual(expire_second["clockSeconds"], 75)
        self.assertEqual(expire_second["leaseCount"], 0)
        self.assertEqual(expire_second["expiredLeases"][0]["clientNode"], "client-2")
        renewed_by_new_dora = reg.run(sid, p, "client", "eth0", 103, 60)
        self.assertEqual(renewed_by_new_dora["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(renewed_by_new_dora["result"]["lease"]["startedAtSeconds"], 75)
        # This is a fresh DORA allocation, not RFC 2131 T1/T2 renewal.
        self.assertEqual(renewed_by_new_dora["result"]["lease"]["transactionId"], 103)

    def test_one_second_before_expiry_exhausted_and_afterwards_reuse(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p, begin="192.0.2.70", end="192.0.2.70")["sessionId"]
        reg.run(sid, p, "client", "eth0", 101, 60)
        reg.advance(sid, p, 59)
        with self.assertRaisesRegex(ProjectValidationError, "pool exhausted"):
            reg.run(sid, p, "client-2", "eth0", 102, 60)
        self.assertEqual(reg._get(sid).state()["operationCount"], 2)
        reg.advance(sid, p, 1)
        new = reg.run(sid, p, "client-2", "eth0", 103, 60)
        self.assertEqual(new["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(new["leases"][0]["clientNode"], "client-2")

    def test_invalid_advances_reject_before_touching_clock_or_lease(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 101, 60)
        baseline = reg._get(sid).state()
        for invalid in (-1, 0, 1.5, True, False, "60", None, 604801, 2**100):
            with self.subTest(value=invalid), self.assertRaises(ProjectValidationError):
                reg.advance(sid, p, invalid)
            self.assertEqual(reg._get(sid).state(), baseline)
        changed = copy.deepcopy(p)
        changed["links"][0]["enabled"] = False
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            reg.advance(sid, changed, 60)
        self.assertEqual(reg._get(sid).state(), baseline)
        with self.assertRaisesRegex(ProjectValidationError, "unknown or expired"):
            reg.advance("invalid-session-id", p, 10)
        self.assertEqual(reg._get(sid).state(), baseline)

    def test_clock_limit_operation_limit_and_reset(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        lab = reg._get(sid)
        lab.clock_seconds = MAX_VIRTUAL_SECONDS - 1
        reg.advance(sid, p, 1)
        before = lab.state()
        with self.assertRaisesRegex(ProjectValidationError, "virtual clock limit"):
            reg.advance(sid, p, 1)
        self.assertEqual(lab.state(), before)
        lab.operation_count = 256
        with self.assertRaisesRegex(ProjectValidationError, "operation limit"):
            reg.advance(sid, p, 1)
        self.assertEqual(lab.state()["clockSeconds"], MAX_VIRTUAL_SECONDS)
        reset = reg.reset(sid, p)
        self.assertEqual(reset["clockSeconds"], 0)
        self.assertEqual(reset["operationCount"], 0)
        self.assertEqual(reset["leases"], [])
        self.assertEqual(reset["macTables"], [])
        reg.run(sid, p, "client", "eth0", 101, 60)
        again = reg.advance(sid, p, 60)
        self.assertEqual(len(again["expiredLeases"]), 1)

    def test_concurrent_advance_and_run_are_serializable(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 100, 60)
        # Either locked ordering is legitimate: Run then Advance makes
        # both leases expire at t=60; Advance then Run reuses .70 at t=60.
        # A fabricated fixed ordering would make the test flaky.
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(reg.advance, sid, p, 60)
            b = pool.submit(reg.run, sid, p, "client-2", "eth0", 101, 60)
            advance = a.result()
            assigned = b.result()
        self.assertEqual(advance["clockSeconds"], 60)
        self.assertEqual(assigned["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(reg._get(sid).state()["clockSeconds"], 60)
        assigned_ip = assigned["result"]["lease"]["ipv4"]
        if assigned_ip == "192.0.2.70":
            self.assertEqual(assigned["result"]["lease"]["startedAtSeconds"], 60)
            self.assertEqual(reg._get(sid).state()["leaseCount"], 1)
        else:
            self.assertEqual(assigned_ip, "192.0.2.71")
            self.assertEqual(assigned["result"]["lease"]["startedAtSeconds"], 0)
            self.assertEqual(reg._get(sid).state()["leaseCount"], 0)
        self.assertEqual(reg._get(sid).state()["operationCount"], 3)

    def test_standalone_dora_untimed_lease_is_not_expired_implicitly(self):
        p = clients()
        direct = DhcpSession(p)
        result = direct.run(
            "client", "eth0", "server", "eth0",
            "192.0.2.70", "192.0.2.71", 101, 60)
        self.assertEqual(result["status"], "ACK_RECEIVED")
        self.assertEqual(len(direct.leases()), 1)
        self.assertNotIn("expiresAtSeconds", direct.leases()[0])
        self.assertEqual(direct.expire_leases(100000), [])
        self.assertEqual(len(direct.leases()), 1)


class ClockHttpTests(unittest.TestCase):
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

    def post(self, endpoint, payload):
        req = Request(
            self.url + endpoint, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_http_lease_expiration_reuse_and_persisted_sha(self):
        p = clients()
        self.store.save("baseline", p)
        saved = self.root / "baseline.yadilab"
        before = saved.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        code, started = self.post("/api/dhcp/session/start", {
            "project": p, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.70"})
        self.assertEqual(code, 200)
        sid = started["sessionId"]
        self.assertEqual(started["clockSeconds"], 0)
        code, first = self.post("/api/dhcp/session/run", {
            "sessionId": sid, "project": p,
            "clientNode": "client", "clientPort": "eth0",
            "transactionId": 101, "leaseSeconds": 60})
        self.assertEqual(code, 200)
        self.assertEqual(first["leases"][0]["remainingSeconds"], 60)
        advance = {"sessionId": sid, "project": p, "seconds": 59}
        code, almost = self.post("/api/dhcp/session/advance", advance)
        self.assertEqual(code, 200)
        self.assertEqual(almost["leases"][0]["remainingSeconds"], 1)
        self.assertEqual(almost["expiredLeases"], [])
        code, expiry = self.post("/api/dhcp/session/advance", {
            **advance, "seconds": 1})
        self.assertEqual(code, 200)
        self.assertEqual(expiry["clockSeconds"], 60)
        self.assertEqual(expiry["leaseCount"], 0)
        self.assertEqual(expiry["expiredLeases"][0]["state"], "EXPIRED")
        code, reused = self.post("/api/dhcp/session/run", {
            "sessionId": sid, "project": p,
            "clientNode": "client-2", "clientPort": "eth0",
            "transactionId": 102, "leaseSeconds": 60})
        self.assertEqual(code, 200)
        self.assertEqual(reused["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(reused["result"]["lease"]["startedAtSeconds"], 60)
        self.assertEqual(reused["leases"][0]["expiresAtSeconds"], 120)
        self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), digest)
        self.assertEqual(saved.read_bytes(), before)
        self.assertEqual(ProjectStore(self.root).read("baseline")["project"], p)
        self.assertEqual(sorted(x.name for x in self.root.glob("*.yadilab")),
                         ["baseline.yadilab"])

    def test_http_strict_bad_steps_changed_project_stop_and_restart(self):
        p = clients()
        code, started = self.post("/api/dhcp/session/start", {
            "project": p, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"})
        self.assertEqual(code, 200)
        sid = started["sessionId"]
        base = {"sessionId": sid, "project": p, "seconds": 60}
        modified = copy.deepcopy(p)
        modified["links"][0]["enabled"] = False
        for invalid in (
            {**base, "seconds": 0}, {**base, "seconds": False},
            {**base, "seconds": -1}, {**base, "seconds": 604801},
            {**base, "seconds": "60"},
            {**base, "extra": True},
            {k:v for k,v in base.items() if k!="project"},
            {**base, "project": modified},
            {**base, "sessionId": "bad"},
        ):
            with self.subTest(body=str(invalid)[:80]):
                code, error = self.post("/api/dhcp/session/advance", invalid)
                self.assertEqual(code, 422)
                self.assertEqual(error["error"], "INVALID_PROJECT")
                self.assertEqual(self.server.dhcp_sessions._get(sid).clock_seconds, 0)
        code, reset = self.post("/api/dhcp/session/reset", {
            "sessionId": sid, "project": p})
        self.assertEqual(code, 200)
        self.assertEqual(reset["clockSeconds"], 0)
        # Server restart discards ephemeral clock and session.
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        code, refused = self.post("/api/dhcp/session/advance", base)
        self.assertEqual(code, 422)
        self.assertIn("unknown or expired", refused["message"])
