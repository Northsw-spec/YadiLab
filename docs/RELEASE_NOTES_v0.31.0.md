# Release notes v0.31.0 — Strict Custom SVG Sanitizer

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.31.0 continues from exact-byte verified v0.30.0.

Added:
- strict passive custom SVG sanitizer;
- image/svg+xml support under assets/ after content validation;
- same sanitizer enforced on PackageIO write and read;
- canonical SVG namespace enforcement;
- active/remote/data/reference-capable SVG constructs fail closed.

Verification highlights:
- PackageIO functional: 25 assertions PASS;
- PackageIO adversarial: 59 assertions PASS;
- safe passive custom SVG survives write/read byte-identically;
- attacker-built correctly SHA-256-hashed package containing script SVG is rejected on read;
- complete Foundation regression through Phase 31 PASS before packaging.

Custom SVG remains untrusted scenario content and is never treated as a trusted built-in asset.
