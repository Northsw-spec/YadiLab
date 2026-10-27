# Release notes v0.34.0 — DNAT / Port-forward-aware NetworkEngine

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.34.0 continues from exact-byte verified v0.33.0.

Added:
- bounded DNAT rule evaluation on transit resources;
- external-port to internal-listener-port translation;
- required/optional NAT policy;
- explainable matched NAT rule and translatedPort result metadata;
- fail-closed malformed/unsupported NAT behavior;
- Engine 0.7.0 and semantic minimum-version gates.

Verification before packaging:
- Engine functional: 99 assertions PASS;
- Engine adversarial: 50 assertions PASS;
- Compiler functional/adversarial: 61 / 40 PASS;
- complete Foundation regression through Phase 34 PASS.

SNAT is not claimed by this checkpoint.
