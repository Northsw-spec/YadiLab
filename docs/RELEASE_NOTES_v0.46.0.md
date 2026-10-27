# Release notes v0.46.0 — executable browser toolchain attestation

YadiLab Foundation v0.46.0 continues directly from the exact verified v0.45.0 ZIP.
Masterprompt v1.2 remains VERIFIED / LOCKED.

## Added

- executable browser-toolchain attestation library;
- fail-closed installed-toolchain command `npm run check:toolchain`;
- React + ReactDOM execution probe;
- React Flow export probe;
- Ajv strict schema compile/validation probe;
- real ELK layout probe;
- zip.js required API export probe;
- exact TypeScript version + transpilation probe;
- exact esbuild version + real TypeScript transform probe, exercising the native
  esbuild execution path;
- direct browser build and offline install integration so the gate cannot be skipped;
- focused Phase 46 functional/adversarial suite.

## Verification

- Phase 46 functional: **12 assertions PASS**;
- Phase 46 adversarial: **20 assertions PASS**;
- Phase 45 transport: **42 assertions PASS**;
- all earlier Foundation suites: PASS (monolithic run reached execution timeout
  after Phase 44; deterministic remaining tail was rerun separately and PASS).

The real dependency tree is still absent in this sandbox, so executable toolchain,
actual React bundle and Parrot acceptance remain correctly BLOCKED. This is a
VERIFIED DEVELOPMENT CHECKPOINT, not a VERIFIED PRODUCT RELEASE.
