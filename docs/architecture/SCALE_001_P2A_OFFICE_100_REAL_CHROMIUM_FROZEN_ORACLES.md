# SCALE-001 P2a — genuine 100-node Office → original-source-approved Builder → visible ReactFlow

**Date:** 2026-11-02. **Protected starting source:** P1b2 merged `8b3535eaf85e585b6d56021303821923f124d8c9`. New P1b2 independent exact-main Linux+actual Chromium [release #41378313584](https://github.com/Northsw-spec/YadiLab/actions/runs/41378313584) must COMPLETE/SUCCESS and produce two valid artifacts before any P2a production code. **Status:** frozen-first acceptance / no implementation implied.

## Owner goal and hard boundary

YadiLab must accurately **display** a 100-device and 99-link genuine original DOCX **and** ODT network in the real compiled Chromium frontend, not merely infer from the parser or source JSON. This is the first practical screenshot/DOM rendering milestone for municipal/campus-scale networks. Do **not** assert 1,000/5,000/10,000 visible devices, a verified physical cable, a network reachability PASS or safety of a real organization. Later P2b/P3 must add hierarchy, viewport/focus and 1,000+ graph navigation.

## New separate opt-in UI and source contract

- Separate scalable Office modal and explicit menu action; **do not change** older P4–P10 cell-by-cell or 12/11 profile contracts or controls.
- User loads a local valid DOCX/ODT original File. Show **only structural table/row/column counts and SHA-256**, no unapproved file text or per-cell hashes. Default counts of approved rows/columns **zero**.
- Require visible, deliberate selection of exact Nodes and Links table ordinals, approved **Node ID + canonical role**, **From + To + Source Port + Target Port** columns, and explicitly displayed source row ranges, with affirmative, separate approval of semantic mapping and Builder replacement. For P2a only, original 100 node rows and 99 link rows, using P1b2-approved column order and <=100 rows/batch. Any source containing extra unselected data must stay undisclosed.
- Before **each** Builder change, compare actual original File fresh bytes, original SHA and structural P1a metadata with the preview, selected decisions and active Builder/Runtime/scenario identity. Repeat independent File read and source/candidate comparison **after** actual compile and layout; reject same-length source swap, concurrent Builder changes, revoked consent or a stale preview without partial mutation.
- Use P1b2 `mapReviewedOfficeBatchesToSource` source-based candidate. Validate with ordinary compiler, auto-layout and existing ReactFlow source→drawing projection. Imported source remains editable Builder, with `tests=[]`, unfulfilled independent manual verification objective and no Runtime/Engine/physical PASS.
- Actual DOM must expose exactly 100 independent rendered node identities and 99 independent, valid SVG semantic edge paths, original endpoint and exact port IDs. Disconnected nodes stay disconnected, documented parallel distinct links must not collapse; measured geometry nonempty/non-NaN. Fail if source contains missing/extra/duplicated nodes, labels, roles, links or invented edges.
- Prevent source disclosures via errors, DOM, logs, local storage, sidecar and exported source. No external network requests. UI must remain responsive and cancelable; do not claim measured 1k+ visual throughput from this 100-node gate.

## FROZEN positive and negative source-browser oracles before production

1. Real independently authored DOCX and ODT ZIP original 100 nodes + 99 source row peer+port links; include unselected secret canary strings in a third Nodes column and fifth Links column, plus canonical source types. Do not reveal source canaries even during preview or errors.
2. Initial preview must render `REVIEW_REQUIRED`, selected approval count 0, Builder unchanged, confirm disabled, metadata-only table row/column counts; then select table/role/ports and check separate approvals. Source/candidate verifies full original SHA and Builder epoch. Final builder export must include exact 100 sources and 99 complete port pairs; no unjustified test PASS.
3. Actual ReactFlow DOM must contain 100 `.react-flow__node[data-id]` and 99 `.react-flow__edge[data-id]`, exact IDs/roles/correct source→target and source+target handles, nonempty finite SVG paths; no duplicate or phantom paths. Source and DOM parities asserted, real compiled app in localhost Chromium, not screenshot mocks.
4. Same-length fresh original source swap after review, canceled import, source missing endpoint, duplicate ID/port, stale active Builder change, and secret selection must all fail closed leaving prior active Builder unchanged. No secret text in DOM/errors or diagnostic artifacts.
5. 4/4 exact-head required PR checks + actual Chromium and original P0/P1a/P1b1/P1b2/P4–P10 regressions PASS; protected expected-head merge; independently exact-main Linux release + real mounted DOM proof in two valid distinct artifacts. No manual Parrot tests.

## Performance and next step

Observe real DOM 100/99 layout/render latency, memory and viewport usability on GitHub Ubuntu. Do not overstate results as certified 1,000–10,000 performance. P2b/P3 must add measured hierarchical site/building/zone layouts, overview→focus navigation, nondeleting graph clustering/viewport virtualisation with intact original semantic IDs and source locators before any 1,000+ drawn-graph certification.
