# Phase 64 — Enterprise Baseline → Scenario/Topology Projection

Phase 64 closes the first deterministic bridge from the normalized Enterprise Model into the ordinary YadiLab scenario/topology pipeline.

## Core rule

Enterprise import does **not** get a separate canvas model. A verified `EnterpriseBaseline` is projected into ordinary `scenario-source`, then uses the same Compiler, Layout Engine and Canvas Projection as every other scenario.

## Projection semantics

- explicit `siteRef` / `zoneRef` relationships create scenario containers;
- explicit site/zone entity types may also become containers;
- remaining enterprise entities become scenario resources using their existing stable IDs and entity types;
- `KNOWN` and `INFERRED` facts may feed active scenario semantics;
- `UNKNOWN`, `CONFLICTING`, `INVALID` and `NOT_APPLICABLE` facts remain preserved enterprise knowledge and do not become active configuration guesses;
- recognized interface facts can project interface labels, addresses and MAC addresses;
- recognized routes/services/firewall/NAT facts can project into existing Engine property contracts;
- supported `network` / `management` / `trust` / `authentication` enterprise relationships become ordinary scenario connections;
- unsupported or unresolved relationships stay preserved as enterprise metadata and are explicitly reported as skipped;
- no topology edge is invented merely to make the picture look complete.

## Traceability

Projected scenario source and normalized scenario may contain an `enterpriseOrigin` binding with:

- `baselineId`,
- exact `baselineIdentity`,
- enterprise `modelVersion`,
- projection version,
- source IDs / SHA-256 / media types.

Raw enterprise source bytes and source display names are not copied into the scenario merely to support projection.

Each projected resource/connection also preserves compact enterprise facts/relationships and the relevant provenance records under its semantic `properties.enterprise` namespace.

## Import Helper integration

Import Helper can explicitly **Replace Builder with imported topology**. That action:

1. projects the current verified enterprise baseline;
2. creates an ordinary Builder workspace;
3. compiles it through the ordinary scenario compiler;
4. runs ordinary ELK auto-layout;
5. displays the result in the ordinary topology canvas.

The action is explicit because it replaces the current Builder scenario.

## Scope boundary

Phase 64 is a deterministic projection, not arbitrary topology inference. Richer enterprise mappings for VLANs, routes, services, interfaces and vendor-specific semantics may expand later, but only when the source data or a deterministic declared rule supports them.

Fault Injection remains a later layer over the projected/reusable baseline and must not be fused into this projection step.
