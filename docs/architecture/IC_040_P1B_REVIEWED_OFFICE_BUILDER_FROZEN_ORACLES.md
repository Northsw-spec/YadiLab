# IC-040 P1b — frozen real Office original-cell → reviewed Builder oracles

**Source authority (2026-11-01):** protected main `f800cc64ba912f40e841fb38b3cc66b6635c501f`, independent exact-main [release #41309546715](https://github.com/Northsw-spec/YadiLab/actions/runs/41309546715) COMPLETED/SUCCESS, Linux artifact `13084474863`, DOM artifact `13084857608`, both unexpired. Zero open PRs at branch creation. [AGENTS.md](../../AGENTS.md), [import masterplan IC-040](IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md), [issue #3](https://github.com/Northsw-spec/YadiLab/issues/3), current P1a source and 278-assertion DOCX/ODT ZIP tests are authoritative.

**Freeze this document and these tests on branch FIRST, before editing production.** This is the narrowest P1b UI activation contract, *not* full IC-040 device/IP/interface/declared-peer mapping.

## UI boundary

- A **separate** "Review DOCX/ODT nodes into Builder" entrypoint and local-only isolated React panel. Existing P1–P6 DOCX/ODT structure/disclosure/reference-sidecar/replay UI remains intact, independent and read-only.
- Both formats use strict existing filename, actual/declared 16 MiB byte checks, original ZIP/XML budget/namespace/active-content checks; initial local File read gets structural metadata and SHA-256 only. No raw cell/header/secret/customer text rendered in DOM or persisted; never fetch or upload.
- Provide a bounded ordinal-only selector (first four tables; first 20 non-header rows and first four cells in each row), up to **four selected node-ID cells**; each cell must have a *fresh* independent checkbox acknowledgment and an explicit operator-supplied device role (generic default). A second separate modeled-resources acknowledgment is required. No implicit default cell, automatic category inference or bulk disclosure; changing cell, role, source, cancel or close revokes relevant consent.
- Invalid/malformed package, header row, duplicate row/ID, extra keys, same-size changed source, source secrets, private unselected cells and stale asynchronous work all BLOCK with sanitized code only; no partial Builder mutation.

## Activation / race contract

- Only the canonical P1a `mapReviewedOfficeOriginalToNodes` engine may produce a candidate, with exact one-cell disclosure and SHA-bound original locators, no caller text. The operator's chosen cells and roles must be revalidated from the **same original selected File**, before and **again after** real `compileBuilderWorkspace` and `autoLayoutBuilder(...ElkLayoutBackend)`.
- Capture current live Builder/workspace identity and scenario transition before any async boundary; after every await and **immediately** before replacement reject competing Builder or Runtime changes `IC040_P1B_WORKSPACE_CHANGED` and changed/canceled file `IC040_P1B_STALE`.
- Require final reread full source SHA and complete source structural metadata parity, *then* exact canonical P1a candidate `source` and `origins` equality with the precompile one. Fail closed on different same-size valid ZIP, race during File.arrayBuffer or during compilation/layout. A failed commit never replaces competing live Builder.
- Explicit success replaces Builder **only** with chosen source nodes, zero connections/interfaces/routes/probes, unfulfilled `office_manual_verification` objective. Do **not** open Runtime/Engine, claim physical topology truth or invent a cable.
- No root adapter registry change and no new external dependency. P1a `canActivate:false` must remain unchanged: UI authorization is a *separate last-moment gate*, not a mutation of P1a's source-only semantics.

## Required proof

1. `tests/browser/run_ic040_p1b_office_builder_tests.mjs`: actual compiled TS file bridge, real synthetic DOCX/ODT packages, exact source SHA, initial one-read, individual consent decision, exact original locators, final source reread, same-size changed valid ZIP, invalid format/size and selection epoch, safe server-rendered React DOM and no private cell text; existing P1a oracles preserved.
2. `tests/acceptance/run_ic040_p1b_office_builder_real_browser.py`: actual built YadiLab in pinned Chromium on GitHub Ubuntu. Per-format manual review → 1 explicitly chosen node in real exported Builder source with no links or secret; cancel and invalid source no mutation; same-size valid original swap on last read denied; live competing scenario change on last read denied and newer workspace retained; no unexpected network requests/JS errors/Runtime/Engine automatic PASS.
3. New focused script in BOTH protected `yadilab-required-ci` and independent exact-main Linux release. Existing Dev11, Engine/OSPF, import, GraphML/draw.io, DOCX/ODT P1–P6, IC-040 P1a 278, AUDIT-007 P1/P2a/P2b/P3, real Chromium, Ubuntu security mirror, AUDIT-006 and manifest security checks remain unchanged.
4. Actual latest-head all checks COMPLETED/SUCCESS, read real job logs, protected squash merge with expected head and no bypass, then independent exact merged-main push release SUCCESS and two unexpired artifact IDs. Update issue #3. No manual Parrot tests.

**Not part of this slice:** import IP/interface/peer from Office, inferred/physical links, an actual device state, Engine probe truth, Runtime activation, general prose interpretation, native Parrot. Further IC-040 P2+ requires separate frozen contracts.
