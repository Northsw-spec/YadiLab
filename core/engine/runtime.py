"""Scenario-owned operational state and immutable inspection records."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from types import MappingProxyType

from .config import (
    AdminState, ConfigError, ConfigSnapshot, Endpoint, PowerState, require_id, require_type,
)
from .events import EventTarget, ScenarioRef, TargetKind


class OperState(StrEnum):
    DOWN = "down"
    UNKNOWN = "unknown"
    UP = "up"
    LOWER_LAYER_DOWN = "lower-layer-down"
    DORMANT = "dormant"
    NOT_PRESENT = "not-present"
    TESTING = "testing"


@dataclass(frozen=True, slots=True)
class DeviceRuntime:
    device_id: str
    power: PowerState

    def __post_init__(self) -> None:
        require_id(self.device_id, "runtime device ID")
        require_type(self.power, PowerState, "runtime power")


@dataclass(frozen=True, slots=True)
class PortRuntime:
    endpoint: Endpoint
    admin_state: AdminState
    oper_state: OperState

    def __post_init__(self) -> None:
        require_type(self.endpoint, Endpoint, "runtime endpoint")
        require_type(self.admin_state, AdminState, "runtime administrative state")
        require_type(self.oper_state, OperState, "runtime operational state")
        if self.admin_state is AdminState.DOWN and self.oper_state not in (
            OperState.DOWN, OperState.NOT_PRESENT,
        ):
            raise ConfigError("An administratively down port cannot be operational")


@dataclass(frozen=True, slots=True)
class LinkRuntime:
    link_id: str
    oper_state: OperState

    def __post_init__(self) -> None:
        require_id(self.link_id, "runtime link ID")
        require_type(self.oper_state, OperState, "runtime link state")


@dataclass(frozen=True, slots=True)
class RuntimeView:
    """Read-only access to installed operational records during a dispatch."""

    devices: Mapping[str, DeviceRuntime]
    ports: Mapping[Endpoint, PortRuntime]
    links: Mapping[str, LinkRuntime]


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    ref: ScenarioRef
    devices: tuple[DeviceRuntime, ...]
    ports: tuple[PortRuntime, ...]
    links: tuple[LinkRuntime, ...]
    actor_states: tuple[tuple[EventTarget, bytes], ...]


class ScenarioRuntime:
    """One mutable store. The kernel owns writes and provides read-only snapshots."""

    def __init__(self, config: ConfigSnapshot, ref: ScenarioRef) -> None:
        require_type(config, ConfigSnapshot, "validated configuration")
        require_type(ref, ScenarioRef, "scenario reference")
        if ref.revision_id != config.revision_id:
            raise ConfigError("Scenario revision differs from configuration revision")
        self._ref = ref
        self._devices = {
            device.device_id: DeviceRuntime(device.device_id, device.initial_power)
            for device in config.devices
        }
        self._ports: dict[Endpoint, PortRuntime] = {}
        for device in config.devices:
            for port in device.ports:
                endpoint = Endpoint(device.device_id, port.port_id)
                oper_state = OperState.DOWN
                if device.initial_power is PowerState.ON and port.admin_state is AdminState.UP:
                    oper_state = OperState.UNKNOWN
                self._ports[endpoint] = PortRuntime(endpoint, port.admin_state, oper_state)
        self._links = {
            link.link_id: LinkRuntime(link.link_id, OperState.UNKNOWN) for link in config.links
        }
        self._actor_states: dict[EventTarget, bytes] = {}
        self._view = RuntimeView(
            MappingProxyType(self._devices),
            MappingProxyType(self._ports),
            MappingProxyType(self._links),
        )

    @property
    def view(self) -> RuntimeView:
        return self._view

    @property
    def ref(self) -> ScenarioRef:
        return self._ref

    def has_target(self, target: EventTarget) -> bool:
        match target.kind:
            case TargetKind.SCENARIO:
                return target.object_id == self.ref.scenario_id
            case TargetKind.DEVICE:
                return target.object_id in self._devices
            case TargetKind.PORT:
                return target.port_id is not None and Endpoint(target.object_id, target.port_id) in self._ports
            case TargetKind.LINK:
                return target.object_id in self._links

    def device(self, device_id: str) -> DeviceRuntime:
        return self._devices[device_id]

    def port(self, endpoint: Endpoint) -> PortRuntime:
        return self._ports[endpoint]

    def link(self, link_id: str) -> LinkRuntime:
        return self._links[link_id]

    def actor_state(self, target: EventTarget) -> bytes:
        if not self.has_target(target):
            raise KeyError(target)
        return self._actor_states.get(target, b"")

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            self.ref,
            tuple(self._devices[key] for key in sorted(self._devices)),
            tuple(self._ports[key] for key in sorted(self._ports)),
            tuple(self._links[key] for key in sorted(self._links)),
            tuple(sorted(self._actor_states.items(), key=lambda item: item[0].sort_key())),
        )

    def _set_actor_state(self, target: EventTarget, value: bytes) -> None:
        if value:
            self._actor_states[target] = value
        else:
            self._actor_states.pop(target, None)

    def _next_generation(self, config: ConfigSnapshot) -> "ScenarioRuntime":
        return ScenarioRuntime(config, replace(self.ref, generation=self.ref.generation + 1))
