# Phase 63 — Import Helper UI

Phase 63 is the first browser user interface over the deterministic enterprise import stack established in Phases 58–62.

## Naming

The approved user-facing name is **Import Helper UI** / **Import Helper**. Do not reintroduce the superseded legacy label in new implementation text.

## Architecture rule

React is orchestration/presentation only. It must not reimplement:

- adapter selection,
- spreadsheet parsing,
- field matching,
- normalized baseline creation,
- conflict semantics,
- re-import diff,
- three-way merge.

Those operations continue to use `enterprise-import` and `enterprise-model` directly.

## Implemented flow

1. Choose a local XLSX, ODS, CSV, TSV or JSON enterprise source.
2. Use the bundled example mapping profile or load a mapping-profile JSON file.
3. Run deterministic mapping review.
4. Show source tables/fields and `RESOLVED`, `MISSING`, `AMBIGUOUS` mapping states.
5. Collect explicit table/field choices and persist them as a new mapping-profile version with `USER_MAPPED` provenance.
6. Import the normalized enterprise baseline.
7. Show records/entities/facts, unmapped fields, diagnostics and explicit source-record conflict choices.
8. Surface `UNKNOWN`, `CONFLICTING` and `INVALID` fact states rather than hiding them.
9. Re-import another source against the current baseline.
10. Show deterministic entity/relationship/fact diff.
11. Show the Phase 62 merge plan and collect explicit `CURRENT`, `INCOMING` or `DELETE` choices when human review is required.
12. Apply the verified three-way merge and update the current enterprise baseline identity.

## File handling

Known supported extensions are authoritative when present. A misleading browser MIME type cannot turn an unsupported extension into a supported import file. Extensionless files may be accepted only when the browser provides an explicitly supported MIME type. Source bytes remain local to the browser workflow.

## Scope boundary

Phase 63 does not yet project the normalized enterprise baseline into the scenario topology canvas. It establishes the reliable browser import/review/re-import/merge workflow first. Baseline-to-topology projection should be implemented as a separate deterministic projection rather than embedding format-specific visualization logic into Import Helper.
