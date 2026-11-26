"""Typed boundaries for device CLI adapters and configuration proposals."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .config import (
    ConfigError, ConfigSnapshot, DeviceConfig, ProfileRef, require_id, require_type, typed_tuple,
)
from .events import ScenarioRef
from .runtime import RuntimeSnapshot


@dataclass(frozen=True, slots=True)
class CommandAST:
    path: tuple[str, ...]
    arguments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        path = typed_tuple(self.path, str, "command path")
        if not path or any(not token or any(char.isspace() for char in token) for token in path):
            raise ConfigError("Command path requires nonempty command tokens")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "arguments", typed_tuple(self.arguments, str, "command arguments"))


@dataclass(frozen=True, slots=True)
class CommandContext:
    scenario: ScenarioRef
    device_id: str
    mode: str
    privilege: int

    def __post_init__(self) -> None:
        require_type(self.scenario, ScenarioRef, "command scenario reference")
        require_id(self.device_id, "command device ID")
        require_id(self.mode, "command mode")
        if type(self.privilege) is not int or self.privilege < 0:
            raise ConfigError("Invalid command privilege")


class CLIErrorCode(StrEnum):
    UNSUPPORTED_COMMAND = "unsupported-command"
    INVALID_SYNTAX = "invalid-syntax"
    INVALID_MODE = "invalid-mode"
    INSUFFICIENT_PRIVILEGE = "insufficient-privilege"
    UNKNOWN_DEVICE = "unknown-device"
    UNSUPPORTED_CAPABILITY = "unsupported-capability"
    STALE_SCENARIO = "stale-scenario"
    REVISION_CONFLICT = "revision-conflict"


@dataclass(frozen=True, slots=True)
class CLIError:
    code: CLIErrorCode
    message: str


@dataclass(frozen=True, slots=True)
class CommandOutput:
    text: str


@dataclass(frozen=True, slots=True)
class ConfigTransaction:
    expected_revision_id: str
    candidate: ConfigSnapshot

    def __post_init__(self) -> None:
        require_id(self.expected_revision_id, "transaction base revision ID")
        require_type(self.candidate, ConfigSnapshot, "transaction candidate")
        if self.candidate.revision_id == self.expected_revision_id:
            raise ConfigError("Candidate configuration requires a new revision ID")

    def validate_against(self, current: ConfigSnapshot) -> CLIError | None:
        if self.expected_revision_id != current.revision_id:
            return CLIError(CLIErrorCode.REVISION_CONFLICT, "Project revision changed")
        return None


type CLIResult = CommandOutput | ConfigTransaction | CLIError


class CommandParser(Protocol):
    def parse(self, text: str, context: CommandContext) -> CommandAST | CLIError: ...


class CLIAdapter(Protocol):
    @property
    def parser(self) -> CommandParser: ...

    def validate(
        self, command: CommandAST, context: CommandContext, device: DeviceConfig,
    ) -> CLIError | None: ...

    def evaluate(
        self, command: CommandAST, context: CommandContext, config: ConfigSnapshot,
        runtime: RuntimeSnapshot,
    ) -> CLIResult: ...


class CLI:
    """Resolve a versioned dialect and return output, a proposal, or a typed error."""

    def __init__(self, adapters: Mapping[ProfileRef, CLIAdapter] | None = None) -> None:
        self._adapters = dict(adapters or {})

    def submit(
        self, text: str, context: CommandContext, config: ConfigSnapshot, runtime: RuntimeSnapshot,
    ) -> CLIResult:
        if context.scenario != runtime.ref:
            return CLIError(CLIErrorCode.STALE_SCENARIO, "Command scenario changed")
        if config.revision_id != runtime.ref.revision_id:
            return CLIError(CLIErrorCode.REVISION_CONFLICT, "Configuration and runtime revisions differ")
        device = next((device for device in config.devices if device.device_id == context.device_id), None)
        if device is None:
            return CLIError(CLIErrorCode.UNKNOWN_DEVICE, "Command target device does not exist")
        dialect = device.profile.cli_dialect
        adapter = self._adapters.get(dialect) if dialect is not None else None
        if adapter is None:
            return CLIError(
                CLIErrorCode.UNSUPPORTED_COMMAND,
                "No command adapter is available for this device profile",
            )
        command = adapter.parser.parse(text, context)
        if isinstance(command, CLIError):
            return command
        error = adapter.validate(command, context, device)
        if error is not None:
            return error
        result = adapter.evaluate(command, context, config, runtime)
        if isinstance(result, ConfigTransaction):
            conflict = result.validate_against(config)
            if conflict is not None:
                return conflict
        return result
