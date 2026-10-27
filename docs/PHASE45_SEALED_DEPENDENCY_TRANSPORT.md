# Phase 45 — Sealed offline dependency transport

YadiLab Foundation v0.45.0 continues directly from the verified v0.44.0 development checkpoint. Phase 44 verifies a transferred dependency snapshot directory. Phase 45 closes the transport gap by defining one canonical, fail-closed archive format and a one-command producer/import path.

## Goal

The dependency handoff must not rely on manually copying a loose npm cache tree. The trusted online Linux x86-64 preparation host can now create one sealed transport ZIP plus a SHA-256 sidecar. The offline Linux/Parrot side verifies the sidecar, safely extracts the ZIP, then runs the complete Phase 44 source/snapshot verifier **before npm sees any transferred cache bytes**.

The intended external continuation is now:

1. on a trusted Internet-connected Linux x86-64 host, run `prepare_offline_browser_snapshot.sh` against the exact v0.45.0 source checkout;
2. transfer the resulting `.zip` and adjacent `.zip.sha256` files;
3. on the offline Linux/Parrot builder, pass the ZIP directly to `install_offline_browser_dependencies.sh`;
4. verify transport SHA-256, canonical ZIP structure and every inner manifest hash;
5. verify exact Phase 44 source/dependency-policy/package-lock binding;
6. run `npm cache verify` and `npm ci --offline`;
7. build/verify/promote the browser release;
8. execute the Phase 43 real Builder -> Runtime browser acceptance on Parrot OS x86-64.

## Canonical transport format

`scripts/pack_offline_dependency_snapshot.py` emits a deterministic ZIP with:

- only regular files;
- no directory entries or symlinks;
- `ZIP_STORED` entries only (no compressed-data bomb surface);
- fixed 1980-01-01 timestamps;
- fixed Unix regular-file mode `0644`;
- empty ZIP comment and entry extras;
- canonical casefold path ordering;
- no duplicate or case-colliding paths;
- exact file set from `snapshot-manifest.json` plus the manifest itself.

For identical snapshot bytes, two independent pack operations must produce byte-identical ZIP bytes.

## Safe import

`scripts/import_offline_dependency_snapshot.sh` requires the adjacent `.zip.sha256` sidecar. The sidecar is parsed as data, not passed to `sha256sum -c`, so an attacker-controlled filename in the sidecar cannot redirect verification to another path. The filename must equal the ZIP basename and the digest must match the actual archive.

`scripts/extract_offline_dependency_snapshot.py` preflights the complete central directory before extraction and rejects:

- absolute paths, traversal, backslashes or invalid relative names;
- duplicate and case-colliding entries;
- symlink/non-regular entries;
- compressed entries;
- non-canonical timestamps/modes/order;
- archive comments/extras outside the canonical format;
- oversized files, file counts or total declared bytes;
- missing/extra files relative to the inner manifest;
- size/hash mismatch for any extracted snapshot file;
- non-empty extraction destinations.

Only after this transport layer passes is `verify_offline_dependency_snapshot.mjs` allowed to validate the extracted snapshot against the current source checkout.

## One-command online preparation

```bash
bash scripts/prepare_offline_browser_snapshot.sh /safe/path/YadiLab_dependencies_v0.45.0.zip
```

The output must be outside the source checkout. The command internally performs the Phase 44 cache preparation, package-lock verification, npm-cache verification, snapshot manifest creation/verification, then seals the result and writes a portable basename-only SHA-256 sidecar.

## Offline consumption

```bash
bash scripts/install_offline_browser_dependencies.sh /transfer/YadiLab_dependencies_v0.45.0.zip
```

The installer still accepts an already-extracted Phase 44 directory for compatibility, but the sealed ZIP is the preferred handoff.

## Verification in this sandbox

- dependency/browser-build gate: **31 assertions PASS**;
- dependency/browser-build adversarial suite: **34 assertions PASS**;
- Phase 44 offline snapshot suite: **28 assertions PASS**;
- Phase 45 sealed transport suite: **42 assertions PASS**.

The Phase 45 suite verifies byte-identical repacking, successful safe import, basename-only sidecar binding, and fail-closed rejection of duplicate entries, traversal, deflate/compression, extra or missing files, symlinks, bad timestamps, payload tampering, case collisions, unsorted archives, non-empty extraction destinations, missing/wrong sidecars, non-ZIP inputs and overwrite attempts.

## External boundary

The current sandbox still cannot create the **real** npm snapshot because npm registry connectivity is unavailable and no complete cache exists. It also is Debian rather than Parrot OS. Therefore Phase 45 improves the path to the external gate but does not convert that external gate into a PASS.

A SHA-256 sidecar and inner manifest provide corruption/integrity detection, not publisher authenticity. A malicious party able to replace the archive and sidecar together can recompute both. Trusted acquisition/transfer provenance remains an external trust requirement.
