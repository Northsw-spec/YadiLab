# Phase 61 — deterministic mapping review, conflict resolution and re-import diff

Authority: **Masterprompt v1.3 VERIFIED / LOCKED**.

Phase 61 makes heterogeneous customer data reviewable before import without adding AI or fuzzy inference to the trusted core.

## Mapping review contract

`runEnterpriseMappingReview()` parses through the same trusted adapter used by real import and emits a schema-defined review artifact containing:

- discovered source tables,
- available fields plus deterministic occurrence counts,
- one review item per entity-ID, entity-label and fact mapping,
- `RESOLVED`, `MISSING` or `AMBIGUOUS`,
- selected source field + mapping class only when resolution is deterministic,
- diagnostics and final `READY`, `REVIEW_REQUIRED` or `BLOCKED` status.

Selector precedence remains explicit. `EXACT` and previously confirmed `USER_MAPPED` selectors use the exact source header. `ALIAS` selectors use only deterministic Unicode/whitespace/case normalization. No edit distance, embeddings, language model or hidden confidence score may choose a source field.

## User-confirmed mappings

`applyMappingReviewDecisions()` requires an explicit new semantic version. It may:

- bind a logical table mapping to one actually discovered source table,
- bind a mapping ID to one exact source field.

A user-selected field is inserted as `USER_MAPPED` and that class survives into per-value provenance in the resulting Enterprise Baseline. Unknown tables/fields, duplicate decisions, unknown mapping IDs and unchanged/invalid versions fail closed.

## Explicit entity-collision resolution

Duplicate source records that map to the same stable entity ID remain blocking conflicts by default. A resolution is accepted only when it:

- references the exact current conflict ID,
- uses code `IMPORT_ENTITY_COLLISION`,
- chooses strategy `select-record`,
- names one exact source table and record index that is actually part of that collision.

Stale, malformed or out-of-conflict choices remain blocking diagnostics. Applied choices are retained in `importContract.conflictResolutions`, so the baseline identity binds the decision.

## Re-import diff

`compareEnterpriseBaselines()` requires the same `baselineId` and produces a deterministic schema-defined diff. Entities are keyed by stable `entityId`; facts are keyed by `(subjectRef, path)`. The result classifies:

- `ADDED`,
- `REMOVED`,
- `CHANGED`,
- `PROVENANCE_ONLY`.

The output is lexically sorted and includes summary counts plus before/after evidence for changed items. Duplicate semantic fact keys are rejected because a merge/diff would otherwise be ambiguous.

## Deliberate boundary

Phase 61 does **not** automatically merge a new import into an existing baseline. Merge semantics must later preserve manual corrections, scenario/fault overlays and explicit user choices without silently rewriting truth. Phase 61 first establishes a deterministic review + diff boundary on which that merge can safely be built.
