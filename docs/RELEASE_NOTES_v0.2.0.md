# Release notes v0.2.0 — Compiler Phase 2

This release advances the foundation from schema-only contracts to a functioning deterministic compiler core.

## Major changes

- Implemented `ScenarioSource -> NormalizedScenario` compilation.
- Added exact capability/profile resolution from version ranges.
- Added data-driven built-in capability/profile catalog.
- Added semantic reference checking and stable diagnostics.
- Added deterministic canonical source SHA-256.
- Added profile default merge semantics.
- Added dedicated layout contract and removed layout from canonical semantic scenario state.
- Added compiler-schema adapter for the Ajv validator boundary.
- Added positive, negative, and adversarial regression suites.

## Compatibility

The current external source schema remains `0.1.0`. The normalized semantic contract was tightened while still using the current Foundation schema version. No user-facing release package format is claimed yet; PackageIO is a later phase.

## Next phase

Phase 3: deterministic Engine core, beginning with state/action reducer and NetworkEngine v1, followed by Rule/Test/Finding/Objective and IdentityEngine boundaries.
