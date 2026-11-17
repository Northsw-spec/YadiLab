"""Bounded one-way IPv4 data-plane over the existing ARP/Ethernet fabric.

Each hop uses the canonical per-node routing table, actual simulated ARP
request/reply and a real Ethernet II frame with an RFC 791 IPv4 header.
Nothing here simulates an ICMP echo, transport service or return route.
"""
from __future__ import annotations

import ipaddress

from .arp import ArpSession
from .ethernet_frame import EthernetFrame
from .ipv4_packet import IPv4Datagram, _ip
from .model import ProjectValidationError
from .routing import ConnectedRoutingTable

MAX_FORWARDING_ROUTERS = 32


class IPv4Trace:
    """One bounded datagram delivery attempt sharing a single Layer-2 session."""

    def __init__(self, project: dict):
        self.arp = ArpSession(project)
        self.fabric = self.arp.fabric
        self.project = self.fabric.project
        self.nodes = self.fabric.nodes
        self.bound_macs = self.fabric.bound_macs()
        self.interfaces = {
            (n["id"], p["id"]): ipaddress.IPv4Interface(p["ipv4"])
            for n in self.project["nodes"] if n["kind"] != "switch"
            for p in n["ports"] if p["ipv4"] is not None
        }

    def send(self, source_node: str, source_port: str,
             destination_ipv4: str, ttl: int) -> dict:
        if not isinstance(source_node, str) or not isinstance(source_port, str):
            raise ProjectValidationError("ipv4: source must name an explicit node and port")
        endpoint = (source_node, source_port)
        node = self.nodes.get(source_node)
        if node is None or node["kind"] == "switch" or (
                source_port not in self.fabric.ports[source_node]):
            raise ProjectValidationError("ipv4: source must be a declared non-switch port")
        if endpoint not in self.interfaces or endpoint not in self.bound_macs:
            raise ProjectValidationError("ipv4: source requires explicit IPv4/CIDR and MAC")
        if not self.fabric.ports[source_node][source_port]["enabled"]:
            raise ProjectValidationError("ipv4: source interface disabled")
        dest = _ip(destination_ipv4, "destination")
        source_ip = str(self.interfaces[endpoint].ip)
        if dest == source_ip:
            raise ProjectValidationError("ipv4: self-delivery is not a wire forwarding operation")
        packet = IPv4Datagram(source_ip, dest, ttl)
        steps: list[dict] = []

        def finish(status: str, reason: str, receiver: tuple[str, str] | None = None) -> dict:
            return {
                "status": status, "meaning": reason,
                "sourceIpv4": packet.source,
                "destinationIpv4": packet.destination,
                "initialTtl": ttl, "finalTtl": packet.ttl,
                "receiver": {"node": receiver[0], "port": receiver[1]} if receiver else None,
                "steps": steps,
                "macTables": self.fabric.learned_mac_tables(),
                "ephemeral": True,
                "icmpSent": False,
            }

        for hop in range(MAX_FORWARDING_ROUTERS + 1):
            device_id, ingress_or_source_port = endpoint
            device = self.nodes[device_id]
            if hop and device["kind"] != "router":
                return finish("NON_ROUTER", "A non-router endpoint does not forward transit IPv4 packets.")
            if hop and packet.ttl <= 1:
                return finish("TTL_EXPIRED", "TTL became insufficient at a transit router; ICMP Time Exceeded is not implemented.")
            route = ConnectedRoutingTable(self.project, device_id).lookup(packet.destination)
            if route["status"] == "NO_ROUTE":
                return finish("NO_ROUTE", "The current node has no matching active configured IPv4 route.")
            if route["status"] == "AMBIGUOUS":
                return finish("AMBIGUOUS_ROUTE", "Equally specific routes exist; no route preference is invented.")
            chosen = route["selectedRoute"]
            out_port = chosen["outInterface"]["port"]
            if hop == 0 and out_port != source_port:
                return finish("SOURCE_INTERFACE_MISMATCH", "Chosen route exits another port; the supplied source interface cannot be silently replaced.")
            next_ip = chosen["nextHop"] if chosen["type"] == "STATIC" else packet.destination
            out_endpoint = (device_id, out_port)
            if out_endpoint not in self.bound_macs or out_endpoint not in self.interfaces:
                return finish("MISSING_INTERFACE_IDENTITY", "Selected output requires explicit MAC and IPv4 identity.")
            arp_result = self.arp.resolve(device_id, out_port, next_ip)
            step = {
                "node": device_id,
                "outPort": out_port,
                "route": chosen,
                "nextHopIpv4": next_ip,
                "arp": arp_result,
                "ttlSent": packet.ttl,
                "ipv4Transmissions": [],
                "vlanDrops": [],
            }
            steps.append(step)
            if arp_result["status"] not in ("RESOLVED", "CACHE_HIT"):
                return finish("ARP_FAILED", "Next-hop ARP did not resolve over actual enabled links and VLANs.")
            frame = EthernetFrame(arp_result["resolvedMac"],
                                  self.bound_macs[out_endpoint], 0x0800, packet.serialize())
            # Validate actual IP header/checksum and Ethernet serialization,
            # not just a fabricated status computed from route lookup.
            encoded = EthernetFrame.parse(frame.serialize())
            if IPv4Datagram.parse(encoded.payload) != packet:
                raise ProjectValidationError("ipv4: serialized datagram failed byte roundtrip")
            forwarded = self.fabric.inject_frame(device_id, out_port, frame)
            step["ipv4Transmissions"] = forwarded["transmissions"]
            step["vlanDrops"] = forwarded.get("vlanDrops", [])
            arrived = []
            for item in forwarded["endpointArrivals"]:
                peer = (item["node"], item["port"])
                # The EthernetFabric explicitly does not implement NIC
                # acceptance; only a matching configured unicast target is
                # accepted by this narrowly modeled IPv4 endpoint.
                if (self.bound_macs.get(peer) == frame.destination and
                        peer in self.interfaces and
                        str(self.interfaces[peer].ip) == next_ip and
                        self.fabric.ports[peer[0]][peer[1]]["enabled"]):
                    arrived.append(peer)
            if len(arrived) != 1:
                return finish("L2_NOT_DELIVERED",
                              "A matching configured next-hop NIC did not receive the IPv4 Ethernet frame.")
            endpoint = arrived[0]
            if str(self.interfaces[endpoint].ip) == dest:
                return finish("DELIVERED",
                              "Experimental IPv4 datagram reached the matching configured destination interface; no transport or reply simulated.",
                              endpoint)
            if self.nodes[endpoint[0]]["kind"] != "router":
                return finish("NON_ROUTER",
                              "The next-hop IP belongs to an endpoint without IPv4 transit forwarding.")
            if any(str(iface.ip) == dest for key, iface in self.interfaces.items()
                   if key[0] == endpoint[0]):
                return finish("LOCAL_DELIVERY_UNSUPPORTED",
                              "Destination IP belongs to a different interface on the router; weak-host local delivery is not modeled.")
            if packet.ttl <= 1:
                return finish("TTL_EXPIRED",
                              "TTL expired at router ingress; no ICMP Time Exceeded is generated.")
            packet = packet.forwarded()

        return finish("HOP_LIMIT", "Simulation router-hop limit reached; no delivery inferred.")
