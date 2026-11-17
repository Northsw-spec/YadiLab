"""RFC 2131 T1/T2 renewal: real packets, bounded virtual state, no false leases."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.dhcp import (
    DhcpMessage, DhcpSession, _checked_frame, _decode_datagram,
)
from network_core.dhcp_registry import DhcpSessionRegistry
from network_core.ethernet_frame import BROADCAST, EthernetFrame
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_dhcp import CLIENT_MAC, SERVER_MAC
from test_dhcp_registry import clients, start


class RenewalCodecTests(unittest.TestCase):
    def test_t1_request_unicast_and_t2_request_broadcast_with_correct_ciaddr(self):
        request = DhcpMessage(3, 77, CLIENT_MAC, client_address="192.0.2.70")
        self.assertEqual(request.serialize()[0], 1)
        self.assertEqual(request.serialize()[10:12], b"\x00\x00")
        self.assertEqual(request.serialize()[12:16], bytes([192, 0, 2, 70]))
        self.assertEqual(request.serialize()[16:20], b"\x00" * 4)
        self.assertEqual(request.serialize()[240:244], bytes((53, 1, 3, 255)))
        self.assertEqual(DhcpMessage.parse(request.serialize()), request)
        unicast = _checked_frame(request, CLIENT_MAC, "192.0.2.70",
                                 "192.0.2.1", SERVER_MAC)
        self.assertEqual(unicast.destination, SERVER_MAC)
        self.assertEqual(unicast.payload[12:20], bytes([192, 0, 2, 70, 192, 0, 2, 1]))
        self.assertEqual(unicast.payload[20:24], bytes.fromhex("00440043"))
        self.assertEqual(_decode_datagram(EthernetFrame.parse(unicast.serialize())),
                         ("192.0.2.70", request))
        rebinding = _checked_frame(request, CLIENT_MAC, "192.0.2.70")
        self.assertEqual(rebinding.destination, BROADCAST)
        self.assertEqual(rebinding.payload[16:20], b"\xff" * 4)
        self.assertEqual(_decode_datagram(EthernetFrame.parse(rebinding.serialize())),
                         ("192.0.2.70", request))

    def test_renewal_ack_unicasts_to_ciaddr_no_yiaddr_and_valid_checksum(self):
        reply = DhcpMessage(
            5, 77, CLIENT_MAC,
            server_identifier="192.0.2.1", subnet_mask="255.255.255.0",
            lease_seconds=3600, client_address="192.0.2.70")
        raw = reply.serialize()
        self.assertEqual(raw[0], 2)
        self.assertEqual(raw[10:12], b"\x00\x00")
        self.assertEqual(raw[12:16], bytes([192, 0, 2, 70]))
        self.assertEqual(raw[16:20], b"\x00" * 4)
        self.assertEqual(DhcpMessage.parse(raw), reply)
        frame = _checked_frame(reply, SERVER_MAC, "192.0.2.1",
                               "192.0.2.70", CLIENT_MAC)
        self.assertEqual(frame.destination, CLIENT_MAC)
        self.assertEqual(frame.payload[12:20], bytes([192, 0, 2, 1, 192, 0, 2, 70]))
        self.assertEqual(frame.payload[20:24], bytes.fromhex("00430044"))
        self.assertEqual(_decode_datagram(EthernetFrame.parse(frame.serialize())),
                         ("192.0.2.1", reply))

    def test_reject_selecting_options_on_renewal_and_corrupt_ciaddr_flags(self):
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(3, 77, CLIENT_MAC, requested_address="192.0.2.70",
                        server_identifier="192.0.2.1", client_address="192.0.2.70")
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(5, 77, CLIENT_MAC, "192.0.2.70", "192.0.2.1",
                        "255.255.255.0", 3600, client_address="192.0.2.70")
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(2, 77, CLIENT_MAC, "192.0.2.70", "192.0.2.1",
                        "255.255.255.0", 3600, client_address="192.0.2.70")
        original = DhcpMessage(3, 77, CLIENT_MAC, client_address="192.0.2.70")
        for offset, value in (
            (10, 0x80),  # wrong broadcast flags for renewal
            (16, 1),     # renewal SELECTING must not set yiaddr
            (240, 50),   # renewal MUST NOT send requested-address option
        ):
            altered = bytearray(original.serialize())
            altered[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ProjectValidationError):
                DhcpMessage.parse(bytes(altered))
        msg = DhcpMessage(5, 77, CLIENT_MAC, server_identifier="192.0.2.1",
                          subnet_mask="255.255.255.0", lease_seconds=60,
                          client_address="192.0.2.70")
        valid = _checked_frame(msg, SERVER_MAC, "192.0.2.1",
                               "192.0.2.70", CLIENT_MAC)
        # IP destination does not equal client's ciaddr, even if checksum
        # is recomputed, cannot be accepted as renewal ACK.
        wrong = EthernetFrame(
            BROADCAST, SERVER_MAC, 0x0800, valid.payload)
        with self.assertRaises(ProjectValidationError):
            _decode_datagram(wrong)


class RenewalSessionTests(unittest.TestCase):
    def test_t1_threshold_and_success_restart_virtual_lease_deadlines(self):
        p = clients()
        baseline = copy.deepcopy(p)
        registry = DhcpSessionRegistry()
        sid = start(registry, p)["sessionId"]
        first = registry.run(sid, p, "client", "eth0", 100, 60)
        self.assertEqual(first["leases"][0]["t1AtSeconds"], 30)
        self.assertEqual(first["leases"][0]["t2AtSeconds"], 53)
        self.assertEqual(first["leases"][0]["renewalCount"], 0)
        registry.advance(sid, p, 29)
        with self.assertRaisesRegex(ProjectValidationError, "T1 not reached"):
            registry.renew(sid, p, "client", "eth0", 101)
        self.assertEqual(registry._get(sid).state()["leases"][0]["expiresAtSeconds"], 60)
        registry.advance(sid, p, 1)
        self.assertEqual(registry._get(sid).state()["leases"][0]["renewalPhase"], "RENEWING")
        renewed = registry.renew(sid, p, "client", "eth0", 102)
        self.assertEqual(renewed["result"]["phase"], "RENEWING")
        self.assertEqual(renewed["result"]["status"], "ACK_RECEIVED")
        self.assertTrue(renewed["result"]["leaseRenewed"])
        self.assertEqual(renewed["result"]["request"]["ipDestination"], "192.0.2.1")
        self.assertEqual(renewed["result"]["request"]["ethernetDestination"], SERVER_MAC)
        self.assertTrue(renewed["result"]["request"]["receivedAtServer"])
        self.assertTrue(renewed["result"]["ack"]["receivedAtClient"])
        self.assertEqual([t["linkId"] for t in renewed["result"]["request"]["transmissions"]],
                         ["to-client", "to-server"])
        self.assertEqual([t["linkId"] for t in renewed["result"]["ack"]["transmissions"]],
                         ["to-server", "to-client"])
        lease = renewed["leases"][0]
        self.assertEqual(lease["ipv4"], "192.0.2.70")
        self.assertEqual(lease["startedAtSeconds"], 30)
        self.assertEqual(lease["expiresAtSeconds"], 90)
        self.assertEqual(lease["t1AtSeconds"], 60)
        self.assertEqual(lease["t2AtSeconds"], 83)
        self.assertEqual(lease["renewalCount"], 1)
        self.assertEqual(lease["renewalPhase"], "BOUND")
        self.assertEqual(lease["remainingSeconds"], 60)
        self.assertEqual(p, baseline)
        self.assertIsNone(p["nodes"][0]["ports"][0]["ipv4"])

    def test_failed_t1_ack_leaves_original_deadline_then_t2_rebind_broadcast(self):
        p = clients()
        registry = DhcpSessionRegistry()
        sid = start(registry, p)["sessionId"]
        registry.run(sid, p, "client", "eth0", 100, 60)
        lab = registry._get(sid)
        original_inject = lab.dhcp.fabric.inject_frame
        registry.advance(sid, p, 30)

        def lose_ack(node, port, frame):
            _, parsed = _decode_datagram(frame)
            result = original_inject(node, port, frame)
            if parsed.message_type == 5 and parsed.client_address is not None:
                return {**result, "endpointArrivals": []}
            return result

        lab.dhcp.fabric.inject_frame = lose_ack
        failed = registry.renew(sid, p, "client", "eth0", 101)
        self.assertEqual(failed["result"]["status"], "ACK_NOT_RECEIVED")
        self.assertFalse(failed["result"]["leaseRenewed"])
        self.assertEqual(failed["leaseCount"], 1)
        self.assertEqual(failed["leases"][0]["expiresAtSeconds"], 60)
        self.assertEqual(failed["leases"][0]["renewalCount"], 0)
        lab.dhcp.fabric.inject_frame = original_inject
        registry.advance(sid, p, 23)
        self.assertEqual(registry._get(sid).state()["leases"][0]["renewalPhase"], "REBINDING")
        rebound = registry.renew(sid, p, "client", "eth0", 102)
        self.assertEqual(rebound["result"]["phase"], "REBINDING")
        self.assertEqual(rebound["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(rebound["result"]["request"]["ipDestination"], "255.255.255.255")
        self.assertEqual(rebound["result"]["request"]["ethernetDestination"], BROADCAST)
        self.assertEqual(rebound["leases"][0]["startedAtSeconds"], 53)
        self.assertEqual(rebound["leases"][0]["expiresAtSeconds"], 113)
        self.assertEqual(rebound["leases"][0]["renewalPhase"], "BOUND")
        self.assertEqual(rebound["leases"][0]["renewalCount"], 1)

    def test_lost_request_does_not_invent_ack_then_expiry_forces_new_dora(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 100, 60)
        lab = reg._get(sid)
        reg.advance(sid, p, 53)
        original = lab.dhcp.fabric.inject_frame

        def lose_request(node, port, frame):
            _, parsed = _decode_datagram(frame)
            result = original(node, port, frame)
            if parsed.message_type == 3 and parsed.client_address:
                return {**result, "endpointArrivals": []}
            return result

        lab.dhcp.fabric.inject_frame = lose_request
        result = reg.renew(sid, p, "client", "eth0", 101)
        self.assertEqual(result["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(result["result"]["ack"]["transmissions"], [])
        self.assertEqual(result["leases"][0]["expiresAtSeconds"], 60)
        self.assertEqual(result["leases"][0]["remainingSeconds"], 7)
        self.assertEqual(reg.advance(sid, p, 7)["leaseCount"], 0)
        with self.assertRaisesRegex(ProjectValidationError, "no active BOUND"):
            reg.renew(sid, p, "client", "eth0", 102)
        lab.dhcp.fabric.inject_frame = original
        newly_assigned = reg.run(sid, p, "client-2", "eth0", 103, 60)
        self.assertEqual(newly_assigned["result"]["lease"]["ipv4"], "192.0.2.70")

    def test_other_client_and_project_mismatch_rejected_without_change(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 100, 60)
        reg.advance(sid, p, 30)
        baseline = reg._get(sid).state()
        altered = copy.deepcopy(p)
        altered["links"][0]["enabled"] = False
        for project, node, xid in (
            (altered, "client", 101), (p, "client-2", 102),
            (p, "client", False), (p, "client", 0)
        ):
            with self.subTest(node=node, xid=xid), self.assertRaises(ProjectValidationError):
                reg.renew(sid, project, node, "eth0", xid)
            self.assertEqual(reg._get(sid).state(), baseline)
        reg.reset(sid, p)
        self.assertEqual(reg._get(sid).state()["clockSeconds"], 0)
        with self.assertRaisesRegex(ProjectValidationError, "no active BOUND"):
            reg.renew(sid, p, "client", "eth0", 103)

    def test_operation_budget_prevents_renewal_without_mutating_lease(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 100, 60)
        reg.advance(sid, p, 30)
        lab = reg._get(sid)
        lab.operation_count = 256
        before = lab.state()
        with self.assertRaisesRegex(ProjectValidationError, "operation limit"):
            reg.renew(sid, p, "client", "eth0", 101)
        self.assertEqual(lab.state(), before)

    def test_full_expiry_without_renewal_after_t2_and_lease_not_written(self):
        p = clients()
        before = copy.deepcopy(p)
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 100, 60)
        self.assertEqual(reg.advance(sid, p, 53)["leases"][0]["renewalPhase"], "REBINDING")
        expired = reg.advance(sid, p, 7)
        self.assertEqual(expired["leaseCount"], 0)
        self.assertEqual(expired["expiredLeases"][0]["state"], "EXPIRED")
        self.assertEqual(p, before)


class RenewalHTTPTests(unittest.TestCase):
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
            with urlopen(req, timeout=10) as reply:
                return reply.status, json.loads(reply.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_http_t1_and_t2_packets_real_session_and_persistent_file_sha(self):
        p = clients()
        self.store.save("original", p)
        saved = self.root / "original.yadilab"
        baseline = saved.read_bytes()
        code, session = self.post("/api/dhcp/session/start", {
            "project": p, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"})
        self.assertEqual(code, 200)
        sid = session["sessionId"]
        code, first = self.post("/api/dhcp/session/run", {
            "sessionId": sid, "project": p, "clientNode": "client",
            "clientPort": "eth0", "transactionId": 100, "leaseSeconds": 60})
        self.assertEqual(code, 200)
        self.assertEqual(first["leases"][0]["t1AtSeconds"], 30)
        self.assertEqual(first["leases"][0]["t2AtSeconds"], 53)
        renew_body = {"sessionId": sid, "project": p, "clientNode": "client",
                      "clientPort": "eth0", "transactionId": 101}
        self.assertEqual(self.post("/api/dhcp/session/renew", renew_body)[0], 422)
        self.assertEqual(self.post("/api/dhcp/session/advance", {
            "sessionId": sid, "project": p, "seconds": 30})[0], 200)
        code, renewed = self.post("/api/dhcp/session/renew", renew_body)
        self.assertEqual(code, 200)
        self.assertEqual(renewed["result"]["phase"], "RENEWING")
        self.assertEqual(renewed["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(renewed["leases"][0]["expiresAtSeconds"], 90)
        self.assertEqual(self.post("/api/dhcp/session/advance", {
            "sessionId": sid, "project": p, "seconds": 53})[0], 200)
        code, rebound = self.post("/api/dhcp/session/renew", {
            **renew_body, "transactionId": 102})
        self.assertEqual(code, 200)
        self.assertEqual(rebound["result"]["phase"], "REBINDING")
        self.assertEqual(rebound["result"]["request"]["ipDestination"], "255.255.255.255")
        self.assertEqual(rebound["leases"][0]["expiresAtSeconds"], 143)
        self.assertEqual(rebound["leases"][0]["renewalCount"], 2)
        self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(),
                         hashlib.sha256(baseline).hexdigest())
        self.assertEqual(saved.read_bytes(), baseline)
        self.assertEqual(ProjectStore(self.root).read("original")["project"], p)

    def test_http_invalid_extra_project_changed_client_and_missing_session(self):
        p = clients()
        code, session = self.post("/api/dhcp/session/start", {
            "project": p, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"})
        self.assertEqual(code, 200)
        sid = session["sessionId"]
        self.post("/api/dhcp/session/run", {
            "sessionId": sid, "project": p, "clientNode": "client",
            "clientPort": "eth0", "transactionId": 100, "leaseSeconds": 60})
        self.post("/api/dhcp/session/advance", {
            "sessionId": sid, "project": p, "seconds": 30})
        good = {"sessionId": sid, "project": p, "clientNode": "client",
                "clientPort": "eth0", "transactionId": 102}
        changed = copy.deepcopy(p)
        changed["links"][0]["enabled"] = False
        for invalid in (
            {**good, "clientNode": "client-2"},
            {**good, "transactionId": False},
            {**good, "transactionId": 0},
            {**good, "extra": 1},
            {k:v for k,v in good.items() if k != "clientPort"},
            {**good, "sessionId": "invalid"},
            {**good, "project": changed},
        ):
            with self.subTest(sample=str(invalid)[:60]):
                status, response = self.post("/api/dhcp/session/renew", invalid)
                self.assertEqual(status, 422)
                self.assertEqual(response["error"], "INVALID_PROJECT")
        self.assertEqual(self.server.dhcp_sessions._get(sid).state()["leases"][0]
                         ["expiresAtSeconds"], 60)
