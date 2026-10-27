# Phase 92 — Host Stack Process / Socket / Service View (v1.1.0-dev.13 candidate)

Authoritative architecture: YadiLab Masterprompt v1.3 VERIFIED / LOCKED plus Living Topology & Visual Simulation Specification v1.0.
Parent checkpoint: YadiLab v1.1.0-dev.12 / Phase 91.

## Goal

Implement the first listed Phase E deliverable: an Engine-owned Host Stack microscope for **process / socket / service view** without inventing guest state or advancing later Phase E protocol semantics.

The authoritative visual chain is:

```text
modeled resource properties
  -> Engine HostStackDecisionTrace
  -> Active Probe transcript
  -> Visual Journey fail-closed validation
  -> Host Stack Microscope UI
```

The UI never discovers processes, calculates socket ownership or repairs incomplete evidence.

## Model

A resource may explicitly declare:

```json
{
  "hostStack": {
    "complete": true,
    "processes": [
      { "id": "proc-rdp", "name": "svchost.exe", "pid": 1160, "service": "rdp" }
    ],
    "sockets": [
      {
        "id": "sock-rdp",
        "protocol": "tcp",
        "localAddress": "0.0.0.0",
        "localPort": 3389,
        "state": "LISTEN",
        "processId": "proc-rdp",
        "service": "rdp"
      }
    ]
  }
}
```

The Engine derives only bounded presentation evidence from that explicit model:

- process ID/name and optional PID;
- explicit process-to-service binding;
- TCP/UDP socket rows;
- local address/port and optional remote address/port;
- socket state;
- bind scope: `WILDCARD`, `LOOPBACK`, or `SPECIFIC`;
- explicit process/socket-to-service ownership;
- selected service/socket rows for the requested protocol/port;
- bounded consistency between declared service-enabled state and explicit listener rows.

`complete` means only that the scenario author declares the provided process/socket snapshot complete. YadiLab does not inspect a real OS to prove it.

## Legacy service-only scenarios

When `properties.hostStack` is absent, the Engine does **not** synthesize a process, PID or socket. It emits a `SERVICE_DECLARATIONS` Host Stack trace with:

- `complete = false`;
- empty process/socket arrays;
- existing declared service rows;
- process/socket ownership explicitly absent / `NOT MODELED`.

This keeps older scenarios compatible without converting service declarations into fake guest evidence.

## Fail-closed rules

Explicit Host Stack state becomes `UNKNOWN` evidence instead of being repaired when it contains, among other cases:

- duplicate process IDs;
- duplicate socket IDs;
- invalid PID/port/socket state;
- TCP `BOUND` or UDP `LISTEN` in this bounded model;
- socket references to undeclared processes;
- process/socket references to undeclared services;
- contradictory process-service vs socket-service ownership.

On fail-closed Host Stack evidence, partially trusted process/socket rows and selected listener rows are not exposed downstream. Network reachability truth remains owned by the pre-existing network/listener semantics; Phase 92 does not silently replace those semantics.

## Schema / compiler boundary

Source and normalized schemas define `hostStackProcess`, `hostStackSocket` and `hostStack` at root `$defs`. Compiler semantic validation additionally checks ownership references, duplicate IDs and TCP/UDP state constraints. Runtime validation repeats critical checks because mutable runtime state may differ from compiled source.

## Presentation boundary

Visual Journey verifies that the Engine trace is bound to the requested destination and rejects manipulated:

- model/truth/completeness fields;
- process or socket identity;
- bind-scope projection;
- service ownership;
- selected service/socket rows;
- listener-consistency labels.

The browser renders service, process and socket tables plus explicit `NOT MODELED` values. It performs no process discovery, socket inference or listener calculation.

## Deliberate non-features

This checkpoint does **not** implement the remaining Phase E deliverables:

- DNS chain;
- DHCP DORA;
- full listener/service-state decision semantics;
- TCP state machine;
- UDP/ICMP failure distinctions;
- MTU/PMTUD;
- real guest process/socket discovery;
- live commands, packet capture or host inspection;
- AI/ML/LLM inference.

The existing service/listener semantics remain authoritative for current reachability. Host Stack consistency is explanatory evidence, not a new competing listener engine.

## Verification target

The checkpoint is accepted only if Engine, Observation/Active Probe, Visual Journey/UI contract, schema/compiler, Canvas, branding, acceptance contract and package-lock gates pass after the version bump. Foundation/browser/build/Parrot gates remain separately classified by actual execution.
## Final local verification on version-bumped source

- `npm run test:engine`: PASS — 281 functional, 145 adversarial, 24 regression, 22 regression-adversarial assertions.
- `npm run test:observation`: PASS — Observation 88 functional + 11 adversarial; Active Probe 191 functional + 29 adversarial assertions.
- `npm run test:visual-journey`: PASS — 30 functional + 83 adversarial; UI contract and `ui/app/main.mjs` syntax PASS.
- `npm run test:schema`: PASS — 55/55 fixture expectations + 18/18 Draft 2020-12 meta-validations, including explicit source/normalized Host Stack cases.
- `npm run test:compiler`: PASS — 69 functional + 96 adversarial assertions + 2/2 generated-output schema validations.
- `npm run test:canvas`: PASS — 19 functional + 10 adversarial; device visuals 31 functional + 16 adversarial.
- branding, acceptance-contract and package-lock gate: PASS; required package count 33.

Environment-dependent gates actually run:

- `npm run test:foundation`: RC 2 / **BLOCKED** after Canvas; first stop is Layout TypeScript compilation because `elkjs/lib/elk.bundled.js` is not installed.
- `npm run check:browser-readiness`: RC 77 / **BLOCKED** because the pinned installed dependency tree is absent.
- `npm run build`: RC 2 / **BLOCKED** on missing `elkjs` and `ajv`.
- Parrot OS x86-64 acceptance: **NOT RUN**.
- final real Chromium acceptance: **NOT RUN**.
- final real Firefox acceptance: **NOT RUN**.

This remains a development checkpoint and is **not** a VERIFIED PRODUCT RELEASE.

## Next authoritative Phase E slice

After this checkpoint is sealed, the next listed Phase E deliverable is **DNS chain**.
