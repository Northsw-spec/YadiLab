# CONVERGENCE OSPFv2 P2P Hello/Dead — bounded protocol-model checkpoint

**Source authority:** GitHub current main at checkpoint start. This document defines a new, read-only protocol sidecar; it is NOT an independent code base or evidence of a full OSPF implementation.

## Source standard / semantic constraints

- [RFC 2328](https://www.rfc-editor.org/rfc/rfc2328.html) §§9.5, 10.1–10.5 and A.3.2: Hello timer; matched area/HelloInterval/RouterDeadInterval; HelloReceived -> Init; seeing our Router ID in a neighbor's Hello -> two-way detection; on point-to-point networks adjacency establishment begins at **ExStart**, not Full; inactivity timer returns Down. RFC permits not comparing network mask on point-to-point links, so this sidecar never claims to validate it.
- An external caller supplies *synthetic, already-admitted* Hello observations. The sidecar is **not** a wire decoder, packet checker, authentication verifier, OSPF neighbor authorization proof, or evidence that two routers are physically connected. It checks declared sender/area/interval/seen-Router-IDs only.
- Supported states in this bounded slice are **DOWN, INIT, EXSTART**. Two-way awareness is visible as ExStart *adjacency attempt*. **Exchange, Loading, Full, DD packet negotiation, LSDB, LSA flooding, SPF, DR/BDR, ECMP, dynamic routes** are explicitly UNMODELED, not silently SUCCESS.

## Engine and scheduler contract

- The current EngineState is source of scenario ID/hash, exact revision and configured network.router resource IDs. Both designated router resources must exist. Router IDs and area ID are strictly canonical dotted IPv4 strings; Hello and Dead intervals are integer milliseconds representing whole seconds. Dead must exceed Hello.
- A versioned **OspfP2pSession** owns a pure SimulationEventPlan: exactly one scheduled local synthetic Hello-transmission *intent*, plus at most one remote inactivity timer after accepted Hellos. No actual network frame is sent.
- Scheduling uses existing `scheduleSimulationEvent` and `cancelSimulationEvent`; advancing uses `advanceSimulationEventPlan`. Periodic intents start at virtual t=0. Accepted Hello refreshes the old dead timer by canceling it and scheduling a new one.
- Synthetic input is processed **after all due timers** at its timestamp. At exact expiry, InactivityTimer takes Down before a new Hello can establish Init/ExStart. This deterministic tie policy is part of this model's public contract.
- One-way Hello -> Init, two-way Hello -> ExStart (no DD exchange). Missing Hellos until the deadline -> Down. A later Hello can restore Init/ExStart. Rejected/mismatched Hellos cause **no state or timer changes**.
- Every operation rechecks source hash/revision, timer ownership, scheme version and queue shape. Prevent arbitrarily injected event kinds. Invalid input and budget overruns fail with original unchanged session, never partial state promotion.
- Bounded to 2048 total scheduled events per session and 512 dispatches per advance; explicit failure avoids runaway loops. No wall-clock/randomness, EngineState mutation, simulated routing truth, fake Full adjacency or claims of actual packet transport.

## Acceptance

- `npm run test:ospf-p2p-hello` compiles actual Engine and runs positive/negative tests plus 1000 byte-identical end-to-end synthetic replays.
- Negative oracles: forged area/source/router ID, interval mismatch, duplicate or malformed neighbor list, non-router target, stale Engine revision or source, manipulated timer/deadline/ordinal/schema, deadline overflow, exact deadline and one-way reversal.
- Assert untouched Engine revision, resource properties and baseline network reachability, and remain fail-closed on corruption. Run within `yadilab-required-ci` before compiled browser and independent real Chromium gate; do not merge until *every applicable PR check* is SUCCESS. Separate post-merge Linux release must succeed for artifact acceptance.
- **Future checkpoints:** explicit DD database-exchange state machine, LSA/LSDB, SPF and route install/withdraw, links and failure/recovery, convergence Timeline/X-Ray. These require separate architecture and adversarial tests.
