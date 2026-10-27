# Phase 44 — Offline dependency snapshot attestation

YadiLab Foundation v0.44.0 continues directly from the verified v0.43.0 development checkpoint. This phase does **not** claim that the real browser dependency tree has been resolved in the current sandbox. It hardens the handoff that will be used when the trusted npm cache can actually be prepared.

## Goal

Turn the Phase 37 developer cache handoff into a fail-closed, self-describing snapshot that can be independently checked **before** `npm ci --offline` consumes transferred bytes.

The intended continuation remains:

1. prepare the exact dependency snapshot on a trusted Internet-connected Linux x86-64 development host;
2. transfer the snapshot to the disconnected build/Parrot path;
3. verify the complete snapshot and exact source dependency contract;
4. run `npm ci --offline` using the transferred cache;
5. build and independently verify the browser release;
6. promote the verified browser assets into the loopback distribution;
7. run the Phase 43 real Chromium Builder -> Runtime workflow on Parrot OS x86-64.

## Snapshot contract

`prepare_offline_browser_cache.sh` now emits:

- `npm-cache/` — npm's transferred cache;
- `package-lock.json` — npm-generated lockfile;
- `SHA256SUMS.txt` — compatibility checksum for the lockfile;
- `development-platform.json` — preparation Node/npm/Linux metadata;
- `snapshot-manifest.json` — Phase 44 complete inventory and source-binding manifest.

The Phase 44 manifest binds the snapshot to:

- Linux x86-64 target development architecture;
- the exact current `package.json` bytes;
- the exact browser dependency policy bytes;
- the exact transferred `package-lock.json` bytes;
- the validated package-lock closure count;
- every regular snapshot file except the manifest itself, with exact relative path, byte size, and SHA-256;
- total file count and total byte count.

## Fail-closed verifier

`verify_offline_dependency_snapshot.mjs` rejects, among other cases:

- malformed/unsupported manifest contract;
- wrong platform target;
- source `package.json` or dependency-policy drift;
- lockfile drift or invalid dependency closure;
- modified cache bytes;
- missing or unlisted files;
- duplicate or non-canonical manifest entries;
- unsafe relative paths/backslashes/traversal;
- symlinks and unsupported filesystem entry types;
- empty npm cache;
- forged file counts, byte counts, or lock package counts.

`install_offline_browser_dependencies.sh` runs this verifier **before** npm consumes the transferred cache. It then requires `npm cache verify`, exact lock parity, the existing package-lock policy gate, and `npm ci --offline`. Browser build, browser release verification, loopback distribution construction, and distribution checksum verification follow only after those dependency gates pass.

## Verification in the current sandbox

- dependency/browser-build gate: **31 assertions PASS**;
- dependency/browser-build adversarial suite: **34 assertions PASS**;
- Phase 44 offline snapshot suite: **28 assertions PASS**;
- whole Foundation v0.1-v0.44 regression: **PASS / exit 0**;
- live browser-workflow ZIP selftest: **5 fixture scenarios PASS**;
- Phase 43 fail-closed browser workflow contract: **27 assertions PASS**.

## External boundary

The current sandbox still has an empty npm cache and no npm-registry connectivity. It therefore has no genuine npm-generated project lockfile, installed dependency closure, or built `ui/dist` React application. The host is Debian rather than Parrot OS.

Accordingly these remain correctly **BLOCKED (exit 77)** here:

- genuine dependency-resolved browser build;
- ready browser-release verification;
- real Parrot OS x86-64 acceptance;
- real Phase 43 interactive Chromium Builder -> Runtime workflow.

Phase 44 is an integrity/reproducibility handoff, **not a publisher-authenticity mechanism**. A malicious party able to replace the entire snapshot and its manifest can recompute the manifest; trusted transfer/provenance remains an external requirement. npm's lockfile SRI and YadiLab's exact dependency policy remain separate gates.
