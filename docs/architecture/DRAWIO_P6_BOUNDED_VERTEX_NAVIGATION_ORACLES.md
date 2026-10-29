# DRAWIO-P6 — frozen bounded vertex-position navigation oracles

**Initial status: PREP / NOT IMPLEMENTED / NOT TESTED.** Canonical GitHub main at PREP: `cc289a361d02e1eb1c1b55418a50c00b283667a0`, tree `4171311af2d1e4600588ff4438b09bd03efc877c`; no open PR. Consulted `AGENTS.md`, `drawio-structural-preview.ts`, `drawio-association-review.ts`, `drawio-report-replay.ts`, P4/P5 browser UI/tests and workflows. This is a presentation-only accessibility correction, not broader .drawio parsing.

## Observed gap and scope

The validated P1/P3 structure profile has 1–16 pages and up to 1000 vertices in total. P4 review currently builds a flattened list then truncates at 20 entries, confusing the **maximum of 20 operator-chosen references** with the number of positions that can be inspected. Valid later positions cannot be chosen at all. P6 exposes the entire existing validated ordinal space in 20-row windows with previous/next controls and a clear position range, retaining only 20 chosen associations across windows. The initial window must be identical to P4 for small files and P4/P5 exports must remain bitwise-schema-compatible.

## Frozen behavior / failure oracles

1. Build the flattened **ordinal-only** index from already validated `preview.pages`: ascending page ordinal, then vertex ordinal. No labels, XML, source cell IDs, IP addresses, styles, edge endpoints, or actual drawn objects. Exactly 20 or fewer select elements rendered at once, even for 1000 positions; no DOM insertion of hidden source content. Empty pages do not consume windows.
2. Window navigation starts at zero; previous disabled at first window, next disabled at last; a 3-vertex fixture renders all three selectors simultaneously (original P4 acceptance compatibility). Larger 45-vertex and max-1000 fixtures reach last positions by navigation. An index beyond 20 may be selected and retained when visiting another window.
3. At most 20 **total** non-empty operator choices across all windows; attempt #21 rejected without dropping earlier choices, acknowledging or exporting. The operator can explicitly clear one or all references; change of any choice clears acknowledgement and prior exported indicator. Duplicate modeled target across different, possibly invisible windows blocks export. Navigation alone must not fabricate consent or change existing decisions.
4. Manual consent remains mandatory; sidecar is the existing P4 exact `REVIEWED_ASSOCIATIONS_ONLY` shape with no truth elevation, no source leakage, max 20, one-to-one references, original-source SHA recheck, live Builder snapshot recheck. P5 must replay newly exported sidecars unchanged. Do not modify parser, Engine, Builder, ScenarioSource or persistent storage.
5. On source replacement, error, modal close/reopen, or workspace epoch/revision change, previous selections, consent, exported status, and pagination all reset; in-flight export must remain stale-safe. No extraneous file output or network fetch.
6. Negative source controls preserve existing XXE/DTD, invalid compressed data, inflation budget, forged counts, invalid ordinals, duplicate model targets, stale Builder and changed same-name original; do not weaken any P1–P5 gates. No true real identity, topology, cabling or Engine `PASS`.
7. Independently constructed 45-vertex multi-page XML fixture with private canary: check full navigation, page-boundary ordinals, selection across hidden windows, duplicate mapping, max-20 guard, changing a selection revokes acknowledgement, JSON sidecar bytes/provenance, genuine P5 replay, no private canary in DOM, unchanged Builder. Include a 1000-position boundary case. Actual **compiled Chromium on Ubuntu GitHub Actions** must exercise the UI, not just SSR; previous P4/P5 real-browser acceptance must remain successful.
8. All applicable GitHub PR-head workflows/check-runs must be SUCCESS before merge. Verify merged-main SHA/tree and independently built Linux release before claiming complete. `NOT_RUN` never counts as PASS.

## Existing design inputs

- `enterprise-import/src/drawio-structural-preview.ts` (strict source/profile budgets, ordinal page count; no source-label disclosure)
- `enterprise-import/src/drawio-association-review.ts` (one-to-one 1–20 selections, fixed sidecar)
- `enterprise-import/src/drawio-report-replay.ts` (full canonical replay)
- `ui/app/drawio-association-review.mjs` (current 20-position truncation)
- Existing `tests/acceptance/run_drawio_p4_real_browser.py` and `run_drawio_p5_real_browser.py` (must not regress)
