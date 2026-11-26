"""Ordered event data and typed outcomes for the scenario boundary."""

from dataclasses import dataclass
from enum import StrEnum

from .config import ConfigError, require_id, require_type

MAX_TIME_NS = (1 << 63) - 1
MAX_SEED = (1 << 64) - 1


class ErrorCode(StrEnum):
    INVALID_TIME = "invalid-time"
    TIME_OVERFLOW = "time-overflow"
    INVALID_EVENT_TYPE = "invalid-event-type"
    INVALID_TARGET = "invalid-target"
    INVALID_PAYLOAD = "invalid-payload"
    STALE_SCENARIO = "stale-scenario"
    REVISION_MISMATCH = "revision-mismatch"
    UNKNOWN_EVENT = "unknown-event"
    QUEUE_LIMIT = "queue-limit"
    TRACE_LIMIT = "trace-limit"
    INVALID_BUDGET = "invalid-budget"
    INVALID_SEED = "invalid-seed"
    INVALID_STATE = "invalid-state"
    ID_EXHAUSTED = "id-exhausted"
    LIVELOCK = "livelock"
    HANDLER_FAILED = "handler-failed"
    REENTRANT_OPERATION = "reentrant-operation"
    FAULTED = "faulted"


class KernelError(RuntimeError):
    def __init__(self, code: ErrorCode, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code.value}: {detail}" if detail else code.value)


class TargetKind(StrEnum):
    SCENARIO = "scenario"
    DEVICE = "device"
    PORT = "port"
    LINK = "link"


@dataclass(frozen=True, slots=True)
class EventTarget:
    kind: TargetKind
    object_id: str
    port_id: str | None = None

    def __post_init__(self) -> None:
        require_type(self.kind, TargetKind, "event target kind")
        require_id(self.object_id, "target ID")
        if self.kind is TargetKind.PORT:
            require_id(self.port_id, "target port ID")
        elif self.port_id is not None:
            raise ConfigError("Only port targets have a port ID")

    def sort_key(self) -> tuple[str, str, str]:
        return self.kind.value, self.object_id, self.port_id or ""


@dataclass(frozen=True, slots=True)
class EventType:
    type_id: str

    def __post_init__(self) -> None:
        require_id(self.type_id, "event type ID")


@dataclass(frozen=True, slots=True)
class ScenarioRef:
    scenario_id: str
    revision_id: str
    generation: int

    def __post_init__(self) -> None:
        require_id(self.scenario_id, "scenario ID")
        require_id(self.revision_id, "scenario revision ID")
        if type(self.generation) is not int or not 0 <= self.generation <= MAX_TIME_NS:
            raise ConfigError("Invalid scenario generation")


@dataclass(frozen=True, slots=True)
class EventRef:
    scenario: ScenarioRef
    event_id: int

    def __post_init__(self) -> None:
        require_type(self.scenario, ScenarioRef, "event scenario reference")
        if type(self.event_id) is not int or not 0 < self.event_id <= MAX_TIME_NS:
            raise ConfigError("Invalid event ID")


@dataclass(frozen=True, slots=True)
class Event:
    ref: EventRef
    time_ns: int
    event_type: EventType
    target: EventTarget
    payload: bytes
    parent_id: int | None


class TraceAction(StrEnum):
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TraceEntry:
    event: Event
    at_ns: int
    action: TraceAction
    error: ErrorCode | None = None


class StopReason(StrEnum):
    STEPPED = "stepped"
    IDLE = "idle"
    PAUSED = "paused"
    EVENT_BUDGET = "event-budget"
    TIME_BUDGET = "time-budget"
    TRACE_BUDGET = "trace-budget"
    FAULTED = "faulted"


@dataclass(frozen=True, slots=True)
class RunResult:
    reason: StopReason
    processed: int
    time_ns: int
    error: ErrorCode | None = None
    event: EventRef | None = None
