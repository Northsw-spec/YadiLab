# Phase 83 — ARP/ND X-Ray (v1.1.0-dev.4)

This checkpoint delivers the ARP/ND table and decision-visualization vertical slice from authoritative Phase C.

## Truth boundary

Neighbor state is read only from `resource.properties.neighbors`. When that property is absent, the Engine emits no neighbor decision and preserves previous reachability behavior. The UI never derives a neighbor entry from topology, interface addresses, route state or visual adjacency.

Each modeled neighbor row declares:

- a stable row ID;
- `ARP` or `ND`;
- an IPv4 or IPv6 neighbor address consistent with that protocol;
- `REACHABLE`, `STALE`, `INCOMPLETE`, `FAILED` or `UNKNOWN` state;
- optional target-resource binding, MAC address and interface.

The Engine validates row structure, address family, declared resource/interface references, optional MAC syntax and consistency with a modeled next-hop address. It preserves declaration order and classifies rows as `MATCH`, `NO_MATCH` or `MALFORMED`.

Exactly one matching row may be selected. Multiple matches, malformed authoritative data, no modeled next-hop row, or route/neighbor egress inconsistency produce `UNKNOWN` without a selected entry. `REACHABLE` and `STALE` prove usable modeled resolution, `FAILED` blocks the path, and `INCOMPLETE` or `UNKNOWN` stop the proven journey with an unknown verdict.

No address, MAC, interface, cache hit or resolution state is synthesized.

## Propagation

The exact immutable trace flows through:

```text
Network Engine
→ ReachabilityDetails.neighborDecisions
→ ActiveProbeTranscript.neighborDecisions
→ VisualJourneyModel / neighbor.decision
→ ARP/ND X-Ray
```

Visual Journey rejects neighbor traces that reference an unknown or non-adjacent path hop, contain duplicate decisions/candidates, disagree about the selected row, alter selected row fields, or claim truth inconsistent with the selected modeled state.

## Presentation

The in-place ARP/ND X-Ray table shows the Engine-provided row order, target, protocol, address, MAC, interface, state, match disposition and selected row. Missing values are labeled `NOT MODELED`, `NOT AVAILABLE` or `UNKNOWN`; the UI performs no resolution logic.

## Tests

Functional coverage verifies ARP and ND, exact row selection, MAC/interface/state propagation, `REACHABLE`, `STALE`, `INCOMPLETE` and `FAILED` semantics, Active Probe propagation, timeline event creation and X-Ray projection.

Adversarial coverage verifies malformed family/protocol data, ambiguous matches, absent next-hop rows, manipulated path binding, forged selection, altered selected MAC and truth/state mismatch.

Parrot OS and final real-environment Chromium/Firefox acceptance remain pending.
