"""A single virtual clock, event queue and dispatch boundary per scenario."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from heapq import heapify, heappop, heappush

from .config import ConfigError, ConfigSnapshot, Endpoint, require_type
from .events import (
    MAX_SEED, MAX_TIME_NS, ErrorCode, Event, EventRef, EventTarget, EventType,
    KernelError, RunResult, ScenarioRef, StopReason, TraceAction, TraceEntry,
)
from .runtime import (
    DeviceRuntime, LinkRuntime, PortRuntime, RuntimeSnapshot, RuntimeView, ScenarioRuntime,
)

RANDOM_VERSION = "scenario-event-sha256-v2"


def _count(value: int) -> bool:
    return type(value) is int and 0 < value <= MAX_TIME_NS


def _time(value: int) -> int:
    if type(value) is not int or value < 0:
        raise KernelError(ErrorCode.INVALID_TIME)
    if value > MAX_TIME_NS:
        raise KernelError(ErrorCode.TIME_OVERFLOW)
    return value


@dataclass(frozen=True, slots=True)
class RunBudget:
    events: int
    duration_ns: int

    def __post_init__(self) -> None:
        if not _count(self.events):
            raise KernelError(ErrorCode.INVALID_BUDGET)
        _time(self.duration_ns)


@dataclass(frozen=True, slots=True)
class KernelLimits:
    pending_events: int
    events_per_timestamp: int
    trace_entries: int
    value_bytes: int

    def __post_init__(self) -> None:
        if not all(map(_count, (
            self.pending_events, self.events_per_timestamp, self.trace_entries, self.value_bytes,
        ))):
            raise KernelError(ErrorCode.INVALID_BUDGET)


@dataclass(frozen=True, slots=True)
class _ScheduledEvent:
    time_ns: int
    event_type: EventType
    target: EventTarget
    payload: bytes


class EventContext:
    """A handler can replace its target's state and stage causally linked events."""

    def __init__(
        self, config: ConfigSnapshot, runtime_view: RuntimeView, state: bytes,
        random_key: bytes, value_bytes: int,
        stage: Callable[[EventType, EventTarget, int, bytes], None],
    ) -> None:
        self._config = config
        self._runtime_view = runtime_view
        self._state = state
        self._random_key = random_key
        self._draw = 0
        self._value_bytes = value_bytes
        self._stage = stage
        self._active = True

    @property
    def state(self) -> bytes:
        return self._state

    @property
    def config(self) -> ConfigSnapshot:
        return self._config

    def device(self, device_id: str) -> DeviceRuntime:
        self._require_active()
        return self._runtime_view.devices[device_id]

    def port(self, endpoint: Endpoint) -> PortRuntime:
        self._require_active()
        return self._runtime_view.ports[endpoint]

    def link(self, link_id: str) -> LinkRuntime:
        self._require_active()
        return self._runtime_view.links[link_id]

    def _require_active(self) -> None:
        if not self._active:
            raise KernelError(ErrorCode.INVALID_STATE, "Event context has expired")

    def replace_state(self, state: bytes) -> None:
        self._require_active()
        if type(state) is not bytes or len(state) > self._value_bytes:
            raise KernelError(ErrorCode.INVALID_STATE)
        self._state = state

    def schedule_after(
        self, event_type: EventType, target: EventTarget, delay_ns: int, payload: bytes = b"",
    ) -> None:
        self._require_active()
        self._stage(event_type, target, delay_ns, payload)

    def random_u64(self) -> int:
        self._require_active()
        if self._draw > MAX_SEED:
            raise KernelError(ErrorCode.ID_EXHAUSTED, "Random draw index exhausted")
        digest = sha256(self._random_key + self._draw.to_bytes(8, "big")).digest()
        self._draw += 1
        return int.from_bytes(digest[:8], "big")


type EventHandler = Callable[[Event, EventContext], None]


class EventKernel:
    """Call from one scenario owner. Each run is a bounded synchronous slice."""

    def __init__(
        self, config: ConfigSnapshot, scenario_id: str, *, revision_id: str, seed: int,
        limits: KernelLimits, actors: Mapping[EventTarget, Mapping[EventType, EventHandler]],
    ) -> None:
        require_type(config, ConfigSnapshot, "validated configuration")
        require_type(limits, KernelLimits, "kernel limits")
        if config.revision_id != revision_id:
            raise KernelError(ErrorCode.REVISION_MISMATCH)
        if type(seed) is not int or not 0 <= seed <= MAX_SEED:
            raise KernelError(ErrorCode.INVALID_SEED)
        self._config = config
        self._runtime = ScenarioRuntime(config, ScenarioRef(scenario_id, revision_id, 0))
        self._random_prefix = RANDOM_VERSION.encode("ascii") + b"\x00" + seed.to_bytes(8, "big")
        self._limits = limits
        self._actors: dict[EventTarget, dict[EventType, EventHandler]] = {}
        for target, handlers in actors.items():
            if type(target) is not EventTarget or not self._runtime.has_target(target):
                raise KernelError(ErrorCode.INVALID_TARGET)
            if any(type(event_type) is not EventType for event_type in handlers):
                raise KernelError(ErrorCode.INVALID_EVENT_TYPE)
            if any(not callable(handler) for handler in handlers.values()):
                raise ConfigError("Actor handlers must be callable")
            self._actors[target] = dict(handlers)
        self._heap: list[tuple[int, int]] = []
        self._pending: dict[int, Event] = {}
        self._trace: list[TraceEntry] = []
        self._next_event_id = 1
        self._generation_first_event_id = self._next_event_id
        self._now_ns = 0
        self._at_timestamp = 0
        self._paused = False
        self._dispatching = False
        self._fault: tuple[ErrorCode, EventRef] | None = None

    @property
    def config(self) -> ConfigSnapshot:
        return self._config

    @property
    def scenario(self) -> ScenarioRef:
        return self._runtime.ref

    @property
    def now_ns(self) -> int:
        return self._now_ns

    @property
    def trace(self) -> tuple[TraceEntry, ...]:
        return tuple(self._trace)

    def snapshot(self) -> RuntimeSnapshot:
        return self._runtime.snapshot()

    def _guard(self) -> None:
        if self._dispatching:
            raise KernelError(ErrorCode.REENTRANT_OPERATION)

    def _check_scenario(self, scenario: ScenarioRef) -> None:
        if type(scenario) is not ScenarioRef or scenario.scenario_id != self.scenario.scenario_id:
            raise KernelError(ErrorCode.STALE_SCENARIO)
        if scenario.revision_id != self.scenario.revision_id:
            raise KernelError(ErrorCode.REVISION_MISMATCH)
        if scenario.generation != self.scenario.generation:
            raise KernelError(ErrorCode.STALE_SCENARIO)

    def _validate_event(
        self, event_type: EventType, target: EventTarget, time_ns: int, payload: bytes,
        extra_pending: int = 0,
    ) -> _ScheduledEvent:
        _time(time_ns)
        if time_ns < self.now_ns:
            raise KernelError(ErrorCode.INVALID_TIME, "Cannot schedule in the past")
        if type(target) is not EventTarget or not self._runtime.has_target(target):
            raise KernelError(ErrorCode.INVALID_TARGET)
        handlers = self._actors.get(target)
        if type(event_type) is not EventType or handlers is None or event_type not in handlers:
            raise KernelError(ErrorCode.INVALID_EVENT_TYPE)
        if type(payload) is not bytes or len(payload) > self._limits.value_bytes:
            raise KernelError(ErrorCode.INVALID_PAYLOAD)
        if len(self._pending) + extra_pending >= self._limits.pending_events:
            raise KernelError(ErrorCode.QUEUE_LIMIT)
        if self._next_event_id + extra_pending > MAX_TIME_NS:
            raise KernelError(ErrorCode.ID_EXHAUSTED)
        return _ScheduledEvent(time_ns, event_type, target, payload)

    def _enqueue(self, item: _ScheduledEvent, parent_id: int | None = None) -> EventRef:
        ref = EventRef(self.scenario, self._next_event_id)
        self._next_event_id += 1
        self._pending[ref.event_id] = Event(
            ref, item.time_ns, item.event_type, item.target, item.payload, parent_id,
        )
        heappush(self._heap, (item.time_ns, ref.event_id))
        return ref

    def schedule(
        self, scenario: ScenarioRef, event_type: EventType, target: EventTarget, *,
        time_ns: int, payload: bytes = b"",
    ) -> EventRef:
        self._guard()
        self._check_scenario(scenario)
        if self._fault:
            raise KernelError(ErrorCode.FAULTED)
        return self._enqueue(self._validate_event(event_type, target, time_ns, payload))

    def schedule_after(
        self, scenario: ScenarioRef, event_type: EventType, target: EventTarget, *,
        delay_ns: int, payload: bytes = b"",
    ) -> EventRef:
        return self.schedule(
            scenario, event_type, target, time_ns=self.now_ns + _time(delay_ns), payload=payload,
        )

    def cancel(self, ref: EventRef) -> None:
        self._guard()
        require_type(ref, EventRef, "event reference")
        self._check_scenario(ref.scenario)
        event = self._pending.get(ref.event_id)
        if event is None:
            raise KernelError(ErrorCode.UNKNOWN_EVENT)
        if len(self._trace) >= self._limits.trace_entries:
            raise KernelError(ErrorCode.TRACE_LIMIT)
        del self._pending[ref.event_id]
        self._trace.append(TraceEntry(event, self.now_ns, TraceAction.CANCELLED))
        # Bound tombstones even if a far-future event is repeatedly replaced.
        if len(self._heap) - len(self._pending) >= self._limits.pending_events:
            self._heap = [(event.time_ns, key) for key, event in self._pending.items()]
            heapify(self._heap)

    def pause(self) -> None:
        self._guard()
        self._paused = True

    def resume(self) -> None:
        self._guard()
        self._paused = False

    def reset(self, scenario: ScenarioRef) -> ScenarioRef:
        self._guard()
        self._check_scenario(scenario)
        if self.scenario.generation == MAX_TIME_NS:
            raise KernelError(ErrorCode.ID_EXHAUSTED, "Scenario generation exhausted")
        self._runtime = self._runtime._next_generation(self.config)
        self._generation_first_event_id = self._next_event_id
        self._heap.clear()
        self._pending.clear()
        self._trace.clear()
        self._now_ns = 0
        self._at_timestamp = 0
        self._paused = False
        self._fault = None
        return self.scenario

    def _peek(self) -> Event | None:
        while self._heap:
            _, event_id = self._heap[0]
            if event_id in self._pending:
                return self._pending[event_id]
            heappop(self._heap)
        return None

    def _dispatch(self, event: Event) -> bool:
        if event.time_ns != self.now_ns:
            self._now_ns = event.time_ns
            self._at_timestamp = 0
        if self._at_timestamp >= self._limits.events_per_timestamp:
            self._fault = ErrorCode.LIVELOCK, event.ref
            return False
        self._at_timestamp += 1
        heappop(self._heap)
        del self._pending[event.ref.event_id]
        followups: list[_ScheduledEvent] = []

        def stage(event_type: EventType, target: EventTarget, delay_ns: int, payload: bytes) -> None:
            followups.append(self._validate_event(
                event_type, target, self.now_ns + _time(delay_ns), payload, len(followups),
            ))

        # Committed enqueue IDs are contiguous within a generation, even after cancellation.
        sequence = event.ref.event_id - self._generation_first_event_id + 1
        context = EventContext(
            self.config, self._runtime.view, self._runtime.actor_state(event.target),
            self._random_prefix + sequence.to_bytes(8, "big"),
            self._limits.value_bytes,
            stage,
        )
        self._dispatching = True
        try:
            result = self._actors[event.target][event.event_type](event, context)
            if result is not None:
                raise TypeError("Event handlers must stage effects and return None")
        except BaseException as exc:
            self._fault = ErrorCode.HANDLER_FAILED, event.ref
            self._trace.append(TraceEntry(
                event, self.now_ns, TraceAction.FAILED, ErrorCode.HANDLER_FAILED,
            ))
            if not isinstance(exc, Exception):
                raise
            return True
        finally:
            context._active = False
            self._dispatching = False

        self._runtime._set_actor_state(event.target, context.state)
        for item in followups:
            self._enqueue(item, event.ref.event_id)
        self._trace.append(TraceEntry(event, self.now_ns, TraceAction.EXECUTED))
        return True

    def _process(self, budget: RunBudget | None) -> RunResult:
        self._guard()
        processed = 0
        deadline = min(MAX_TIME_NS, self.now_ns + budget.duration_ns) if budget else MAX_TIME_NS
        while True:
            if self._fault:
                error, event_ref = self._fault
                return RunResult(StopReason.FAULTED, processed, self.now_ns, error, event_ref)
            if budget and self._paused:
                return RunResult(StopReason.PAUSED, processed, self.now_ns)
            event = self._peek()
            if event is None:
                return RunResult(StopReason.IDLE, processed, self.now_ns)
            if budget and processed >= budget.events:
                return RunResult(StopReason.EVENT_BUDGET, processed, self.now_ns)
            if event.time_ns > deadline:
                return RunResult(StopReason.TIME_BUDGET, processed, self.now_ns)
            if len(self._trace) >= self._limits.trace_entries:
                return RunResult(StopReason.TRACE_BUDGET, processed, self.now_ns)
            processed += int(self._dispatch(event))
            if self._fault is None and budget is None:
                return RunResult(StopReason.STEPPED, processed, self.now_ns, event=event.ref)

    def step(self) -> RunResult:
        return self._process(None)

    def run(self, budget: RunBudget) -> RunResult:
        if type(budget) is not RunBudget:
            raise KernelError(ErrorCode.INVALID_BUDGET)
        return self._process(budget)
