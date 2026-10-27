# Phase 24 — Capability / Domain Pack Runtime Availability

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 24 continues from exact-byte verified v0.23.0.

## Purpose

The compiler already resolved source capability version ranges into exact `capabilityLocks`. Phase 24 closes the Runtime side of that contract: a scenario must not enter play unless every exact capability lock is available in the trusted Runtime.

## Implemented

- `CapabilityPackRegistry` with exact `id@version` resolution.
- Built-in Foundation packs: `core.network`, `core.identity`, `core.windows`, `core.linux`, `core.virtualization`, `core.security`, `core.logging`, `core.backup`.
- `engine` execution mode for packs backed by dedicated Engine semantics; `declarative` mode for trusted domain packs handled by generic Engine/rule semantics.
- Registry/catalog consistency regression: exact built-in Runtime locks must match the compiler catalog.
- Packaged `.yadilab` Runtime opening checks capability availability before Engine state creation.
- Builder Runtime Preview performs the same exact availability gate.
- Missing pack, missing exact version, and duplicate locks fail closed with explicit diagnostics.

## Security boundary

Capability packs are trusted application/runtime components. Scenario packages are data and may not supply or execute JavaScript, Python, shell code, binaries, or arbitrary plugin code as capability implementations. Future external capability installation must preserve this trust boundary and require its own explicit distribution/security model.

## Reproducibility

Source version ranges remain compiler input. Compiled scenarios/packages carry exact locks. Runtime checks those exact locks; it never substitutes another installed version silently.
