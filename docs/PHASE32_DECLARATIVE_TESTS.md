# Phase 32 — Remaining Foundation Declarative Tests / Engine 0.5.0

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 32 closes the remaining named declarative test gaps from Masterprompt §28 while preserving the bounded deterministic simulator contract. No packet emulator, SIEM backend, hypervisor API, or real backup system is introduced. Outcomes derive only from declared scenario/runtime state.

## Added trusted Engine evaluators

### `network.port_scan`
Required: `from`, `to`, and either integer `port` or non-empty integer `ports[]` (1..65535). Optional `protocol`: `tcp` or `udp`, default `tcp`.

- `TRUE`: at least one requested port is proven reachable/listening.
- `FALSE`: every requested port is proven unreachable/not listening.
- `UNKNOWN`: no port is proven reachable and at least one result lacks sufficient evidence.

### `identity.password_audit`
Required: `target`. Default evidence path: `properties.passwordPolicy.compliant`. Default expected value: `true`. Optional `path` and boolean `equals` may override the defaults.

### `virtualization.management_exposure`
Required: `from`, `to`, integer `port`. Optional `protocol`: `tcp` or `udp`, default `tcp`. Uses the same deterministic reachability/policy/listener semantics as NetworkEngine. `TRUE` means the declared management endpoint is proven exposed from the requested source.

### `logging.visibility_test`
Required: `target`. Default evidence path: `properties.logging.visible`. Default expected value: `true`. Optional `path` / boolean `equals` override.

### `logging.alert_test`
Required: `target`. Default evidence path: `properties.logging.alerting`. Default expected value: `true`. Optional `path` / boolean `equals` override.

### `backup.restore_test`
Required: `target`. Default evidence path: `properties.backup.restoreTested`. Default expected value: `true`. Optional `path` / boolean `equals` override.

For all boolean audit types, absent/non-boolean evidence yields `UNKNOWN`, never a fabricated `FALSE`.

## Compiler hardening

- Known Foundation test parameters are statically validated before Runtime.
- Resource references in these test parameters must resolve.
- A test type that is merely claimed by a capability prefix but has no trusted evaluator is rejected with `TEST_TYPE_UNIMPLEMENTED`.
- Test semantics contribute to normalized `minimumEngineVersion`: existing Phase-3/4 test evaluators require at least Engine 0.4.0; the six Phase-32 evaluators require Engine 0.5.0.
- Browser and CLI production compiler contexts now use the actual `ENGINE_VERSION` constant rather than hard-coded baselines.

## Version boundary

Engine version is advanced from 0.4.0 to **0.5.0** because previously unsupported named tests now produce deterministic results. Runtime package compatibility continues to use the normal minimum-Engine-version gate.
