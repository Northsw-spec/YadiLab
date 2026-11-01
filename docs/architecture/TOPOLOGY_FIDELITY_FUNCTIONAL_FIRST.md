# YadiLab — functional topology fidelity / release blocker priority

**BINDING: owner superseding decision, 2026-11-01.** Current protected GitHub main is the only source authority. Issue [#96](https://github.com/Northsw-spec/YadiLab/issues/96) tracks bugs, [#3](https://github.com/Northsw-spec/YadiLab/issues/3) tracks import completion. Existing security tests remain, but hacker risk is not the main priority.

## Definition of correctly imported topology

A supported document declaring six nodes and five peer links must produce **the exact six node IDs, labels, supported roles, and those exact five endpoint pairs and declared ports**, with no omitted, duplicated, swapped, or invented nodes/edges. This must remain true from the real file bytes through parsing, semantic mapping, Builder source, compiler, layout and actual displayed ReactFlow DOM. Also test isolated nodes, branches, cycles, multi-links and conflicts. An unrecognized/ambiguous device, port or peer must remain unverified or explicitly reviewed, never guessed from IP, gateway, subnet, hostname or positional proximity.

Imported documents are **evidence of declared topology, not independent physical verification**. Do not mark modeled reachability/Engine PASS without a real modeled test, and never use a tautology such as a node's own assigned type to satisfy imported scenario completion.

## Existing capabilities and honest gaps

- CSV/TSV, Excel/ODS, JSON: explicit Devices/Links or `Connected To` are mapped. Audit graph parity, actual Builder visualization and false PASS first.
- GraphML and diagrams.net: separate reviewed, consented graph mappings exist. Preserve selected-original edge identities and assert no additional edges or role guesses.
- DOCX/ODT IC-040 P2: **four reviewed node IDs and four explicitly consented peer links maximum; interfaces/ports not yet mapped**. Source-grounded original cells, actual compiled/visible ReactFlow endpoints, duplicate/unknown peers and original/workspace race protection passed on protected `main=da6cd7ef6f2bd3d1ee989042cc851aba51550e3a`, independent Linux release #41340396235. It is a partial bounded capability, NOT full document-topology recovery. P3 must separately review both endpoint port cells and verify source/Builder/DOM parity without inventing cables from IP, names or table proximity. Arbitrary document topology remains incomplete.
- Unsupported PDF/prose/complex diagrams: report limitations and source-grounded uncertainty; do not claim arbitrary document-to-network automatic reconstruction.

## Required implementation/verifications

1. Freeze reproducible negative + valid positive source/Builder tests before changing app code; inspect actual prepatch FAIL, not guesses.
2. Exact node ID/type/label/address and link endpoint+port set equality in source and compiled Builder. Count equality alone is insufficient. Add real mounted Chromium graph checks where UI affects rendering.
3. No silently fabricated or missing physical link, automatic green imported objective, or TRUE reachability based solely on source text. Preserve genuine Engine truth where actual modeled network is configured.
4. For ambiguous/invalid endpoints and source conflicts, show accurate explicit warnings or block without replacing the workspace. Distinguish incompleteness from an actual broken importer.
5. Preserve all previous Engine/Dev11/import/security/Ubuntu mirror/AUDIT-006 regressions. Require latest-head all GitHub Actions SUCCESS and log inspection, protected expected-head merge, independent exact-main Linux push release SUCCESS and both valid Linux/DOM artifact IDs.

For any generic "fortsätt": choose real topology/false PASS/release defect first, then document relationship implementation needed for truthful graph. Keep full-source inventory honest: passing unrelated CI does not mark 1,446+ files reviewed.
