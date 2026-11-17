"""Evidence-first DHCP troubleshooting lab acceptance and strict HTTP tests."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.dhcp_investigation import (
    DIAGNOSES, InvestigationRegistry, InvestigationSession, MAX_PROBES,
)
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_dhcp_registry import clients
from test_dhcp_port_vlan_fault import vlan_clients


def scenario(project, choice):
    return InvestigationSession(project, "client", "eth0", "server", "eth0",
                                "192.0.2.70", "192.0.2.71", 60,
                                _test_choice=choice)


def probe(session, kind, **target):
    return session.probe(kind, target)


class InvestigationEngineTests(unittest.TestCase):
    def test_each_hidden_cause_is_revealed_only_by_measured_observations(self):
        for kind in DIAGNOSES:
            p = vlan_clients()
            canonical = copy.deepcopy(p)
            with self.subTest(kind=kind):
                session = scenario(p, kind)
                state = session.public_state()
                self.assertEqual(state["clockSeconds"], 30)
                self.assertEqual(state["expiresAtSeconds"], 60)
                self.assertEqual(state["remainingSeconds"], 30)
                self.assertEqual(state["phase"], "RENEWING")
                self.assertFalse(state["diagnosed"])
                self.assertNotIn("faulted", json.dumps(state))
                self.assertNotIn(kind, json.dumps(state))
                self.assertEqual(session.lab.dhcp.leases()[0]["state"], "BOUND")
                lease = probe(session, "lease")["observation"]
                self.assertEqual(lease["status"], "BOUND")
                self.assertEqual(lease["remainingSeconds"], 30)
                attempt = probe(session, "renew")["observation"]
                self.assertEqual(attempt["phase"], "RENEWING")
                self.assertEqual(attempt["status"], "REQUEST_NOT_RECEIVED")
                self.assertFalse(attempt["requestReachedServer"])
                self.assertFalse(attempt["ackReachedClient"])
                self.assertFalse(attempt["leaseRenewed"])
                self.assertEqual(session.lab.dhcp.leases()[0]["expiresAtSeconds"], 60)
                link = probe(session, "link", linkId="to-server")["observation"]
                port = probe(session, "port", nodeId="sw", portId="s")["observation"]
                vlan = probe(session, "vlan", nodeId="sw", portId="c")["observation"]
                self.assertEqual(link["documentedActive"], True)
                self.assertEqual(port["documentedEnabled"], True)
                self.assertEqual(vlan["documentedVlan"], 10)
                expect_link = "DOWN" if kind != "VLAN_MISMATCH" else "UP"
                self.assertEqual(link["observedCarrier"], expect_link)
                self.assertEqual(port["observedAdmin"], "DOWN" if kind == "PORT_SHUTDOWN" else "UP")
                self.assertEqual(vlan["observedVlan"], 20 if kind == "VLAN_MISMATCH" else 10)
                wrong = next(d for d in DIAGNOSES if d != kind)
                feedback = session.diagnose(wrong)
                self.assertFalse(feedback["correct"])
                self.assertFalse(feedback["repairAvailable"])
                self.assertNotIn(kind, json.dumps(feedback))
                with self.assertRaisesRegex(ProjectValidationError, "correct diagnosis"):
                    session.repair()
                accepted = session.diagnose(kind)
                self.assertTrue(accepted["correct"])
                self.assertTrue(accepted["repairAvailable"])
                self.assertFalse(accepted["repaired"])
                restored = session.repair()
                self.assertEqual(restored["status"], "RECOVERED")
                self.assertTrue(restored["requestReachedServer"])
                self.assertTrue(restored["ackReachedClient"])
                self.assertEqual(restored["cause"], kind)
                self.assertEqual(restored["expiresAtSeconds"], 90)
                self.assertEqual(session.lab.dhcp.leases()[0]["renewalCount"], 1)
                self.assertEqual(session.lab.state()["faultedLinks"], [])
                self.assertEqual(session.lab.state()["faultedPorts"], [])
                self.assertEqual(session.lab.state()["faultedAccessVlans"], [])
                self.assertEqual(p, canonical)
                with self.assertRaisesRegex(ProjectValidationError, "already repaired"):
                    session.repair()
                with self.assertRaisesRegex(ProjectValidationError, "already repaired"):
                    probe(session, "lease")

    def test_diagnosis_requires_real_renewal_and_two_independent_checks(self):
        p = vlan_clients()
        case = scenario(p, "VLAN_MISMATCH")
        with self.assertRaisesRegex(ProjectValidationError, "observe real renewal"):
            case.diagnose("VLAN_MISMATCH")
        probe(case, "renew")
        probe(case, "lease")
        with self.assertRaisesRegex(ProjectValidationError, "two other"):
            case.diagnose("VLAN_MISMATCH")
        probe(case, "lease")
        with self.assertRaisesRegex(ProjectValidationError, "two other"):
            case.diagnose("VLAN_MISMATCH")
        probe(case, "vlan", nodeId="sw", portId="c")
        self.assertTrue(case.diagnose("VLAN_MISMATCH")["correct"])

    def test_wrong_guesses_capped_and_never_leak_hidden_cause(self):
        p = vlan_clients()
        case = scenario(p, "PORT_SHUTDOWN")
        probe(case, "renew")
        probe(case, "lease")
        probe(case, "link", linkId="to-server")
        for _ in range(3):
            r = case.diagnose("CABLE_DOWN")
            self.assertFalse(r["correct"])
            self.assertNotIn("PORT_SHUTDOWN", json.dumps(r))
        with self.assertRaisesRegex(ProjectValidationError, "maximum three"):
            case.diagnose("PORT_SHUTDOWN")

    def test_no_vlan_configuration_never_invents_vlan_candidate(self):
        p = clients()
        with patch("network_core.dhcp_investigation.secrets.randbelow", return_value=1):
            case = InvestigationSession(
                p, "client", "eth0", "server", "eth0", "192.0.2.70",
                "192.0.2.71", 60)
        self.assertEqual(case._fault["kind"], "PORT_SHUTDOWN")
        with self.assertRaisesRegex(ProjectValidationError, "scenario unsupported"):
            scenario(p, "VLAN_MISMATCH")
        with self.assertRaisesRegex(ProjectValidationError, "documented switch access"):
            probe(case, "vlan", nodeId="sw", portId="c")

    def test_reject_invalid_probes_without_mutation_or_state_leak(self):
        p = vlan_clients()
        case = scenario(p, "CABLE_DOWN")
        before = case.public_state()
        for name, target in (
            ("unknown", {}), ("lease", {"linkId": "to-server"}),
            ("renew", {"nodeId": "sw"}), ("link", {}),
            ("link", {"linkId": "unreal"}), ("link", {"linkId": "to-server", "x": 1}),
            ("port", {"nodeId": "sw"}), ("port", {"nodeId": "client", "portId": "eth0"}),
            ("vlan", {"nodeId": "sw", "portId": "bad"}),
            ("vlan", {"nodeId": "sw", "portId": "bad", "x": 1}),
        ):
            with self.subTest(probe=name, target=target), self.assertRaises(ProjectValidationError):
                case.probe(name, target)
            self.assertEqual(case.public_state(), before)
        with self.assertRaises(ProjectValidationError):
            case.diagnose("unsupported")
        with self.assertRaises(ProjectValidationError):
            case.diagnose(None)
        self.assertEqual(case.public_state(), before)
        for seconds in (0, 59, True, "60", 604801):
            with self.subTest(seconds=seconds), self.assertRaises(ProjectValidationError):
                InvestigationSession(p, "client", "eth0", "server", "eth0",
                                     "192.0.2.70", "192.0.2.71", seconds)
        for _ in range(MAX_PROBES):
            probe(case, "lease")
        with self.assertRaisesRegex(ProjectValidationError, "observation limit"):
            probe(case, "lease")
        self.assertEqual(case.public_state()["observations"], MAX_PROBES)

    def test_invalid_baseline_cannot_become_false_exercise(self):
        # The cabling is fully declared/active, but client is on another
        # documented VLAN: actual baseline DORA must fail and never become
        # a misleading exercise.
        p = vlan_clients()
        p["nodes"][1]["ports"][0]["vlan"]["vlan"] = 20
        with self.assertRaisesRegex(ProjectValidationError, "baseline DORA"):
            scenario(p, "CABLE_DOWN")
        # Already disconnected documented cable is rejected even earlier,
        # before a hidden fault is chosen or any packet is sent.
        q = vlan_clients()
        q["links"][1]["enabled"] = False
        with self.assertRaisesRegex(ProjectValidationError, "documented active cables"):
            scenario(q, "CABLE_DOWN")

    def test_isolated_sessions_bound_to_project_and_opaque_ids(self):
        p = vlan_clients()
        reg = InvestigationRegistry()
        with patch("network_core.dhcp_investigation.secrets.randbelow", side_effect=[0, 1]):
            one = reg.start(p, "client", "eth0", "server", "eth0",
                            "192.0.2.70", "192.0.2.71", 60)
            two = reg.start(p, "client", "eth0", "server", "eth0",
                            "192.0.2.70", "192.0.2.71", 60)
        sid1, sid2 = one["sessionId"], two["sessionId"]
        self.assertNotEqual(sid1, sid2)
        self.assertNotIn("faulted", json.dumps(one))
        self.assertNotIn("faulted", json.dumps(two))
        self.assertEqual(reg.probe(sid1, p, "renew", {})["observation"]["status"],
                         "REQUEST_NOT_RECEIVED")
        self.assertEqual(reg.probe(sid2, p, "lease", {})["observation"]["status"], "BOUND")
        changed = copy.deepcopy(p)
        changed["links"][0]["enabled"] = False
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            reg.probe(sid1, changed, "link", {"linkId": "to-server"})
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            reg.diagnose(sid2, changed, "PORT_SHUTDOWN")
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            reg.repair(sid1, changed)
        self.assertEqual(reg.stop(sid1), {"status": "STOPPED"})
        with self.assertRaisesRegex(ProjectValidationError, "unknown or expired"):
            reg.probe(sid1, p, "lease", {})

    def test_lab_never_reaches_project_store_by_accident(self):
        p = vlan_clients()
        with tempfile.TemporaryDirectory() as td:
            storage = ProjectStore(Path(td))
            storage.save("unchanged", p)
            file = Path(td) / "unchanged.yadilab"
            before = file.read_bytes()
            case = scenario(p, "PORT_SHUTDOWN")
            for kind, target in (
                ("lease", {}), ("renew", {}),
                ("port", {"nodeId": "sw", "portId": "s"}),
                ("link", {"linkId": "to-server"}),
            ):
                case.probe(kind, target)
            self.assertTrue(case.diagnose("PORT_SHUTDOWN")["correct"])
            self.assertEqual(case.repair()["status"], "RECOVERED")
            self.assertEqual(file.read_bytes(), before)
            self.assertEqual(storage.read("unchanged")["project"], p)


class InvestigationHttpTests(unittest.TestCase):
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
        req = Request(self.url + path, data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def start(self, p):
        return self.post("/api/dhcp/investigation/start", {
            "project": p, "clientNode": "client", "clientPort": "eth0",
            "serverNode": "server", "serverPort": "eth0", "poolStart": "192.0.2.70",
            "poolEnd": "192.0.2.71", "leaseSeconds": 60})

    def test_http_real_renewal_exclusion_verdict_repair_and_save(self):
        p = vlan_clients()
        self.store.save("baseline", p)
        path = self.root / "baseline.yadilab"
        data = path.read_bytes()
        with patch("network_core.dhcp_investigation.secrets.randbelow", return_value=2):
            code, start = self.start(p)
        self.assertEqual(code, 200)
        self.assertNotIn("VLAN_MISMATCH", json.dumps(start))
        self.assertNotIn("faulted", json.dumps(start))
        sid = start["sessionId"]
        base = {"sessionId": sid, "project": p}
        def call(path, **fields):
            return self.post("/api/dhcp/investigation/" + path, {**base, **fields})
        status, attempt = call("probe", probe="renew", target={})
        self.assertEqual(status, 200)
        self.assertFalse(attempt["observation"]["requestReachedServer"])
        self.assertEqual(attempt["observation"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(call("probe", probe="lease", target={})[1]["observation"]["remainingSeconds"], 30)
        self.assertEqual(call("probe", probe="link", target={"linkId": "to-server"})[1]
                         ["observation"]["observedCarrier"], "UP")
        self.assertEqual(call("probe", probe="port", target={"nodeId": "sw", "portId": "s"})[1]
                         ["observation"]["observedAdmin"], "UP")
        self.assertEqual(call("probe", probe="vlan", target={"nodeId": "sw", "portId": "c"})[1]
                         ["observation"]["observedVlan"], 20)
        code, wrong = call("diagnose", diagnosis="CABLE_DOWN")
        self.assertEqual(code, 200)
        self.assertFalse(wrong["correct"])
        self.assertNotIn("VLAN_MISMATCH", json.dumps(wrong))
        self.assertEqual(call("repair")[0], 422)
        code, right = call("diagnose", diagnosis="VLAN_MISMATCH")
        self.assertEqual(code, 200)
        self.assertTrue(right["correct"])
        code, restored = call("repair")
        self.assertEqual(code, 200)
        self.assertEqual(restored["status"], "RECOVERED")
        self.assertTrue(restored["ackReachedClient"])
        self.assertEqual(restored["expiresAtSeconds"], 90)
        self.assertEqual(path.read_bytes(), data)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         hashlib.sha256(data).hexdigest())

    def test_http_invalid_payloads_and_restart_expires_session(self):
        p = vlan_clients()
        code, state = self.start(p)
        self.assertEqual(code, 200)
        sid = state["sessionId"]
        base = {"sessionId": sid, "project": p, "probe": "lease", "target": {}}
        modified = copy.deepcopy(p)
        modified["links"][0]["enabled"] = False
        for path, body in (
            ("/api/dhcp/investigation/probe", {**base, "surprise": "x"}),
            ("/api/dhcp/investigation/probe", {**base, "probe": "unknown"}),
            ("/api/dhcp/investigation/probe", {**base, "sessionId": "invalid"}),
            ("/api/dhcp/investigation/probe", {**base, "project": modified}),
            ("/api/dhcp/investigation/diagnose", {
                "sessionId": sid, "project": p, "diagnosis": "bogus"}),
            ("/api/dhcp/investigation/start", {
                "project": p, "clientNode": "client", "clientPort": "eth0",
                "serverNode": "server", "serverPort": "eth0",
                "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71",
                "leaseSeconds": False}),
        ):
            with self.subTest(path=path):
                code, error = self.post(path, body)
                self.assertEqual(code, 422)
                self.assertEqual(error["error"], "INVALID_PROJECT")
        self.assertEqual(self.server.investigations._get(sid).public_state()["observations"], 0)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        code, error = self.post("/api/dhcp/investigation/probe", base)
        self.assertEqual(code, 422)
        self.assertIn("unknown or expired", error["message"])
