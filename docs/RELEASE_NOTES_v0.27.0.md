# Release notes v0.27.0 — Package-aware CLI / Safe Unpack

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.27.0 continues from exact-byte verified v0.26.0.

Added:
- binary CLI I/O and package input routing;
- SafePackageIO-gated package inspect/test/render/unpack;
- student initial-state package testing and author full canonical regression;
- embedded package layout rendering;
- faithful raw-manifest safe unpack;
- current-version byte-identical package migration;
- fail-closed future package migration boundary;
- package schema/Engine/capability/layout compatibility gates before CLI execution.

Verification highlights:
- CLI: 68 functional + 22 adversarial assertions PASS;
- PackageIO: 23 functional + 42 adversarial assertions PASS;
- Browser package-session regression: 20 functional + 20 adversarial assertions PASS;
- complete Foundation regression through Phase 27 PASS before packaging.

Boundary:
- package command semantics are verified via SafePackageIO + MemoryArchiveBackend;
- real ZIP-byte execution via the pinned `ZipJsArchiveBackend` remains BLOCKED in this sandbox because `@zip.js/zip.js` is not installed/resolvable here;
- no alternate ZIP parser was introduced.
