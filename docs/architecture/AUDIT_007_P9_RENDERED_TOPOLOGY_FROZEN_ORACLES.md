# AUDIT-007 P9 — frozen original file to REAL DRAWN TOPOLOGY oracles

**Status: ORACLES_FROZEN / SOURCE_UI_UNCHANGED / CI_REPRODUCTION_PENDING.** Owner priority is actual wrong or misleading rendered network topology, release failures and false green, not hacker threat models. Source authority protected `main=7b5e6c595f765b566efb1e41f598b2fe7135d8a3`, Git tree `ca3934417bd69cc1228b9e6b6618c150b2beb734`, [prior P8 exact-main successful release](https://github.com/Northsw-spec/YadiLab/actions/runs/41333323737), [functional plan](TOPOLOGY_FIDELITY_FUNCTIONAL_FIRST.md).

**Real user-visible requirement:** A local CSV with six documented resource identities (firewall, router, switch, server, Windows client, Linux client) and five explicitly declared `Connected To` pairs must produce **exactly the same actual mounted ReactFlow device DOM IDs, role/icon families, labels and SVG edge identities + endpoints**. A rendered edge must expose its **actual ReactFlow source and target**, not just an ID whose relationship exists only in the exported JSON. Every semantic SVG edge must have finite nonempty geometry, enabled network presentation. Source is not real physical cable verification.

**Frozen cases in `tests/acceptance/run_audit007_p9_rendered_topology_real_browser.py`:**
1. Actual compiled Chromium source upload → READY preview six devices/five links → Builder activation → independently compare original hard-coded node roles/peer set, exported Builder source, `.react-flow__node[data-id]` count/IDs/visible family/labels/box sizes, `.react-flow__edge[data-id]` count/IDs, custom `path.react-flow__edge-path.semantic-edge` SVG geometry and **`data-connection-source`/`data-connection-target` attributes**. Require edge equality by exact ID and source/target, NOT count-only. Check graph panel edge ledger.
2. Two documented isolated devices in same subnet + gateway: zero inferred source connections, zero actual drawn SVG edges; two real rendered devices.
3. Unknown `Connected To` endpoint: BLOCKED, explicit diagnostic, activation disabled, existing Builder source unchanged.

**Boundary:** This is a real rendered DOM fidelity gate for existing structured CSV import, not DOCX/ODT support. Existing DOCX/ODT IC-040 P1b still nodes-only; no claim links can be imported from Office yet. Real original-file/source-local refetch and previous P8 35 PASS remain mandatory. No physical network, Parrot manual or user acceptance claimed.

**Freeze first:** add test and invoke it in BOTH required CI and independent Linux release Chrome invocation **without modifying production UI**. The initial expected failure is the lack of actual SVG edge endpoint attributes. Inspect actual prepatch job log before making the minimal production fix: expose immutable edge.source/edge.target as DOM data attributes directly from the `SemanticJourneyEdge` ReactFlow props; do not synthesize missing source connections or weaken tests.

Then all latest-head checks SUCCESS, protected expected-head squash merge, exact-main Linux release success with both unexpired artifacts; record in issues #96 and #3.
