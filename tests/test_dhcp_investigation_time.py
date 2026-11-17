"""Staged DHCP investigation: T1 unicast, T2 broadcast, expiry and real DORA."""
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

from network_core.dhcp_investigation import InvestigationRegistry, InvestigationSession
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_dhcp_port_vlan_fault import vlan_clients


def exercise(kind="CABLE_DOWN", difficulty="EXPIRY_RECOVERY", duration=60):
    return InvestigationSession(
        vlan_clients(), "client", "eth0", "server", "eth0",
        "192.0.2.70", "192.0.2.71", duration,
        difficulty=difficulty, _test_choice=kind)


def evidence(case):
    for kind, target in (
        ("lease", {}), ("link", {"linkId": "to-server"}),
        ("port", {"nodeId": "sw", "portId": "s"}),
    ):
        case.probe(kind, target)


class StagedEngineTests(unittest.TestCase):
    def test_advanced_all_hidden_faults_require_t1_t2_then_expire_and_real_dora(self):
        for kind in ("CABLE_DOWN", "PORT_SHUTDOWN", "VLAN_MISMATCH"):
            with self.subTest(kind=kind):
                case = exercise(kind)
                project_copy = copy.deepcopy(case.lab.project)
                first = case.public_state()
                self.assertEqual(first["phase"], "RENEWING")
                self.assertEqual(first["difficulty"], "EXPIRY_RECOVERY")
                self.assertEqual(first["t1AtSeconds"], 30)
                self.assertEqual(first["t2AtSeconds"], 53)
                self.assertEqual(first["expiresAtSeconds"], 60)
                self.assertEqual(first["nextClockTargetSeconds"], 53)
                self.assertFalse(first["canAdvance"])
                with self.assertRaisesRegex(ProjectValidationError, "observe real T1"):
                    case.advance(23)
                self.assertEqual(case.public_state()["clockSeconds"], 30)
                t1 = case.probe("renew", {})["observation"]
                self.assertEqual(t1["phase"], "RENEWING")
                self.assertEqual(t1["status"], "REQUEST_NOT_RECEIVED")
                self.assertFalse(t1["requestReachedServer"])
                self.assertFalse(t1["ackReachedClient"])
                self.assertFalse(t1["leaseRenewed"])
                self.assertTrue(case.public_state()["canAdvance"])
                before = case.lab.dhcp.leases()[0]
                step = case.advance(23)
                self.assertEqual(step["advancedSeconds"], 23)
                self.assertEqual(step["expiredLeases"], [])
                self.assertEqual(step["phase"], "REBINDING")
                self.assertEqual(step["clockSeconds"], 53)
                self.assertEqual(step["nextClockTargetSeconds"], 60)
                self.assertFalse(step["canAdvance"])
                self.assertEqual(case.lab.dhcp.leases()[0]["expiresAtSeconds"],
                                 before["expiresAtSeconds"])
                with self.assertRaisesRegex(ProjectValidationError, "observe real T2"):
                    case.advance(7)
                t2 = case.probe("renew", {})["observation"]
                self.assertEqual(t2["phase"], "REBINDING")
                self.assertEqual(t2["status"], "REQUEST_NOT_RECEIVED")
                self.assertFalse(t2["requestReachedServer"])
                self.assertFalse(t2["ackReachedClient"])
                self.assertFalse(t2["leaseRenewed"])
                self.assertTrue(case.public_state()["canAdvance"])
                evidence(case)
                with self.assertRaisesRegex(ProjectValidationError, "expired lease"):
                    case.diagnose(kind)
                expired = case.advance(7)
                self.assertEqual(expired["clockSeconds"], 60)
                self.assertEqual(expired["expiredLeases"], [{
                    "ipv4": "192.0.2.70", "state": "EXPIRED",
                    "expiresAtSeconds": 60,
                }])
                self.assertFalse(expired["leaseActive"])
                self.assertEqual(expired["phase"], "EXPIRED")
                self.assertEqual(expired["remainingSeconds"], 0)
                self.assertEqual(expired["requiredRecovery"], "NEW_DORA")
                self.assertIsNone(expired["nextClockTargetSeconds"])
                self.assertEqual(case.lab.dhcp.leases(), [])
                observed = case.probe("lease", {})["observation"]
                self.assertEqual(observed["status"], "EXPIRED")
                self.assertEqual(observed["remainingSeconds"], 0)
                with self.assertRaisesRegex(ProjectValidationError, "renewal impossible"):
                    case.probe("renew", {})
                self.assertTrue(case.diagnose(kind)["correct"])
                recovered = case.repair()
                self.assertEqual(recovered["status"], "RECOVERED")
                self.assertEqual(recovered["verifiedProtocol"], "NEW_DORA")
                self.assertEqual(recovered["packetStatus"], "ACK_RECEIVED")
                self.assertTrue(recovered["discoverReachedServer"])
                self.assertTrue(recovered["offerReachedClient"])
                self.assertTrue(recovered["requestReachedServer"])
                self.assertTrue(recovered["ackReachedClient"])
                self.assertTrue(recovered["leaseActive"])
                self.assertEqual(recovered["phase"], "BOUND")
                self.assertEqual(recovered["clockSeconds"], 60)
                self.assertEqual(recovered["expiresAtSeconds"], 120)
                self.assertEqual(recovered["leaseIpv4"], "192.0.2.70")
                self.assertEqual(case.lab.dhcp.leases()[0]["startedAtSeconds"], 60)
                self.assertEqual(case.lab.dhcp.leases()[0]["renewalCount"], 0)
                self.assertEqual(case.lab.state()["faultedLinks"], [])
                self.assertEqual(case.lab.state()["faultedPorts"], [])
                self.assertEqual(case.lab.state()["faultedAccessVlans"], [])
                self.assertEqual(case.lab.project, project_copy)

    def test_intermediate_t2_real_rebind_then_ack_without_expiration(self):
        case = exercise("VLAN_MISMATCH", "T2_REBIND")
        self.assertEqual(case.public_state()["phase"], "RENEWING")
        with self.assertRaisesRegex(ProjectValidationError, "observe real renewal"):
            case.diagnose("VLAN_MISMATCH")
        self.assertEqual(case.probe("renew", {})["observation"]["phase"], "RENEWING")
        self.assertEqual(case.advance(23)["phase"], "REBINDING")
        with self.assertRaisesRegex(ProjectValidationError, "exceeds"):
            case.advance(1)
        evidence(case)
        with self.assertRaisesRegex(ProjectValidationError, "real rebinding"):
            case.diagnose("VLAN_MISMATCH")
        t2 = case.probe("renew", {})["observation"]
        self.assertEqual(t2["phase"], "REBINDING")
        self.assertEqual(t2["status"], "REQUEST_NOT_RECEIVED")
        self.assertTrue(case.diagnose("VLAN_MISMATCH")["correct"])
        result = case.repair()
        self.assertEqual(result["verifiedProtocol"], "RENEWAL")
        self.assertEqual(result["packetStatus"], "ACK_RECEIVED")
        self.assertIsNone(result["discoverReachedServer"])
        self.assertIsNone(result["offerReachedClient"])
        self.assertEqual(result["clockSeconds"], 53)
        self.assertEqual(result["expiresAtSeconds"], 113)
        self.assertEqual(case.lab.dhcp.leases()[0]["renewalCount"], 1)

    def test_basic_rejects_clock_changes_without_spending_operations(self):
        case = exercise("PORT_SHUTDOWN", "T1_ONLY")
        original = case.public_state()
        budget = case.lab.operation_count
        with self.assertRaisesRegex(ProjectValidationError, "T1-only"):
            case.advance(1)
        self.assertEqual(case.public_state(), original)
        self.assertEqual(case.lab.operation_count, budget)
        case.probe("renew", {})
        evidence(case)
        self.assertTrue(case.diagnose("PORT_SHUTDOWN")["correct"])
        recovered = case.repair()
        self.assertEqual(recovered["verifiedProtocol"], "RENEWAL")
        self.assertEqual(recovered["clockSeconds"], 30)
        self.assertEqual(recovered["expiresAtSeconds"], 90)

    def test_explicit_exact_boundaries_and_invalid_steps_do_not_mutate(self):
        case = exercise("CABLE_DOWN", "EXPIRY_RECOVERY", duration=61)
        self.assertEqual(case.public_state()["clockSeconds"], 31)
        self.assertEqual(case.public_state()["t2AtSeconds"], 54)
        self.assertEqual(case.public_state()["expiresAtSeconds"], 61)
        case.probe("renew", {})
        frozen = case.public_state()
        for seconds in (0, -1, 1.5, True, "1", None, 604801, 31):
            with self.subTest(seconds=seconds), self.assertRaises(ProjectValidationError):
                case.advance(seconds)
            self.assertEqual(case.public_state(), frozen)
        self.assertEqual(case.advance(22)["clockSeconds"], 53)
        self.assertEqual(case.public_state()["phase"], "RENEWING")
        self.assertEqual(case.advance(1)["phase"], "REBINDING")
        case.probe("renew", {})
        self.assertEqual(case.advance(6)["clockSeconds"], 60)
        self.assertTrue(case.public_state()["leaseActive"])
        event = case.advance(1)
        self.assertEqual(event["phase"], "EXPIRED")
        self.assertEqual(event["expiredLeases"][0]["expiresAtSeconds"], 61)
        with self.assertRaisesRegex(ProjectValidationError, "already expired"):
            case.advance(1)
        self.assertEqual(case.public_state()["clockSeconds"], 61)

    def test_cannot_skip_explicit_t1_or_t2_or_advance_after_diagnosis(self):
        case = exercise("CABLE_DOWN")
        case.probe("renew", {})
        evidence(case)
        with self.assertRaisesRegex(ProjectValidationError, "expired lease"):
            case.diagnose("CABLE_DOWN")
        case.advance(23)
        case.probe("renew", {})
        case.advance(7)
        self.assertTrue(case.diagnose("CABLE_DOWN")["correct"])
        with self.assertRaisesRegex(ProjectValidationError, "clock is locked"):
            case.advance(1)

    def test_invalid_difficulties_and_missing_routes_fail_closed(self):
        for difficulty in (None, "", "advanced", True, 1, "T2_REBINDING"):
            with self.subTest(difficulty=difficulty), self.assertRaisesRegex(
                    ProjectValidationError, "unsupported difficulty"):
                exercise("CABLE_DOWN", difficulty)
        with patch("network_core.dhcp_investigation.secrets.randbelow", return_value=0):
            case = InvestigationSession(
                vlan_clients(), "client", "eth0", "server", "eth0",
                "192.0.2.70", "192.0.2.71", 60, difficulty="EXPIRY_RECOVERY")
        self.assertNotIn("faulted", json.dumps(case.public_state()))
        self.assertEqual(case.public_state()["difficulty"], "EXPIRY_RECOVERY")


class StagedHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = ProjectStore(self.root)
        self.server = LabHTTPServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def post(self, suffix, body):
        request = Request(
            self.url + "/api/dhcp/investigation/" + suffix,
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_http_t1_t2_expiry_and_dora_without_file_write(self):
        project = vlan_clients()
        self.store.save("baseline", project)
        file = self.root / "baseline.yadilab"
        saved = file.read_bytes()
        with patch("network_core.dhcp_investigation.secrets.randbelow", return_value=2):
            status, started = self.post("start", {
                "project": project, "clientNode": "client", "clientPort": "eth0",
                "serverNode": "server", "serverPort": "eth0", "poolStart": "192.0.2.70",
                "poolEnd": "192.0.2.71", "leaseSeconds": 60,
                "difficulty": "EXPIRY_RECOVERY",
            })
        self.assertEqual(status, 200)
        self.assertEqual(started["phase"], "RENEWING")
        self.assertNotIn("faulted", json.dumps(started))
        base = {"sessionId": started["sessionId"], "project": project}
        def call(route, **data):
            return self.post(route, {**base, **data})
        self.assertEqual(call("advance", seconds=23)[0], 422)
        self.assertEqual(call("probe", probe="renew", target={})[1]["observation"]["phase"],
                         "RENEWING")
        self.assertEqual(call("advance", seconds=23)[1]["phase"], "REBINDING")
        self.assertEqual(call("advance", seconds=7)[0], 422)
        self.assertEqual(call("probe", probe="renew", target={})[1]["observation"]["phase"],
                         "REBINDING")
        self.assertEqual(call("probe", probe="link", target={"linkId": "to-server"})[0], 200)
        self.assertEqual(call("probe", probe="port", target={
            "nodeId": "sw", "portId": "s"})[0], 200)
        status, expired = call("advance", seconds=7)
        self.assertEqual(status, 200)
        self.assertEqual(expired["phase"], "EXPIRED")
        self.assertEqual(expired["requiredRecovery"], "NEW_DORA")
        self.assertEqual(call("probe", probe="lease", target={})[1]
                         ["observation"]["status"], "EXPIRED")
        self.assertEqual(call("probe", probe="renew", target={})[0], 422)
        self.assertEqual(call("repair")[0], 422)
        status, diagnosis = call("diagnose", diagnosis="VLAN_MISMATCH")
        self.assertEqual(status, 200)
        self.assertTrue(diagnosis["correct"])
        status, result = call("repair")
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "RECOVERED")
        self.assertEqual(result["verifiedProtocol"], "NEW_DORA")
        self.assertTrue(result["discoverReachedServer"])
        self.assertTrue(result["offerReachedClient"])
        self.assertTrue(result["requestReachedServer"])
        self.assertTrue(result["ackReachedClient"])
        self.assertEqual(result["expiresAtSeconds"], 120)
        self.assertEqual(file.read_bytes(), saved)
        self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),
                         hashlib.sha256(saved).hexdigest())
        self.assertEqual(self.store.read("baseline")["project"], project)

    def test_http_reject_malformed_advance_and_preserves_session(self):
        project = vlan_clients()
        body = {"project": project, "clientNode": "client", "clientPort": "eth0",
                "serverNode": "server", "serverPort": "eth0", "poolStart": "192.0.2.70",
                "poolEnd": "192.0.2.71", "leaseSeconds": 60,
                "difficulty": "T2_REBIND"}
        status, started = self.post("start", body)
        self.assertEqual(status, 200)
        sid = started["sessionId"]
        original = self.server.investigations._get(sid).public_state()
        base = {"sessionId": sid, "project": project, "seconds": 23}
        different = copy.deepcopy(project)
        different["links"][0]["enabled"] = False
        for data in (
            {**base, "seconds": True}, {**base, "seconds": -1},
            {**base, "seconds": 1.5}, {**base, "seconds": None},
            {**base, "project": different}, {**base, "sessionId": "bad"},
            {**base, "unexpected": "extra"},
            {k:v for k,v in base.items() if k != "seconds"},
        ):
            with self.subTest(data=str(data)[:100]):
                status, message = self.post("advance", data)
                self.assertEqual(status, 422)
                self.assertEqual(message["error"], "INVALID_PROJECT")
                self.assertEqual(self.server.investigations._get(sid).public_state(), original)
        invalid_start = {**body, "difficulty": "INVALID"}
        self.assertEqual(self.post("start", invalid_start)[0], 422)
        self.assertEqual(self.post("start", {**body, "extra": "bad"})[0], 422)
