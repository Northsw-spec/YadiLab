"""Narrow RFC 826 Ethernet/IPv4 ARP model over explicit Layer-2 forwarding.

ARP messages and cache exist only in a simulation session. Configured v1.1
project MACs can be used as explicit NIC identities. No MAC inference,
router forwarding, IPv6, VLAN, proxy-ARP or host IP data-plane is implemented.
"""
from __future__ import annotations

import ipaddress
import struct
from dataclasses import dataclass
from collections.abc import Mapping

from .ethernet import EthernetFabric
from .ethernet_frame import BROADCAST, EthernetFrame, normalize_mac
from .model import ProjectValidationError

ARP_ETHER_TYPE = 0x0806
_ZERO_MAC = "00:00:00:00:00:00"
_HEADER = struct.Struct("!HHBBH")


def _ipv4(value: str, where: str) -> str:
    if not isinstance(value, str):
        raise ProjectValidationError(f"arp: {where} must be an IPv4 address")
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        raise ProjectValidationError(f"arp: {where} must be an IPv4 address") from None
    if address.is_unspecified or address.is_multicast or int(address) == 0xFFFFFFFF:
        raise ProjectValidationError(f"arp: {where} must be a usable unicast IPv4 address")
    return str(address)


@dataclass(frozen=True)
class ArpMessage:
    """ARP over Ethernet for IPv4, 28 octets, excluding Ethernet padding.

    Requests require zero target hardware address. Replies require a concrete
    unicast target MAC. Unsupported hardware/protocol types are rejected.
    """

    operation: int
    sender_mac: str
    sender_ip: str
    target_mac: str
    target_ip: str

    def __post_init__(self) -> None:
        if type(self.operation) is not int or self.operation not in (1, 2):
            raise ProjectValidationError("arp: operation must be request (1) or reply (2)")
        object.__setattr__(self, "sender_mac", normalize_mac(self.sender_mac, source=True))
        object.__setattr__(self, "sender_ip", _ipv4(self.sender_ip, "sender IP"))
        object.__setattr__(self, "target_ip", _ipv4(self.target_ip, "target IP"))
        if self.operation == 1:
            if self.target_mac != _ZERO_MAC:
                raise ProjectValidationError("arp: request target MAC must be zero")
        else:
            object.__setattr__(self, "target_mac", normalize_mac(self.target_mac, source=True))

    def serialize(self) -> bytes:
        return (_HEADER.pack(1, 0x0800, 6, 4, self.operation)
                 + bytes.fromhex(self.sender_mac.replace(":", ""))
                 + ipaddress.IPv4Address(self.sender_ip).packed
                 + bytes.fromhex(self.target_mac.replace(":", ""))
                 + ipaddress.IPv4Address(self.target_ip).packed)

    @classmethod
    def parse(cls, payload: bytes) -> ArpMessage:
        if type(payload) is not bytes or len(payload) != 28:
            raise ProjectValidationError("arp: payload must be exactly 28 bytes")
        hardware, protocol, hlen, plen, op = _HEADER.unpack(payload[:8])
        if (hardware, protocol, hlen, plen) != (1, 0x0800, 6, 4):
            raise ProjectValidationError("arp: unsupported hardware/protocol address format")
        return cls(op, payload[8:14].hex(":"), str(ipaddress.IPv4Address(payload[14:18])),
                   payload[18:24].hex(":"), str(ipaddress.IPv4Address(payload[24:28])))

    def to_frame(self) -> EthernetFrame:
        dest = BROADCAST if self.operation == 1 else self.target_mac
        return EthernetFrame(dest, self.sender_mac, ARP_ETHER_TYPE, self.serialize())

    @classmethod
    def from_frame(cls, frame: EthernetFrame) -> ArpMessage:
        if not isinstance(frame, EthernetFrame) or frame.ether_type != ARP_ETHER_TYPE:
            raise ProjectValidationError("arp: Ethernet frame must have EtherType 0x0806")
        if frame.vlan_id is not None:
            raise ProjectValidationError("arp: tagged VLAN frames unsupported by isolated endpoint ARP")
        if len(frame.payload) < 28 or len(frame.payload) > 46 or any(frame.payload[28:]):
            raise ProjectValidationError("arp: unsupported trailing ARP payload or padding")
        message = cls.parse(frame.payload[:28])
        if message.sender_mac != frame.source:
            raise ProjectValidationError("arp: Ethernet and ARP sender MAC disagree")
        expected = BROADCAST if message.operation == 1 else message.target_mac
        if frame.destination != expected:
            raise ProjectValidationError("arp: Ethernet and ARP target MAC disagree")
        return message


class ArpSession:
    """Simulate one ARP exchange over the canonical declared Ethernet fabric.

    Only configured endpoint IPv4 interfaces with explicit session MACs can
    reply. ARP cache is session-only and replies require return wire delivery.
    """

    def __init__(self, project: dict, *, interface_macs: Mapping[tuple[str, str], str] | None = None):
        self.fabric = EthernetFabric(project, interface_macs=interface_macs)
        self._macs = self.fabric.bound_macs()
        self._ips: dict[tuple[str, str], ipaddress.IPv4Interface] = {}
        known_ips: dict[str, tuple[str, str]] = {}
        for node in self.fabric.project["nodes"]:
            if node["kind"] == "switch":
                continue
            for port in node["ports"]:
                if port["ipv4"] is None:
                    continue
                endpoint = (node["id"], port["id"])
                iface = ipaddress.IPv4Interface(port["ipv4"])
                address = str(iface.ip)
                if address in known_ips:
                    raise ProjectValidationError("arp: duplicate declared endpoint IPv4 address")
                known_ips[address] = endpoint
                self._ips[endpoint] = iface
        self._cache: dict[tuple[str, str], dict[str, str]] = {}

    def arp_table(self, node_id: str, port_id: str) -> dict[str, str]:
        endpoint = (node_id, port_id)
        if not isinstance(node_id, str) or not isinstance(port_id, str) or \
                node_id not in self.fabric.ports or port_id not in self.fabric.ports[node_id]:
            raise ProjectValidationError("arp: undeclared endpoint")
        return dict(sorted(self._cache.get(endpoint, {}).items()))

    def resolve(self, node_id: str, port_id: str, target_ipv4: str) -> dict:
        """Perform broadcast request and concrete reply; no IP packets or ping."""
        endpoint = (node_id, port_id)
        if not isinstance(node_id, str) or not isinstance(port_id, str) or \
                node_id not in self.fabric.ports or port_id not in self.fabric.ports[node_id]:
            raise ProjectValidationError("arp: undeclared source endpoint")
        if endpoint not in self._ips or endpoint not in self._macs:
            raise ProjectValidationError("arp: source requires explicit IPv4 and MAC configuration")
        target = _ipv4(target_ipv4, "requested IP")
        iface = self._ips[endpoint]
        if target == str(iface.ip):
            raise ProjectValidationError("arp: target is the source interface's own IP")
        if ipaddress.IPv4Address(target) not in iface.network:
            raise ProjectValidationError("arp: off-link resolution unsupported (no proxy ARP or routing)")
        if target in self._cache.get(endpoint, {}):
            return {"status": "CACHE_HIT", "resolvedMac": self._cache[endpoint][target],
                    "requestTransmissions": [], "replyTransmissions": [],
                    "meaning": "Previously resolved in this isolated ARP session; no new frames emitted."}

        request = ArpMessage(1, self._macs[endpoint], str(iface.ip), _ZERO_MAC, target)
        # Exercise the same strict byte codec used by external Ethernet II frames.
        request_frame = EthernetFrame.parse(request.to_frame().serialize())
        if ArpMessage.from_frame(request_frame) != request:
            raise ProjectValidationError("arp: inconsistent encoded request")
        dispatched = self.fabric.inject_frame(node_id, port_id, request_frame)
        if dispatched["status"] == "NO_ACTIVE_LINK":
            return {"status": "NO_ACTIVE_LINK", "resolvedMac": None,
                    "requestTransmissions": [], "replyTransmissions": [],
                    "meaning": "No enabled physical link at source; no ARP request was transmitted."}

        responders = []
        pending_unbound = False
        for arrival in dispatched["endpointArrivals"]:
            peer = (arrival["node"], arrival["port"])
            if peer == endpoint or peer not in self._ips or str(self._ips[peer].ip) != target:
                continue
            if peer not in self._macs:
                pending_unbound = True
                continue
            responders.append(peer)
        if len(responders) > 1:
            raise ProjectValidationError("arp: ambiguous duplicate responses")
        if not responders:
            return {"status": "UNKNOWN" if pending_unbound else "NO_REPLY",
                    "resolvedMac": None, "requestTransmissions": dispatched["transmissions"],
                    "replyTransmissions": [],
                    "meaning": ("Matching endpoint has no explicit MAC binding." if pending_unbound else
                                "No configured endpoint in the reached broadcast domain answered the ARP request.")}
        peer = responders[0]
        reply = ArpMessage(2, self._macs[peer], target, self._macs[endpoint], str(iface.ip))
        reply_frame = EthernetFrame.parse(reply.to_frame().serialize())
        if ArpMessage.from_frame(reply_frame) != reply:
            raise ProjectValidationError("arp: inconsistent encoded reply")
        response = self.fabric.inject_frame(peer[0], peer[1], reply_frame)
        if {"node": node_id, "port": port_id} not in response["endpointArrivals"]:
            return {"status": "NO_REPLY", "resolvedMac": None,
                    "requestTransmissions": dispatched["transmissions"],
                    "replyTransmissions": response["transmissions"],
                    "meaning": "ARP reply did not reach the requesting interface."}
        self._cache.setdefault(endpoint, {})[target] = self._macs[peer]
        return {"status": "RESOLVED", "resolvedMac": self._macs[peer],
                "requestTransmissions": dispatched["transmissions"],
                "replyTransmissions": response["transmissions"],
                "meaning": "Simulated ARP resolution over explicit Ethernet links, not IP reachability."}
