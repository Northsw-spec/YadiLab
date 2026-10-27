# Release notes v0.25.0 — Explicit Versioning / Migration Framework

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.25.0 continues from exact-byte verified v0.24.0.

Added:
- explicit current scenario schema version contract;
- deterministic `MigrationRegistry`;
- `app migrate` CLI command;
- version-aware CLI validate/test;
- compiler fail-closed schema compatibility gate;
- browser Runtime fail-closed schema compatibility gate.

Verification highlights:
- versioning/migration: 15 functional + 12 adversarial assertions PASS;
- CLI: 45 functional + 14 adversarial assertions PASS;
- complete Foundation regression through Phase 25 PASS before packaging.

No historical migration is fabricated. Unknown historical/future versions remain blocked until an explicit migration step exists.
