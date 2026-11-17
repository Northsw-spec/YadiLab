"""Strict Ethernet II codec with optional single 802.1Q tag (no FCS).

Only one C-tag with PCP=0 and DEI=0 is supported. QinQ, priority-tagged
VID 0, reserved VID 4095 and protocol payload decoding are unsupported.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .model import ProjectValidationError

_MAC_FORMAT = re.compile(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$")
BROADCAST = "FF:FF:FF:FF:FF:FF"
VLAN_TPID = 0x8100
_RESERVED_TAGS = {VLAN_TPID, 0x88A8, 0x9100}


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


def validate_vlan_id(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 4094:
        raise ProjectValidationError("vlan: VLAN ID must be an integer 1..4094")
    return value


def _ether_type(value: int) -> int:
    # IEEE 802.3 lengths are <=1500, 1501..1535 undefined, 1536+ EtherType.
    if type(value) is not int or not 0x0600 <= value <= 0xFFFF:
        raise ProjectValidationError("frame: EtherType must be an integer 0x0600..0xFFFF")
    if value in _RESERVED_TAGS:
        raise ProjectValidationError("frame: nested 802.1Q/802.1ad or unsupported tags")
    return value


@dataclass(frozen=True)
class EthernetFrame:
    """Immutable Ethernet II header and opaque payload, without FCS.

    vlan_id=None is untagged. An integer VLAN ID creates a single 0x8100 C-tag
    with zero PCP/DEI. Original wire padding remains opaque after parsing.
    """

    destination: str
    source: str
    ether_type: int
    payload: bytes
    vlan_id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "destination", normalize_mac(self.destination, source=False))
        object.__setattr__(self, "source", normalize_mac(self.source, source=True))
        _ether_type(self.ether_type)
        if self.vlan_id is not None:
            validate_vlan_id(self.vlan_id)
        if type(self.payload) is not bytes or len(self.payload) > 1500:
            raise ProjectValidationError("frame: payload must be bytes of length 0..1500")

    def serialize(self) -> bytes:
        """Create 60..1514 (untagged) or 60..1518 (tagged) bytes, excluding FCS."""
        header = (bytes.fromhex(self.destination.replace(":", ""))
                  + bytes.fromhex(self.source.replace(":", "")))
        if self.vlan_id is None:
            header += self.ether_type.to_bytes(2, "big")
            minimum_payload = 46
        else:
            header += (VLAN_TPID.to_bytes(2, "big")
                       + self.vlan_id.to_bytes(2, "big")
                       + self.ether_type.to_bytes(2, "big"))
            minimum_payload = 42
        return header + self.payload.ljust(minimum_payload, b"\x00")

    @classmethod
    def parse(cls, raw: bytes) -> EthernetFrame:
        """Parse only the supported Ethernet II C-tag format, without FCS."""
        if type(raw) is not bytes or not 60 <= len(raw) <= 1518:
            raise ProjectValidationError("frame: Ethernet II bytes without FCS must be length 60..1518")
        outer = int.from_bytes(raw[12:14], "big")
        if outer == VLAN_TPID:
            tci = int.from_bytes(raw[14:16], "big")
            if tci & 0xF000:
                raise ProjectValidationError("frame: PCP and DEI are unsupported; require zero")
            vlan_id = validate_vlan_id(tci & 0x0FFF)
            inner = int.from_bytes(raw[16:18], "big")
            payload = raw[18:]
        else:
            if len(raw) > 1514:
                raise ProjectValidationError("frame: untagged frame exceeds 1514 bytes without FCS")
            vlan_id = None
            inner = outer
            payload = raw[14:]
        _ether_type(inner)
        return cls(
            destination=raw[0:6].hex(":"),
            source=raw[6:12].hex(":"),
            ether_type=inner,
            payload=payload,
            vlan_id=vlan_id,
        )
