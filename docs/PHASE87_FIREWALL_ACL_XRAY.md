# Phase 87 — Firewall/ACL X-Ray (v1.1.0-dev.8 candidate)

This checkpoint begins the authoritative Phase D — Stateful Network Decisions roadmap with the first bounded vertical slice: deterministic firewall/ACL decision evidence and X-Ray presentation. It deliberately does **not** implement NAT/PAT, conntrack/session state or forward/return-path comparison; those remain later Phase D checkpoints.

## Truth boundary

Firewall and ACL policy evaluation remains owned by the Network Engine. Existing ordered first-match semantics are preserved. The Engine now emits an immutable `PolicyDecisionTrace` whenever an ACL or firewall layer participates in a reachability decision.

A decision trace binds:

- policy kind: `ACL` or `FIREWALL`;
- evaluating resource and requested destination;
- exact Engine truth: `TRUE`, `FALSE` or `UNKNOWN`;
- observed source address when the Engine has one;
- ordered rule rows;
- selected policy identity, when one exists;
- declared default action and whether that default was actually used;
- the Engine explanation for the decision.

Each ordered rule row is explicit about whether it was:

- `MATCH`;
- `NO_MATCH`;
- `DISABLED`;
- `MALFORMED`;
- `INDETERMINATE`;
- `NOT_EVALUATED` because an earlier ordered rule already terminated evaluation.

Source, destination, protocol and port match evidence is carried from the Engine where it was actually evaluated. A later rule is never presented as evaluated after a terminal match or indeterminate selector.

The Engine also owns ACL default-only decisions. The former Active Probe-only fallback for `aclDefaultAction` has been removed so there is one policy truth source rather than a second presentation/observation evaluator.

## Fail-closed behavior

The existing Engine keeps unsupported, malformed or unresolved policy input as `UNKNOWN`; it does not coerce uncertainty into allow/deny. The trace makes that boundary visible rather than inventing a reason after the fact.

Visual Journey independently validates the received Engine trace before rendering it. It rejects manipulated or internally inconsistent traces including:

- unknown resources or path/destination mismatch;
- unsupported policy kinds;
- duplicate decisions for the same resource/policy layer;
- reordered/incomplete rule indexes;
- duplicate rule identities;
- ambiguous or inconsistent selected rows;
- rules marked evaluated after a terminal match/indeterminate row;
- `NOT_EVALUATED` before any terminal ordered decision;
- a default action claimed after an indeterminate rule;
- selected/default action truth that disagrees with the declared action;
- `TRUE` policy truth without an explicit selected allow rule or valid allow default.

A rejected trace produces no Firewall/ACL X-Ray. The UI never repairs, re-evaluates or guesses policy state.

## Propagation

The exact trace flows through the existing authoritative chain:

```text
Network Engine
→ ReachabilityDetails.policyDecisions
→ ActiveProbeTranscript.policyDecisions
→ VisualJourneyModel.policyDecisions
   → policy.decision
→ Firewall/ACL X-Ray
```

A blocking firewall/ACL decision is emitted before the terminal drop event. Visual Journey does not create a later `flow.segment` beyond the proven blocking point.

Phase C truth remains authoritative in the same path. A firewall/ACL allow cannot create motion over a path already stopped by routing, neighbor, MAC/VLAN or STP truth; presentation code cannot use policy state to bypass STP blocking.

## Presentation

The in-place Firewall/ACL X-Ray displays only Engine-produced fields:

- policy layer and resource;
- destination and observed source;
- final Engine truth;
- selected policy identity;
- default action and whether it was used;
- ordered rule table;
- per-rule selector/match evidence and evaluation disposition.

Selected, uncertain and not-evaluated rows use distinct semantic styling. DOM acceptance attributes expose the policy kind, resource, truth, selected policy, default provenance and per-row selected/disposition state.

The UI explicitly states that it performs no firewall/ACL evaluation.

## Verification coverage in this environment

Tests actually run after the Phase 87 implementation include:

- `npm run test:engine`: **199 functional + 107 adversarial + 24 regression + 22 regression-adversarial PASS**;
- Active Probe core: **137 functional + 24 adversarial PASS**;
- `npm run test:visual-journey`: **14 functional + 45 adversarial + UI-contract PASS**, including the JavaScript syntax check for `ui/app/main.mjs`;
- `npm run test:observation`: Observation Wave 1 plus Active Probe PASS;
- troubleshooting notebook: **48 functional + 18 adversarial PASS**;
- evidence review: **35 functional + 14 adversarial PASS**;
- remediation loop: **28 functional + 16 adversarial PASS**;
- typed remediation: **41 functional + 30 adversarial PASS**;
- `npm run test:compiler`: **69 functional + 63 adversarial + 2/2 generated-output schema validations PASS**;
- `npm run test:canvas`: **19 functional + 10 adversarial + 31 device-visual functional + 16 device-visual adversarial PASS**;
- `npm run test:schema`: **55/55 fixture expectations + 18/18 schema meta-validations PASS**;
- branding and acceptance-contract gates: **PASS**;
- source-checkout identity tests: **6 functional + 6 adversarial PASS**;
- package-lock structural gate: **PASS, 33 required packages**.

`npm run test:foundation` was also attempted. It passed the repository chain through schema, branding, enterprise, fault engine, observation, compiler, versioning, renderer, capability packs, asset library, Engine, PackageIO, CLI and Canvas, then stopped at Layout TypeScript compilation because the pinned `elkjs/lib/elk.bundled.js` dependency is not installed in this execution environment. The interrupted dependency install could not be reconstructed offline because at least `zustand-4.5.7.tgz` is absent from the npm cache. The full Foundation command is therefore **BLOCKED, not PASS**.

For the same environment reason, `npm run test:active-probes` passes its Active Probe core and then is **BLOCKED** when the browser tree needs `elkjs`; `npm run test:browser` and `npm run build` are **BLOCKED** at missing installed pinned packages, and browser-readiness reports the dependency closure as unavailable. No dependency declaration was added or changed by Phase 87.

Real Parrot OS and final real Chromium/Firefox acceptance were **NOT RUN**.

## Remaining Phase D work

The next authoritative Phase D slice is NAT/PAT transformation X-Ray according to the existing roadmap. Conntrack/session-table semantics follow after NAT/PAT, then forward/return-path comparison.

Real Parrot OS and final target Chromium/Firefox acceptance also remain pending. This is a development checkpoint, not a VERIFIED PRODUCT RELEASE.
