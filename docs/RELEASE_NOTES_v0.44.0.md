# Release notes v0.44.0 — offline dependency snapshot attestation

YadiLab Foundation v0.44.0 continues directly from v0.43.0 and preserves Masterprompt v1.2 as the VERIFIED / LOCKED architecture agreement.

## Added

- complete offline dependency-snapshot inventory (`snapshot-manifest.json`);
- exact source `package.json`, dependency-policy, and package-lock SHA-256 binding;
- per-file size + SHA-256 inventory for the transferred npm cache and handoff files;
- target/platform and lock-closure metadata;
- standalone snapshot creation and verification CLIs;
- fail-closed snapshot verification before `npm ci --offline`;
- 28 targeted functional/adversarial snapshot assertions;
- automatic browser-release verification after a successful offline dependency install/build.

## Preserved

All prior Foundation regressions, browser-release promotion controls, and the Phase 43 real Chromium Builder -> Runtime acceptance workflow remain in the verification path. Production runtime still requires no Node/npm tooling after built assets exist.

## Boundary

This sandbox still cannot produce the real npm dependency snapshot: registry access is unavailable and the npm cache is empty. Therefore v0.44.0 is a **VERIFIED DEVELOPMENT CHECKPOINT**, not a verified product release. The genuine dependency-resolved browser bundle and real Parrot OS x86-64 browser acceptance remain BLOCKED/unclaimed until executed on the required environments.
