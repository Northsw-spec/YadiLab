# Release notes v0.24.0 — Capability / Domain Pack Runtime Availability

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.24.0 continues from exact-byte verified v0.23.0.

Added:
- trusted `CapabilityPackRegistry`;
- exact capability-pack availability/version validation before Runtime play;
- the same gate for Builder Runtime Preview;
- built-in registry/catalog consistency verification;
- explicit Runtime diagnostics for unavailable pack/version and duplicate exact locks;
- resolved capability-pack metadata in package-session information.

Verification highlights:
- CapabilityPackRegistry: 25 functional + 11 adversarial assertions PASS;
- Browser package-session: 20 functional + 18 adversarial assertions PASS;
- Browser adversarial: 44 assertions PASS;
- complete Foundation regression through Phase 24 PASS before packaging.

Scenario packages remain data-only and cannot inject executable capability code. Dependency-resolved rendered-browser and real Parrot OS x86-64 acceptance remain external gates.
