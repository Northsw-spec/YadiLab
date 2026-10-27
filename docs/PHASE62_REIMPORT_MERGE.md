# Phase 62 — three-way re-import merge and baseline preservation

Authority: **Masterprompt v1.3 VERIFIED / LOCKED**.

Phase 62 turns the Phase 61 diff boundary into a deterministic, fail-closed merge workflow while preserving the distinction between imported baseline state and independent scenario/fault overlays.

## Three-way merge inputs

A merge always uses three verified baselines with the same stable `baselineId`:

- `ancestor` — the previous imported baseline before local working changes,
- `current` — the current working baseline that may contain deliberate operator/manual changes,
- `incoming` — the newly imported customer baseline.

All three baseline identities are verified before planning.

## Deterministic decisions

Each entity, relationship and semantic fact key is compared against the common ancestor.

- current unchanged + incoming changed → `AUTO_APPLY_INCOMING`,
- current changed + incoming unchanged → `KEEP_CURRENT`,
- both changed to the same semantic state → `ALREADY_CONVERGED`,
- both changed differently → `REVIEW_REQUIRED`.

Provenance-only incoming refreshes may be applied automatically only when the current side has not independently changed. No fuzzy matching, timestamps, hidden priority score or AI decides a merge.

## Explicit resolution

`REVIEW_REQUIRED` entries cannot be applied without one exact recorded choice:

- `CURRENT`,
- `INCOMING`,
- `DELETE`.

Duplicate, stale, missing or impossible choices fail closed. A supplied merge plan is recomputed from the actual three baselines and rejected if stale or tampered.

## Baseline preservation

The merge engine starts from current working state and applies only planned decisions. It does not mutate independent scenario/fault overlays.

The result:

- keeps only provenance required by selected semantic objects,
- preserves required historical source descriptors,
- retains incoming source descriptors for the new import generation,
- uses the incoming import contract as the active import context,
- runs full Enterprise Model verification after merge.

A combination that would create a dangling relationship, unknown subject, invalid provenance or other broken model is rejected even if each individual decision looked locally valid.

## Lineage

A non-no-op merge adds `REIMPORT_MERGE` lineage to the Enterprise Baseline. Lineage binds:

- ancestor baseline identity,
- current baseline identity,
- incoming baseline identity,
- canonical merge-plan SHA-256,
- explicit review resolutions.

Lineage is part of the canonical baseline identity. Duplicate parent roles and duplicate resolution keys are semantic errors.

An exact no-op re-import preserves the previous baseline identity rather than manufacturing a new identity only because the re-import action occurred.

## Relationship-complete diff

The Phase 61 re-import diff is upgraded so entities, relationships and facts all report:

- `ADDED`,
- `REMOVED`,
- `CHANGED`,
- `PROVENANCE_ONLY`.

This keeps the preview/diff surface aligned with what the merge engine can actually apply.
