# Phase 51 — snapshot consumer environment coherence

Phase 50 bound a sealed dependency snapshot to the Linux x86-64 producer environment that created and replayed it. Phase 51 closes the other side of that reproducibility boundary: the offline consumer must execute the snapshot with the same Node and npm tool identities recorded by the producer.

## Fail-closed rule

Before npm is allowed to inspect the transferred cache or run `npm ci --offline`, the installer now checks:

- consumer platform is Linux;
- consumer architecture is x86-64 (`process.arch=x64` is normalized to `x86_64`);
- consumer `node --version` exactly equals `snapshot-manifest.json -> preparedWith.node`;
- consumer `npm --version` exactly equals `snapshot-manifest.json -> preparedWith.npm`.

A mismatch exits 77/BLOCKED. The installer does not silently accept a nearby Node/npm release, `--prefer-offline`, or a regenerated lockfile.

## Why this matters

A package-lock and npm cache alone do not fully identify the installation engine. Different npm/Node releases can differ in lockfile interpretation, optional dependency handling, lifecycle behavior, and generated installation metadata. Phase 51 therefore makes the sealed snapshot a producer/consumer toolchain contract rather than only a file transport.

## Verification

- functional consumer-environment checks;
- adversarial platform/architecture/Node/npm mismatch checks;
- static installer-order checks proving the environment gate runs before npm cache consumption and strict-offline installation;
- prior producer, snapshot, transport, native optional dependency, and executable toolchain suites remain mandatory regressions.
