# Phase 50 — sealed-snapshot producer coherence and offline replay

Phase 50 continues directly from the exact v0.49.0 checkpoint under Masterprompt v1.2 VERIFIED / LOCKED.

## Gap closed

The dependency snapshot already hash-inventoried `development-platform.json`, but earlier verification treated those bytes as opaque. A snapshot could therefore contain producer metadata claiming another platform/architecture or a different Node/npm identity while the manifest separately claimed Linux x86-64. The file was integrity-protected, but its meaning was not enforced.

A second producer-side gap was that the online preparation path populated an npm cache and verified the first installed `node_modules` tree, but did not prove that the populated cache alone could reproduce the install without network access before the snapshot was transferred.

## Phase 50 contract

`development-platform.json` is now parsed and must contain:

- `platform: "linux"`;
- `arch: "x86_64"`;
- a syntactically valid `vMAJOR.MINOR.PATCH` Node identity;
- a syntactically valid `MAJOR.MINOR.PATCH` npm identity;
- a non-empty, single-line kernel identity.

The snapshot manifest derives `target` and `preparedWith` from that validated metadata. Verification fails closed if the manifest and platform metadata diverge. Explicit producer Node/npm values supplied during manifest generation must also agree with the metadata file.

The trusted online producer now performs two installs:

1. online `npm ci` to populate the dedicated snapshot cache, followed by readiness and executable toolchain checks;
2. cache verification, destruction of the first `node_modules`, then a fresh strict `npm ci --offline` using only the snapshot cache, followed again by readiness and executable toolchain checks.

Only after the offline replay succeeds may the lock, producer metadata and snapshot manifest be sealed for transfer.

## What this does not claim

Phase 50 does not fabricate dependency bytes and does not make the current disconnected Debian environment dependency-resolved. A real snapshot still has to be produced on a trusted internet-connected Linux x86-64 host from the exact source checkpoint. Parrot acceptance and the real Chromium Builder→Runtime/offline-reload proof remain external gates.
