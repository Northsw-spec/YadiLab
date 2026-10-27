# Phase 14 — browser package session

Phase 14 continues directly from the exact v0.13.0 checkpoint. It connects the already verified PackageIO layer to the browser Runtime boundary without changing package semantics or making ZIP state canonical.

## Runtime open path

The new browser path is:

```text
File/Blob (.yadilab)
  -> PackageIO.read()
  -> archive/path/size/hash/manifest safety
  -> normalized scenario validation
  -> Engine version compatibility
  -> layout validation + scenario identity check
  -> Engine initial state
  -> RuntimeWorkspace
```

The Runtime starts from the normalized package scenario. It does not reconstruct scenario source, editor history, or arbitrary package scripts.

## Student/author boundary

Student Runtime opening rejects author packages by default. An instructor caller must explicitly set `allowAuthorPackage: true` to inspect an author package.

Even when an author package is explicitly opened:

- `solution.json` is not injected into `RuntimeWorkspace.scenario`;
- Runtime Engine state contains no canonical solution;
- only a boolean `authorSolutionPresent` metadata fact is exposed by the package-session result.

This preserves the rule that canonical solution material is not part of ordinary student Runtime state.

## Validation

PackageIO remains responsible for:

- archive traversal/collision safety;
- compressed/decompressed limits;
- MIME/path policy;
- exact archive/manifest file-set agreement;
- SHA-256/size integrity;
- manifest/scenario identity and capability/profile locks;
- student solution leakage prevention.

The browser package session additionally requires injected authoritative validators for:

- normalized scenario schema;
- layout schema.

The validator contract now includes `layout` as a first-class schema kind.

The browser session also rejects scenarios whose `minimumEngineVersion` is newer than the current deterministic Engine.

## UI source

The dependency-gated React entry now includes a packaged-lab file picker using the centrally configured scenario extension. It constructs SafePackageIO with the zip.js backend only at the UI integration edge. PackageIO and Engine remain generic and independently tested.

## Verification

Phase 14 adds:

- 18 browser package-session assertions;
- 14 adversarial package-session assertions;
- PackageIO error propagation checks;
- author-package default-deny check;
- Engine-version incompatibility check;
- normalized/layout validator rejection checks;
- layout/scenario identity mismatch check;
- student solution non-leakage check;
- Runtime operation after package open.

The full Foundation regression remains mandatory.

## Boundary

Actual zip.js execution in the rendered browser bundle remains blocked in the current sandbox because the genuine dependency graph is not installed. The same controller path is verified with the generic MemoryArchive backend. No claim is made that the blocked browser dependency gate has passed.
