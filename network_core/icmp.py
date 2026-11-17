"""Strict ICMPv4 Echo (RFC 792) request/reply codec only.

Type 8/code 0 and type 0/code 0; no other ICMP types are modeled.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .ipv4_packet import checksum
from .model import ProjectValidationError

_ECHO_HEADER = struct.Struct("!BBHHH")
ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0


def _sum(data: bytes) -> int:
    return checksum(data + (b"\x00" if len(data) % 2 else b""))


@dataclass(frozen=True)
class ICMPEcho:
    icmp_type: int
    identifier: int
    sequence: int
    payload: bytes = b""

    def __post_init__(self) -> None:
        if type(self.icmp_type) is not int or self.icmp_type not in (ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY):
            raise ProjectValidationError("icmp: only Echo Request type 8 and Echo Reply type 0 are modeled")
        for name in ("identifier", "sequence"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 65535:
                raise ProjectValidationError(f"icmp: {name} must be an integer 0..65535")
        if type(self.payload) is not bytes or len(self.payload) > 1472:
            raise ProjectValidationError("icmp: payload must be bytes of length 0..1472")

    def serialize(self) -> bytes:
        raw = _ECHO_HEADER.pack(self.icmp_type, 0, 0, self.identifier, self.sequence) + self.payload
        return raw[:2] + _sum(raw).to_bytes(2, "big") + raw[4:]

    @classmethod
    def parse(cls, raw: bytes) -> "ICMPEcho":
        if type(raw) is not bytes or not 8 <= len(raw) <= 1480:
            raise ProjectValidationError("icmp: Echo message needs 8..1480 bytes")
        icmp_type, code, crc, identifier, sequence = _ECHO_HEADER.unpack(raw[:8])
        if icmp_type not in (ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY) or code != 0:
            raise ProjectValidationError("icmp: only Echo Request/Reply with code zero is supported")
        if _sum(raw) != 0:
            raise ProjectValidationError("icmp: invalid Echo checksum")
        return cls(icmp_type, identifier, sequence, raw[8:])

    def reply(self) -> "ICMPEcho":
        if self.icmp_type != ICMP_ECHO_REQUEST:
            raise ProjectValidationError("icmp: only a received Echo Request can produce a reply")
        return ICMPEcho(ICMP_ECHO_REPLY, self.identifier, self.sequence, self.payload)
