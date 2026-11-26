"""Independent Ethernet end-device and access-switch actors."""

from dataclasses import dataclass
from typing import NamedTuple

from ..events import MAX_TIME_NS, Event, EventType
from ..kernel import EventContext
from .codec import (
    ARP_TYPE, BROADCAST, ZERO_MAC, ARPMessage, ARPOperation, EthernetFrame, WireError, individual_mac,
)
from .config import AccessPort, HostSettings, SwitchSettings
from .transport import (
    TX_QUEUED, DropReason, Frame, PortAddress, drop, endpoint_drop, hop_drop, require_hop,
)

RESOLVE = EventType("arp/resolve")
ARP_EXPIRE = EventType("arp/expire")


class Neighbor(NamedTuple):
    ip: bytes
    mac: bytes


class Outstanding(NamedTuple):
    ip: bytes
    timer: int


class HostState(NamedTuple):
    # One host actor owns a single explicit interface in this slice.
    neighbors: tuple[Neighbor, ...] = ()
    pending: tuple[Outstanding, ...] = ()


@dataclass(frozen=True, slots=True)
class HostActor:
    settings: HostSettings

    @property
    def address(self) -> PortAddress:
        return PortAddress.from_endpoint(self.settings.endpoint)

    def _send(self, ctx: EventContext, destination: bytes, arp: ARPMessage) -> None:
        wire = EthernetFrame(destination, self.settings.mac, ARP_TYPE, arp.encode()).encode()
        ctx.schedule_after(TX_QUEUED, self.address.target(), 0, Frame(ctx.event_sequence, self.address, wire))

    def resolve(self, event: Event, ctx: EventContext) -> None:
        target = event.payload
        if type(target) is not bytes or len(target) != 4:
            raise TypeError("Expected IPv4 address bytes")
        state = ctx.state if isinstance(ctx.state, HostState) else HostState()
        failure = endpoint_drop(ctx, self.address)
        if failure:
            drop(event, ctx, failure)
        elif target == self.settings.ip or not self.settings.accepts(target):
            drop(event, ctx, DropReason.NOT_FOR_INTERFACE)
        elif any(entry.ip == target for entry in (*state.neighbors, *state.pending)):
            return
        elif len(state.pending) >= self.settings.pending_limit:
            drop(event, ctx, DropReason.STATE_LIMIT)
        elif event.time_ns + self.settings.timeout_ns > MAX_TIME_NS:
            drop(event, ctx, DropReason.TIME_LIMIT)
        else:
            timer = ctx.schedule_after(ARP_EXPIRE, event.target, self.settings.timeout_ns, target)
            ctx.replace_state(state._replace(pending=(*state.pending, Outstanding(target, timer))))
            self._send(ctx, BROADCAST, ARPMessage(
                ARPOperation.REQUEST, self.settings.mac, self.settings.ip, ZERO_MAC, target,
            ))

    def expire(self, event: Event, ctx: EventContext) -> None:
        state = ctx.state
        if isinstance(state, HostState) and any(item.timer == ctx.event_sequence for item in state.pending):
            ctx.replace_state(state._replace(pending=tuple(
                item for item in state.pending if item.timer != ctx.event_sequence
            )))
            drop(event, ctx, DropReason.ARP_TIMEOUT)

    def receive(self, event: Event, ctx: EventContext) -> None:
        hop = require_hop(event.payload)
        failure = hop_drop(ctx, hop, stamped=True)
        if failure:
            drop(event, ctx, failure, hop)
            return
        frame = EthernetFrame.decode(hop.frame.wire)
        if frame.destination not in (self.settings.mac, BROADCAST):
            drop(event, ctx, DropReason.NOT_FOR_INTERFACE, hop)
            return
        if frame.ethertype != ARP_TYPE:
            drop(event, ctx, DropReason.UNSUPPORTED_PROTOCOL, hop)
            return
        try:
            arp = ARPMessage.decode(frame.payload)
        except WireError:
            drop(event, ctx, DropReason.INVALID_ARP, hop)
            return
        if (arp.sender_mac != frame.source or not individual_mac(arp.sender_mac)
                or not self.settings.accepts(arp.sender_ip) or arp.sender_ip == self.settings.ip):
            drop(event, ctx, DropReason.INVALID_ARP, hop)
            return
        if arp.target_ip != self.settings.ip:
            drop(event, ctx, DropReason.NOT_FOR_INTERFACE, hop)
            return
        if arp.operation is ARPOperation.REQUEST:
            self._send(ctx, arp.sender_mac, ARPMessage(
                ARPOperation.REPLY, self.settings.mac, self.settings.ip, arp.sender_mac, arp.sender_ip,
            ))
            return
        state = ctx.state if isinstance(ctx.state, HostState) else HostState()
        request = next((item for item in state.pending if item.ip == arp.sender_ip), None)
        if request is None or arp.target_mac != self.settings.mac or frame.destination != self.settings.mac:
            drop(event, ctx, DropReason.UNEXPECTED_ARP, hop)
            return
        ctx.cancel_timer(request.timer)
        # FIFO eviction bounds the cache. Only validated, solicited replies add entries.
        ctx.replace_state(HostState(
            (*state.neighbors[-(self.settings.cache_limit - 1):], Neighbor(arp.sender_ip, arp.sender_mac))
            if self.settings.cache_limit > 1 else (Neighbor(arp.sender_ip, arp.sender_mac),),
            tuple(item for item in state.pending if item != request),
        ))


class FDBEntry(NamedTuple):
    vlan: int
    mac: bytes
    port: str


class SwitchState(NamedTuple):
    fdb: tuple[FDBEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class SwitchActor:
    settings: SwitchSettings
    ports: tuple[AccessPort, ...]

    def receive(self, event: Event, ctx: EventContext) -> None:
        hop = require_hop(event.payload)
        failure = hop_drop(ctx, hop, stamped=True)
        if failure:
            drop(event, ctx, failure, hop)
            return
        frame = EthernetFrame.decode(hop.frame.wire)
        if frame.destination[0] & 1 and frame.destination != BROADCAST:
            drop(event, ctx, DropReason.UNSUPPORTED_PROTOCOL, hop)
            return
        state = ctx.state if isinstance(ctx.state, SwitchState) else SwitchState()
        ingress = hop.destination.port
        key = (hop.vlan, frame.source)
        entries = tuple(entry for entry in state.fdb if entry[:2] != key)
        entries = (*entries, FDBEntry(*key, ingress))
        entries = entries[-self.settings.fdb_limit:]
        ctx.replace_state(SwitchState(entries))
        alternatives = tuple(port for port in self.ports if port.endpoint.port_id != ingress)
        peers = tuple(port for port in alternatives if port.vlan == hop.vlan)
        known = next((entry.port for entry in entries if entry[:2] == (hop.vlan, frame.destination)), None)
        if known == ingress:
            drop(event, ctx, DropReason.NO_EGRESS_PORT, hop)
            return
        if known is not None:
            peers = tuple(port for port in peers if port.endpoint.port_id == known)
        if not peers:
            drop(event, ctx, DropReason.VLAN_BLOCKED if alternatives and known is None else
                 DropReason.NO_EGRESS_PORT, hop)
            return
        eligible = tuple(port for port in peers if not endpoint_drop(ctx, PortAddress.from_endpoint(port.endpoint)))
        if not eligible:
            drop(event, ctx, DropReason.PORT_DOWN, hop)
            return
        for port in eligible:
            ctx.schedule_after(TX_QUEUED, PortAddress.from_endpoint(port.endpoint).target(), 0, hop.frame)
