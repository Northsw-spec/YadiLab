"""Wiring and inspection for access Ethernet actors using one EventKernel."""

from dataclasses import dataclass
from ipaddress import IPv4Address

from ..config import (
    AdminState, ConfigError, ConfigSnapshot, DeviceKind, Endpoint, InterfaceKind, PowerState, index_by,
    require_type, typed_tuple,
)
from ..events import EventRef, EventTarget, EventType, EventValue, TraceAction
from ..kernel import EventHandler, EventKernel, KernelLimits
from ..runtime import OperState
from .actors import ARP_EXPIRE, RESOLVE, HostActor, HostState, SwitchActor, SwitchState
from .config import AccessPort, HostSettings, LinkTiming, SwitchSettings
from .transport import (
    DROP, INJECT, PARSE, PROCESS, PROPAGATED, RX_FRAME, SERIALIZED, SET_OPER, SET_POWER, TX_QUEUED,
    TX_SERVICE, TX_START, Drop, DropReason, Frame, Hop, LinkActor, PortActor, PortAddress, device_target,
    link_target, observe_drop, set_oper, set_power,
)


@dataclass(frozen=True, slots=True)
class EthernetConfig:
    project: ConfigSnapshot
    ports: tuple[AccessPort, ...]
    links: tuple[LinkTiming, ...]
    hosts: tuple[HostSettings, ...]
    switches: tuple[SwitchSettings, ...]

    def __post_init__(self) -> None:
        require_type(self.project, ConfigSnapshot, "project configuration")
        ports = typed_tuple(self.ports, AccessPort, "access ports")
        links = typed_tuple(self.links, LinkTiming, "link timings")
        hosts = typed_tuple(self.hosts, HostSettings, "hosts")
        switches = typed_tuple(self.switches, SwitchSettings, "switches")
        expected = {
            Endpoint(device.device_id, port.port_id)
            for device in self.project.devices for port in device.ports
            if port.profile.kind is InterfaceKind.PHYSICAL
        }
        if set(index_by(ports, lambda p: p.endpoint, "access port")) != expected:
            raise ConfigError("Each physical port requires explicit access settings")
        if set(index_by(links, lambda link: link.link_id, "link timing")) != {
            link.link_id for link in self.project.links
        }:
            raise ConfigError("Each physical cable requires explicit link timing")
        if any(link.profile.medium not in ("copper", "fiber") for link in self.project.links):
            raise ConfigError("Only full-duplex Ethernet copper or fiber is modeled")
        host_index = index_by(hosts, lambda host: host.endpoint.device_id, "host actor device")
        switch_index = index_by(switches, lambda switch: switch.device_id, "switch actor device")
        if set(host_index) & set(switch_index) or set(host_index) | set(switch_index) != {
            device.device_id for device in self.project.devices
        }:
            raise ConfigError("Each device requires one host or switch actor")
        for device in self.project.devices:
            endpoints = {endpoint for endpoint in expected if endpoint.device_id == device.device_id}
            if device.device_id in host_index:
                if (device.profile.kind not in (DeviceKind.HOST, DeviceKind.SERVER)
                        or endpoints != {host_index[device.device_id].endpoint}):
                    raise ConfigError("Host actors require an explicit single physical host interface")
            elif device.profile.kind is not DeviceKind.SWITCH:
                raise ConfigError("Switch actor requires a switch profile")
            if len(endpoints) != len(device.ports):
                raise ConfigError("Only physical access interfaces are modeled")
        object.__setattr__(self, "ports", ports)
        object.__setattr__(self, "links", links)
        object.__setattr__(self, "hosts", hosts)
        object.__setattr__(self, "switches", switches)


@dataclass(frozen=True, slots=True)
class FrameObservation:
    event: EventRef
    parent_id: int | None
    at_ns: int
    action: TraceAction
    stage: EventType
    target: EventTarget
    frame: Frame | None
    hop: Hop | None
    vlan: int | None
    reason: DropReason | None


class EthernetScenario:
    """Configure actors and schedule user actions. Simulation state lives in the kernel."""

    def __init__(self, config: EthernetConfig, scenario_id: str, *, seed: int, limits: KernelLimits) -> None:
        self.config = config
        timing = {link.link_id: link for link in config.links}
        connections = {}
        for link in config.project.links:
            connections[link.a] = PortAddress.from_endpoint(link.b), timing[link.link_id]
            connections[link.b] = PortAddress.from_endpoint(link.a), timing[link.link_id]
        actors: dict[EventTarget, dict[EventType, EventHandler]] = {}
        for access in config.ports:
            peer, link = connections.get(access.endpoint, (None, None))
            port = PortActor(access, peer, link)
            actors[port.address.target()] = {
                INJECT: port.inject, TX_QUEUED: port.enqueue, TX_SERVICE: port.service, TX_START: port.start, RX_FRAME: port.receive,
                PARSE: port.parse, SET_OPER: set_oper, DROP: observe_drop,
            }
        for link in config.links:
            actor = LinkActor(link)
            actors[link_target(link.link_id)] = {
                SERIALIZED: actor.advance, PROPAGATED: actor.advance, SET_OPER: set_oper, DROP: observe_drop,
            }
        for settings in config.hosts:
            host = HostActor(settings)
            actors[device_target(settings.endpoint.device_id)] = {
                RESOLVE: host.resolve, ARP_EXPIRE: host.expire, PROCESS: host.receive,
                SET_POWER: set_power, DROP: observe_drop,
            }
        for settings in config.switches:
            switch = SwitchActor(settings, tuple(sorted(
                (port for port in config.ports if port.endpoint.device_id == settings.device_id),
                key=lambda port: port.endpoint,
            )))
            actors[device_target(settings.device_id)] = {
                PROCESS: switch.receive, SET_POWER: set_power, DROP: observe_drop,
            }
        self.kernel = EventKernel(
            config.project, scenario_id, revision_id=config.project.revision_id, seed=seed,
            limits=limits, actors=actors,
        )

    def initialize(self) -> None:
        """Schedule the explicit enabled link and port startup states at current time."""
        now = self.kernel.now_ns
        for link in sorted(self.config.links, key=lambda link: link.link_id):
            self.set_link(link.link_id, True, at_ns=now)
        for device in sorted(self.config.project.devices, key=lambda device: device.device_id):
            if device.initial_power is PowerState.ON:
                for port in sorted(device.ports, key=lambda port: port.port_id):
                    if port.admin_state is AdminState.UP:
                        self.set_port(Endpoint(device.device_id, port.port_id), True, at_ns=now)

    def _schedule(
        self, event_type: EventType, target: EventTarget, payload: EventValue, at_ns: int,
    ) -> EventRef:
        return self.kernel.schedule(self.kernel.scenario, event_type, target, time_ns=at_ns, payload=payload)

    def set_port(self, endpoint: Endpoint, up: bool, *, at_ns: int) -> EventRef:
        require_type(up, bool, "port state")
        return self._schedule(SET_OPER, PortAddress.from_endpoint(endpoint).target(),
                              OperState.UP if up else OperState.DOWN, at_ns)

    def set_link(self, link_id: str, up: bool, *, at_ns: int) -> EventRef:
        require_type(up, bool, "link state")
        return self._schedule(SET_OPER, link_target(link_id), OperState.UP if up else OperState.DOWN, at_ns)

    def set_device_power(self, device_id: str, on: bool, *, at_ns: int) -> EventRef:
        require_type(on, bool, "power state")
        return self._schedule(SET_POWER, device_target(device_id), PowerState.ON if on else PowerState.OFF, at_ns)

    def resolve(self, device_id: str, ip: str, *, at_ns: int) -> EventRef:
        return self._schedule(RESOLVE, device_target(device_id), IPv4Address(ip).packed, at_ns)

    def inject(self, endpoint: Endpoint, wire: bytes, *, at_ns: int) -> EventRef:
        require_type(wire, bytes, "injected wire frame")
        return self._schedule(INJECT, PortAddress.from_endpoint(endpoint).target(), wire, at_ns)

    def host_state(self, device_id: str) -> HostState:
        state = dict(self.kernel.snapshot().actor_states).get(device_target(device_id))
        return state if isinstance(state, HostState) else HostState()

    def switch_state(self, device_id: str) -> SwitchState:
        state = dict(self.kernel.snapshot().actor_states).get(device_target(device_id))
        return state if isinstance(state, SwitchState) else SwitchState()

    def observations(self) -> tuple[FrameObservation, ...]:
        observations = []
        vlans = {PortAddress.from_endpoint(port.endpoint).target(): port.vlan for port in self.config.ports}
        for entry in self.kernel.trace:
            event = entry.event
            value = event.payload
            if isinstance(value, Drop):
                hop, vlan, reason = value.hop, value.vlan, value.reason
                frame = hop.frame if hop is not None else value.frame
            elif isinstance(value, Hop):
                frame, hop, vlan, reason = value.frame, value, value.vlan, None
            elif isinstance(value, Frame):
                frame, hop, vlan, reason = value, None, vlans.get(event.target), None
            else:
                continue
            observations.append(FrameObservation(
                event.ref, event.parent_id, entry.at_ns, entry.action, event.event_type,
                event.target, frame, hop, vlan, reason,
            ))
        return tuple(observations)
