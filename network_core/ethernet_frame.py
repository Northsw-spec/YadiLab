"""Strict, payload-opaque Ethernet II frames without FCS or VLAN support.

No protocol is decoded. In particular, an EtherType of IPv4 or ARP does not
imply that IP forwarding or ARP exists in this application.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .model import ProjectValidationError

_MAC_FORMAT = re.compile(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$")
BROADCAST = "FF:FF:FF:FF:FF:FF"
_UNSUPPORTED_TAGS = {0x8100, 0x88A8, 0x9100}


def normalize_mac(address: str, *, source: bool) -> str:
    """Require colon-delimited EUI-48; multicast destinations are unsupported."""
    if not isinstance(address, str) or not _MAC_FORMAT.fullmatch(address):
        raise ProjectValidationError("frame: MAC must contain six colon-separated hex octets")
    value = address.upper()
    if source and ((int(value[:2], 16) & 1) or value == "00:00:00:00:00:00"):
        raise ProjectValidationError("frame: source MAC must be nonzero unicast")
    if not source and value != BROADCAST and (int(value[:2], 16) & 1):
        raise ProjectValidationError("frame: destination multicast is not supported")
    return value


def _ether_type(value: int) -> int:
    # IEEE 802.3 lengths are <=1500, 1501..1535 are undefined; 1536+ EtherType.
    if type(value) is not int or not 0x0600 <= value <= 0xFFFF:
        raise ProjectValidationError("frame: EtherType must be an integer 0x0600..0xFFFF")
    if value in _UNSUPPORTED_TAGS:
        raise ProjectValidationError("frame: 802.1Q/802.1ad tags are not supported")
    return value


@dataclass(frozen=True)
class EthernetFrame:
    """Immutable Ethernet II header and opaque payload, excluding FCS.

    serialize() pads the payload to 46 octets. parse() preserves any wire
    padding as opaque bytes since protocol-specific length is not known.
    """

    destination: str
    source: str
    ether_type: int
    payload: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "destination", normalize_mac(self.destination, source=False))
        object.__setattr__(self, "source", normalize_mac(self.source, source=True))
        _ether_type(self.ether_type)
        if type(self.payload) is not bytes or len(self.payload) > 1500:
            raise ProjectValidationError("frame: payload must be bytes of length 0..1500")

    def serialize(self) -> bytes:
        """Build 60..1514 octet Ethernet II frame excluding FCS, no VLAN tags."""
        header = (bytes.fromhex(self.destination.replace(":", ""))
                  + bytes.fromhex(self.source.replace(":", ""))
                  + self.ether_type.to_bytes(2, "big"))
        return header + self.payload.ljust(46, b"\x00")

    @classmethod
    def parse(cls, raw: bytes) -> EthernetFrame:
        """Read complete Ethernet II bytes excluding FCS; reject ambiguous formats."""
        if type(raw) is not bytes or not 60 <= len(raw) <= 1514:
            raise ProjectValidationError("frame: Ethernet II bytes without FCS must be length 60..1514")
        ether_type = int.from_bytes(raw[12:14], "big")
        _ether_type(ether_type)
        return cls(
            destination=raw[0:6].hex(":"),
            source=raw[6:12].hex(":"),
            ether_type=ether_type,
            payload=raw[14:],
        )
