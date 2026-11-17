"""RFC 792 Echo bytes and actual bidirectional routing/ARP/Ethernet ping."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.icmp import ICMPEcho, ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY
from network_core.icmp_ping import EchoExchange
from network_core.ipv4 import IPv4Trace
from network_core.ipv4_packet import IPv4Datagram, checksum, ICMP_PROTOCOL
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_ipv4_forwarding import lab, getport, multihop


def routed_reply_lab():
    p = lab()
    next(n for n in p["nodes"] if n["id"] == "b")["staticRoutes"] = [{
        "id":"return-to-a","destination":"192.0.2.0/24",
        "nextHop":"203.0.113.1","outPort":"eth0",
    }]
    return p


def multihop_reply_lab():
    p = multihop()
    next(n for n in p["nodes"] if n["id"]=="b")["staticRoutes"] = [{
        "id":"return-to-a","destination":"192.0.2.0/24",
        "nextHop":"198.51.100.1","outPort":"eth0",
    }]
    next(n for n in p["nodes"] if n["id"]=="r2")["staticRoutes"] = [{
        "id":"return-over-r","destination":"192.0.2.0/24",
        "nextHop":"203.0.113.1","outPort":"in",
    }]
    return p


class ICMPCodecTests(unittest.TestCase):
    def test_known_rfc_checksum_request_header(self):
        request = ICMPEcho(8, 0, 0, b"")
        self.assertEqual(request.serialize(), bytes.fromhex("0800f7ff00000000"))
        self.assertEqual(ICMPEcho.parse(request.serialize()), request)
        self.assertEqual(ICMPEcho.parse(request.reply().serialize()).icmp_type, 0)
        self.assertEqual(ICMPEcho.parse(request.reply().serialize()).sequence, 0)

    def test_odd_data_checksum_and_exact_echo_reply_identity(self):
        request = ICMPEcho(8, 65535, 31, b"abcde")
        raw = request.serialize()
        self.assertEqual(checksum(raw + b"\x00"), 0)
        self.assertEqual(ICMPEcho.parse(raw), request)
        reply = request.reply()
        self.assertEqual(reply.identifier, request.identifier)
        self.assertEqual(reply.sequence, request.sequence)
        self.assertEqual(reply.payload, request.payload)
        self.assertNotEqual(reply.serialize()[0], request.serialize()[0])
        self.assertEqual(ICMPEcho.parse(reply.serialize()), reply)
        with self.assertRaises(ProjectValidationError):
            reply.reply()

    def test_reject_malformed_echo_before_any_ip_network_work(self):
        original = ICMPEcho(8, 2, 3, b"abcd").serialize()
        bad = [
            b"", original[:7], original+b"\x01"*1480,
            b"\x03"+original[1:],
            original[:1]+b"\x01"+original[2:],
            original[:2]+b"\x00\x00"+original[4:],
            original[:-1]+b"\x01", "not bytes", None,
        ]
        for blob in bad:
            with self.subTest(value=str(blob)[:50]), self.assertRaises(ProjectValidationError):
                ICMPEcho.parse(blob)
        for kind, ident, seq, payload in (
            (3,1,1,b""), (8,True,1,b""), (8,-1,1,b""),
            (0,65536,1,b""), (8,1,65536,b""), (0,1,False,b""),
            (8,1,1,b"x"*1473), (8,1,1,"not bytes"),
        ):
            with self.subTest(kind=kind,ident=ident,seq=seq), self.assertRaises(ProjectValidationError):
                ICMPEcho(kind,ident,seq,payload)

    def test_ip_protocol_1_header_roundtrip_and_ttl_keep_protocol(self):
        payload = ICMPEcho(8, 123, 7, b"abc").serialize()
        ip = IPv4Datagram("192.0.2.10","203.0.113.20",64,payload,ICMP_PROTOCOL)
        raw = ip.serialize()
        self.assertEqual(raw[9],1)
        self.assertEqual(checksum(raw[:20]),0)
        self.assertEqual(IPv4Datagram.parse(raw),ip)
        self.assertEqual(IPv4Datagram.parse(raw+b"\x00"*20),ip)
        fw = ip.forwarded()
        self.assertEqual(fw.protocol,1)
        self.assertEqual(fw.ttl,63)
        self.assertEqual(IPv4Datagram.parse(fw.serialize()).payload,payload)
        self.assertEqual(ICMPEcho.parse(fw.payload).identifier,123)
        for protocol in (0,6,17,254,True,None):
            with self.subTest(protocol=protocol), self.assertRaises(ProjectValidationError):
                IPv4Datagram("192.0.2.10","203.0.113.20",4,b"",protocol)
        with self.assertRaisesRegex(ProjectValidationError,"checksum"):
            IPv4Datagram.parse(raw[:10]+b"\x00\x00"+raw[12:])

    def test_raw_protocol_1_invalid_echo_fails_before_arp(self):
        with self.assertRaisesRegex(ProjectValidationError,"icmp"):
            IPv4Trace(lab()).send("a","eth0","203.0.113.20",4,
                                  protocol=ICMP_PROTOCOL,payload=b"not-echo")


class EchoExchangeTests(unittest.TestCase):
    def test_direct_peer_ping_request_and_reply_on_real_vlan(self):
        p = lab()
        original = copy.deepcopy(p)
        result = EchoExchange(p).ping("a","eth0","192.0.2.1",1,173,8)
        self.assertEqual(result["status"],"REPLIED")
        self.assertTrue(result["replyMatched"])
        self.assertIsNone(result["rttMs"])
        self.assertEqual(result["identifier"],173)
        self.assertEqual(result["sequence"],8)
        self.assertEqual(result["request"]["status"],"DELIVERED")
        self.assertEqual(result["reply"]["status"],"DELIVERED")
        self.assertEqual(result["request"]["receiver"],{"node":"r","port":"wan"})
        self.assertEqual(result["reply"]["receiver"],{"node":"a","port":"eth0"})
        self.assertEqual(result["request"]["initialTtl"],1)
        self.assertEqual(result["reply"]["initialTtl"],1)
        self.assertEqual(result["request"]["finalTtl"],1)
        self.assertEqual(result["reply"]["finalTtl"],1)
        self.assertTrue(result["request"]["icmpSent"])
        self.assertTrue(result["reply"]["icmpSent"])
        self.assertEqual([t["linkId"] for t in result["request"]["steps"][0]["ipv4Transmissions"]],
                         ["la","lr1"])
        self.assertEqual([t["linkId"] for t in result["reply"]["steps"][0]["ipv4Transmissions"]],
                         ["lr1","la"])
        self.assertEqual(result["request"]["deliveredDatagram"]["protocol"],1)
        self.assertEqual(result["reply"]["deliveredDatagram"]["protocol"],1)
        self.assertEqual(p,original)

    def test_one_router_routed_ping_requires_explicit_reverse_route(self):
        p = routed_reply_lab()
        result = EchoExchange(p).ping("a","eth0","203.0.113.20",5,13,99)
        self.assertEqual(result["status"],"REPLIED")
        self.assertEqual([s["node"] for s in result["request"]["steps"]],["a","r"])
        self.assertEqual([s["node"] for s in result["reply"]["steps"]],["b","r"])
        self.assertEqual([s["ttlSent"] for s in result["request"]["steps"]],[5,4])
        self.assertEqual([s["ttlSent"] for s in result["reply"]["steps"]],[5,4])
        self.assertEqual([s["arp"]["status"] for s in result["request"]["steps"]],
                         ["RESOLVED","RESOLVED"])
        self.assertEqual([s["arp"]["status"] for s in result["reply"]["steps"]],
                         ["RESOLVED","RESOLVED"])
        self.assertEqual(result["reply"]["steps"][0]["nextHopIpv4"],"203.0.113.1")
        self.assertEqual(result["reply"]["steps"][1]["nextHopIpv4"],"192.0.2.10")
        self.assertEqual(result["reply"]["receiver"],{"node":"a","port":"eth0"})
        self.assertTrue(result["replyMatched"])

    def test_oneway_delivered_must_not_be_reported_as_successful_ping(self):
        p = lab()  # no declared reverse route on destination b
        one_way = IPv4Trace(p).send("a","eth0","203.0.113.20",5)
        self.assertEqual(one_way["status"],"DELIVERED")
        result = EchoExchange(p).ping("a","eth0","203.0.113.20",5,1,1)
        self.assertEqual(result["status"],"REPLY_FAILED")
        self.assertFalse(result["replyMatched"])
        self.assertEqual(result["request"]["status"],"DELIVERED")
        self.assertEqual(result["reply"]["status"],"NO_ROUTE")
        self.assertEqual(result["reply"]["steps"],[])
        self.assertIsNone(result["rttMs"])

    def test_return_next_hop_absent_causes_reply_arp_failure(self):
        p = routed_reply_lab()
        next(n for n in p["nodes"] if n["id"]=="b")["staticRoutes"][0]["nextHop"] = "203.0.113.254"
        result = EchoExchange(p).ping("a","eth0","203.0.113.20",5,1,2)
        self.assertEqual(result["status"],"REPLY_FAILED")
        self.assertEqual(result["request"]["status"],"DELIVERED")
        self.assertEqual(result["reply"]["status"],"ARP_FAILED")
        self.assertEqual(result["reply"]["steps"][0]["ipv4Transmissions"],[])

    def test_multihop_two_router_ping_and_ttl_per_direction(self):
        p = multihop_reply_lab()
        result = EchoExchange(p).ping("a","eth0","198.51.100.20",4,7,65535)
        self.assertEqual(result["status"],"REPLIED")
        self.assertEqual([s["node"] for s in result["request"]["steps"]],["a","r","r2"])
        self.assertEqual([s["node"] for s in result["reply"]["steps"]],["b","r2","r"])
        self.assertEqual(result["request"]["finalTtl"],2)
        self.assertEqual(result["reply"]["finalTtl"],2)
        self.assertEqual(result["reply"]["receiver"],{"node":"a","port":"eth0"})
        self.assertEqual(result["reply"]["deliveredDatagram"]["ttl"],2)

    def test_ttl_one_does_not_synthesize_echo_reply_through_router(self):
        result = EchoExchange(routed_reply_lab()).ping("a","eth0","203.0.113.20",1,4,5)
        self.assertEqual(result["status"],"REQUEST_FAILED")
        self.assertEqual(result["request"]["status"],"TTL_EXPIRED")
        self.assertIsNone(result["reply"])
        self.assertFalse(result["replyMatched"])

    def test_ttl_low_through_two_routers_request_fails(self):
        result = EchoExchange(multihop_reply_lab()).ping("a","eth0","198.51.100.20",2,2,3)
        self.assertEqual(result["status"],"REQUEST_FAILED")
        self.assertEqual(result["request"]["status"],"TTL_EXPIRED")
        self.assertIsNone(result["reply"])

    def test_vlan_isolation_and_down_link_never_form_ping_success(self):
        p = routed_reply_lab()
        getport(p,"sw-left","r")["vlan"]={"mode":"access","vlan":20}
        failed = EchoExchange(p).ping("a","eth0","203.0.113.20",5,22,1)
        self.assertEqual(failed["status"],"REQUEST_FAILED")
        self.assertEqual(failed["request"]["status"],"ARP_FAILED")
        self.assertIsNone(failed["reply"])
        p = routed_reply_lab()
        p["links"][0]["enabled"]=False
        down = EchoExchange(p).ping("a","eth0","203.0.113.20",5,22,1)
        self.assertEqual(down["request"]["status"],"ARP_FAILED")
        self.assertEqual(down["request"]["steps"][0]["arp"]["status"],"NO_ACTIVE_LINK")

    def test_missing_response_mac_no_guess(self):
        p=routed_reply_lab()
        getport(p,"b","eth0").pop("mac")
        result=EchoExchange(p).ping("a","eth0","203.0.113.20",5,1,1)
        self.assertEqual(result["status"],"REQUEST_FAILED")
        self.assertEqual(result["request"]["status"],"ARP_FAILED")
        self.assertIsNone(result["reply"])

    def test_firewall_has_no_invented_responder(self):
        p=routed_reply_lab()
        next(n for n in p["nodes"] if n["id"]=="b")["kind"]="firewall"
        result=EchoExchange(p).ping("a","eth0","203.0.113.20",5,1,1)
        self.assertEqual(result["status"],"RESPONDER_UNSUPPORTED")
        self.assertEqual(result["request"]["status"],"DELIVERED")
        self.assertIsNone(result["reply"])
        self.assertFalse(result["replyMatched"])

    def test_invalid_identity_ttl_and_ipv4_fail_closed(self):
        p = lab()
        for dest,ttl,identifier,seq in (
            ("203.0.113.20",0,1,1), ("203.0.113.20",True,1,1),
            ("203.0.113.20",256,1,1), ("bad",2,1,1),
            ("2001:db8::1",2,1,1), ("203.0.113.20",2,-1,1),
            ("203.0.113.20",2,True,1), ("203.0.113.20",2,1,65536),
            ("203.0.113.20",2,1,None),
        ):
            with self.subTest(dest=dest,ttl=ttl,identifier=identifier,seq=seq), self.assertRaises(ProjectValidationError):
                EchoExchange(p).ping("a","eth0",dest,ttl,identifier,seq)
        self.assertEqual(p["schemaVersion"],"1.3")


class ICMPEchoHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = LabHTTPServer(("127.0.0.1",0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def request(self,body):
        req = Request(self.base+"/api/icmp/echo",
                      data=json.dumps(body).encode(),
                      headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=7) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as err:
            return err.code,json.loads(err.read())

    def body(self, project=None, dest="203.0.113.20", ttl=5):
        return {"project":project if project is not None else routed_reply_lab(),
                "sourceNode":"a","sourcePort":"eth0","destinationIpv4":dest,
                "ttl":ttl,"identifier":100,"sequence":42}

    def test_real_http_routed_echo_request_and_return_reply(self):
        p = routed_reply_lab()
        original=copy.deepcopy(p)
        code,d = self.request(self.body(p))
        self.assertEqual(code,200)
        self.assertEqual(d["status"],"REPLIED")
        self.assertTrue(d["replyMatched"])
        self.assertEqual(d["reply"]["receiver"],{"node":"a","port":"eth0"})
        self.assertEqual(d["reply"]["deliveredDatagram"]["protocol"],1)
        self.assertEqual(p,original)
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_real_http_reject_false_success_without_reverse_route(self):
        code,d=self.request(self.body(lab()))
        self.assertEqual(code,200)
        self.assertEqual(d["request"]["status"],"DELIVERED")
        self.assertEqual(d["status"],"REPLY_FAILED")
        self.assertEqual(d["reply"]["status"],"NO_ROUTE")
        code,d=self.request(self.body(routed_reply_lab(),ttl=1))
        self.assertEqual(d["status"],"REQUEST_FAILED")
        self.assertEqual(d["request"]["status"],"TTL_EXPIRED")

    def test_real_http_bad_shapes_rejected_without_state(self):
        base=self.body()
        bad=[
            {k:v for k,v in base.items() if k!="identifier"},
            {**base,"extra":"not allowed"},
            {**base,"identifier":True},
            {**base,"sequence":65536},
            {**base,"ttl":0},
            {**base,"sourcePort":"absent"},
            {**base,"destinationIpv4":"192.0.2.1/24"},
            ["not","an","icmp request"],
        ]
        for payload in bad:
            with self.subTest(payload=str(payload)[:70]):
                code,d=self.request(payload)
                self.assertEqual(code,422)
                self.assertEqual(d["error"],"INVALID_PROJECT")
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_real_http_no_disk_mutation_and_no_reused_sessions(self):
        p = routed_reply_lab()
        saved=self.server.store.save("lab",p)
        raw=(self.root/"lab.yadilab").read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        self.assertEqual(saved["sha256"],sha)
        for _ in range(2):
            code,d=self.request(self.body(p))
            self.assertEqual(code,200)
            self.assertEqual(d["status"],"REPLIED")
            self.assertEqual(d["request"]["steps"][0]["arp"]["status"],"RESOLVED")
        self.assertEqual((self.root/"lab.yadilab").read_bytes(),raw)
        self.assertEqual(self.server.store.read("lab")["sha256"],sha)


if __name__ == "__main__":
    unittest.main()
