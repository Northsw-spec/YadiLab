"""RFC 792 ICMP router errors: strictly bounded Time Exceeded / Net Unreachable.

Implements *only* type 11 code 0 (TTL in transit) and type 3 code 0
(network unreachable at transit router). Each message quotes the original
20-byte IPv4 header and 8 bytes of data, never a fabricated network event.
"""
from __future__ import annotations

import ipaddress
import struct
from dataclasses import dataclass

from .ipv4_packet import ICMP_PROTOCOL, EXPERIMENTAL_PROTOCOL, checksum
from .model import ProjectValidationError

ICMP_TIME_EXCEEDED = 11
ICMP_DEST_UNREACHABLE = 3
ICMP_NET_UNREACHABLE = 0
ICMP_TTL_EXPIRED = 0
_ERROR_HEADER = struct.Struct("!BBH4s")


@dataclass(frozen=True)
class ICMPError:
    icmp_type: int
    code: int
    quoted_ipv4: bytes

    def __post_init__(self) -> None:
        if type(self.icmp_type) is not int or self.icmp_type not in (
                ICMP_TIME_EXCEEDED, ICMP_DEST_UNREACHABLE):
            raise ProjectValidationError("icmp: only router Time Exceeded and Network Unreachable supported")
        if type(self.code) is not int or self.code != 0:
            raise ProjectValidationError("icmp: only code zero is modeled for these errors")
        if type(self.quoted_ipv4) is not bytes or len(self.quoted_ipv4) != 28:
            raise ProjectValidationError("icmp: quoted IPv4 must have 20-byte header and first eight data bytes")
        quoted = self.quoted_ipv4
        if quoted[0] != 0x45 or quoted[1] != 0 or checksum(quoted[:20]) != 0:
            raise ProjectValidationError("icmp: original quoted IPv4 header invalid")
        total = int.from_bytes(quoted[2:4], "big")
        if total < 28 or total > 1500 or quoted[6:8] != b"\x00\x00":
            raise ProjectValidationError("icmp: original quoted IPv4 length/fragment unsupported")
        if quoted[9] not in (EXPERIMENTAL_PROTOCOL, ICMP_PROTOCOL):
            raise ProjectValidationError("icmp: original protocol not supported")
        if quoted[9] == ICMP_PROTOCOL and quoted[20] in (ICMP_TIME_EXCEEDED, ICMP_DEST_UNREACHABLE):
            raise ProjectValidationError("icmp: do not generate errors in response to ICMP errors")
        for offset in (12, 16):
            address = ipaddress.IPv4Address(quoted[offset:offset + 4])
            if address.is_unspecified or address.is_multicast or address.is_reserved:
                raise ProjectValidationError("icmp: unusable original IPv4 source/destination")

    def serialize(self) -> bytes:
        message = _ERROR_HEADER.pack(self.icmp_type, self.code, 0, b"\x00" * 4) + self.quoted_ipv4
        return message[:2] + checksum(message).to_bytes(2, "big") + message[4:]

    @classmethod
    def parse(cls, raw: bytes) -> "ICMPError":
        if type(raw) is not bytes or len(raw) != 36:
            raise ProjectValidationError("icmp: error requires exactly 36 bytes (8 + 20 + 8)")
        kind, code, crc, reserved = _ERROR_HEADER.unpack(raw[:8])
        if reserved != b"\x00" * 4 or checksum(raw) != 0:
            raise ProjectValidationError("icmp: invalid unused field or ICMP checksum")
        return cls(kind, code, raw[8:])

    @property
    def quoted_source(self) -> str:
        return str(ipaddress.IPv4Address(self.quoted_ipv4[12:16]))

    @property
    def quoted_destination(self) -> str:
        return str(ipaddress.IPv4Address(self.quoted_ipv4[16:20]))

    @property
    def quoted_protocol(self) -> int:
        return self.quoted_ipv4[9]


def parse_icmp_message(raw: bytes):
    """Accept only explicitly implemented Echo or router-error types."""
    if type(raw) is not bytes or not raw:
        raise ProjectValidationError("icmp: missing protocol data")
    if raw[0] in (ICMP_TIME_EXCEEDED, ICMP_DEST_UNREACHABLE):
        return ICMPError.parse(raw)
    from .icmp import ICMPEcho
    return ICMPEcho.parse(raw)
