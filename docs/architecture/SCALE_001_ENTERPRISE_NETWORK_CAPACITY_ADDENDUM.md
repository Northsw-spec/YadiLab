# SCALE-001 — Enterprise-scale source-to-topology fidelity addendum

**Date:** 2026-11-02
**Authority:** Owner-approved priority superseding the next discretionary IC-050 PDF feature. Applies to YadiLab's current canonical GitHub main and future work. This document is a forward-only addendum to the **SHA-256 locked** `YadiLab_Masterprompt_v1.3_VERIFIED.md`; it does NOT modify, replace or invalidate that verified historical file. All existing source-safety and exact-identity requirements remain mandatory.
**State:** ACCEPTANCE CONTRACT / IMPLEMENTATION NOT IMPLIED. Real performance and Linux release status must be evidenced separately by exact commits and GitHub Actions.

## New top priority, before IC-050 and OSPF/SPF enhancements

YadiLab must support faithful import, review, Builder representation, topology visualization and useful navigation for documented enterprise and campus networks substantially larger than twelve devices. Target **100, 1,000, 5,000 and 10,000+ source-declared devices** with explicit topology links; these are **synthetic benchmarks**, not factual inventories or permission to access any organization. A municipal office, city hall, campus and international airport are scale/use-case illustrations only, never sources of assumed device counts or public/private network detail.

## Mandatory source and truth contract

1. The fixed Office P4 4/4, P5–P7 6/5, P8 8/7, P9 10/9, P10 12/11 reviewed profiles remain backwards compatible and independently regression-tested. No series of +2 capacity patches is an acceptable end-state. Introduce a separately versioned scalable, opt-in profile without weakening old approvals.
2. Devices, labels, roles, interface IDs/IPs, zones, links, port pairs and parallel links may enter the modeled graph only when declared in a supported original source location and expressly reviewed. Never synthesize links from shared subnets, IP/gateway, hostname, physical proximity or arbitrary prose. No false Runtime/Engine or physical-cabling PASS.
3. Support bounded, **explicit table-column/row-range/batch approval** with preview, selection counts, sensitive-field suppression and individually traceable source locators; the approval must NOT silently disclose or ingest unselected columns/rows. Default-deny ambiguous roles, endpoints, duplicate/unknown devices, port reuse and conflicting tables. Source SHA-256 and active Builder identity must be reread before committing. A broad click does not imply consent for all content in a document.
4. Scale stages: original bytes → parser/bounded preview → source-indexed review → normalized graph → compiler/Builder → displayed graph → safe persistence/reimport. No claim of a successful stage without an actual test of that stage. CSV/TSV/JSON/XLSX/ODS and DOCX/ODT are separate proof obligations.
5. Hierarchy: site/building/floor/network zone or VLAN/asset (only if declared); expand/collapse, focused node/edge search, bounded view of large graphs and local inspection of exact source evidence. Viewport virtualization/graph clustering may reduce **visible** elements but MUST NOT delete underlying graph nodes, semantic edges or evidence.
6. Retain independent IDs of parallel edges and their port pairs across importer, Builder, compiled source and ReactFlow paths. No duplicate, phantom, missing, wrong-role or misrouted edges. Do not treat a virtual aggregate line as a real cable.

## Versioned proof ladder (planned, not achieved by this addendum)

| Gate | Source assets | Links | Required evidence |
| --- | ---: | ---: | --- |
| S0 | 100 | >=99 | Real CSV original → selected source → Builder compile, negative conflicts and no fake PASS |
| S1 | 1,000 | >=999 | Source identity and Builder fidelity; profile-specific row/column review, nonleaking provenance |
| S2 | 5,000 | >=5,000 | Hierarchical/partitioned graph; real Chromium navigation, stable memory, usable rendering |
| S3 | >=10,000 | >=10,000 | Full source→Builder→Chromium and independently released Linux app; measured memory/time on Ubuntu |

Record deterministic fixture generation, exact roles/IDs/endpoint pairs/ports, original bytes hashes, rejected sources, source/DOM graph counts, browser interactions, memory and runtime, and CI job logs. Large stages must use clearly defined limits and fail closed on budget exhaustion. No guessed arbitrary numeric memory/time PASS thresholds without measured baseline and published repeatable test conditions.

## Execution sequence

A. **SCALE-001 P0**: frozen 100-node/99-link and 1,000-node/999-link generated genuine CSV source tests to establish actual existing compiler and importer capacity, plus negative unknown/duplicate endpoint controls. Gate in GitHub-hosted Ubuntu required CI and independent release. This is a baseline, NOT a 10,000-device certification or an Office unlock.
B. P1: redesign Office selection semantics and structural preview budgets so source-reviewed 100+ rows can be safely selected by bounded batches with per-row traceability, without repeated full ZIP parsing per cell or exposing secrets.
C. P2: scale source indexes/Builder compilation and explicit subnet/interface validation; profile/regression behavior preserved.
D. P3: introduce hierarchy, search/focus/virtualization and retained edge identity; test real mounted Chromium across sizes. Never fake full visible SVG parity for collapsed graph views.
E. P4: successive 1k/5k/10k real source+UI+Linux capacity gates with measured resource footprints, adversarial cases and independent releases, then resume IC-050 digital PDF after scalable graph foundation is demonstrably ready.

**Governance:** Always start each implementation from fresh protected main, freeze positive and negative tests before modifying application code, require exact-HEAD PR CI, protected expected-head merge, independent exact-main Linux release and two nonexpired distinct artifacts. GitHub Actions on Ubuntu is the required verification; no manual Parrot verification.
