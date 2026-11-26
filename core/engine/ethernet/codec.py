"""Ethernet II wire frames and RFC 826 Ethernet/IPv4 messages."""

from binascii import crc32
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from struct import Struct

MIN_FRAME = 64
MAX_FRAME = 1518
MAX_PAYLOAD = 1500
ARP_TYPE = 0x0806
BROADCAST = b"\xff" * 6
ZERO_MAC = bytes(6)
_TAG_TYPES = (0x8100, 0x88A8, 0x9100)
_ARP = Struct("!HHBBH6s4s6s4s")


class WireErrorCode(StrEnum):
    INVALID_FRAME = "invalid-frame"
    INVALID_FCS = "invalid-fcs"
    UNSUPPORTED_FORMAT = "unsupported-format"
    INVALID_ARP = "invalid-arp"
    UNSUPPORTED_ARP = "unsupported-arp"


class WireError(ValueError):
    def __init__(self, code: WireErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def is_mac(value: object) -> bool:
    return type(value) is bytes and len(value) == 6


def individual_mac(value: bytes) -> bool:
    return is_mac(value) and value != ZERO_MAC and not value[0] & 1


@dataclass(frozen=True, slots=True)
class EthernetFrame:
    destination: bytes
    source: bytes
    ethertype: int
    payload: bytes

    def __post_init__(self) -> None:
        if (not is_mac(self.destination) or not individual_mac(self.source)
                or type(self.payload) is not bytes or len(self.payload) > MAX_PAYLOAD
                or type(self.ethertype) is not int or not 0 <= self.ethertype <= 0xffff):
            raise WireError(WireErrorCode.INVALID_FRAME)
        if self.ethertype < 0x0600 or self.ethertype in _TAG_TYPES:
            raise WireError(WireErrorCode.UNSUPPORTED_FORMAT)

    def encode(self) -> bytes:
        body = self.destination + self.source + self.ethertype.to_bytes(2, "big")
        body += self.payload.ljust(46, b"\0")
        return body + crc32(body).to_bytes(4, "little")

    @classmethod
    def decode(cls, wire: bytes) -> "EthernetFrame":
        if type(wire) is not bytes or not MIN_FRAME <= len(wire) <= MAX_FRAME:
            raise WireError(WireErrorCode.INVALID_FRAME)
        if crc32(wire[:-4]).to_bytes(4, "little") != wire[-4:]:
            raise WireError(WireErrorCode.INVALID_FCS)
        return cls(wire[:6], wire[6:12], int.from_bytes(wire[12:14], "big"), wire[14:-4])


class ARPOperation(IntEnum):
    REQUEST = 1
    REPLY = 2


@dataclass(frozen=True, slots=True)
class ARPMessage:
    operation: ARPOperation
    sender_mac: bytes
    sender_ip: bytes
    target_mac: bytes
    target_ip: bytes

    def __post_init__(self) -> None:
        if type(self.operation) is not ARPOperation:
            raise WireError(WireErrorCode.UNSUPPORTED_ARP)
        if (not is_mac(self.sender_mac) or not is_mac(self.target_mac)
                or any(type(ip) is not bytes or len(ip) != 4 for ip in (self.sender_ip, self.target_ip))):
            raise WireError(WireErrorCode.INVALID_ARP)

    def encode(self) -> bytes:
        return _ARP.pack(1, 0x0800, 6, 4, self.operation, self.sender_mac,
                         self.sender_ip, self.target_mac, self.target_ip)

    @classmethod
    def decode(cls, payload: bytes) -> "ARPMessage":
        # An untagged Ethernet/IPv4 ARP message is 28 bytes with up to 18 bytes
        # of media padding. Padding has no ARP meaning and need not be zero.
        if type(payload) is not bytes or not _ARP.size <= len(payload) <= 46:
            raise WireError(WireErrorCode.INVALID_ARP)
        hardware, protocol, hlen, plen, operation, *addresses = _ARP.unpack_from(payload)
        if (hardware, protocol) != (1, 0x0800):
            raise WireError(WireErrorCode.UNSUPPORTED_ARP)
        if (hlen, plen) != (6, 4):
            raise WireError(WireErrorCode.INVALID_ARP)
        try:
            op = ARPOperation(operation)
        except ValueError as exc:
            raise WireError(WireErrorCode.UNSUPPORTED_ARP) from exc
        return cls(op, *addresses)
