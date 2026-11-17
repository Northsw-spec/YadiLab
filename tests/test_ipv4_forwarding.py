"""IPv4 packet byte codec and real L3 forwarding over ARP / Ethernet / VLAN."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.ipv4_packet import IPv4Datagram, checksum
from network_core.ipv4 import IPv4Trace
from network_core.model import ProjectValidationError, blank_project, validate_project
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_ethernet import node, link


def lab():
    p = blank_project("Explicit one-router IPv4 delivery")
    p["nodes"] = [
        node("a", "host", ["eth0"]),
        node("sw-left", "switch", ["a", "r"]),
        node("r", "router", ["wan", "lan"]),
        node("sw-right", "switch", ["r", "b"]),
        node("b", "host", ["eth0"]),
    ]
    p["links"] = [
        link("la", "a", "eth0", "sw-left", "a"),
        link("lr1", "sw-left", "r", "r", "wan"),
        link("lr2", "r", "lan", "sw-right", "r"),
        link("lb", "sw-right", "b", "b", "eth0"),
    ]
    configured = {
        ("a", "eth0"): ("192.0.2.10/24", "02:00:00:00:00:0A"),
        ("r", "wan"): ("192.0.2.1/24", "02:00:00:00:00:01"),
        ("r", "lan"): ("203.0.113.1/24", "02:00:00:00:00:02"),
        ("b", "eth0"): ("203.0.113.20/24", "02:00:00:00:00:0B"),
    }
    for n in p["nodes"]:
        for port in n["ports"]:
            if (n["id"], port["id"]) in configured:
                port["ipv4"], port["mac"] = configured[n["id"], port["id"]]
            if n["id"] == "sw-left":
                port["vlan"] = {"mode": "access", "vlan": 10}
            if n["id"] == "sw-right":
                port["vlan"] = {"mode": "access", "vlan": 20}
    p["nodes"][0]["staticRoutes"] = [{
        "id": "via-router", "destination": "203.0.113.0/24",
        "nextHop": "192.0.2.1", "outPort": "eth0",
    }]
    return validate_project(p)


def getport(p, node, port):
    return next(x for n in p["nodes"] if n["id"] == node
                for x in n["ports"] if x["id"] == port)


def multihop():
    p = lab()
    router = next(n for n in p["nodes"] if n["id"] == "r")
    router["staticRoutes"] = [{
        "id": "r2-transit", "destination": "198.51.100.0/24",
        "nextHop": "203.0.113.2", "outPort": "lan",
    }]
    client = next(n for n in p["nodes"] if n["id"] == "a")
    client["staticRoutes"][0]["destination"] = "198.51.100.0/24"
    peer = next(n for n in p["nodes"] if n["id"] == "b")
    peer["ports"][0]["ipv4"] = "198.51.100.20/24"
    r2 = node("r2", "router", ["in", "out"])
    r2["ports"][0].update(ipv4="203.0.113.2/24", mac="02:00:00:00:00:03")
    r2["ports"][1].update(ipv4="198.51.100.1/24", mac="02:00:00:00:00:04")
    sw3 = node("sw-third", "switch", ["r", "b"])
    for port in sw3["ports"]:
        port["vlan"] = {"mode": "access", "vlan": 30}
    p["nodes"].extend([r2, sw3])
    p["links"] = [l for l in p["links"] if l["id"] != "lb"]
    p["links"].extend([
        link("to-r2", "sw-right", "b", "r2", "in"),
        link("from-r2", "r2", "out", "sw-third", "r"),
        link("to-b", "sw-third", "b", "b", "eth0"),
    ])
    return validate_project(p)


class Ipv4PacketTests(unittest.TestCase):
    def test_rfc791_minimal_header_checksum_and_roundtrip(self):
        p=IPv4Datagram("192.0.2.10","203.0.113.20",64)
        raw=p.serialize()
        self.assertEqual(len(raw),20)
        self.assertEqual(raw[0:4],b"\x45\x00\x00\x14")
        self.assertEqual(raw[8:10],b"\x40\xfd")
        self.assertEqual(checksum(raw[:20]),0)
        self.assertEqual(IPv4Datagram.parse(raw),p)
        self.assertEqual(IPv4Datagram.parse(raw+b"\x00"*26),p)
        self.assertEqual(p.forwarded().ttl,63)
        self.assertNotEqual(p.forwarded().serialize()[10:12],raw[10:12])

    def test_checksum_and_packet_shape_rejected_not_ignored(self):
        p=IPv4Datagram("192.0.2.10","203.0.113.20",64)
        raw=p.serialize()
        for bad in (
            raw[:8], raw[:10]+b"\x00\x00"+raw[12:],
            raw[:8]+b"\x01"+raw[9:],
            raw[:2]+b"\x00\x19"+raw[4:],
            raw+b"\x01",
            b"\x46"+raw[1:],
            b"\x45\xff"+raw[2:],
        ):
            with self.subTest(bad=bad[:10]), self.assertRaises(ProjectValidationError):
                IPv4Datagram.parse(bad)
        for ttl in (0,256,True,None,"64",1.0):
            with self.subTest(ttl=ttl), self.assertRaises(ProjectValidationError):
                IPv4Datagram("192.0.2.10","203.0.113.20",ttl)
        for address in ("2001:db8::1","bad","192.0.2.10/24","0.0.0.0",
                        "224.0.0.1","255.255.255.255", 0, None):
            with self.subTest(addr=address), self.assertRaises(ProjectValidationError):
                IPv4Datagram(address,"203.0.113.20",64)
        with self.assertRaisesRegex(ProjectValidationError,"TTL"):
            IPv4Datagram("192.0.2.10","203.0.113.20",1).forwarded()

    def test_experimental_payload_is_not_echo_icmp(self):
        p=IPv4Datagram("192.0.2.10","203.0.113.20",2,b"\x01\x02\x03")
        self.assertEqual(IPv4Datagram.parse(p.serialize()),p)
        self.assertEqual(p.serialize()[9],253)
        with self.assertRaises(ProjectValidationError):
            IPv4Datagram("192.0.2.10","203.0.113.20",2,b"x"*1481)


class IPv4TraceTests(unittest.TestCase):
    def test_one_router_forwarding_uses_real_arp_and_vlan_links(self):
        p=lab()
        original=copy.deepcopy(p)
        data=IPv4Trace(p).send("a","eth0","203.0.113.20",5)
        self.assertEqual(data["status"],"DELIVERED")
        self.assertEqual(data["receiver"],{"node":"b","port":"eth0"})
        self.assertEqual(data["sourceIpv4"],"192.0.2.10")
        self.assertEqual(data["destinationIpv4"],"203.0.113.20")
        self.assertEqual(data["initialTtl"],5)
        self.assertEqual(data["finalTtl"],4)
        self.assertFalse(data["icmpSent"])
        self.assertTrue(data["ephemeral"])
        self.assertEqual([s["node"] for s in data["steps"]],["a","r"])
        self.assertEqual([s["ttlSent"] for s in data["steps"]],[5,4])
        self.assertEqual([s["arp"]["status"] for s in data["steps"]],["RESOLVED","RESOLVED"])
        self.assertEqual([s["nextHopIpv4"] for s in data["steps"]],
                         ["192.0.2.1","203.0.113.20"])
        self.assertEqual([[t["linkId"] for t in s["ipv4Transmissions"]] for s in data["steps"]],
                         [["la","lr1"],["lr2","lb"]])
        self.assertEqual(data["steps"][0]["route"]["type"],"STATIC")
        self.assertEqual(data["steps"][1]["route"]["type"],"CONNECTED")
        self.assertEqual(data["steps"][0]["ipv4Transmissions"][0]["vlanId"],10)
        self.assertEqual(data["steps"][1]["ipv4Transmissions"][0]["vlanId"],20)
        self.assertEqual(p,original)

    def test_same_subnet_direct_wire_with_ttl_one_delivers_without_router(self):
        p=lab()
        a=next(n for n in p["nodes"] if n["id"]=="a")
        a.pop("staticRoutes")
        getport(p,"a","eth0")["ipv4"]="203.0.113.10/24"
        # Use right-side broadcast domain only, cable physically rebuilt.
        p["links"] = [l for l in p["links"] if l["id"] not in ("la","lr1")]
        p["links"].append(link("host-cable","a","eth0","sw-left","a"))
        getport(p,"r","wan")["ipv4"]="203.0.113.1/24"
        # Instead, replace left-side switch->router wire with direct client b
        # by moving destination b onto left segment.
        p["links"]=[l for l in p["links"] if l["id"] != "lb"]
        p["links"].append(link("destination","sw-left","r","b","eth0"))
        getport(p,"b","eth0")["ipv4"]="203.0.113.20/24"
        output=IPv4Trace(p).send("a","eth0","203.0.113.20",1)
        self.assertEqual(output["status"],"DELIVERED")
        self.assertEqual(output["finalTtl"],1)
        self.assertEqual(len(output["steps"]),1)

    def test_ttl_one_expires_at_actual_router_ingress(self):
        result=IPv4Trace(lab()).send("a","eth0","203.0.113.20",1)
        self.assertEqual(result["status"],"TTL_EXPIRED")
        self.assertEqual([s["node"] for s in result["steps"]],["a"])
        self.assertEqual(result["receiver"],None)
        self.assertFalse(result["icmpSent"])
        self.assertEqual(result["steps"][0]["ipv4Transmissions"][0]["linkId"],"la")

    def test_multihop_forwarding_and_ttl_per_router(self):
        p=multihop()
        success=IPv4Trace(p).send("a","eth0","198.51.100.20",3)
        self.assertEqual(success["status"],"DELIVERED")
        self.assertEqual(success["finalTtl"],1)
        self.assertEqual([s["node"] for s in success["steps"]],["a","r","r2"])
        self.assertEqual([s["ttlSent"] for s in success["steps"]],[3,2,1])
        expired=IPv4Trace(p).send("a","eth0","198.51.100.20",2)
        self.assertEqual(expired["status"],"TTL_EXPIRED")
        self.assertEqual([s["node"] for s in expired["steps"]],["a","r"])
        self.assertEqual(expired["finalTtl"],1)
        self.assertFalse(expired["icmpSent"])

    def test_no_source_route_is_explicit_no_route_without_arp(self):
        p=lab()
        p["nodes"][0].pop("staticRoutes")
        result=IPv4Trace(p).send("a","eth0","203.0.113.20",5)
        self.assertEqual(result["status"],"NO_ROUTE")
        self.assertEqual(result["steps"],[])
        self.assertEqual(result["macTables"],[])

    def test_router_port_disabled_stops_further_forwarding(self):
        p=lab()
        getport(p,"r","lan")["enabled"]=False
        result=IPv4Trace(p).send("a","eth0","203.0.113.20",5)
        self.assertEqual(result["status"],"NO_ROUTE")
        self.assertEqual([s["node"] for s in result["steps"]],["a"])

    def test_vlan_isolation_prevents_arp_and_any_ipv4_frame(self):
        p=lab()
        getport(p,"sw-left","r")["vlan"]={"mode":"access","vlan":20}
        result=IPv4Trace(p).send("a","eth0","203.0.113.20",6)
        self.assertEqual(result["status"],"ARP_FAILED")
        self.assertEqual(result["steps"][0]["arp"]["status"],"NO_REPLY")
        self.assertEqual(result["steps"][0]["ipv4Transmissions"],[])
        self.assertEqual(result["receiver"],None)

    def test_link_down_prevents_next_hop_resolution(self):
        p=lab()
        p["links"][0]["enabled"]=False
        result=IPv4Trace(p).send("a","eth0","203.0.113.20",5)
        self.assertEqual(result["status"],"ARP_FAILED")
        self.assertEqual(result["steps"][0]["arp"]["status"],"NO_ACTIVE_LINK")
        self.assertEqual(result["steps"][0]["ipv4Transmissions"],[])

    def test_unbound_next_hop_mac_is_not_guessed(self):
        p=lab()
        getport(p,"r","wan").pop("mac")
        result=IPv4Trace(p).send("a","eth0","203.0.113.20",5)
        self.assertEqual(result["status"],"ARP_FAILED")
        self.assertEqual(result["steps"][0]["arp"]["status"],"UNKNOWN")
        self.assertEqual(result["steps"][0]["ipv4Transmissions"],[])

    def test_nonrouter_next_hop_does_not_forward(self):
        p=lab()
        router=next(n for n in p["nodes"] if n["id"]=="r")
        router["kind"]="host"
        result=IPv4Trace(p).send("a","eth0","203.0.113.20",6)
        self.assertEqual(result["status"],"NON_ROUTER")
        self.assertEqual([s["node"] for s in result["steps"]],["a"])

    def test_wrong_explicit_source_port_does_not_change_egress(self):
        p=lab()
        a=next(n for n in p["nodes"] if n["id"]=="a")
        a["ports"].append({"id":"eth1","name":"eth1","enabled":True,
                           "ipv4":"198.51.100.10/24","mac":"02:00:00:00:00:0C"})
        result=IPv4Trace(p).send("a","eth1","203.0.113.20",8)
        self.assertEqual(result["status"],"SOURCE_INTERFACE_MISMATCH")
        self.assertEqual(result["steps"],[])

    def test_duplicate_equally_specific_route_never_guess(self):
        p=lab()
        p["nodes"][0]["staticRoutes"].append({
            "id":"extra","destination":"203.0.113.0/24",
            "nextHop":"192.0.2.2","outPort":"eth0"})
        result=IPv4Trace(p).send("a","eth0","203.0.113.20",8)
        self.assertEqual(result["status"],"AMBIGUOUS_ROUTE")
        self.assertEqual(result["steps"],[])

    def test_invalid_ip_ttl_identity_and_legacy_preservation(self):
        p=lab()
        for dest,ttl in (("bad",4),("203.0.113.20/24",4),
                         ("2001:db8::1",3),("203.0.113.20",0),
                         ("203.0.113.20",True),("203.0.113.20",256)):
            with self.subTest(dest=dest,ttl=ttl), self.assertRaises(ProjectValidationError):
                IPv4Trace(p).send("a","eth0",dest,ttl)
        with self.assertRaisesRegex(ProjectValidationError,"self-delivery"):
            IPv4Trace(p).send("a","eth0","192.0.2.10",10)
        for node_id,port in (("sw-left","a"),("missing","p"),("a","absent")):
            with self.subTest(node=node_id), self.assertRaises(ProjectValidationError):
                IPv4Trace(p).send(node_id,port,"203.0.113.20",5)
        self.assertEqual(p["schemaVersion"],"1.3")
        self.assertNotIn("icmp",json.dumps(p).lower())

    def test_failed_topology_validation_cannot_be_evaded(self):
        p=lab()
        p["links"].append(link("implicit","a","eth0","r","wan"))
        with self.assertRaises(ProjectValidationError):
            IPv4Trace(p)
        p=lab()
        getport(p,"sw-left","r")["vlan"]=None
        with self.assertRaises(ProjectValidationError):
            IPv4Trace(p)


class IPv4HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def request(self,data):
        req=Request(self.base+"/api/ipv4/trace",data=json.dumps(data).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=5) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as err:
            return err.code,json.loads(err.read())

    def body(self,p=None,ttl=4,dest="203.0.113.20"):
        return {"project":p or lab(),"sourceNode":"a","sourcePort":"eth0",
                "destinationIpv4":dest,"ttl":ttl}

    def test_real_loopback_http_two_subnets_full_delivery(self):
        p=lab()
        original=copy.deepcopy(p)
        status,output=self.request(self.body(p))
        self.assertEqual(status,200)
        self.assertEqual(output["status"],"DELIVERED")
        self.assertEqual(output["receiver"],{"node":"b","port":"eth0"})
        self.assertEqual([s["node"] for s in output["steps"]],["a","r"])
        self.assertEqual(p,original)
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_http_real_ttl_expiration_and_vlan_drop(self):
        status,output=self.request(self.body(ttl=1))
        self.assertEqual(status,200)
        self.assertEqual(output["status"],"TTL_EXPIRED")
        p=lab()
        getport(p,"sw-left","r")["vlan"]={"mode":"access","vlan":20}
        status,output=self.request(self.body(p))
        self.assertEqual(status,200)
        self.assertEqual(output["status"],"ARP_FAILED")
        self.assertEqual(output["steps"][0]["ipv4Transmissions"],[])

    def test_http_bad_requests_422_never_success(self):
        base=self.body()
        for bad in (
            {k:v for k,v in base.items() if k!="ttl"},
            {**base,"extra":1},
            {**base,"ttl":True},
            {**base,"ttl":256},
            {**base,"sourceNode":"missing"},
            {**base,"destinationIpv4":"192.0.2.1/24"},
            ["not","an","IPv4 query"],
        ):
            with self.subTest(bad=str(bad)[:100]):
                status,body=self.request(bad)
                self.assertEqual(status,422)
                self.assertEqual(body["error"],"INVALID_PROJECT")
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_api_never_mutates_save_open_bytes_or_sessions(self):
        p=lab()
        saved=self.server.store.save("document",p)
        raw=(self.root/"document.yadilab").read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        self.assertEqual(saved["sha256"],sha)
        for _ in range(2):
            status,result=self.request(self.body(p))
            self.assertEqual(status,200)
            self.assertEqual(result["steps"][0]["arp"]["status"],"RESOLVED")
        self.assertEqual(raw,(self.root/"document.yadilab").read_bytes())
        self.assertEqual(self.server.store.read("document")["sha256"],sha)


if __name__=="__main__":
    unittest.main()
