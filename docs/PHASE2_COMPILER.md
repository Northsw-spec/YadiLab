# Phase 2 Compiler — implementation contract

## Input

`ScenarioSource` that has passed the authoritative Draft 2020-12 source schema.

## Output

On success:

- fully normalized semantic `NormalizedScenario`,
- exact capability locks,
- exact profile locks,
- minimum Engine version,
- canonical source SHA-256,
- separate `LayoutRequest` preserving semantic layout hints,
- zero or more non-fatal warnings.

On failure:

- no normalized model,
- stable diagnostics with `severity`, `code`, `path`, and message.

## Compiler order

1. Validate compiler/catalog integrity.
2. Validate source via injected authoritative schema validator.
3. Resolve capability requirements.
4. Resolve profile requirements.
5. Validate semantic references and capability claims.
6. Apply profile defaults and source overrides.
7. Compute canonical source SHA-256.
8. Resolve minimum Engine version.
9. Build normalized semantic model.
10. Validate normalized model via injected authoritative schema validator.

## Deterministic rules

- IDs are never silently renamed. Invalid IDs must be rejected by schema.
- Version ranges resolve to the highest available compatible exact version.
- Compiled locks are exact and sorted by ID.
- Profile defaults are deep-merged for objects; explicit source values win.
- Arrays are replaced, not implicitly merged.
- Layout is not fabricated by Compiler. ELK owns actual auto-layout in its later phase.

## Diagnostics implemented

Examples include:

- `DUPLICATE_REQUIREMENT_ID`
- `VERSION_RANGE_INVALID`
- `CAPABILITY_UNAVAILABLE`
- `CAPABILITY_VERSION_UNAVAILABLE`
- `PROFILE_UNAVAILABLE`
- `PROFILE_VERSION_UNAVAILABLE`
- `CAPABILITY_NOT_DECLARED`
- `CAPABILITY_CLAIM_AMBIGUOUS`
- `PROFILE_NOT_DECLARED`
- `PROFILE_TYPE_MISMATCH`
- `DUPLICATE_GLOBAL_ID`
- `DUPLICATE_INTERFACE_ID`
- `UNKNOWN_ZONE_REFERENCE`
- `ZONE_PARENT_CYCLE`
- `UNKNOWN_RESOURCE_REFERENCE`
- `UNKNOWN_INTERFACE_REFERENCE`
- `UNKNOWN_TEST_REFERENCE`
- `UNKNOWN_SOLUTION_TARGET`
- `UNKNOWN_LAYOUT_TARGET`
- `CATALOG_VERSION_INVALID`
- `CATALOG_DUPLICATE_DEFINITION`
- `SOURCE_HASH_FAILED`

## Intentional Phase 2 boundary

The generic compiler validates topology/reference semantics. Deep schemas for vendor/domain resource properties and test parameters will be owned by capability/profile packs and integrated as those Engine capabilities become executable. Until then, arbitrary domain payloads are preserved but are not claimed to be fully semantically validated.
