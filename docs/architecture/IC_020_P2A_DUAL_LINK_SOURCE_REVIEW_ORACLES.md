# IC-020 P2a — frozen dual-explicit-link source review and freshness oracles

**Authority (2026-10-31):** current protected `main=ddfa52110cc4e6e170b592aed7a20e343d91fa94`, Git tree `a54b46b0ceda91c6a72910ca246d8d0efbbfe7ec`; no open PRs at baseline. Read root `AGENTS.md`, active `IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md`, issue #3, actual `network-inventory.ts`, `workbook-mapping.ts`, `network-topology-import.ts`, core NetworkTopologyImportPanel code, existing five adapters, current P1 real-Chromium test, original reimport implementation and existing Engine truth tests. This is a **scoped IC-020 P2a subcheckpoint**, not completion of IC-020.

## Problem and strict bounds

A structural Devices inventory may contain both `Connected To` values and a distinct explicit `Links` table. Existing `normalizeNetworkInventoryDocument` correctly yields hard `NETWORK_IMPORT_LINK_SOURCES_CONFLICT` to avoid auto-merge but provides no reviewed operator resolution. Arbitrary network documents with partial or contradictory facts must not silently create physical links. This P2a resolves only **which of two independently explicitly declared link sources to accept**, never creates links from IP/gateway/hostname or automatically merges both lists. Real workbook JSON with `Devices` and `Links`, or existing XLSX/ODS producer with corresponding tables, is the intended subset. Never treat Nmap/Nessus observations as active topology or claimed physical evidence.

## Required implementation (immutable decision bound to original source)

1. Keep unresolved conflict **BLOCKED** by default. Expose bounded numeric-only `linkSourceConflict` (`inlineDeclaredLinks`, `sheetDeclaredLinks`) and exact fixed `NETWORK_IMPORT_LINK_SOURCES_CONFLICT` status; no raw link IDs, hostnames, secret cells or source line data in new review UI.
2. Only if **both** the `Devices` records' `Connected To` and `Links` table exist may the operator explicitly select one of two fixed choices:
   - `LINKS_SHEET`: use ONLY explicitly declared `Links` rows, discard implicit alternative `Connected To` link rows.
   - `INLINE_CONNECTED_TO`: use ONLY inline `Connected To` declarations, discard `Links` table's link rows.
   No default choice, no auto-combination, no heuristics. Both selections must still run existing `validateNetworkWorkbook`, endpoint/ID/role checks and Compiler/Engine unchanged. Invalid/unknown choices, attempts to supply choice for a nonconflicting source, structural inconsistencies, unknown endpoints or duplicate IDs always BLOCK.
3. `NetworkTopologyImportPanel` displays two real, unambiguous review buttons only on this conflict. Clicking a choice must **reparse the same original file** under that exact choice. If SHA, file identity or the selected-source epoch changed since initial review, fail closed with fixed `IC020_P2A_SOURCE_CHANGED`/`IC020_P1_STALE`. Do not export raw document fields or introduce active probes on preview. Once a choice is selected, show `REVIEWED` only for the chosen source *decision* and the supported original source hash, not a verified network or physical cabling. Separate Builder/Runtime activation button still required.
4. P1 freshness gate must re-open and reparse with the *same choice* just before activation, compare SHA, size, mapped ScenarioSource, diagnostics, reviewed choice and original dual-source counts. Stale workspace, source switch, Escape, failure, cancel, or reopened modal cannot reuse earlier decisions. No replacement of existing five adapters.
5. Preserve prior behavior for normal single-source JSON/CSV/TSV/XLSX/ODS, the original IC-010 read-only inspector, original existing mapping/reimport flows, Builder, Engine/OSPF and other source formats. No version bump or physical truth claim.

## Mandatory tests before merge

- New `test:ic020-p2a-link-review` tests existing producers with a realistic synthetic 8-device JSON Devices+Links dataset and three explicit inline/sheet link differences, independently verified SHA/counts, fixed conflict denial, both explicit choices and correct exact edges, source size checks, unknown/duplicate/invalid/ambiguous references, invalid choice type or nonconflicting choice, same original source hash but different decision -> distinct ScenarioSource/diagnostics; P1 review/reparse fresh/changed/stale per choice; compile and modeled Engine truth, without guest execution.
- Real compiled Chromium `run_ic020_p2a_link_review_real_browser.py`: one-click native JSON picker, explicit review both choices across separate clean sessions, correct exact Builder nodes/links, SHA proof, unresolved disabled activation; tampered same-size original after review and after explicit choice denied; file switch/cancel/reopen does not retain choice, no external requests or Engine mutation; earlier P1 exact real-browser still PASS.
- Wire both gates to required exact PR-head CI and independent exact-main Linux release; do not merge from a failing head. Report actual 36-ish check-runs (never assume their count), actual Chromium source SHA and release artifact.
- Record source, CI attempts, PASS/FAIL, merged SHA and next P2b in GitHub issue #3; issue stays OPEN. **Do not claim P2 full reimport/replay or any remaining format complete**.

## Future checkpoints untouched

`IC-020 P2b` safe reviewed source-bound reimport and sidecar/report replay, `P2c` heterogeneous realistic multi-sheet workbook and complete positive/negative/UNKNOWN modeled probe acceptance, then IC-030 onward. Documentation-only mappings, blocked unknown formats, real hardware/Parrot user testing are separate gates.
