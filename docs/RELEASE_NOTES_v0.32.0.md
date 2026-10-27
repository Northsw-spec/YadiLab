# Release notes v0.32.0 — Remaining Foundation Declarative Tests / Engine 0.5.0

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.32.0 continues directly from exact-byte verified v0.31.0.

Added:
- deterministic evaluators for `network.port_scan`;
- `identity.password_audit`;
- `virtualization.management_exposure`;
- `logging.visibility_test`;
- `logging.alert_test`;
- `backup.restore_test`;
- static compiler validation for the new test parameters/references;
- fail-closed rejection of capability-claimed test types with no trusted Engine evaluator;
- test-semantic minimum-Engine-version calculation;
- production browser/CLI compiler baselines tied to `ENGINE_VERSION`.

Engine version: **0.5.0**.

Verification highlights before packaging:
- Engine functional: 86 assertions PASS;
- Engine adversarial: 42 assertions PASS;
- Compiler functional: 61 assertions PASS;
- Compiler adversarial: 40 assertions PASS;
- complete Foundation regression through Phase 32 PASS.

The six new tests remain bounded deterministic simulation over declared state. Missing evidence propagates `UNKNOWN`; no external infrastructure is contacted.
