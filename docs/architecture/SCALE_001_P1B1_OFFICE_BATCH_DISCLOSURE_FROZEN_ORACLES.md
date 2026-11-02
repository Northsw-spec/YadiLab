# SCALE-001 P1b1 — source-bound Office batch disclosure, frozen acceptance

**Date:** 2026-11-02. **Starting main:** `25127036a5865a7103b9198adeb0f33f85c56f18` (P1a 1k-row structural-only PR #120 merged). P1a's independent Linux release must succeed before P1b production code. **Status:** planned / frozen-contract only.

## Problem statement

Old DOCX/ODT `discloseReviewed*Cell` revalidates the entire original ZIP and reparses XML **per source cell**. For a thousand individually consented node rows and hundreds of port-linked rows that creates N full source reads and an unacceptable scaling pattern. The new profile is separate, opt-in, source-bound, never an implicit or legacy P4–P10 extension.

## P1b1 strictly source-only profile

`office.scaled-reviewed-batch.v1`. Input: exact original DOCX/ODT bytes + SHA-256, source format, explicit structural table ordinal, **inclusive** non-header row interval (initial maximum 100 rows/batch), exact selected column ordinals (initial maximum four), separately acknowledged row-range and column choices, and affirmative disclosure permission. No default selected rows or columns. Original ZIP must be fully validated using P1a's strict opted-in large structural limits and source SHA; one bounded indexed batch disclosure, with number of full source archive/XML validations **independent of N selected cells**. Ideally a single verified pass per batch; if two passes are needed for independent freshness assurance, measure/justify them separately and prohibit per-cell scans. Do not stash sensitive full-source strings in UI state, logs or sidecars.

Output: immutable bounded array of **only** selected original (table,row,column) locators and values with exact source SHA, `REVEALED_UNVERIFIED`; no table-wide content, no unselected headers, no canActivate, Builder/Engine/physical flags, nor automatic role/cable guesses. Use narrow original header/row-label and selected-value sensitive-data blockers with stable diagnostic codes and no original private text in failures.

## Mandatory frozen tests BEFORE production

1. Actual independently generated genuine DOCX and ODT ZIPs containing 100 node rows and 99 original explicit Links rows, plus 1,000/999 larger sources (including header rows), with a private canary column not selected. Verify exact original SHA and selected structural locators, all chosen strings and NOTHING else in returned artifacts.
2. At most 100 source rows per batch, initial selected column cap 4, deny zero/default approval, unknown/mismatched SHA, invalid file format, unsupported profile, excess/duplicate row or column selection, header row, missing table/cell and source swap. Fail closed without partial output.
3. Reject selected values under `Password`, `Token`, `Secret` and similar original column headings, suspicious cell literals and sensitive row labels; no canary or private source text in errors. Never parse arbitrary prose as links.
4. Separate confirmed node/source port/peer disclosure only when those exact columns/rows consented. Duplicate source identity/ports and unknown endpoints become blocking at the later P1b2 mapping stage — P1b1 disclosure alone is not a Builder/graph proof.
5. Preserve no-option original P1a 200-row limits and P1a opted-in structure-only behavior, plus P4–P10 historical exact profile tests and Chromium legacy regressions. Record real source, limits, measured Ubuntu memory and time; no ungrounded time target.

## Delivery and next boundary

Start with plan, genuine ZIP tests and required+independent-release Ubuntu gate in **separate commits before production changes**. First CI red at missing P1b1 capability; then minimum scoped parser implementation after P1a independently RELEASE_VERIFIED. Require 7/7 (or current exact-head full required) PR checks, inspected logs, protected SHA-guarded merge and independent new-main Linux+real Chromium release with two separate unexpired artifacts.

**P1b2** (separate future checkpoint) maps reviewed source batches to exact 100/99 and 1000/999 source/Builder resources, endpoints, ports and parallel links, with source revalidation and concurrent Builder identity; then separate 100-node real Chromium and 1000+ hierarchical view acceptance. P1b1 alone does not prove network import, visualization, Engine truth or physical cabling.
