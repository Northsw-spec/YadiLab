# Phase 25 — Explicit Versioning / Migration Framework

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 25 continues from exact-byte verified v0.24.0.

## Contract

- Current scenario source and normalized schema version is explicitly `0.1.0`.
- Structural JSON Schema validity alone is not enough to claim compatibility.
- Compiler, packaged Runtime, and CLI test paths reject unsupported schema versions before semantic execution.
- `MigrationRegistry` executes only explicitly registered deterministic steps.
- There is no fabricated legacy production migration: no older published schema transition exists yet. Current production registry therefore supports the current version as a no-op and rejects unknown historical/future versions until a real migration step is registered.
- Migration steps cannot silently change format ID or lie about their destination version.

## CLI

`app migrate --input <document.json> [--output <migrated.json>]` targets the current schema for the document format.

A current `0.1.0` document returns unchanged semantics with `changed: false`. An unregistered version returns `MIGRATION_PATH_UNAVAILABLE`.

## No silent reinterpretation

Unsupported schema versions are blocked by:
- compiler source entry;
- CLI validate/compile/test;
- browser `.yadilab` Runtime open.
