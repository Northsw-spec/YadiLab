"""Validated, immutable values used to start a simulation scenario."""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum


class ConfigError(ValueError):
    """Invalid input at the project-to-engine boundary."""


def require_id(value: object, field: str) -> None:
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]*", value):
        raise ConfigError(f"Invalid {field}")


def require_type[T](value: T, expected: type[T], field: str) -> None:
    if type(value) is not expected:
        raise ConfigError(f"Invalid {field}")


def typed_tuple[T](values: Iterable[T], expected: type[T], field: str) -> tuple[T, ...]:
    if isinstance(values, (str, bytes)):
        raise ConfigError(f"Invalid {field}")
    try:
        result = tuple(values)
    except TypeError as exc:
        raise ConfigError(f"Invalid {field}") from exc
    for value in result:
        require_type(value, expected, field)
    return result


def id_set(values: Iterable[str], field: str) -> frozenset[str]:
    result = typed_tuple(values, str, field)
    for value in result:
        require_id(value, field)
    return frozenset(result)


def index_by[K, V](values: Iterable[V], key: Callable[[V], K], field: str) -> dict[K, V]:
    index: dict[K, V] = {}
    for value in values:
        identity = key(value)
        if identity in index:
            raise ConfigError(f"Duplicate {field}: {identity}")
        index[identity] = value
    return index


class DeviceKind(StrEnum):
    ROUTER = "router"
    SWITCH = "switch"
    HOST = "host"
    SERVER = "server"
    FIREWALL = "firewall"
    INDUSTRIAL = "industrial"
    IOT = "iot"
    OTHER = "other"


class InterfaceKind(StrEnum):
    PHYSICAL = "physical"
    LOGICAL = "logical"


class AdminState(StrEnum):
    UP = "up"
    DOWN = "down"


class PowerState(StrEnum):
    OFF = "off"
    STARTING = "starting"
    ON = "on"
    SHUTTING_DOWN = "shutting-down"
    REBOOTING = "rebooting"


@dataclass(frozen=True, slots=True, order=True)
class ProfileRef:
    profile_id: str
    version: str

    def __post_init__(self) -> None:
        require_id(self.profile_id, "profile ID")
        require_id(self.version, "profile version")


@dataclass(frozen=True, slots=True)
class PortProfile:
    ref: ProfileRef
    kind: InterfaceKind
    media: frozenset[str]
    capabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        require_type(self.ref, ProfileRef, "port profile reference")
        require_type(self.kind, InterfaceKind, "interface kind")
        object.__setattr__(self, "media", id_set(self.media, "port medium"))
        object.__setattr__(self, "capabilities", id_set(self.capabilities, "port capability"))
        if self.kind is InterfaceKind.PHYSICAL and not self.media:
            raise ConfigError("Physical ports require an explicit medium")


@dataclass(frozen=True, slots=True)
class ModuleProfile:
    ref: ProfileRef
    port_profiles: tuple[PortProfile, ...]

    def __post_init__(self) -> None:
        require_type(self.ref, ProfileRef, "module profile reference")
        profiles = typed_tuple(self.port_profiles, PortProfile, "module port profiles")
        index_by(profiles, lambda profile: profile.ref, "module port profile")
        object.__setattr__(self, "port_profiles", profiles)


@dataclass(frozen=True, slots=True)
class ModuleSlot:
    slot_id: str
    allowed_profiles: tuple[ModuleProfile, ...]

    def __post_init__(self) -> None:
        require_id(self.slot_id, "slot ID")
        profiles = typed_tuple(self.allowed_profiles, ModuleProfile, "allowed module profiles")
        index_by(profiles, lambda profile: profile.ref, "allowed module profile")
        object.__setattr__(self, "allowed_profiles", profiles)


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    ref: ProfileRef
    kind: DeviceKind
    vendor: str
    model: str
    port_profiles: tuple[PortProfile, ...]
    capabilities: frozenset[str] = frozenset()
    cli_dialect: ProfileRef | None = None
    slots: tuple[ModuleSlot, ...] = ()

    def __post_init__(self) -> None:
        require_type(self.ref, ProfileRef, "device profile reference")
        require_type(self.kind, DeviceKind, "device kind")
        for label in (self.vendor, self.model):
            if type(label) is not str or not label.strip():
                raise ConfigError("Device profile requires a vendor and model")
        profiles = typed_tuple(self.port_profiles, PortProfile, "device port profiles")
        index_by(profiles, lambda profile: profile.ref, "device port profile")
        object.__setattr__(self, "port_profiles", profiles)
        object.__setattr__(self, "capabilities", id_set(self.capabilities, "device capability"))
        slots = typed_tuple(self.slots, ModuleSlot, "device slots")
        index_by(slots, lambda slot: slot.slot_id, "device slot")
        object.__setattr__(self, "slots", slots)
        if self.cli_dialect is not None:
            require_type(self.cli_dialect, ProfileRef, "CLI dialect")


@dataclass(frozen=True, slots=True)
class LinkProfile:
    ref: ProfileRef
    medium: str

    def __post_init__(self) -> None:
        require_type(self.ref, ProfileRef, "link profile reference")
        require_id(self.medium, "link medium")


@dataclass(frozen=True, slots=True, order=True)
class Endpoint:
    device_id: str
    port_id: str

    def __post_init__(self) -> None:
        require_id(self.device_id, "endpoint device ID")
        require_id(self.port_id, "endpoint port ID")


@dataclass(frozen=True, slots=True)
class PortConfig:
    port_id: str
    profile: PortProfile
    admin_state: AdminState
    capabilities: frozenset[str] = frozenset()
    module_slot_id: str | None = None

    def __post_init__(self) -> None:
        require_id(self.port_id, "port ID")
        require_type(self.profile, PortProfile, "port profile")
        require_type(self.admin_state, AdminState, "administrative state")
        if self.module_slot_id is not None:
            require_id(self.module_slot_id, "port module slot ID")
        capabilities = id_set(self.capabilities, "enabled port capability")
        if not capabilities <= self.profile.capabilities:
            raise ConfigError("Unsupported port capabilities")
        object.__setattr__(self, "capabilities", capabilities)


@dataclass(frozen=True, slots=True)
class ModuleConfig:
    slot_id: str
    profile: ModuleProfile

    def __post_init__(self) -> None:
        require_id(self.slot_id, "installed module slot ID")
        require_type(self.profile, ModuleProfile, "installed module profile")


@dataclass(frozen=True, slots=True)
class DeviceConfig:
    device_id: str
    profile: DeviceProfile
    ports: tuple[PortConfig, ...]
    initial_power: PowerState
    capabilities: frozenset[str] = frozenset()
    modules: tuple[ModuleConfig, ...] = ()

    def __post_init__(self) -> None:
        require_id(self.device_id, "device ID")
        require_type(self.profile, DeviceProfile, "device profile")
        require_type(self.initial_power, PowerState, "initial power")
        if self.initial_power not in (PowerState.OFF, PowerState.ON):
            raise ConfigError("Initial power must be a stable state")
        capabilities = id_set(self.capabilities, "enabled device capability")
        if not capabilities <= self.profile.capabilities:
            raise ConfigError("Unsupported device capabilities")
        object.__setattr__(self, "capabilities", capabilities)

        modules = typed_tuple(self.modules, ModuleConfig, "installed modules")
        installed = index_by(modules, lambda module: module.slot_id, "installed module slot")
        slots = {slot.slot_id: slot for slot in self.profile.slots}
        for module in modules:
            slot = slots.get(module.slot_id)
            if slot is None or module.profile not in slot.allowed_profiles:
                raise ConfigError(f"Incompatible module in slot {module.slot_id}")
        object.__setattr__(self, "modules", modules)

        ports = typed_tuple(self.ports, PortConfig, "ports")
        index_by(ports, lambda port: port.port_id, "device port ID")
        for port in ports:
            profiles = self.profile.port_profiles
            if port.module_slot_id is not None:
                module = installed.get(port.module_slot_id)
                if module is None:
                    raise ConfigError(f"Port {port.port_id} references an empty module slot")
                profiles = module.profile.port_profiles
            if port.profile not in profiles:
                raise ConfigError(f"Unsupported profile for port {port.port_id}")
        object.__setattr__(self, "ports", ports)


@dataclass(frozen=True, slots=True)
class LinkConfig:
    link_id: str
    profile: LinkProfile
    a: Endpoint
    b: Endpoint
    evidence_id: str

    def __post_init__(self) -> None:
        require_id(self.link_id, "link ID")
        require_type(self.profile, LinkProfile, "link profile")
        require_type(self.a, Endpoint, "first endpoint")
        require_type(self.b, Endpoint, "second endpoint")
        require_id(self.evidence_id, "link evidence ID")
        if self.a == self.b:
            raise ConfigError("Link endpoints must be distinct")


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    revision_id: str
    devices: tuple[DeviceConfig, ...]
    links: tuple[LinkConfig, ...]

    def __post_init__(self) -> None:
        require_id(self.revision_id, "project revision ID")
        devices = typed_tuple(self.devices, DeviceConfig, "devices")
        links = typed_tuple(self.links, LinkConfig, "links")
        index_by(devices, lambda device: device.device_id, "device ID")
        index_by(links, lambda link: link.link_id, "link ID")
        ports = {
            Endpoint(device.device_id, port.port_id): port
            for device in devices for port in device.ports
        }
        occupied: set[Endpoint] = set()
        for link in links:
            for endpoint in (link.a, link.b):
                port = ports.get(endpoint)
                if port is None:
                    raise ConfigError(f"Unknown link endpoint: {endpoint}")
                if endpoint in occupied:
                    raise ConfigError(f"Port already has a cable: {endpoint}")
                if (port.profile.kind is not InterfaceKind.PHYSICAL
                        or link.profile.medium not in port.profile.media):
                    raise ConfigError(f"Incompatible link medium at endpoint: {endpoint}")
                occupied.add(endpoint)
        object.__setattr__(self, "devices", devices)
        object.__setattr__(self, "links", links)
