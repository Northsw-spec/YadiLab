# IC-040 P9 frozen source-to-real-graph contract — DOCX/ODT ten nodes, nine Links rows

Canonical starting point: protected `main=d5d386dc31e4592b373db3e6f6d7690287a25354` (tree `721165a27002514a7cfedd32b7f67156d0eb38ac`), independently attested [P8 exact-main Linux/Chromium release #41363773640](https://github.com/Northsw-spec/YadiLab/actions/runs/41363773640) COMPLETED/SUCCESS, artifact IDs Linux `13106820592` and real mounted DOM `13106780590` until 2027-01-30. P8 already supports eight original-ID cells and seven distinct original Links rows, all with separately approved two-sided original port cells; parallel device-pair rows require distinct physical port IDs.

## New functional P9 scope — separately opted in, no legacy widening

Dedicated `office.reviewed-network-tables.ten-by-nine-parallel-port-links.v1` requires **EXACTLY TEN** individually selected original DOCX/ODT node ID cells + manually selected modeled roles, and **EXACTLY NINE** individually selected independent original Links table rows; each row requires consent to original from/to ID cells AND two port-ID cells. Distinct original source rows connecting one unordered device pair may coexist only on non-reused, two-sided original port IDs. No invented endpoints, derived cables, inferred connectivity, subnet/IP-derived links or automatic Engine PASS; physical connection evidence remains unverified. All existing legacy P4 4/4, P5/P6/P7 6/5 and P8 8/7 shapes, capacity denials and independently verified source/Builder/DOM gates **must remain unchanged**.

Real two-table DOCX and ODT original ZIP fixtures have ten source IDs `sw01,fw01,rt01,srv01,pc01,pc02,ap01,db01,nas01,vpn01`, ten source-cell/role consents. Nine independently reviewed original Links rows:
1. `sw01.eth1 → fw01.eth0`;
2. `sw01.eth2 → fw01.eth1` (same unordered devices but distinct ports);
3. `sw01.eth3 → rt01.eth0`;
4. `sw01.eth4 → srv01.eth0`;
5. `pc01.eth0 → pc02.eth0`;
6. `sw01.eth5 → ap01.eth0`;
7. `srv01.eth1 → db01.eth0`;
8. `sw01.eth6 → nas01.eth0`;
9. `rt01.eth1 → vpn01.eth0`.
Every row must retain the original table ordinal, original row/column/port locators and original ZIP SHA-256. Unique modeled link ID per original row; exact port-per-resource inventory, correct source role families and no unselected private/sensitive source cells or synthetic test probes.

## Frozen tests BEFORE application code

Add real DOCX/ODT ZIP source+compiled Builder oracles `tests/browser/run_ic040_p9_office_ten_by_nine_tests.mjs` and wire directly after P8 in the same `test:ic040-p1b-office-builder` script used by both required PR CI and independent exact-main release. Positive: 10 original nodes, 9 source-supported connections with exact source/peer/port quadruples, nine original link origins, nine two-sided port locator pairs, no extra interfaces, correct source schema and compiled Builder. Negative: P8 8/7 slice still READY; P8 with 10/9 BLOCKED, P7 6/5 slice still READY, P4–P6 limits unaffected; 9/9, 10/8, missing consent, portless row, duplicate original row, unknown endpoint, reused local port, reversed identical source port pair, stale original SHA, sensitive cell all BLOCK with no Builder side effects.

**Expected frozen-only red CI:** current dispatcher does not recognize P9; required CI should fail only the new P9 gate with `IC040_P5_CAPACITY_PROFILE_INVALID`, after old P4/P5/P6/P7/P8 source oracles pass. Inspect and log this failure **before** writing app code.

## UI and actual Chromium acceptance

New visibly distinct P9 opt-in selection toggles ten-node/nine-link bounds, resets ALL old P4–P8 selections and acknowledges on mode change; no silently widened P8. Actual compiled DOCX + ODT in mounted Chromium must prove **ten correctly typed visible ReactFlow nodes and nine independent semantic SVG edges**, exact nine original source/compiled/DOM endpoint and port quadruples, two visibly distinct same-device-pair `sw01↔fw01` path geometries and both correct port handles; no extra graph vertices/edges, secret disclosure, runtime probe or auto verified physical cabling. Unknown endpoint, duplicate reversed-port pair and reused interface must fail without Builder mutation.

Merge only after final exact-head PR all check runs COMPLETED/SUCCESS with log proof; guard against head SHA drift; protected squash merge; **new independently triggered exact-new-main Linux+real Chromium release**, job COMPLETED/SUCCESS and two distinct nonexpired Linux/DOM artifacts. No manual Parrot testing.
