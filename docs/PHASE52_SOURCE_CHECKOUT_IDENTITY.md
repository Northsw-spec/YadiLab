# Phase 52 — exact source-checkout identity binding

Phase 51 bound the offline snapshot consumer to the producer's Linux x86-64 Node/npm execution environment. Phase 52 closes the remaining source-side reproducibility gap: a sealed dependency snapshot must now be consumed by the exact YadiLab source checkpoint it was prepared for, not merely any checkout that happens to retain the same dependency declarations.

## Gap closed

Before Phase 52 the snapshot manifest bound `package.json`, the browser dependency policy and the npm-generated lockfile. Application code, build scripts, verifier code, tests, schemas and other source files could change without necessarily changing those dependency files. Such a different checkpoint could therefore pass the dependency snapshot source contract.

## Source-checkout identity

The snapshot manifest schema is now **1.1.0** and records a deterministic source-checkout identity containing:

- identity schema version;
- SHA-256 over a canonical ordered file table;
- exact regular-file count;
- exact total source bytes;
- each included file's relative path, size, Unix permission mode and SHA-256 as inputs to the aggregate digest.

Generated/developer-local state is excluded from the identity: `.git`, `node_modules`, the producer-generated root `package-lock.json`, generated `distribution/`, `ui/dist`, `ui/dist-shell`, top-level `dist-*-test` directories and known smoke/acceptance output files. Everything else in the release checkout is source-bound.

Source symlinks or unsupported filesystem entries fail closed.

## Consumer rule

`verify_offline_dependency_snapshot.mjs` recomputes the current checkout identity before npm is allowed to consume transferred cache bytes. Any path, content, size, mode, file-count or aggregate-byte drift is rejected as `SNAPSHOT_SOURCE_CHECKOUT_MISMATCH`.

This is a reproducibility/integrity binding, not publisher authentication. Trusted acquisition of the source checkpoint and snapshot remains an external trust requirement.
