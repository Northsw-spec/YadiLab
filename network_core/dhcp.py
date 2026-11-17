"""Bounded RFC 2131 DHCPDISCOVER/DHCPOFFER over explicit Ethernet and VLANs.

This is a single read-only simulation of an explicitly selected DHCP server
and proposed address, not a general DHCP service or an address allocator.
The bootstrap broadcast path needs 0.0.0.0 and 255.255.255.255, which are
intentionally rejected by the normal unicast IPv4Trace; this codec models
only DHCP UDP/IPv4 bootstrap broadcasts and reuses the ONE EthernetFabric.
"""
from __future__ import annotations

import ipaddress
import struct
from dataclasses import dataclass

from .ethernet import EthernetFabric
from .ethernet_frame import BROADCAST, EthernetFrame, normalize_mac
from .ipv4_packet import checksum
from .model import ProjectValidationError

_BOOTP = struct.Struct("!BBBBIHH4s4s4s4s16s64s128s")
_IPV4 = struct.Struct("!BBHHHBBH4s4s")
_UDP = struct.Struct("!HHHH")
_ZERO_IP = b"\x00" * 4
_COOKIE = b"\x63\x82\x53\x63"
_DISCOVER, _OFFER = 1, 2
_UDP_PROTOCOL = 17
_ETHER_IPV4 = 0x0800


def _fail(reason: str):
    raise ProjectValidationError("dhcp: " + reason)


def _address(value: str, field: str) -> str:
    if not isinstance(value, str):
        _fail(field + " must be a canonical IPv4 address")
    try:
        parsed = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        _fail(field + " must be a canonical IPv4 address")
    if (str(parsed) != value or parsed.is_unspecified or parsed.is_multicast
            or parsed.is_reserved or parsed == ipaddress.IPv4Address("255.255.255.255")):
        _fail(field + " must be a usable canonical unicast IPv4")
    return value


def _mask(value: str) -> str:
    if not isinstance(value, str):
        _fail("subnet mask must be an IPv4 dotted netmask")
    try:
        raw = ipaddress.IPv4Address(value)
        network = ipaddress.IPv4Network("0.0.0.0/" + str(raw))
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
        _fail("invalid contiguous subnet mask")
    if str(raw) != value or not 1 <= network.prefixlen <= 30:
        _fail("subnet mask must represent prefix /1../30")
    return value


@dataclass(frozen=True)
class DhcpMessage:
    """Restricted BOOTP/DHCP wire payload: message type 1 or 2, broadcast flag.

    The offered address is never installed in the client's canonical port.
    No DHCPREQUEST, DHCPACK, relay, lease database or option overload.
    """
    message_type: int
    transaction_id: int
    client_mac: str
    offered_address: str | None = None
    server_identifier: str | None = None
    subnet_mask: str | None = None
    lease_seconds: int | None = None

    def __post_init__(self):
        if type(self.message_type) is not int or self.message_type not in (_DISCOVER, _OFFER):
            _fail("only DISCOVER (1) and OFFER (2) supported")
        if type(self.transaction_id) is not int or not 1 <= self.transaction_id <= 0xFFFFFFFF:
            _fail("transaction ID must be an integer 1..4294967295")
        object.__setattr__(self, "client_mac", normalize_mac(self.client_mac, source=True))
        properties = (self.offered_address, self.server_identifier,
                      self.subnet_mask, self.lease_seconds)
        if self.message_type == _DISCOVER:
            if any(x is not None for x in properties):
                _fail("DISCOVER cannot contain a proposed offer")
        else:
            if any(x is None for x in properties):
                _fail("OFFER requires address, server identifier, subnet mask and lease")
            object.__setattr__(self, "offered_address",
                               _address(self.offered_address, "offered IPv4"))
            object.__setattr__(self, "server_identifier",
                               _address(self.server_identifier, "server identifier"))
            object.__setattr__(self, "subnet_mask", _mask(self.subnet_mask))
            if type(self.lease_seconds) is not int or not 60 <= self.lease_seconds <= 604800:
                _fail("lease time must be an integer 60..604800 seconds")

    def serialize(self) -> bytes:
        client = bytes.fromhex(self.client_mac.replace(":", ""))
        yiaddr = (ipaddress.IPv4Address(self.offered_address).packed
                  if self.message_type == _OFFER else _ZERO_IP)
        header = _BOOTP.pack(
            1 if self.message_type == _DISCOVER else 2, 1, 6, 0,
            self.transaction_id, 0, 0x8000, _ZERO_IP, yiaddr, _ZERO_IP,
            _ZERO_IP, client.ljust(16, b"\x00"), bytes(64), bytes(128),
        )
        options = bytes((53, 1, self.message_type))
        if self.message_type == _OFFER:
            options += (bytes((54, 4)) + ipaddress.IPv4Address(self.server_identifier).packed
                        + bytes((1, 4)) + ipaddress.IPv4Address(self.subnet_mask).packed
                        + bytes((51, 4)) + self.lease_seconds.to_bytes(4, "big"))
        # DHCP's documented minimum IP UDP payload is 300 bytes.
        return (header + _COOKIE + options + b"\xff").ljust(300, b"\x00")

    @classmethod
    def parse(cls, payload: bytes) -> "DhcpMessage":
        if type(payload) is not bytes or not 300 <= len(payload) <= 1472:
            _fail("DHCP payload must be 300..1472 bytes")
        (op, hardware, hlen, hops, xid, secs, flags, ci, yi, si, gi, ch,
         sname, file_name) = _BOOTP.unpack(payload[:236])
        if ((hardware, hlen, hops, secs, flags) != (1, 6, 0, 0, 0x8000)
                or ci != _ZERO_IP or si != _ZERO_IP or gi != _ZERO_IP
                or any(ch[6:]) or any(sname) or any(file_name)
                or payload[236:240] != _COOKIE):
            _fail("unsupported BOOTP fields, hardware, relay or magic cookie")
        options = {}
        position = 240
        found_end = False
        while position < len(payload):
            option = payload[position]
            position += 1
            if option == 0:
                continue
            if option == 255:
                found_end = True
                break
            if option not in (53, 54, 1, 51) or option in options:
                _fail("unsupported or duplicated DHCP option")
            if position >= len(payload):
                _fail("truncated DHCP option")
            length = payload[position]
            position += 1
            if position + length > len(payload):
                _fail("truncated DHCP option value")
            value = payload[position:position + length]
            position += length
            if length != (1 if option == 53 else 4):
                _fail("invalid DHCP option length")
            options[option] = value
        if not found_end or any(payload[position:]) or 53 not in options:
            _fail("missing DHCP end/type option or nonzero trailing bytes")
        kind = options[53][0]
        if (kind == _DISCOVER and (op != 1 or yi != _ZERO_IP or set(options) != {53})) or (
                kind == _OFFER and (op != 2 or set(options) != {53, 54, 1, 51})):
            _fail("BOOTP operation or DHCP options disagree")
        if kind not in (_DISCOVER, _OFFER):
            _fail("unsupported DHCP message type")
        return cls(
            kind, xid, ch[:6].hex(":"),
            str(ipaddress.IPv4Address(yi)) if kind == _OFFER else None,
            str(ipaddress.IPv4Address(options[54])) if kind == _OFFER else None,
            str(ipaddress.IPv4Address(options[1])) if kind == _OFFER else None,
            int.from_bytes(options[51], "big") if kind == _OFFER else None,
        )


def _sum_even(value: bytes) -> int:
    return checksum(value if len(value) % 2 == 0 else value + b"\x00")


def _datagram(message: DhcpMessage, source: str) -> bytes:
    # DHCP bootstrapping is the only explicitly allowed 0.0.0.0/broadcast
    # IPv4 use. Normal IPv4Trace's unicast routing rules remain unchanged.
    src = ipaddress.IPv4Address(source).packed
    dst = ipaddress.IPv4Address("255.255.255.255").packed
    source_port, destination_port = ((68, 67) if message.message_type == _DISCOVER
                                     else (67, 68))
    payload = message.serialize()
    udp_len = 8 + len(payload)
    udp = _UDP.pack(source_port, destination_port, udp_len, 0) + payload
    pseudo = src + dst + struct.pack("!BBH", 0, _UDP_PROTOCOL, udp_len)
    udp_crc = _sum_even(pseudo + udp) or 0xFFFF
    udp = udp[:6] + udp_crc.to_bytes(2, "big") + udp[8:]
    ipv4 = _IPV4.pack(0x45, 0, 20 + len(udp), 0, 0, 64,
                      _UDP_PROTOCOL, 0, src, dst)
    ipv4 = ipv4[:10] + checksum(ipv4).to_bytes(2, "big") + ipv4[12:]
    return ipv4 + udp


def _decode_datagram(frame: EthernetFrame) -> tuple[str, DhcpMessage]:
    if not isinstance(frame, EthernetFrame) or frame.destination != BROADCAST or (
            frame.ether_type != _ETHER_IPV4 or frame.vlan_id is not None):
        _fail("expected untagged Ethernet IPv4 limited broadcast")
    raw = frame.payload
    if len(raw) < 28:
        _fail("truncated IPv4/UDP datagram")
    version, tos, total, identification, flags, ttl, protocol, crc, src, dst = _IPV4.unpack(raw[:20])
    if ((version, tos, identification, flags, ttl, protocol) != (0x45, 0, 0, 0, 64, 17)
            or dst != b"\xff" * 4 or not 28 <= total <= len(raw)
            or any(raw[total:]) or checksum(raw[:20]) != 0):
        _fail("invalid limited broadcast IPv4 header, checksum or padding")
    src_port, dst_port, udp_len, udp_crc = _UDP.unpack(raw[20:28])
    if udp_len != total - 20 or not udp_crc:
        _fail("invalid UDP length or missing checksum")
    pseudo = src + dst + struct.pack("!BBH", 0, _UDP_PROTOCOL, udp_len)
    if _sum_even(pseudo + raw[20:total]) != 0:
        _fail("invalid UDP checksum")
    message = DhcpMessage.parse(raw[28:total])
    expected_ports = (68, 67) if message.message_type == _DISCOVER else (67, 68)
    if (src_port, dst_port) != expected_ports or (
            message.message_type == _DISCOVER and src != _ZERO_IP):
        _fail("DHCP message type, IPv4 source or UDP ports mismatch")
    if message.message_type == _OFFER and (
            str(ipaddress.IPv4Address(src)) != message.server_identifier):
        _fail("DHCPOFFER IPv4 source differs from server identifier")
    if frame.source != (message.client_mac if message.message_type == _DISCOVER else frame.source):
        _fail("DHCPDISCOVER Ethernet MAC differs from BOOTP chaddr")
    return str(ipaddress.IPv4Address(src)), message


def discover_offer(project: object, client_node: str, client_port: str,
                   server_node: str, server_port: str, proposed_ipv4: str,
                   transaction_id: int, lease_seconds: int) -> dict:
    """Run a read-only DISCOVER->OFFER, never install address or lease."""
    fabric = EthernetFabric(project)
    nodes, ports, macs = fabric.nodes, fabric.ports, fabric.bound_macs()
    client, server = (client_node, client_port), (server_node, server_port)
    if (not all(isinstance(x, str) for x in (*client, *server)) or
            client_node not in nodes or server_node not in nodes or
            client_port not in ports[client_node] or server_port not in ports[server_node]
            or client == server):
        _fail("client and server must be different declared interfaces")
    if nodes[client_node]["kind"] != "host" or nodes[server_node]["kind"] not in ("host", "router"):
        _fail("DHCP client must be a host and selected server a host/router")
    if client not in macs or server not in macs:
        _fail("client and server require explicit MAC addresses")
    if ports[client_node][client_port]["ipv4"] is not None:
        _fail("client must be unconfigured (IPv4 null); no implicit address replacement")
    server_address = ports[server_node][server_port]["ipv4"]
    if server_address is None:
        _fail("selected server interface requires explicit IPv4/CIDR")
    interface = ipaddress.IPv4Interface(server_address)
    if not 1 <= interface.network.prefixlen <= 30:
        _fail("DHCP offer requires a server subnet prefix /1../30")
    candidate = ipaddress.IPv4Address(_address(proposed_ipv4, "proposed IPv4"))
    if (candidate not in interface.network or candidate in
            (interface.network.network_address, interface.network.broadcast_address)):
        _fail("proposed address must be a usable host inside the selected server subnet")
    if any(p["ipv4"] is not None and ipaddress.IPv4Interface(p["ipv4"]).ip == candidate
           for node in fabric.project["nodes"] for p in node["ports"]):
        _fail("proposed address is already configured on a documented interface")
    discover = DhcpMessage(_DISCOVER, transaction_id, macs[client])
    offer = DhcpMessage(_OFFER, transaction_id, macs[client],
                        str(candidate), str(interface.ip),
                        str(interface.network.netmask), lease_seconds)

    sent = EthernetFrame(BROADCAST, macs[client], _ETHER_IPV4,
                         _datagram(discover, "0.0.0.0"))
    parsed = EthernetFrame.parse(sent.serialize())
    if _decode_datagram(parsed) != ("0.0.0.0", discover):
        _fail("DISCOVER serialization roundtrip failed")
    first = fabric.inject_frame(*client, parsed)

    def finish(status: str, reply: dict | None = None) -> dict:
        return {
            "status": status, "ephemeral": True,
            "meaning": {
                "NO_ACTIVE_LINK": "Client has no enabled outgoing physical link.",
                "DISCOVER_NOT_RECEIVED": "Selected server did not receive the broadcast through the declared Layer-2 fabric.",
                "OFFER_NOT_RECEIVED": "Server sent a DHCPOFFER but the original client interface did not receive it.",
                "OFFER_RECEIVED": "Real encoded DHCPDISCOVER and DHCPOFFER traversed the modeled Ethernet/VLAN fabric; address NOT assigned.",
            }[status],
            "offeredIpv4": str(candidate) if status == "OFFER_RECEIVED" else None,
            "subnetMask": str(interface.network.netmask) if status == "OFFER_RECEIVED" else None,
            "serverIdentifier": str(interface.ip) if status == "OFFER_RECEIVED" else None,
            "transactionId": transaction_id,
            "discover": {
                "transmissions": first["transmissions"],
                "vlanDrops": first.get("vlanDrops", []),
                "receivedAtServer": {"node": server_node, "port": server_port} in first["endpointArrivals"],
            },
            "offer": {
                "transmissions": reply["transmissions"] if reply else [],
                "vlanDrops": reply.get("vlanDrops", []) if reply else [],
            },
            "macTables": fabric.learned_mac_tables(),
            "leaseCommitted": False,
        }

    if first["status"] == "NO_ACTIVE_LINK":
        return finish("NO_ACTIVE_LINK")
    if {"node": server_node, "port": server_port} not in first["endpointArrivals"]:
        return finish("DISCOVER_NOT_RECEIVED")
    # Only a server that actually received DISCOVER may generate this OFFER.
    sent_offer = EthernetFrame(BROADCAST, macs[server], _ETHER_IPV4,
                               _datagram(offer, str(interface.ip)))
    parsed_offer = EthernetFrame.parse(sent_offer.serialize())
    source_ip, response = _decode_datagram(parsed_offer)
    if (source_ip != str(interface.ip) or response != offer
            or response.transaction_id != discover.transaction_id
            or response.client_mac != discover.client_mac):
        _fail("OFFER serialization or transaction identity mismatch")
    second = fabric.inject_frame(*server, parsed_offer)
    if {"node": client_node, "port": client_port} not in second["endpointArrivals"]:
        return finish("OFFER_NOT_RECEIVED", second)
    return finish("OFFER_RECEIVED", second)
