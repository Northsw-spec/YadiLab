# Release notes v0.12.0 — Parrot acceptance harness

YadiLab Foundation v0.12.0 continues directly from the exact v0.11.0 checkpoint.

## Added

- fail-closed Parrot OS x86-64 target gate;
- machine-readable local browser acceptance page;
- secure-context probe;
- IndexedDB read/write probe;
- CacheStorage read/write probe;
- service-worker registration/ready probe;
- Chromium-based DOM acceptance gate;
- Firefox headless render gate;
- candidate checksum, loopback-bind, traversal and response-header checks;
- acceptance contract regression test that proves non-Parrot hosts cannot report target PASS;
- dynamic distribution checksums covering all bundled web assets.

## Preserved

All Phase 0-11 contracts, compiler, Engine, regression, PackageIO, CLI, canvas, layout, Builder/Runtime, persistence/PWA, and launcher tests remain in `npm run test:foundation`.

## Current acceptance status

The current build environment identifies as Debian 13, not Parrot OS. The target harness therefore correctly returns `BLOCKED` with exit code 77. This checkpoint is a verified development checkpoint, not a Parrot-verified release.

The full repository TypeScript check remains blocked only by unavailable installed Ajv modules in the sandbox. The isolated typed slices and all Foundation tests pass.
