# Release notes v0.28.0 — Third-party License Inventory / Release Provenance

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.28.0 continues from exact-byte verified v0.27.0.

Added:
- exact dependency/license policy;
- deterministic generated THIRD_PARTY_NOTICES;
- machine-readable third-party inventory;
- esbuild-metafile-driven resolved bundle inventory path;
- fail-closed missing-license and version-drift checks;
- notices/inventory shipping in the loopback distribution and SHA-256 manifest.

Verification highlights:
- notices/inventory: 19 functional assertions PASS;
- notices/inventory adversarial: 8 assertions PASS;
- launcher smoke verifies shipped notices/inventory and checksums;
- complete Foundation regression through Phase 28 PASS before packaging.

Dependency-resolved bundle inventory remains externally BLOCKED in this sandbox until the pinned npm dependency graph can be installed.
