# Release notes v0.15.0 — browser package export

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.15.0 continues directly from v0.14.0.

Added:

- Builder -> student/author `.yadilab` package export controller;
- mandatory PackageIO read-back verification before browser delivery;
- stale/orphan/duplicate layout export guards;
- student solution-leak and author solution-loss detection;
- browser Blob download descriptor;
- React application source buttons for student/author package export.

Verification:

- browser package-export: 17 assertions PASS;
- package-export adversarial: 16 assertions PASS;
- full Foundation regression: PASS.

Rendered dependency-resolved browser execution and Parrot target acceptance remain explicit external gates.
