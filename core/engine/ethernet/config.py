"""Explicit access ports, link timing and host/switch settings."""

from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Interface

from ..config import ConfigError, Endpoint, require_id, require_type
from ..events import MAX_TIME_NS
from .codec import MAX_FRAME, individual_mac


def positive(value: int, label: str) -> None:
    if type(value) is not int or not 0 < value <= MAX_TIME_NS:
        raise ConfigError(f"Invalid {label}")


@dataclass(frozen=True, slots=True)
class AccessPort:
    endpoint: Endpoint
    vlan: int
    queue_limit: int

    def __post_init__(self) -> None:
        require_type(self.endpoint, Endpoint, "access endpoint")
        if type(self.vlan) is not int or not 1 <= self.vlan <= 4094:
            raise ConfigError("Invalid access VLAN")
        positive(self.queue_limit, "TX queue limit")


@dataclass(frozen=True, slots=True)
class LinkTiming:
    link_id: str
    rate_bps: int
    propagation_ns: int

    def __post_init__(self) -> None:
        require_id(self.link_id, "timed link ID")
        positive(self.rate_bps, "link rate")
        if type(self.propagation_ns) is not int or not 0 <= self.propagation_ns <= MAX_TIME_NS:
            raise ConfigError("Invalid propagation delay")

    def _duration(self, wire_octets: int, overhead: int) -> int:
        if type(wire_octets) is not int or not 1 <= wire_octets <= MAX_FRAME:
            raise ConfigError("Invalid transmission frame size")
        return ((wire_octets + overhead) * 8_000_000_000 + self.rate_bps - 1) // self.rate_bps

    def serialization_ns(self, wire_octets: int) -> int:
        return self._duration(wire_octets, 8)

    def slot_ns(self, wire_octets: int) -> int:
        return self._duration(wire_octets, 8 + 12)


@dataclass(frozen=True, slots=True)
class HostSettings:
    endpoint: Endpoint
    mac: bytes
    address: str
    cache_limit: int
    pending_limit: int
    timeout_ns: int

    def __post_init__(self) -> None:
        require_type(self.endpoint, Endpoint, "host endpoint")
        if not individual_mac(self.mac):
            raise ConfigError("Invalid host MAC")
        if type(self.address) is not str or "/" not in self.address:
            raise ConfigError("Host IPv4 configuration requires a prefix")
        try:
            interface = IPv4Interface(self.address)
        except ValueError as exc:
            raise ConfigError("Invalid host IPv4 interface") from exc
        if not self.accepts(interface.ip.packed):
            raise ConfigError("Host address must be a usable unicast IPv4 address")
        positive(self.cache_limit, "ARP cache limit")
        positive(self.pending_limit, "ARP outstanding limit")
        positive(self.timeout_ns, "ARP timeout")

    @property
    def ip(self) -> bytes:
        return IPv4Interface(self.address).ip.packed

    def accepts(self, packed: bytes) -> bool:
        candidate = IPv4Address(packed)
        subnet = IPv4Interface(self.address).network
        return (subnet.prefixlen <= 30 and candidate in subnet
                and candidate not in (subnet.network_address, subnet.broadcast_address)
                and not candidate.is_multicast and not candidate.is_unspecified
                and not candidate.is_loopback and not candidate.is_reserved)


@dataclass(frozen=True, slots=True)
class SwitchSettings:
    device_id: str
    fdb_limit: int

    def __post_init__(self) -> None:
        require_id(self.device_id, "switch ID")
        positive(self.fdb_limit, "FDB limit")
