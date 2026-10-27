# Release notes v0.13.0 — dependency-locked browser build gate

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.13.0 continues directly from v0.12.0 and adds Phase 13 without rebuilding earlier phases.

Added:

- exact browser dependency policy;
- pinned esbuild build tool declaration;
- deterministic dependency-contract checker;
- fail-closed browser build readiness checker;
- remote runtime URL/CDN guard;
- first real React/React Flow application entry source wired to the existing compiler/Engine/layout/browser layers;
- production browser bundle builder that emits SHA-256 file metadata when dependencies are available;
- explicit shell-only browser manifest when they are not;
- hardened Parrot acceptance that refuses shell-only builds.

Current environment status:

- Foundation regression: required to PASS before checkpoint packaging;
- dependency policy: PASS;
- dependency-resolved browser build: BLOCKED because the build sandbox cannot reach npm registry DNS and no valid package-lock/node_modules set exists;
- Parrot acceptance: BLOCKED because current host is not Parrot.

No missing dependency or blocked browser is converted into PASS.
