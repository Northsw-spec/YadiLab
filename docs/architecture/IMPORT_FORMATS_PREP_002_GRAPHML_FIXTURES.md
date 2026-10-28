# IMPORT-FORMATS-PREP-002: GraphML fixture contract (before parser code)

Source-of-code authority: **current** GitHub main (the branch was created from main `f5b01b3e3f3a18de8f230e56720ddc097d8b10d6` at work start). Historical releases, ZIPs, earlier commits and external source trees are **not** implementation sources. Fixtures below were newly authored from published GraphML syntax.

Normative format: https://graphml.graphdrawing.org/specification.html
Readable examples: https://graphml.graphdrawing.org/primer/graphml-primer.html

**Status:** FIXTURES AND EXPECTED RESULTS ONLY; GraphML is **NOT IMPLEMENTED** by this checkpoint. No current adapter, scenario model, or Engine semantics changed.

## Initial profile proposed (not yet implemented)

- Name: `graphml.core.structural.v1`; semantic track `TOPOLOGY_DECLARED`.
- Supported profile subset when implemented: one graph, XML namespace `http://graphml.graphdrawing.org/xmlns`, unique node ids, edges with explicit source and target, explicit graph `edgedefault` directed/undirected, optional `edge directed=true/false`, string-valued node label via declared key. No network device/OS inference from labels.
- Do **not** interpret edges as verified cables. The allowed semantic output is a `GRAPH_EDGE` candidate for human review. No `PHYSICAL_LINK`, Engine TRUE/PASS, IP address, route, VLAN or active probe result emerges from these fixtures.
- Nested graph, hyperedge, SVG embedded data, unsafe DTD/ENTITY, external references and unknown producer extensions should fail closed in this version unless separately designed/tested.
- Unbound arbitrary GraphML data keys: **NOT YET SEMANTICALLY SUPPORTED**; no implicit mapping into scenario properties.
- No network request, JavaScript execution, or arbitrary filesystem access during parse.

## Expected oracles (not derived by parsing each fixture)

| Fixture | Expected nodes | Expected relation candidates | Expected status | Required details |
|---|---:|---:|---|---|
| `valid-two-nodes.graphml` | 2 | 1 | PREVIEW_ONLY / REVIEW_REQUIRED | `router_1`, `switch_1`; explicit labels; undirected `edge_1`; 0 verified cables |
| `valid-mixed-directed.graphml` | 2 | 2 | PREVIEW_ONLY / REVIEW_REQUIRED | `e1` directed (graph default); `e2` undirected override; edges may precede node declarations |
| `invalid-missing-endpoint.graphml` | none activated | 0 | BLOCKED | Edge targets nonexistent `missing_node` |
| `invalid-duplicate-node.graphml` | none activated | 0 | BLOCKED | Repeated id `same` |
| `invalid-wrong-namespace.graphml` | none activated | 0 | BLOCKED | Incorrect GraphML namespace |
| `adversarial-xxe.graphml` | none activated | 0 | BLOCKED | Contains DTD and external entity; **never** fetch local file |

## Candidate provenance contract

Each `node` and `edge` must retain source SHA-256, graph id and element id/position in a **typed GraphML locator**; do not pretend this is an Excel cell. Error messages name the offending element, without leaking external-entity text. Source bytes are never changed. Two runs of the same file and declared parser profile must produce deterministic candidates or the same deterministic diagnostic code.

## Required independent negative checks

1. Replacing target with an unknown id must BLOCK, leaving active workspace unchanged.
2. Inserting duplicate node id must BLOCK (no merge guessed).
3. Wrong namespace must BLOCK even when filename extension says `.graphml`.
4. DTD/ENTITY must BLOCK before expansion; no external resource accessed.
5. A test with code intentionally treating `GRAPH_EDGE` as `PHYSICAL_LINK` must fail (semantic truth gate).
6. An empty, oversized or deeply nested XML must block at bounded resource limits.
7. Removing label data must not invent OS, IP, vendor or node type.
8. At least one fixture verifies edge declarations preceding node declarations.
9. Run and record regression on existing JSON/CSV/TSV/XLSX/ODS after GraphML profile is added.
10. Real browser preview/cancel/confirm and Parrot test remain separate required gates for an end-user `SUPPORTED` status.

## Release boundaries

Fixture files alone do not pass any parser feature. No new import UI accepts GraphML in PREP-002. No `SUPPORTED` declaration is permissible until later profile-specific implementation, positive/negative tests, actual UI acceptance, and security/performance evidence are achieved.

**CI claims:** NONE; the fixtures are test inputs and independently written oracles, not parser test results.
