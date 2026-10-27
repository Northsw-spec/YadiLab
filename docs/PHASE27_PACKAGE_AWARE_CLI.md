# Phase 27 — Package-aware CLI / Safe Unpack

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 27 continues from exact-byte verified v0.26.0.

## Implemented

- binary-aware CLI I/O boundary separated from JSON/text I/O;
- `.yadilab` package input is routed through `SafePackageIO`, never parsed as JSON;
- `app inspect --input <scenario.yadilab>` returns validated package/scenario metadata;
- `app test --input <scenario.yadilab>`:
  - student distributions run initial-state expectations without pretending a canonical solution exists;
  - author distributions with `solution.json` run full canonical regression;
- `app render --input <scenario.yadilab> --output <preview.svg>` uses validated embedded `layout.json`, with optional explicit layout override;
- `app unpack --input <scenario.yadilab> --output <directory>` writes only files that already passed PackageIO path, size, hash, manifest and file-set verification;
- PackageIO now preserves exact `manifest.json` bytes so unpack does not need to synthesize manifest content;
- current-version `app migrate` on a package is a byte-identical no-op when no schema change is required;
- if a future migration changes scenario content, package migrate fails closed with `PACKAGE_MIGRATION_REPACK_REQUIRED` until safe repack of assets/docs/solution is explicitly implemented;
- package execution additionally gates normalized schema, schema version, Engine minimum version, exact capability pack availability and layout/scenario identity.

## Verification boundary

The command semantics are fully tested through the same `SafePackageIO` abstraction using `MemoryArchiveBackend`. This proves package command routing and all PackageIO/runtime gates without introducing a second ZIP implementation.

The real Node binary path remains `ZipJsArchiveBackend`, as required by the locked architecture. `@zip.js/zip.js` is not installed in this sandbox because npm registry resolution is unavailable, so actual ZIP-byte execution is **BLOCKED**, not claimed PASS here.
