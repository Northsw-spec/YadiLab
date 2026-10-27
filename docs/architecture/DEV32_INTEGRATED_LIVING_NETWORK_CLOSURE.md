# Dev32 — Integrated Living Network Closure

Dev32 closes the cross-layer contract without inventing new protocol truth. The Engine remains authoritative; the browser projects Engine events, provenance, state revision, and invalidation diagnostics.

## Continuity

- A Journey is derived from one `ActiveProbeTranscript` and its exact `scenarioId`, `scenarioHash`, and `stateRevision`.
- Replay of the same transcript and scenario is deterministic: event ids, ordering, terminal outcome, X-Ray decisions, and provenance are stable.
- A transcript from another scenario revision is rejected with `VISUAL_JOURNEY_SCENARIO_MISMATCH`; the UI must not keep presenting stale evidence as current.
- MTU evaluation is a first-class Engine projection and can coexist with the existing Journey/X-Ray event contract. Its packet size, egress MTU, path MTU, and NOT_MODELED fragmentation/ICMP dispositions are explicit.

## Closure boundaries

The integrated closure covers scenario switching, native compiler round-trip, fault mutation/rollback, replay determinism, and the 80-node enterprise matrix. It does not claim guest-stack execution, fabricated PMTUD adaptation, or protocol state absent from Engine truth.

## Failure semantics

Unknown, incomplete, stale, or unmodeled state is surfaced as a diagnostic or explicit truth value. No UI event is synthesized to imply a red drop, ICMP packet, fragmentation, ARP/FDB/STP/VLAN state, or return path unless the Engine supplied that evidence.
