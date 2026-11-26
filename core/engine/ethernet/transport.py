"""Port egress scheduling and physical link events on the shared kernel."""

from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple

from ..config import AdminState, Endpoint, PowerState
from ..events import MAX_TIME_NS, Event, EventTarget, EventType, EventValue, TargetKind
from ..kernel import EventContext
from ..runtime import OperState
from .codec import MAX_FRAME, EthernetFrame, WireError, WireErrorCode
from .config import AccessPort, LinkTiming

INJECT = EventType("ethernet/inject")
TX_QUEUED = EventType("ethernet/tx-queued")
TX_SERVICE = EventType("ethernet/tx-service")
TX_START = EventType("ethernet/tx-start")
SERIALIZED = EventType("ethernet/serialization-complete")
PROPAGATED = EventType("ethernet/propagation-complete")
RX_FRAME = EventType("ethernet/rx-frame")
PARSE = EventType("ethernet/parse")
PROCESS = EventType("ethernet/device-process")
DROP = EventType("ethernet/drop")
SET_OPER = EventType("ethernet/set-oper")
SET_POWER = EventType("ethernet/set-power")


class DropReason(StrEnum):
    PORT_DOWN = "port-down"
    LINK_DOWN = "link-down"
    DEVICE_OFF = "device-off"
    INVALID_FCS = "invalid-fcs"
    INVALID_FRAME = "invalid-frame"
    VLAN_BLOCKED = "vlan-blocked"
    NO_EGRESS_PORT = "no-egress-port"
    QUEUE_FULL = "queue-full"
    UNSUPPORTED_PROTOCOL = "unsupported-protocol"
    INVALID_ARP = "invalid-arp"
    UNEXPECTED_ARP = "unexpected-arp"
    NOT_FOR_INTERFACE = "not-for-interface"
    STATE_LIMIT = "state-limit"
    TIME_LIMIT = "time-limit"
    ARP_TIMEOUT = "arp-timeout"


class PortAddress(NamedTuple):
    device: str
    port: str

    @classmethod
    def from_endpoint(cls, endpoint: Endpoint) -> "PortAddress":
        return cls(endpoint.device_id, endpoint.port_id)

    def endpoint(self) -> Endpoint:
        return Endpoint(self.device, self.port)

    def target(self) -> EventTarget:
        return EventTarget(TargetKind.PORT, self.device, self.port)


class Frame(NamedTuple):
    frame_id: int
    origin: PortAddress
    wire: bytes

    @property
    def ethertype(self) -> int | None:
        return int.from_bytes(self.wire[12:14], "big") if len(self.wire) >= 14 else None


class Hop(NamedTuple):
    frame: Frame
    source: PortAddress
    destination: PortAddress
    link_id: str
    vlan: int
    epochs: tuple[int, int, int, int, int] = (0, 0, 0, 0, 0)


class Drop(NamedTuple):
    reason: DropReason
    frame: Frame | None
    hop: Hop | None
    vlan: int | None


class TransmitQueue(NamedTuple):
    waiting: tuple[Hop, ...] = ()
    ready_ns: int = 0
    scheduled: bool = False


def device_target(device_id: str) -> EventTarget:
    return EventTarget(TargetKind.DEVICE, device_id)


def link_target(link_id: str) -> EventTarget:
    return EventTarget(TargetKind.LINK, link_id)


def drop(event: Event, ctx: EventContext, reason: DropReason, evidence: Hop | Frame | None = None,
         vlan: int | None = None) -> None:
    hop = evidence if isinstance(evidence, Hop) else None
    frame = evidence if isinstance(evidence, Frame) else None
    if vlan is None and hop is not None:
        vlan = hop.vlan
    ctx.schedule_after(DROP, event.target, 0, Drop(reason, frame, hop, vlan))


def observe_drop(event: Event, ctx: EventContext) -> None:
    if not isinstance(event.payload, Drop):
        raise TypeError("Expected drop evidence")


def set_oper(event: Event, ctx: EventContext) -> None:
    state = OperState(event.payload)
    target = event.target
    if state is OperState.UP and target.kind is TargetKind.PORT:
        if ctx.device(target.object_id).power is not PowerState.ON:
            drop(event, ctx, DropReason.DEVICE_OFF)
            return
        if ctx.port(Endpoint(target.object_id, target.port_id)).admin_state is AdminState.DOWN:
            drop(event, ctx, DropReason.PORT_DOWN)
            return
    ctx.set_oper_state(state)


def set_power(event: Event, ctx: EventContext) -> None:
    ctx.set_power(PowerState(event.payload))


def endpoint_drop(ctx: EventContext, port: PortAddress) -> DropReason | None:
    if ctx.device(port.device).power is not PowerState.ON:
        return DropReason.DEVICE_OFF
    if ctx.port(port.endpoint()).oper_state is not OperState.UP:
        return DropReason.PORT_DOWN
    return None


def require_hop(payload: EventValue) -> Hop:
    if not isinstance(payload, Hop):
        raise TypeError("Expected a physical frame hop")
    return payload


def epochs(ctx: EventContext, hop: Hop) -> tuple[int, int, int, int, int]:
    return (ctx.device(hop.source.device).epoch, ctx.device(hop.destination.device).epoch,
            ctx.port(hop.source.endpoint()).epoch, ctx.port(hop.destination.endpoint()).epoch,
            ctx.link(hop.link_id).epoch)


def hop_drop(ctx: EventContext, hop: Hop, *, stamped: bool) -> DropReason | None:
    if ctx.link(hop.link_id).oper_state is not OperState.UP:
        return DropReason.LINK_DOWN
    failure = endpoint_drop(ctx, hop.source) or endpoint_drop(ctx, hop.destination)
    if failure or not stamped:
        return failure
    current = epochs(ctx, hop)
    if current[4] != hop.epochs[4]:
        return DropReason.LINK_DOWN
    if current[:2] != hop.epochs[:2]:
        return DropReason.DEVICE_OFF
    if current[2:4] != hop.epochs[2:4]:
        return DropReason.PORT_DOWN
    return None


@dataclass(frozen=True, slots=True)
class PortActor:
    settings: AccessPort
    peer: PortAddress | None
    timing: LinkTiming | None

    @property
    def address(self) -> PortAddress:
        return PortAddress.from_endpoint(self.settings.endpoint)

    def _queue(self, ctx: EventContext) -> TransmitQueue:
        return ctx.state if isinstance(ctx.state, TransmitQueue) else TransmitQueue()

    def inject(self, event: Event, ctx: EventContext) -> None:
        if type(event.payload) is not bytes:
            raise TypeError("Expected raw Ethernet bytes")
        ctx.schedule_after(TX_QUEUED, event.target, 0, Frame(ctx.event_sequence, self.address, event.payload))

    def enqueue(self, event: Event, ctx: EventContext) -> None:
        frame = event.payload
        if not isinstance(frame, Frame):
            raise TypeError("Expected Ethernet frame")
        vlan = self.settings.vlan
        if not 1 <= len(frame.wire) <= MAX_FRAME:
            drop(event, ctx, DropReason.INVALID_FRAME, frame, vlan)
            return
        if self.peer is None or self.timing is None:
            drop(event, ctx, DropReason.NO_EGRESS_PORT, frame, vlan)
            return
        hop = Hop(frame, self.address, self.peer, self.timing.link_id, vlan)
        failure = hop_drop(ctx, hop, stamped=False)
        if failure:
            drop(event, ctx, failure, hop)
            return
        queue = self._queue(ctx)
        if len(queue.waiting) >= self.settings.queue_limit:
            drop(event, ctx, DropReason.QUEUE_FULL, hop)
            return
        stamped = hop._replace(epochs=epochs(ctx, hop))
        self._save_queue(event, ctx, queue._replace(waiting=(*queue.waiting, stamped)))

    def _save_queue(self, event: Event, ctx: EventContext, queue: TransmitQueue) -> None:
        if queue.waiting and not queue.scheduled:
            ctx.schedule_after(TX_SERVICE, event.target, max(0, queue.ready_ns - event.time_ns),
                               queue.waiting[0])
            queue = queue._replace(scheduled=True)
        ctx.replace_state(queue)

    def service(self, event: Event, ctx: EventContext) -> None:
        queue = self._queue(ctx)
        hop, *pending = queue.waiting
        if self.timing is None:
            raise RuntimeError("Queued transmission has no link")
        failure = hop_drop(ctx, hop, stamped=True)
        ready_ns = queue.ready_ns
        if not failure:
            size = len(hop.frame.wire)
            serialization = self.timing.serialization_ns(size)
            if event.time_ns + serialization + self.timing.propagation_ns > MAX_TIME_NS:
                failure = DropReason.TIME_LIMIT
            else:
                ready_ns = min(MAX_TIME_NS, event.time_ns + self.timing.slot_ns(size))
                ctx.schedule_after(TX_START, event.target, 0, hop)
        if failure:
            drop(event, ctx, failure, hop)
        self._save_queue(event, ctx, TransmitQueue(tuple(pending), ready_ns))

    def start(self, event: Event, ctx: EventContext) -> None:
        hop = require_hop(event.payload)
        failure = hop_drop(ctx, hop, stamped=True)
        if failure:
            drop(event, ctx, failure, hop)
            return
        if self.timing is None:
            raise RuntimeError("Transmission has no link")
        delay = self.timing.serialization_ns(len(hop.frame.wire))
        ctx.schedule_after(SERIALIZED, link_target(hop.link_id), delay, hop)

    def receive(self, event: Event, ctx: EventContext) -> None:
        hop = require_hop(event.payload)
        failure = hop_drop(ctx, hop, stamped=True)
        if failure:
            drop(event, ctx, failure, hop, self.settings.vlan)
        else:
            ctx.schedule_after(PARSE, event.target, 0, hop)

    def parse(self, event: Event, ctx: EventContext) -> None:
        hop = require_hop(event.payload)
        failure = hop_drop(ctx, hop, stamped=True)
        if failure:
            drop(event, ctx, failure, hop, self.settings.vlan)
            return
        try:
            EthernetFrame.decode(hop.frame.wire)
        except WireError as exc:
            reason = {
                WireErrorCode.INVALID_FCS: DropReason.INVALID_FCS,
                WireErrorCode.INVALID_FRAME: DropReason.INVALID_FRAME,
                WireErrorCode.UNSUPPORTED_FORMAT: DropReason.UNSUPPORTED_PROTOCOL,
            }[exc.code]
            drop(event, ctx, reason, hop, self.settings.vlan)
            return
        # Ingress classification belongs to this receiving port.
        ctx.schedule_after(PROCESS, device_target(self.address.device), 0,
                           hop._replace(vlan=self.settings.vlan))


@dataclass(frozen=True, slots=True)
class LinkActor:
    timing: LinkTiming

    def advance(self, event: Event, ctx: EventContext) -> None:
        hop = require_hop(event.payload)
        failure = hop_drop(ctx, hop, stamped=True)
        if failure:
            drop(event, ctx, failure, hop)
        elif event.event_type == SERIALIZED:
            ctx.schedule_after(PROPAGATED, event.target, self.timing.propagation_ns, hop)
        else:
            ctx.schedule_after(RX_FRAME, hop.destination.target(), 0, hop)
