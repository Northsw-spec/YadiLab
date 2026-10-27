# Phase 86 — STP/BPDU X-Ray (v1.1.0-dev.7 candidate)

This slice completes the authoritative Phase C routing-and-switching order with deterministic STP/BPDU forwarding and blocking visualization. It does not start Phase D.

## Truth boundary

The Network Engine reads STP truth only from explicit `resource.properties.stp` and `resource.properties.stpPorts` state. The bridge record can declare protocol, bridge identity, root identity and root path cost. Each port row declares an interface, role, data-plane state and optional BPDU direction.

Supported trace values are deliberately bounded:

- protocols: `STP`, `RSTP`, `MSTP`, `UNKNOWN`;
- roles: `ROOT`, `DESIGNATED`, `ALTERNATE`, `BACKUP`, `DISABLED`, `UNKNOWN`;
- states: `FORWARDING`, `BLOCKING`, `DISCARDING`, `LEARNING`, `LISTENING`, `DISABLED`, `UNKNOWN`;
- BPDU dispositions: `SEND`, `RECEIVE`, `NONE`, `UNKNOWN`.

The Engine does not elect a root, derive a role, infer a transition, synthesize a BPDU, or run a timer. `isRootBridge` is only the Engine's exact comparison of the two explicitly modeled bridge identities. No time-based convergence or aging is introduced.

When an explicit STP model is present, every connected switch interface must have one unambiguous modeled port row and one modeled link. Missing, duplicate, malformed, ambiguous or `UNKNOWN` path state yields `UNKNOWN` with `modelComplete: false` where the model itself is incomplete. A non-forwarding ingress or egress yields `FALSE`; only explicitly `FORWARDING` ingress and egress yield `TRUE`. Legacy scenarios without STP state preserve their prior behavior and receive no fabricated STP trace.

Unknown-unicast and broadcast flood sets are filtered by the same Engine-owned STP state. A blocked/discarding/non-forwarding port is excluded. Incomplete or unknown STP eligibility makes the flood decision `UNKNOWN`; presentation code never repairs the set.

## Propagation

The exact immutable trace flows through:

```text
Network Engine
→ ReachabilityDetails.stpDecisions
→ ActiveProbeTranscript.stpDecisions
→ VisualJourneyModel
   → stp.bpdu (only for explicit SEND/RECEIVE evidence)
   → stp.decision
→ STP/BPDU X-Ray + Engine-projected topology edge
```

Visual Journey validates resource/path binding, interface identity, complete port projection, path-role markers, bounded role/state/BPDU values, bridge/root consistency, explicit model completeness, and truth/state agreement before rendering. A manipulated or internally inconsistent trace fails closed.

## Presentation

The in-place STP/BPDU X-Ray shows only trace fields supplied by the Engine:

- protocol, bridge ID, root bridge ID, root status and root path cost;
- ingress and egress interfaces;
- explicit model completeness;
- each projected interface's path role, STP role, state and BPDU direction;
- the exact Engine truth for forwarding, blocking or uncertainty.

Forwarding, blocked and unknown rows use separate semantic styling. DOM acceptance attributes expose the selected resource, truth, egress, root identity, model completeness and per-port state/role. The UI performs no STP election or port-state calculation.

## Verification coverage

Focused coverage includes:

- functional forwarding and explicit blocking decisions;
- root identity and BPDU propagation;
- STP-aware unknown-unicast flood exclusion;
- missing, duplicate, malformed and explicitly unknown port state;
- malformed bridge state and ambiguous connectivity;
- Active Probe propagation without hidden reconstruction;
- deterministic `stp.bpdu` and `stp.decision` visual events;
- manipulated-trace, incomplete-table, invalid-state, bridge inconsistency and truth-mismatch fail-closed tests;
- browser/UI contract coverage for the STP/BPDU X-Ray.

Real Parrot OS and final target Chromium/Firefox acceptance remain pending. This is a development checkpoint, not a VERIFIED PRODUCT RELEASE.

## Next authoritative work

Phase C's listed routing/switching X-Ray slices are now implemented. The next authoritative phase is Phase D — Stateful Network Decisions. Do not begin it until this checkpoint is fully green and finalized.
