# Phase 82 — Routing X-Ray (v1.1.0-dev.3)

Status: DEVELOPMENT CHECKPOINT CANDIDATE — not a verified product release.

This checkpoint begins Phase C of the authoritative Living Topology & Visual Simulation Specification with one complete routing decision slice.

Implemented vertical slice:

- the Network Engine emits an explicit, backward-compatible route-decision trace for each modeled path hop that declares an authoritative route table;
- every declared route row remains in source order and is classified as `MATCH`, `NO_MATCH`, `DISABLED` or `MALFORMED`;
- the Engine alone marks the selected row and exposes its declared next hop and outgoing interface;
- numeric metric and preference fields are shown only when explicitly modeled and are not silently used by the UI as a second routing algorithm;
- equal-specificity conflicting routes produce `UNKNOWN` with no selected row;
- malformed or incomplete route state remains `UNKNOWN` or `NOT AVAILABLE` rather than being repaired visually;
- Active Probe transcripts carry the exact Engine route trace;
- Visual Journey validates that each trace belongs to an adjacent proven path hop and rejects inconsistent/tampered winner markers;
- a deterministic `route.decision` timeline event appears before the corresponding packet segment;
- the in-place Routing X-Ray table highlights only the Engine-selected row and remains semantically complete under reduced motion.

Truth boundary:

The browser does not parse destinations, calculate longest-prefix match, compare metrics, select next hops or infer interfaces. It renders the Engine trace verbatim. Routes are absent from the overlay when no authoritative route table is modeled. ARP/ND, MAC/CAM, switching, VLAN trunk and STP decision traces are not fabricated by this slice.

Focused verification:

- Engine functional and adversarial route-trace tests;
- Observation Engine propagation tests;
- Visual Journey functional and adversarial trace-binding tests;
- Routing X-Ray UI contract and JavaScript syntax;
- browser, package-export, certification, browser-build and acceptance contracts;
- full Foundation regression where the local pinned Python and Go toolchains permit it.

Still pending in Phase C:

- ARP/ND decision/table trace;
- MAC/CAM decision/table trace;
- learn/flood/unicast events;
- VLAN access/trunk tag transitions;
- STP blocked/forwarding trace.

Still required before any verified v1.1.0 product claim:

- real Chromium and Firefox DOM/screenshot acceptance;
- Parrot OS x86-64 acceptance;
- complete release signing and reproducibility gates.
