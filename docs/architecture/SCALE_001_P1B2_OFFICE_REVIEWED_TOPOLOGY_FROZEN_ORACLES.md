# SCALE-001 P1b2 — exact reviewed Office rows → compiled Builder, frozen acceptance

**Date:** 2026-11-02. **Base commit:** protected P1b1 merged `ab435935c8d159fd2ff97323c80abe3c4d875335`. P1b1's [independent Linux+Chromium release #41376081033](https://github.com/Northsw-spec/YadiLab/actions/runs/41376081033) must be **COMPLETED/SUCCESS** with two exact-main artifacts before any P1b2 application implementation. **Status:** test-first contract, no feature delivery implied.

## Goal / restricted scope

Move from P1b1's source-bound 100-row disclosure batches to actual source-faithful 100 / 1,000 node and 99 / 999 explicit port-linked connection **Builder source** for original real DOCX and ODT ZIP files, with original-cell provenance. Never synthesize a physical link from IP/gateway/hostname, infer device role from name, or declare Engine/Runtime or physical PASS. This P1b2 remains a **source/compiled-Builder candidate only, not a live UI/large DOM** claim. Real 100-node Chromium and large hierarchical navigation are separate gates in P2/P3.

## New distinct opt-in profile

`office.scaled-reviewed-topology.v1` from original file bytes + exact expected SHA-256 and a **declared set** of bounded P1b1 approvals. Operator must independently acknowledge each source table, specific row intervals (<=100 rows per batch), columns and semantic meaning before activation. Explicit node-ID + canonical node-role source columns (e.g. `network.switch`, `endpoint.windows`), and two independent peer-ID + optional separately acknowledged original port columns in a distinct Links table. No implicit selected rows/columns; require exact source SHA in all batch decisions; reject conflicting table origins or unreviewed columns. The test can explicitly declare 100/1,000 source device and 99/999 source link rows without depending on any particular real airport/municipality inventory.

Use P1b1 bounded original read for each batch, but **not** the old per-cell ZIP disclosure APIs. Build a temporary, all-or-nothing provenance-bound candidate, then verify original identifiers and types, unique links, exact endpoint existence and node-bound port uniqueness. Project through ordinary shared Network Workbook → ScenarioSource → actual Builder compiler; preserve source-typed node/port/link IDs, allow multiple distinct parallel port links, and never self-fill the manual independent verification objective. The model is not a separate graph renderer.

## Mandatory RED → GREEN original ZIP oracles

1. Independent real DOCX and ODT original ZIP generation with 100 nodes + 99 explicit links and 1,000 nodes + 999 explicit links, original tables with header, selected original `Device ID` / `Device Role` columns, plus separately approved `From` / `To` / `Source Port` / `Target Port` columns. Include an unselected private canary column in **both** tables.
2. Full exact source→compiled Builder fidelity: node identities/types and cardinalities, original links/ports and source locators, unique per-node port IDs including a core with many distinct reviewed ports, completion manual review only and **no imported Engine-tested state**. No omitted, extra or invented edge. Denied paths must not replace or partially update Builder.
3. Reject missing node row batches, overlapping/duplicate row batches, absent consent, out-of-range rows, duplicate node ID, conflicting/unknown role, unknown endpoint, a declared port duplicated on the same node across different source link rows, conflict and source SHA mismatch (including valid same-size source swap), secret-value or secret-header selection. Return stable error codes without exposing source cells.
4. Accept two different source-authorized **parallel** links connecting the same pair of nodes iff ports are distinct and explicitly approved; preserve both unique edge IDs and port provenance, never collapse to one cable.
5. Reject unsupported profile or format, mixed DOCX/ODT source claims and excessive batches; deterministic memory/time bounded tests on Ubuntu, no arbitrary PASS performance claim.
6. Preserve P0 49, P1a 72, P1b1 881 and legacy Office P4–P10 exact-original + mounted Chromium checks. Freeze tests and shared required+independent-release Ubuntu gate **before** P1b2 production code. First CI RED at missing new module. Only after P1b1 independent release, write product implementation.

## Delivery and later stages

All required latest-HEAD Ubuntu PR checks must be COMPLETED/SUCCESS, inspect source and actual Chromium logs; SHA-guarded protected merge and independent exact-main Linux release with two nonexpired artifact IDs. Then **P2** integrate a safe review UI with explicit columns/batches and actual fresh-File/Builder-epoch guard and independently observed 100-node/99-link rendered DOM. **P3** introduce site/building/zone hierarchy and focus/viewport strategy for 1,000+ while preserving underlying source/provenance graph. **P4** measured 5k/10k original-to-DOM Linux proof. Do not claim any of P2–P4 merely from P1b2 source tests.
