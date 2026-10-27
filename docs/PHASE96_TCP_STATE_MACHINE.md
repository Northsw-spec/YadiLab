# Phase 96 — TCP State Machine X-Ray (v1.1.0-dev.17)

## Scope

Phase 96 formalizes a bounded, Engine-owned TCP lifecycle microscope over explicit Phase-92 Host Stack socket evidence. It does not execute guest commands, sniff packets, mutate socket state or simulate TCP timing.

The authoritative query is `queryTcpStateMachine(state, sourceId, destinationId, port)`. For a TCP destination-port probe the Engine emits one immutable `TcpStateMachineDecisionTrace` containing:

- exact source, destination and service-port binding;
- evidence model: `EXPLICIT_HOST_STACK` or legacy `SERVICE_DECLARATIONS`;
- Host Stack snapshot completeness;
- listener truth inherited from Phase 95;
- exact modeled TCP socket rows for the destination port;
- selected source-bound session socket(s), when explicit peer identity matches the modeled source address;
- current lifecycle state(s);
- canonical TCP transition table and allowed next states;
- explicit `NOT_MODELED` status for sequence/ACK timeline and retransmission markers;
- one disposition and explanation.

## Bounded lifecycle

Supported TCP lifecycle states are:

`CLOSED`, `LISTEN`, `SYN_SENT`, `SYN_RECEIVED`, `ESTABLISHED`, `FIN_WAIT_1`, `FIN_WAIT_2`, `CLOSE_WAIT`, `CLOSING`, `LAST_ACK`, `TIME_WAIT`, `UNKNOWN`.

The canonical transition table covers active/passive open, SYN/SYN-ACK/ACK establishment, active/passive FIN close, CLOSING/LAST_ACK/TIME_WAIT and return to CLOSED. The transition table is protocol knowledge only; it is not evidence that a transition actually happened.

TCP session states other than `LISTEN`, `CLOSED` and `UNKNOWN` require explicit `remoteAddress` and `remotePort`. Authoring without peer identity is rejected, and runtime mutation of such rows fails closed.

## Truth rules

- Explicit source-bound session row(s) with one consistent state => `TRUE / SESSION_OBSERVED`.
- Explicit LISTEN socket with no source-bound child session => `TRUE / LISTENING`.
- Destination reached with proven no listener => `FALSE / CONNECTION_REFUSED`.
- Partial Host Stack with unresolved listener => `UNKNOWN / SNAPSHOT_INCOMPLETE`.
- Multiple source-bound sessions with conflicting lifecycle states => `UNKNOWN / SESSION_AMBIGUOUS`.
- Malformed Host Stack or incomplete session peer identity => `UNKNOWN / MALFORMED`.
- Service-only compatibility => `UNKNOWN / DECLARATION_ONLY`; no socket lifecycle rows are fabricated.
- Missing source/destination resource => `UNKNOWN / RESOURCE_ABSENT`.

Network failures before the destination still terminate in the existing reachability layers; downstream TCP socket state is not evaluated for a host the flow never reaches. This preserves the distinction between a network/policy timeout-like failure and a reached-host `CONNECTION_REFUSED` outcome without fabricating exact RST packet fields.

## Propagation and presentation

`queryReachability` attaches the TCP state-machine trace only for TCP port probes after the destination listener layer is evaluated. Active Probe propagates the Engine trace unchanged.

Visual Journey validates source/destination/port binding, Host Stack model/completeness, listener truth, exact socket projection, source-bound selection, current-state set, role/next-state projection and the full canonical transition table before rendering. Missing or manipulated TCP trace fails closed when TCP Host Stack evidence is present.

TCP State Machine X-Ray displays:

- current modeled state(s);
- socket role and explicit peer;
- allowed next state(s);
- the canonical transition table;
- listener/disposition truth;
- `NOT_MODELED` sequence/ACK and retransmission telemetry.

The UI performs no TCP state inference and no packet/timer simulation.

## Deliberate non-features

This checkpoint does not implement:

- live guest socket discovery;
- automatic SYN/SYN-ACK/ACK packet generation;
- actual sequence/ACK number progression;
- retransmission, duplicate ACK, SACK or out-of-order telemetry;
- RTT/RTO/backoff timers;
- MSS/window/zero-window/window-probe behavior;
- keepalive;
- congestion-control phases;
- automatic socket-state mutation.

Those can be modeled only in a future explicit packet/session timeline capability. The next listed Phase E deliverable is **UDP/ICMP failure distinctions**.

## Verification

Final version-bumped verification: Engine **363 functional + 187 adversarial + 24 regression + 22 regression-adversarial**; Observation **88 + 11**; Active Probe **225 functional + 32 adversarial**; Visual Journey **44 functional + 97 adversarial** plus UI contract; Compiler **69 functional + 131 adversarial + 2/2 output schema**; schema **55/55 fixtures + 18/18 meta-validations**; Canvas **19 + 10**, branding, acceptance-contract and package-lock gate (**33 required packages**) PASS.

Aggregate/environment gates on the same frozen source: `test:active-probes` passes the **225 + 32** core assertions and is then **RC 2 / BLOCKED** at browser TypeScript compilation because `elkjs/lib/elk.bundled.js` is not installed. `test:foundation` was run in the same dependency-incomplete environment and its independently re-run Layout gate is **RC 2 / BLOCKED** at the same missing pinned `elkjs` module. Browser readiness is **RC 77 / BLOCKED** because no genuine `npm ci` installed dependency tree is present. Top-level build is **RC 2 / BLOCKED** on missing `elkjs` and `ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN** and must not be relabeled PASS without execution.
