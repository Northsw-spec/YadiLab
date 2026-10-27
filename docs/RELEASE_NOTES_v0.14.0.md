# Release notes v0.14.0 — browser package session

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.14.0 continues directly from v0.13.0.

Added:

- safe `.yadilab` package -> Runtime browser-session controller;
- normalized scenario and layout validation at package-to-Runtime boundary;
- Engine minimum-version compatibility gate;
- explicit default denial of author packages in student Runtime;
- canonical solution non-leakage into Runtime state;
- package asset/document metadata classification;
- React entry integration for packaged-lab opening;
- layout contract support in the Ajv validator surface;
- browser and persistence typecheck coverage for the PackageIO dependency boundary.

Verification:

- browser package-session: 18 assertions PASS;
- package-session adversarial: 14 assertions PASS;
- full Foundation regression: PASS.

The dependency-resolved rendered browser application and Parrot target remain explicit external gates.
