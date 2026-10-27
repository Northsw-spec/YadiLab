# Phase 84 — MAC/CAM/FDB X-Ray (v1.1.0-dev.5 candidate)

This slice extends authoritative Phase C with deterministic modeled Ethernet switching evidence. It is intentionally narrower than full VLAN/trunk or STP simulation: MAC learning, destination lookup, known-unicast selection, explicit unknown-unicast/broadcast flooding, and filtering are exposed only when the Network Engine has enough modeled state to prove them.

## Truth boundary

Switching state is read only from explicit topology and `resource.properties.macTable`. The UI never learns MAC addresses, chooses an egress port, constructs a flood set, infers a VLAN, ages a table entry, or decides that a frame is unicast/broadcast on its own.

A modeled MAC/CAM row has a stable row ID, MAC address, interface and optional VLAN. Declaration order is preserved. The Engine validates MAC syntax, interface references, duplicate/ambiguous rows and VLAN scope before any row can contribute to a decision.

The Engine emits a `MacDecisionTrace` only at a modeled switching boundary. That trace records source MAC, ingress interface, destination MAC, expected egress, optional VLAN, source-learning disposition, forwarding disposition, candidate rows, exact selected row/egress and exact flood interfaces where applicable.

Learning dispositions are `LEARNED`, `REFRESHED`, `MOVED` or `UNKNOWN`. The query remains side-effect-free: a learning result describes what the modeled switching decision proves; it does not mutate the scenario's MAC table.

Forwarding dispositions are `UNICAST`, `FLOOD`, `FILTERED`, `BROADCAST` or `UNKNOWN`.

- Known unicast can select only one valid destination row.
- A destination learned on the ingress port is filtered rather than forwarded back out the same port.
- Unknown unicast and Ethernet broadcast use only the Engine's explicitly modeled eligible connected interfaces, excluding ingress.
- Duplicate/ambiguous destination rows, malformed authoritative state, duplicate peer MAC evidence, an unmodeled multi-switch boundary, multicast without modeled membership, group source MAC, or an inconsistent VLAN context fail closed to `UNKNOWN`.
- No MAC address, entry, port, flood branch, cache hit, aging timer or multicast membership is synthesized.

Full VLAN/access/trunk semantics, STP, MAC aging/timers and multicast membership are deliberately deferred to later Phase C slices.

## Propagation

The exact immutable trace flows through:

```text
Network Engine
→ ReachabilityDetails.macDecisions
→ ActiveProbeTranscript.macDecisions
→ VisualJourneyModel
   → mac.learn
   → mac.lookup
   → mac.forward / mac.flood
→ MAC/CAM X-Ray + Engine-projected topology branches
```

Visual Journey validates the Engine trace before rendering it. It rejects path/resource mismatches, duplicate candidate indexes or entry IDs, inconsistent learning dispositions, forged selections, truth mismatches, unknown interface references and projected egress/flood interfaces that cannot be mapped uniquely to the modeled topology.

For a known-unicast decision, the selected Engine egress is projected to exactly one connection. For unknown-unicast or broadcast flooding, every Engine-listed flood interface is projected to its exact connection. This mapping is presentation-only: it never chooses a forwarding result. If an Engine-selected interface cannot be mapped uniquely, rendering fails closed instead of animating another edge.

## Presentation

The in-place MAC/CAM X-Ray shows:

- source MAC and ingress interface;
- learning disposition;
- destination MAC;
- forwarding disposition;
- expected and selected egress;
- exact flood set;
- VLAN when modeled;
- Engine-provided FDB rows in declaration order and the exact selected destination row.

Missing fields are labeled `NOT MODELED`, `NOT AVAILABLE` or `UNKNOWN`. The topology renderer lights the switch ingress plus all Engine-projected active egress interfaces. A known unicast animates the exact selected branch; a flood animates all proven branches simultaneously. Reduced-motion mode suppresses motion only and retains the complete decision evidence.

DOM contract attributes expose the current Engine projection for real-browser acceptance without requiring text scraping: `data-mac-learning`, `data-mac-forwarding`, `data-mac-flood-count`, `data-selected-mac-entry` and `data-journey-decision`.

## Tests

Functional coverage includes:

- source refresh and source learn;
- source MAC move;
- known unicast with exact selected row/egress;
- unknown-unicast flood with exact fan-out;
- Ethernet broadcast flood;
- destination on ingress port filtering;
- Active Probe trace propagation;
- deterministic Visual Journey event sequence;
- exact unicast edge projection and multi-edge flood projection.

Adversarial coverage includes:

- duplicate/ambiguous destination entries;
- malformed or unknown interface entries;
- a selected wrong-but-modeled egress remaining explicit rather than being corrected by UI code;
- duplicate peer MAC evidence;
- non-broadcast multicast without modeled membership;
- group source MAC;
- manipulated trace selection/truth/learning/projection data;
- unmapped Engine-selected interfaces;
- duplicate projected/candidate identities.

Parrot OS and final real-environment Chromium/Firefox acceptance remain pending. This development slice is not a product release.
