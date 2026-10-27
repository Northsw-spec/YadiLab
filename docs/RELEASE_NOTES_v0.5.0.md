# Release notes v0.5.0 — PackageIO Phase 5

YadiLab Foundation v0.5.0 continues directly from v0.4.0.

## Added

- generic PackageIO / ArchiveBackend boundary;
- zip.js production adapter source;
- student and author package builders;
- canonical solution stripping from student packages;
- separate `solution.json` for author distributions;
- SHA-256 manifest integrity;
- exact archive/manifest file-set verification;
- path traversal and absolute-path defenses;
- duplicate and case-collision defenses;
- compressed/decompressed/single-file limits;
- compression-ratio guard;
- conservative MIME/asset policy;
- fail-closed custom SVG policy;
- manifest/scenario/profile/capability cross-checks;
- PackageIO functional and adversarial suites.

## Preserved

All Phase 0-4 schema, compiler, Engine and canonical-regression tests remain in the same Foundation test command.

## Environment limitation

The real zip.js package is declared but is not installed in this sandbox. The adapter is typechecked against its required interface; the backend-independent PackageIO behavior is fully exercised. Real zip.js runtime smoke testing remains required before end-to-end ZIP runtime verification.
