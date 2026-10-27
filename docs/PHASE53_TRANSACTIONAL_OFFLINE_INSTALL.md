# Phase 53 — transactional offline dependency install

Phase 52 bound each sealed npm snapshot to the exact source checkout. Phase 53 closes the next state-integrity gap: consuming a valid snapshot must not partially mutate the live checkout when npm, bundling, distribution assembly, or final promotion fails.

## Stage-first rule

`install_offline_browser_dependencies.sh` now verifies the sealed snapshot and consumer environment first, then copies only source-identity-controlled files into a sibling staging checkout. The stage preserves file bytes and Unix modes and must reproduce the exact source-checkout identity. `package-lock.json`, `node_modules`, `ui/dist`, and `distribution/` remain generated state and are not copied from the live checkout.

All dependency and build work runs in the stage: `npm ci --offline`, readiness, executable toolchain attestation, full browser bundle, browser release verification, loopback distribution build, and distribution SHA-256 verification. A failure before final promotion leaves live generated state untouched.

## Transactional promotion

Only four generated targets may be promoted after all staged gates pass: `package-lock.json`, `node_modules`, `ui/dist`, and `distribution/linux-x86_64`. Existing targets are first renamed into a sibling transaction backup. Promotion state is recorded in a journal. Ordinary failures trigger immediate rollback; an interrupted process leaves the journal and backups for deterministic recovery on the next installer entry.

Source-controlled files are never transaction targets, so a successful dependency build does not invalidate the Phase 52 source identity.
