"""Minimal IPv4 datagram codec (RFC 791 header, no options/fragmentation).

Protocol 253 is an experimental opaque payload, NOT ICMP, TCP or UDP.
We model no transport, host reply, NAT, IP fragmentation or ICMP errors.
"""
from __future__ import annotations

import ipaddress
import struct
from dataclasses import dataclass

from .model import ProjectValidationError

_HEADER = struct.Struct("!BBHHHBBH4s4s")
EXPERIMENTAL_PROTOCOL = 253


def checksum(data: bytes) -> int:
    if type(data) is not bytes or len(data) % 2:
        raise ProjectValidationError("ipv4: checksum input must be even-length bytes")
    words = sum(int.from_bytes(data[i:i + 2], "big") for i in range(0, len(data), 2))
    while words > 0xFFFF:
        words = (words & 0xFFFF) + (words >> 16)
    return (~words) & 0xFFFF


def _ip(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ProjectValidationError(f"ipv4: {label} must be a canonical IPv4 address")
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        raise ProjectValidationError(f"ipv4: {label} must be a canonical IPv4 address") from None
    if (str(address) != value or address.is_unspecified or address.is_multicast or
            address.is_reserved or int(address) == 0xFFFFFFFF):
        raise ProjectValidationError(f"ipv4: {label} must be a usable canonical unicast IPv4")
    return value


@dataclass(frozen=True)
class IPv4Datagram:
    source: str
    destination: str
    ttl: int
    payload: bytes = b""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _ip(self.source, "source"))
        object.__setattr__(self, "destination", _ip(self.destination, "destination"))
        if type(self.ttl) is not int or not 1 <= self.ttl <= 255:
            raise ProjectValidationError("ipv4: TTL must be an integer 1..255")
        if type(self.payload) is not bytes or len(self.payload) > 1480:
            raise ProjectValidationError("ipv4: payload must be bytes of length 0..1480")

    def serialize(self) -> bytes:
        head = _HEADER.pack(
            0x45, 0, 20 + len(self.payload), 0, 0, self.ttl,
            EXPERIMENTAL_PROTOCOL, 0,
            ipaddress.IPv4Address(self.source).packed,
            ipaddress.IPv4Address(self.destination).packed,
        )
        head = head[:10] + checksum(head).to_bytes(2, "big") + head[12:]
        return head + self.payload

    @classmethod
    def parse(cls, data: bytes) -> "IPv4Datagram":
        if type(data) is not bytes or len(data) < 20:
            raise ProjectValidationError("ipv4: truncated datagram")
        version, tos, total, identification, flags, ttl, protocol, crc, src, dst = _HEADER.unpack(data[:20])
        if (version, tos, identification, flags, protocol) != (
                0x45, 0, 0, 0, EXPERIMENTAL_PROTOCOL):
            raise ProjectValidationError("ipv4: unsupported header, options, fragmentation or protocol")
        if not 20 <= total <= len(data) or any(data[total:]):
            raise ProjectValidationError("ipv4: invalid total length or nonzero Ethernet padding")
        if checksum(data[:20]) != 0:
            raise ProjectValidationError("ipv4: invalid header checksum")
        return cls(str(ipaddress.IPv4Address(src)), str(ipaddress.IPv4Address(dst)),
                   ttl, data[20:total])

    def forwarded(self) -> "IPv4Datagram":
        if self.ttl <= 1:
            raise ProjectValidationError("ipv4: packet TTL exhausted at forwarding router")
        return IPv4Datagram(self.source, self.destination, self.ttl - 1, self.payload)
