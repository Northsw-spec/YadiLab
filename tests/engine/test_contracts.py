import unittest
from dataclasses import FrozenInstanceError, replace

from core.engine.cli import (
    CLI, CLIError, CLIErrorCode, CommandAST, CommandContext, CommandOutput, ConfigTransaction,
)
from core.engine.config import (
    AdminState, ConfigError, ConfigSnapshot, DeviceConfig, DeviceKind, DeviceProfile, Endpoint,
    InterfaceKind, LinkConfig, LinkProfile, ModuleConfig, ModuleProfile, ModuleSlot, PortConfig,
    PortProfile, PowerState, ProfileRef,
)
from core.engine.events import ErrorCode, KernelError, ScenarioRef
from core.engine.kernel import EventKernel, KernelLimits
from core.engine.runtime import OperState, PortRuntime, ScenarioRuntime

COPPER = PortProfile(ProfileRef("copper-port", "1"), InterfaceKind.PHYSICAL, {"copper"}, {"dot1q"})
LOGICAL = PortProfile(ProfileRef("logical-port", "1"), InterfaceKind.LOGICAL, set())
CABLE = LinkProfile(ProfileRef("cable", "1"), "copper")
DIALECT = ProfileRef("test-cli", "1")
PROFILE = DeviceProfile(
    ProfileRef("host", "1"), DeviceKind.HOST, "Test vendor", "Host",
    (COPPER, LOGICAL), {"console"}, DIALECT,
)
A = Endpoint("a", "eth0")
B = Endpoint("b", "eth0")


def device(device_id, *, admin=AdminState.UP, power=PowerState.ON):
    return DeviceConfig(device_id, PROFILE, (PortConfig("eth0", COPPER, admin),), power)


def topology():
    return ConfigSnapshot("rev-1", (device("a"), device("b")), (
        LinkConfig("link-1", CABLE, A, B, "user/cable-1"),
    ))


class ConfigTests(unittest.TestCase):
    def test_explicit_endpoints_and_scoped_port_ids(self):
        config = topology()
        self.assertEqual(config.links[0].a, Endpoint("a", "eth0"))
        self.assertEqual(config.links[0].b, Endpoint("b", "eth0"))
        self.assertEqual(config.links[0].evidence_id, "user/cable-1")
        self.assertEqual([item.ports[0].port_id for item in config.devices], ["eth0", "eth0"])
        self.assertEqual(config.devices[0].ports[0].admin_state, AdminState.UP)

    def test_duplicate_device_port_and_link_ids(self):
        config = topology()
        with self.assertRaisesRegex(ConfigError, "Duplicate device ID"):
            replace(config, devices=(device("a"), device("a")))
        with self.assertRaisesRegex(ConfigError, "Duplicate device port ID"):
            replace(config.devices[0], ports=config.devices[0].ports * 2)
        with self.assertRaisesRegex(ConfigError, "Duplicate link ID"):
            replace(config, links=config.links * 2)

    def test_rejects_dangling_endpoints(self):
        config = topology()
        for endpoint in (Endpoint("absent", "eth0"), Endpoint("b", "eth9")):
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(
                ConfigError, "Unknown link endpoint",
            ):
                replace(config, links=(replace(config.links[0], b=endpoint),))

    def test_cable_requires_compatible_physical_media(self):
        config = topology()
        fiber = replace(CABLE, medium="fiber")
        with self.assertRaisesRegex(ConfigError, "Incompatible link medium"):
            replace(config, links=(replace(config.links[0], profile=fiber),))
        logical_port = PortConfig("eth0", LOGICAL, AdminState.UP)
        logical_host = replace(config.devices[1], ports=(logical_port,))
        with self.assertRaisesRegex(ConfigError, "Incompatible link medium"):
            replace(config, devices=(config.devices[0], logical_host))

    def test_cable_rejects_identical_or_occupied_endpoints(self):
        config = topology()
        with self.assertRaisesRegex(ConfigError, "endpoints must be distinct"):
            replace(config.links[0], b=A)
        other = replace(config.links[0], link_id="link-2", b=Endpoint("c", "eth0"))
        with self.assertRaisesRegex(ConfigError, "Port already has a cable"):
            replace(config, devices=(*config.devices, device("c")), links=(*config.links, other))

    def test_device_and_port_reject_unadvertised_capabilities(self):
        host = device("a")
        with self.assertRaisesRegex(ConfigError, "Unsupported device capabilities"):
            replace(host, capabilities={"routing"})
        with self.assertRaisesRegex(ConfigError, "Unsupported port capabilities"):
            replace(host.ports[0], capabilities={"wireless"})
        enabled_port = replace(host.ports[0], capabilities={"dot1q"})
        enabled = replace(host, capabilities={"console"}, ports=(enabled_port,))
        self.assertEqual(enabled.capabilities, {"console"})
        self.assertEqual(enabled.ports[0].capabilities, {"dot1q"})

    def test_module_controls_port_compatibility(self):
        module = ModuleProfile(ProfileRef("network-card", "1"), (COPPER,))
        profile = replace(PROFILE, port_profiles=(LOGICAL,), slots=(ModuleSlot("slot-1", (module,)),))
        port = PortConfig("eth0", COPPER, AdminState.UP, module_slot_id="slot-1")
        installed = ModuleConfig("slot-1", module)
        host = DeviceConfig("a", profile, (port,), PowerState.ON, modules=(installed,))
        self.assertEqual(host.ports[0].module_slot_id, installed.slot_id)
        with self.assertRaisesRegex(ConfigError, "empty module slot"):
            replace(host, modules=())
        with self.assertRaisesRegex(ConfigError, "Incompatible module"):
            replace(host, modules=(replace(installed, profile=replace(module, port_profiles=(LOGICAL,))),))
        with self.assertRaisesRegex(ConfigError, "Unsupported profile"):
            replace(host, ports=(replace(port, profile=LOGICAL),))

    def test_runtime_admin_oper_and_initial_power_invariants(self):
        with self.assertRaisesRegex(ConfigError, "administratively down"):
            PortRuntime(A, AdminState.DOWN, OperState.UP)
        with self.assertRaisesRegex(ConfigError, "stable state"):
            replace(device("a"), initial_power=PowerState.REBOOTING)
        config = ConfigSnapshot("rev-1", (
            device("a", admin=AdminState.DOWN),
            device("b", power=PowerState.OFF),
            device("c"),
        ), ())
        runtime = ScenarioRuntime(config, ScenarioRef("scenario", "rev-1", 0))
        self.assertEqual(runtime.port(A).oper_state, OperState.DOWN)
        self.assertEqual(runtime.port(B).oper_state, OperState.DOWN)
        self.assertEqual(runtime.port(Endpoint("c", "eth0")).oper_state, OperState.UNKNOWN)

    def test_invalid_identifiers_and_revision_references(self):
        for bad in ("", " a", "a\n", "é", 100):
            with self.subTest(identifier=bad), self.assertRaises(ConfigError):
                Endpoint(bad, "eth0")
        config = topology()
        with self.assertRaises(ConfigError):
            replace(config, revision_id="")
        with self.assertRaisesRegex(ConfigError, "differs from"):
            ScenarioRuntime(config, ScenarioRef("scenario", "rev-2", 0))
        with self.assertRaises(KernelError) as raised:
            EventKernel(config, "scenario", revision_id="rev-2", seed=0,
                        limits=KernelLimits(10, 10, 10, 128), actors={})
        self.assertEqual(raised.exception.code, ErrorCode.REVISION_MISMATCH)

    def test_configuration_and_runtime_inspection_are_immutable(self):
        media = {"copper"}
        port_profile = replace(COPPER, media=media)
        profiles = [port_profile]
        profile = replace(PROFILE, port_profiles=profiles)
        ports = [PortConfig("eth0", port_profile, AdminState.UP)]
        devices = [DeviceConfig("a", profile, ports, PowerState.ON)]
        config = ConfigSnapshot("rev-1", devices, [])
        runtime = ScenarioRuntime(config, ScenarioRef("scenario", "rev-1", 0))
        media.clear()
        profiles.clear()
        ports.clear()
        devices.clear()
        self.assertEqual(config.devices[0].ports[0].profile.media, frozenset({"copper"}))
        self.assertEqual(config.devices[0].profile.port_profiles, (port_profile,))
        self.assertEqual(runtime.port(A).admin_state, AdminState.UP)
        with self.assertRaises(FrozenInstanceError):
            config.devices[0].ports[0].admin_state = AdminState.DOWN
        with self.assertRaises(FrozenInstanceError):
            runtime.snapshot().ports[0].oper_state = OperState.UP


class InspectAdapter:
    @property
    def parser(self):
        return self

    def parse(self, text, context):
        if text != "inspect power":
            return CLIError(CLIErrorCode.UNSUPPORTED_COMMAND, "Unknown command")
        return CommandAST(("inspect", "power"))

    def validate(self, command, context, device):
        if context.mode != "exec":
            return CLIError(CLIErrorCode.INVALID_MODE, "Requires exec mode")
        if "console" not in device.capabilities:
            return CLIError(CLIErrorCode.UNSUPPORTED_CAPABILITY, "Console is disabled")
        return None

    def evaluate(self, command, context, config, runtime):
        device = next(device for device in runtime.devices if device.device_id == context.device_id)
        return CommandOutput(device.power.value)


class CLITests(unittest.TestCase):
    def setUp(self):
        self.config = topology()
        self.ref = ScenarioRef("scenario", "rev-1", 0)
        self.runtime = ScenarioRuntime(self.config, self.ref).snapshot()
        self.context = CommandContext(self.ref, "a", "exec", 0)

    def test_unsupported_cli_has_no_fictional_output(self):
        response = CLI().submit("show ip route", self.context, self.config, self.runtime)
        self.assertIsInstance(response, CLIError)
        self.assertIs(response.code, CLIErrorCode.UNSUPPORTED_COMMAND)
        self.assertTrue(response.message)

    def test_cli_rejects_stale_or_mismatched_inputs(self):
        cli = CLI()
        cases = (
            (replace(self.context, scenario=replace(self.ref, generation=1)), self.config,
             CLIErrorCode.STALE_SCENARIO),
            (self.context, replace(self.config, revision_id="rev-2"), CLIErrorCode.REVISION_CONFLICT),
            (replace(self.context, device_id="missing"), self.config, CLIErrorCode.UNKNOWN_DEVICE),
        )
        for context, config, expected in cases:
            with self.subTest(expected=expected):
                self.assertIs(cli.submit("inspect", context, config, self.runtime).code, expected)

    def test_cli_runs_parse_validation_and_real_runtime_inspection(self):
        cli = CLI({DIALECT: InspectAdapter()})
        response = cli.submit("unknown", self.context, self.config, self.runtime)
        self.assertIs(response.code, CLIErrorCode.UNSUPPORTED_COMMAND)
        response = cli.submit("inspect power", self.context, self.config, self.runtime)
        self.assertIs(response.code, CLIErrorCode.UNSUPPORTED_CAPABILITY)
        enabled = replace(self.config.devices[0], capabilities={"console"}, initial_power=PowerState.OFF)
        config = replace(self.config, devices=(enabled, self.config.devices[1]))
        runtime = ScenarioRuntime(config, self.ref).snapshot()
        response = cli.submit("inspect power", replace(self.context, mode="config"), config, runtime)
        self.assertIs(response.code, CLIErrorCode.INVALID_MODE)
        self.assertEqual(cli.submit("inspect power", self.context, config, runtime), CommandOutput("off"))

    def test_transaction_is_revision_checked_without_mutating_current_config(self):
        candidate = replace(self.config, revision_id="rev-2", devices=(device("c"),), links=())
        tx = ConfigTransaction("rev-1", candidate)
        self.assertIsNone(tx.validate_against(self.config))
        self.assertIs(tx.validate_against(candidate).code, CLIErrorCode.REVISION_CONFLICT)
        self.assertEqual(tuple(device.device_id for device in self.config.devices), ("a", "b"))
        with self.assertRaises(ConfigError):
            ConfigTransaction("rev-1", self.config)
        with self.assertRaises(ConfigError):
            CommandAST("inspect")
