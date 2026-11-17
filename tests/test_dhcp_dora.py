"""RFC 2131 selecting-state DHCP DORA with bounded, transient leases.

The successful path traverses the real declared Ethernet/VLAN fabric four
times. Negative tests must never create a simulated lease from a mere offer.
"""
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
    DhcpMessage, DhcpSession, _checked_frame, _datagram, _decode_datagram,
    simulate_dora,
)
from network_core.ethernet_frame import BROADCAST, EthernetFrame
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_dhcp import topology, CLIENT_MAC, SERVER_MAC
from test_ethernet import link, node


def dora(project=None, *, start="192.0.2.70", end="192.0.2.72"):
    return simulate_dora(
        topology() if project is None else project,
        "client", "eth0", "server", "eth0",
        start, end, 0x12345678, 3600,
    )


class DORACodecTests(unittest.TestCase):
    def test_selecting_request_and_ack_codec_matches_rfc2131_options(self):
        request = DhcpMessage(
            3, 0x12345678, CLIENT_MAC,
            server_identifier="192.0.2.1", requested_address="192.0.2.70")
        ack = DhcpMessage(
            5, 0x12345678, CLIENT_MAC,
            "192.0.2.70", "192.0.2.1", "255.255.255.0", 3600)
        for message, source, sender, src_port, dst_port, op, expected_options in (
            (request, "0.0.0.0", CLIENT_MAC, 68, 67, 1, (53, 50, 54)),
            (ack, "192.0.2.1", SERVER_MAC, 67, 68, 2, (53, 54, 1, 51)),
        ):
            with self.subTest(kind=message.message_type):
                encoded = message.serialize()
                self.assertEqual(encoded[0], op)
                self.assertEqual(int.from_bytes(encoded[4:8], "big"), 0x12345678)
                self.assertEqual(encoded[10:12], b"\x80\x00")
                self.assertEqual(encoded[236:240], bytes.fromhex("63825363"))
                self.assertEqual(DhcpMessage.parse(encoded), message)
                # Parse the actual cookie-terminated RFC 2132 options, not a
                # mirror of the implementation's expected list.
                options = []
                i = 240
                while encoded[i] != 255:
                    options.append(encoded[i])
                    i += encoded[i+1] + 2
                self.assertEqual(tuple(options), expected_options)
                frame = _checked_frame(message, sender, source)
                self.assertEqual(frame.destination, BROADCAST)
                self.assertEqual(_decode_datagram(frame), (source, message))
                wire = _datagram(message, source)
                self.assertEqual(wire[9], 17)
                self.assertEqual(int.from_bytes(wire[20:22], "big"), src_port)
                self.assertEqual(int.from_bytes(wire[22:24], "big"), dst_port)

    def test_reject_malformed_requests_and_acks_without_silent_fallback(self):
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(3, 2, CLIENT_MAC)
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(3, 2, CLIENT_MAC,
                        server_identifier="192.0.2.1", requested_address="bad")
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(3, 2, CLIENT_MAC, "192.0.2.70",
                        server_identifier="192.0.2.1", requested_address="192.0.2.70")
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(5, 2, CLIENT_MAC, "192.0.2.70", "192.0.2.1",
                        "255.255.255.0", 3600, "192.0.2.70")
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(5, 2, CLIENT_MAC, "192.0.2.70", "192.0.2.1",
                        "255.0.255.0", 3600)
        with self.assertRaises(ProjectValidationError):
            DhcpMessage(9, 2, CLIENT_MAC)

        request = DhcpMessage(
            3, 2, CLIENT_MAC,
            server_identifier="192.0.2.1", requested_address="192.0.2.70")
        for offset, replacement in (
            (0, 2),       # request must be BOOTREQUEST, not reply
            (16, 5),      # requesting client has no yiaddr
            (241, 4),     # message type altered to DECLINE
            (243, 49),    # 50 option is required, not 49
        ):
            raw = bytearray(request.serialize())
            raw[offset] = replacement
            with self.subTest(position=offset), self.assertRaises(ProjectValidationError):
                DhcpMessage.parse(bytes(raw))
        # Wrong source, client MAC, UDP length, checksum or DHCP code can
        # never be decoded into a valid selecting-state REQUEST.
        frame = _checked_frame(request, CLIENT_MAC, "0.0.0.0")
        with self.assertRaises(ProjectValidationError):
            _decode_datagram(EthernetFrame(BROADCAST, SERVER_MAC, 0x0800, frame.payload))
        wire = bytearray(frame.payload)
        wire[20] ^= 1
        with self.assertRaises(ProjectValidationError):
            _decode_datagram(EthernetFrame(BROADCAST, CLIENT_MAC, 0x0800, bytes(wire)))


class DORASimulationTests(unittest.TestCase):
    def test_four_actual_l2_broadcasts_and_volatile_lease_only_after_ack(self):
        project = topology()
        initial = copy.deepcopy(project)
        session = DhcpSession(project)
        self.assertEqual(session.leases(), [])
        result = session.run(
            "client", "eth0", "server", "eth0", "192.0.2.70", "192.0.2.71",
            0x12345678, 3600)
        self.assertEqual(result["status"], "ACK_RECEIVED")
        self.assertTrue(result["leaseCommitted"])
        self.assertEqual(result["lease"]["state"], "BOUND")
        self.assertEqual(result["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(result["lease"]["clientNode"], "client")
        self.assertEqual(result["lease"]["clientMac"], CLIENT_MAC)
        self.assertEqual(result["lease"]["serverIdentifier"], "192.0.2.1")
        self.assertEqual(result["lease"]["subnetMask"], "255.255.255.0")
        self.assertTrue(result["discover"]["receivedAtServer"])
        self.assertTrue(result["request"]["receivedAtServer"])
        self.assertTrue(result["ack"]["receivedAtClient"])
        for phase, expected in (
            ("discover", ["to-client", "to-server"]),
            ("offer", ["to-server", "to-client"]),
            ("request", ["to-client", "to-server"]),
            ("ack", ["to-server", "to-client"]),
        ):
            self.assertEqual(
                [t["linkId"] for t in result[phase]["transmissions"]],
                expected, phase)
        self.assertEqual(result["macTables"][0]["entries"], {
            CLIENT_MAC: "c", SERVER_MAC: "s"})
        self.assertTrue(result["ephemeral"])
        self.assertEqual(project, initial)
        self.assertIsNone(project["nodes"][0]["ports"][0]["ipv4"])
        self.assertEqual(session.leases(), [result["lease"]])
        snapshot = session.leases()
        snapshot[0]["state"] = "FAKE"
        self.assertEqual(session.leases()[0]["state"], "BOUND")

    def test_disabled_cables_and_vlan_isolation_cannot_commit_lease(self):
        p = topology()
        p["links"][0]["enabled"] = False
        result = dora(p)
        self.assertEqual(result["status"], "NO_ACTIVE_LINK")
        self.assertEqual(result["discover"]["transmissions"], [])
        self.assertEqual(result["request"]["transmissions"], [])
        self.assertEqual(result["ack"]["transmissions"], [])
        self.assertFalse(result["leaseCommitted"])
        self.assertIsNone(result["lease"])

        p = topology()
        p["links"][1]["enabled"] = False
        result = dora(p)
        self.assertEqual(result["status"], "DISCOVER_NOT_RECEIVED")
        self.assertEqual([t["linkId"] for t in result["discover"]["transmissions"]],
                         ["to-client"])
        self.assertEqual(result["offer"]["transmissions"], [])
        self.assertFalse(result["leaseCommitted"])

        p = topology()
        p["nodes"][1]["ports"][0]["vlan"] = {"mode":"access", "vlan":10}
        p["nodes"][1]["ports"][1]["vlan"] = {"mode":"access", "vlan":20}
        result = dora(p)
        self.assertEqual(result["status"], "DISCOVER_NOT_RECEIVED")
        self.assertIsNone(result["lease"])
        p["nodes"][1]["ports"][1]["vlan"] = {"mode":"access", "vlan":10}
        self.assertEqual(dora(p)["status"], "ACK_RECEIVED")

    def test_pool_selection_skips_documented_ips_and_prior_session_leases(self):
        p = topology()
        # Declare another unused host with its real MAC and physical link.
        extra = node("other", "host", ["eth0"])
        extra["ports"][0]["mac"] = "02:00:00:00:00:0C"
        p["nodes"].append(extra)
        p["nodes"][1]["ports"].append(node("spare", "switch", ["x"])["ports"][0])
        p["links"].append(link("to-other", "sw", "x", "other", "eth0"))
        # Reserve the first candidate as a separately documented host IP.
        documented = node("fixed", "host", ["eth0"])
        documented["ports"][0]["ipv4"] = "192.0.2.70/24"
        p["nodes"].append(documented)
        session = DhcpSession(p)
        first = session.run(
            "client", "eth0", "server", "eth0", "192.0.2.70", "192.0.2.72", 101, 3600)
        self.assertEqual(first["status"], "ACK_RECEIVED")
        self.assertEqual(first["lease"]["ipv4"], "192.0.2.71")
        second = session.run(
            "other", "eth0", "server", "eth0", "192.0.2.70", "192.0.2.72", 102, 3600)
        self.assertEqual(second["status"], "ACK_RECEIVED")
        self.assertEqual(second["lease"]["ipv4"], "192.0.2.72")
        self.assertEqual(len(session.leases()), 2)
        with self.assertRaisesRegex(ProjectValidationError, "already owns"):
            session.run("client", "eth0", "server", "eth0",
                        "192.0.2.70", "192.0.2.72", 103, 3600)
        # Session 2 has no prior lease and may select 71 again: explicit scope.
        self.assertEqual(dora(p)["lease"]["ipv4"], "192.0.2.71")

    def test_pool_exhaustion_bad_range_and_wrong_config_rejected(self):
        p = topology()
        for start, end in (
            ("192.0.2.1", "192.0.2.1"),  # server's own address
            ("192.0.2.0", "192.0.2.1"),  # network address
            ("192.0.2.254", "192.0.2.255"),  # broadcast
            ("192.0.2.74", "192.0.2.70"),
            ("192.0.2.20", "203.0.113.100"),
            ("192.0.2.70", "192.0.3.70"),   # >256, wrong subnet
            ("not-an-ip", "192.0.2.72"),
            ("192.0.2.070", "192.0.2.72"),
        ):
            with self.subTest(start=start, end=end), self.assertRaises(ProjectValidationError):
                dora(p, start=start, end=end)
        for node_name, port_name in (
            ("ghost", "eth0"), ("server", "unknown"), ("sw", "c")
        ):
            with self.subTest(node=node_name, port=port_name), self.assertRaises(ProjectValidationError):
                simulate_dora(p, "client", "eth0", node_name, port_name,
                              "192.0.2.70", "192.0.2.72", 2, 3600)
        with self.assertRaises(ProjectValidationError):
            simulate_dora(p, "client", "eth0", "server", "eth0",
                          "192.0.2.70", "192.0.2.72", True, 3600)
        with self.assertRaises(ProjectValidationError):
            simulate_dora(p, "client", "eth0", "server", "eth0",
                          "192.0.2.70", "192.0.2.72", 5, 0)

    def test_no_fake_router_relay(self):
        p = topology()
        p["nodes"][1]["kind"] = "router"
        for index, port in enumerate(p["nodes"][1]["ports"]):
            port["mac"] = "02:00:00:00:00:" + f"{0x20 + index:02X}"
            port["ipv4"] = f"198.51.100.{index+1}/24"
        result = dora(p)
        self.assertEqual(result["status"], "DISCOVER_NOT_RECEIVED")
        self.assertFalse(result["leaseCommitted"])

    def test_dropped_request_or_ack_never_commits_lease(self):
        # A test-only intercepted fabric delivery models a transient
        # downstream failure; no mocked network success is asserted.
        for dropped_type, status in ((3, "REQUEST_NOT_RECEIVED"),
                                     (5, "ACK_NOT_RECEIVED")):
            with self.subTest(dropped_type=dropped_type):
                session = DhcpSession(topology())
                original = session.fabric.inject_frame

                def cut(node_id, port_id, frame):
                    _, message = _decode_datagram(frame)
                    result = original(node_id, port_id, frame)
                    if message.message_type == dropped_type:
                        return {**result, "endpointArrivals": []}
                    return result

                session.fabric.inject_frame = cut
                result = session.run(
                    "client", "eth0", "server", "eth0",
                    "192.0.2.70", "192.0.2.71", 11, 3600)
                self.assertEqual(result["status"], status)
                self.assertFalse(result["leaseCommitted"])
                self.assertIsNone(result["lease"])
                self.assertEqual(session.leases(), [])


class DORAHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/api/dhcp/dora"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def post(self, body):
        request = Request(self.url, data=json.dumps(body).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    @staticmethod
    def request(p):
        return {
            "project": p, "clientNode": "client", "clientPort": "eth0",
            "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.72",
            "transactionId": 0x12345678, "leaseSeconds": 3600,
        }

    def test_real_http_dora_has_no_file_write_even_after_new_project_store(self):
        p = topology()
        original = copy.deepcopy(p)
        self.server.store.save("existing", p)
        saved = self.root / "existing.yadilab"
        before = saved.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        for _ in range(2):
            code, value = self.post(self.request(p))
            self.assertEqual(code, 200)
            self.assertEqual(value["status"], "ACK_RECEIVED")
            self.assertEqual(value["lease"]["state"], "BOUND")
            self.assertTrue(value["leaseCommitted"])
            self.assertEqual(value["lease"]["ipv4"], "192.0.2.70")
            self.assertEqual(value["lease"]["leaseSeconds"], 3600)
            self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), digest)
            self.assertEqual(ProjectStore(self.root).read("existing")["project"], original)
            self.assertEqual(self.root.joinpath("existing.yadilab").read_bytes(), before)
        self.assertEqual(sorted(self.root.glob("*.yadilab")), [saved])

    def test_http_invalid_pool_unknown_endpoint_extra_fields_do_not_write(self):
        p = topology()
        self.server.store.save("existing", p)
        saved = self.root / "existing.yadilab"
        before = saved.read_bytes()
        good = self.request(p)
        bad_requests = [
            {k:v for k,v in good.items() if k != "poolEnd"},
            {**good, "unrecognizedField": 1},
            {**good, "poolStart":"192.0.2.1", "poolEnd":"192.0.2.1"},
            {**good, "clientNode":"does-not-exist"},
            {**good, "poolEnd":"198.51.100.20"},
            {**good, "transactionId":False},
            {**good, "leaseSeconds":1000000},
            ["not", "an", "object"],
        ]
        for body in bad_requests:
            with self.subTest(body=str(body)[:50]):
                code, result = self.post(body)
                self.assertEqual(code, 422)
                self.assertEqual(result["error"], "INVALID_PROJECT")
                self.assertEqual(saved.read_bytes(), before)
