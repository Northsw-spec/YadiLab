# Release notes v0.29.0 — Scenario Certification Pipeline

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.29.0 continues from exact-byte verified v0.28.0.

Added:
- reusable headless Scenario Certification Pipeline;
- mandatory canonical initial/solved regression before verified package export;
- semantic layout hierarchy/geometry certification;
- Engine/capability Runtime compatibility gate before packaging and after readback;
- exact PackageIO readback checks for scenario/layout/distribution/solution policy;
- explicit certification certificate attached to successful Builder package exports;
- Builder `selfVerified: true` now means full certification, not only package readback.

Verification highlights:
- scenario certification: 11 functional assertions PASS;
- scenario certification adversarial: 7 assertions PASS;
- browser package-export: 20 functional + 20 adversarial assertions PASS;
- complete Foundation regression through Phase 29 PASS before packaging.

External boundaries remain unchanged: dependency-resolved browser/zip.js execution and real Parrot OS acceptance are still fail-closed external gates in this environment.
