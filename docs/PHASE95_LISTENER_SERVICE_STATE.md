# Phase 95 — Listener / Service State semantics (v1.1.0-dev.16 candidate)

## Scope

Phase 95 formalizes destination listener truth as an Engine-owned decision distinct from service declaration state. It extends the Phase-92 Host Stack model; it does not discover real processes/sockets or execute guest commands.

The authoritative query is `queryListenerServiceState(...)` (and the compatibility wrapper `queryListeningPort(...)`). For TCP/UDP port-bearing reachability, the Engine emits one immutable `ListenerServiceDecisionTrace` containing:

- destination resource, protocol and port binding;
- evidence model: `EXPLICIT_HOST_STACK` or legacy `SERVICE_DECLARATIONS`;
- snapshot completeness;
- listener state: `LISTENING`, `NOT_LISTENING` or `UNKNOWN`;
- service declaration state: `ENABLED`, `DISABLED`, `MIXED`, `UNKNOWN` or `UNDECLARED`;
- exact selected service/socket identities;
- Host Stack listener-consistency state;
- one explicit disposition and explanation.

## Truth rules

When `properties.hostStack` is explicitly modeled:

- a matching TCP `LISTEN` / UDP `BOUND` socket proves listener `TRUE`;
- a complete snapshot with no matching listener proves `FALSE / NO_LISTENER` (or `SERVICE_DISABLED` when the selected service is explicitly disabled);
- a partial snapshot with no match remains `UNKNOWN / SNAPSHOT_INCOMPLETE`;
- malformed, duplicate or contradictory ownership evidence remains fail-closed `UNKNOWN / MALFORMED`;
- service enabled/disabled state is preserved separately and never overrides explicit socket truth.

This intentionally permits visible mismatches such as `service=ENABLED` + `listener=NOT_LISTENING`, or `service=DISABLED` + an explicitly modeled live listening socket. The mismatch is evidence; it is not silently normalized away.

When no Host Stack is modeled, existing service declarations remain backward compatible as `SERVICE_DECLARATIONS`. That compatibility never fabricates process/socket IDs and is explicitly labeled declaration-only in Active Probe / UI surfaces.

## Propagation and presentation

Reachability carries the listener/service trace only after the destination has actually been reached. Upstream routing, VLAN/STP, firewall, NAT or other blocks therefore prevent downstream listener evidence from being fabricated.

Active Probe propagates the Engine trace unchanged. Visual Journey validates resource/protocol/port binding, Host Stack model/completeness/selection, service state, listener state, disposition and terminal truth before rendering. Missing listener trace is fail-closed when port-bearing Host Stack evidence is present.

Listener / Service State X-Ray presents **Socket listener truth** and **Service declaration state** separately and flags modeled mismatches. The UI performs no listener inference, service enablement inference or socket discovery.

The existing Host Stack Microscope remains the ownership/evidence table; Phase 95 adds the decision layer that consumes it.

## Deliberate non-features

This checkpoint does not implement:

- real process/socket discovery;
- guest commands or live host interrogation;
- automatic service-manager lifecycle;
- TCP handshake/state machine;
- UDP/ICMP failure classification;
- MTU/PMTUD;
- automatic mutation of socket state.

The next authoritative Phase E slice is **TCP state machine**.

## Verification

Final version-bumped verification: Engine **344 functional + 177 adversarial + 24 regression + 22 regression-adversarial**; Observation **88 + 11**; Active Probe **218 functional + 32 adversarial**; Visual Journey **44 functional + 97 adversarial** plus UI contract; Compiler **69 functional + 126 adversarial + 2/2 output-schema**; schema **55/55 fixtures + 18/18 meta-validations**; Canvas, branding, acceptance-contract and package-lock gate PASS. `test:active-probes` passes its Engine/Observation portion (**218 + 32**) then is **RC 2 / BLOCKED** when browser TypeScript reaches missing `elkjs/lib/elk.bundled.js`. `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** on the same missing `elkjs`. Browser readiness is **RC 77 / BLOCKED** because the pinned dependency tree is not installed. Top-level build is **RC 2 / BLOCKED** on missing `elkjs`/`ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN**.
