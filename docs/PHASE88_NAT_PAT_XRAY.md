# Phase 88 — NAT/PAT transformation X-Ray (v1.1.0-dev.9 candidate)

This checkpoint advances authoritative Phase D — Stateful Network Decisions with the second bounded vertical slice: immutable Engine-owned NAT/PAT transformation evidence and X-Ray presentation. It deliberately does **not** implement conntrack/session state or forward/return-path comparison; those remain later Phase D checkpoints.

## Truth boundary

Existing Network Engine NAT semantics from the earlier DNAT and SNAT phases remain authoritative. Phase 88 does not add a second NAT evaluator and does not reinterpret translation in the UI. The Engine now emits an immutable `NatDecisionTrace` whenever a DNAT or SNAT layer participates in a reachability decision.

A NAT decision trace binds:

- translation layer: `DNAT` or `SNAT`;
- evaluating resource and requested destination;
- exact Engine truth: `TRUE`, `FALSE` or `UNKNOWN`;
- required/optional policy mode when declared;
- transformation disposition: `TRANSLATED`, `PASSTHROUGH`, `BLOCKED` or `UNKNOWN`;
- exact ordered NAT rule rows;
- selected rule identity, when one exists;
- before/after source identity and port values where the Engine actually knows them;
- the Engine explanation for the decision.

Each NAT rule row records the Engine-owned evaluation disposition:

- `MATCH`;
- `NO_MATCH`;
- `DISABLED`;
- `MALFORMED`;
- `INDETERMINATE`;
- `NOT_EVALUATED` after an ordered terminal decision;
- `OTHER_KIND` when a rule belongs to the other NAT layer;
- `DECLARED` only for syntactically valid SNAT rows whose match pass was deliberately not reached because SNAT prevalidation failed closed on another malformed declaration.

The trace also carries exact selector results where evaluated: source, destination, protocol and port matching.

## Preserved DNAT and SNAT semantics

Phase 88 preserves the existing Engine behavior rather than changing it for presentation convenience.

DNAT remains ordered first-match destination translation. A selected rule can translate the destination port, explicitly block, pass through, or become `UNKNOWN` for unsupported/malformed state. Later rows after an ordered terminal DNAT decision are reported as `NOT_EVALUATED`.

SNAT keeps its stricter existing prevalidation boundary: every enabled SNAT declaration is syntactically validated before any source rewrite is selected. Therefore a malformed later SNAT declaration can invalidate the SNAT layer even when an earlier rule would otherwise match. In that outcome valid rows remain `DECLARED`, the malformed row is explicit, no selected rule is invented, and the decision is `UNKNOWN`.

Source-port PAT is still **not modeled for SNAT**. A SNAT declaration that attempts `translatedPort` remains malformed/fail-closed. Destination-port translation through DNAT remains the existing bounded port-forward/PAT-like behavior.

No conntrack table, stateful return-flow reconstruction or automatic reverse NAT is introduced in this checkpoint.

## Fail-closed presentation boundary

Visual Journey validates the Engine NAT trace before rendering it. Manipulated or internally inconsistent traces are rejected rather than repaired. Guards include:

- unknown resources or path/destination mismatch;
- unsupported NAT kind or transformation disposition;
- duplicate decisions for the same resource/NAT layer;
- reordered/incomplete rule indexes;
- duplicate rule identities;
- ambiguous or inconsistent selected rows;
- `NOT_EVALUATED` before a terminal ordered decision;
- continued ordered evaluation after a match/indeterminate row;
- leftover `DECLARED` rows outside the exact malformed-SNAT prevalidation outcome;
- truth/transformation disagreement;
- invalid input/output ports;
- SNAT source-port PAT projection;
- DNAT source-address rewriting;
- selected rule type disagreement with the NAT layer;
- blocking action inconsistent with `FALSE/BLOCKED`;
- `TRANSLATED` without a selected rule or without an actual before/after rewrite.

A rejected trace produces no NAT/PAT X-Ray. The UI never re-evaluates NAT rules, chooses a winner or synthesizes before/after values.

## Propagation

The exact trace flows through the existing authoritative chain:

```text
Network Engine
→ ReachabilityDetails.natDecisions
→ ActiveProbeTranscript.natDecisions
→ VisualJourneyModel.natDecisions
   → nat.transform
→ NAT/PAT X-Ray
```

For combined translation, DNAT is emitted before SNAT and the SNAT input port is the Engine's post-DNAT port. NAT evaluation is bound to path reachability: a transit resource is evaluated only after the preceding modeled path has actually reached it, so an upstream VLAN/MAC/STP/route/neighbor block cannot produce a downstream NAT trace. A blocking or unknown NAT layer stops later fabricated motion according to the Engine verdict. Existing Phase C STP and Phase 87 firewall/ACL truth remain independent authoritative layers; NAT cannot override a previously proven block.

## Presentation

The in-place NAT/PAT X-Ray displays only Engine-produced data:

- DNAT/SNAT layer and resource;
- requested destination;
- policy mode;
- final truth and transformation disposition;
- selected rule identity;
- source before/after;
- port before/after;
- ordered NAT rule table;
- declared rule type, selectors, action and translated fields;
- per-selector match evidence and evaluation disposition.

The UI explicitly states that it performs no NAT/PAT evaluation and that conntrack/return-path symmetry is not simulated in this phase.

## Verification coverage in this environment

Tests actually run after the Phase 88 implementation include:

- `npm run test:engine`: **220 functional + 114 adversarial + 24 regression + 22 regression-adversarial PASS**;
- `npm run test:observation`: Observation Wave 1 **88 functional + 11 adversarial PASS** and Active Probe **149 functional + 25 adversarial PASS**;
- `npm run test:visual-journey`: **16 functional + 58 adversarial + UI-contract PASS**, including JavaScript syntax validation for `ui/app/main.mjs`;
- `npm run test:schema`: **55/55 fixture expectations + 18/18 schema meta-validations PASS**;
- `npm run test:compiler`: **69 functional + 63 adversarial + 2/2 generated-output schema validations PASS**;
- `npm run test:canvas`: **19 functional + 10 adversarial + 31 device-visual functional + 16 device-visual adversarial PASS**;
- branding guard: **PASS**;
- acceptance-contract: **PASS**;
- package-lock structural gate: **PASS, 33 required packages**.

A whole-chain `npm run test:foundation` attempt on the Phase 88 implementation passed schema, branding, enterprise, fault engine, Observation/Active Probe, troubleshooting notebook/evidence/remediation, compiler, versioning, renderer, capability packs, asset library, Engine, PackageIO, CLI and Canvas, then stopped at Layout TypeScript compilation because `elkjs/lib/elk.bundled.js` is not installed in this execution environment. After the final cross-layer path-reachability hardening, all focused/core suites above were rerun and passed; a second whole-chain attempt was externally terminated by this execution harness after CLI before reaching Layout. A separate final `tsc -p tests/tsconfig.layout.json` check still fails at exactly the same missing `elkjs/lib/elk.bundled.js` dependency boundary. Full Foundation is therefore **BLOCKED / NOT COMPLETED, not PASS**.

Real Parrot OS and final real Chromium/Firefox acceptance were **NOT RUN**. No dependency declaration was added or changed by Phase 88.

## Remaining Phase D work

The next authoritative Phase D slice is **conntrack/session state** according to the existing roadmap. Forward/return-path comparison follows after conntrack/session state.

This is a development checkpoint, not a VERIFIED PRODUCT RELEASE.
