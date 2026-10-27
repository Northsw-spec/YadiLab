# Phase 90 — Local Host Firewall vs Network Firewall Distinction (v1.1.0-dev.11 candidate)

This checkpoint advances authoritative Phase D — Stateful Network Decisions with the fourth bounded vertical slice: an explicit Engine-owned distinction between a network firewall on the transit path and a local host firewall attached to an endpoint or other non-`network.firewall` resource. It does **not** implement forward/return-path comparison, automatic conntrack lifecycle, reverse-tuple reconstruction, live host-firewall inspection, or any UI-owned firewall inference.

## Truth boundary

Phase 90 formalizes a firewall-location model that already existed implicitly in Engine reachability semantics. It does not create a second firewall engine. The classification is:

- resource type `network.firewall` → `firewallScope = NETWORK`;
- non-`network.firewall` resource with `properties.isFirewall = true` → `firewallScope = LOCAL_HOST`;
- non-network resource with firewall policy but without `isFirewall=true` → scope cannot be proven and evaluation fails closed;
- malformed runtime `isFirewall` values → scope cannot be proven and evaluation fails closed.

`network.firewall` remains authoritative at runtime. A manipulated runtime marker cannot downgrade a resource whose declared type is already `network.firewall`. Source/compiler validation separately rejects a contradictory `network.firewall` declaration with `isFirewall=false`.

## Engine-owned policy location

Firewall rule evaluation remains the same ordered Engine policy machinery introduced before this phase. Phase 90 adds `FirewallScope = NETWORK | LOCAL_HOST` to the Engine-owned FIREWALL decision trace. The scope is decided once by Engine classification and travels with the immutable trace.

A local host firewall therefore does not become a special allow/deny shortcut. It still uses the same ordered rules, default action, source/destination/protocol/port predicates and Phase-89 conntrack state binding as a network firewall. The difference is **where the policy is proven to live**, not a competing decision algorithm.

## Schema and compiler contract

Source and normalized scenario schemas now explicitly define:

```json
{
  "properties": {
    "isFirewall": true
  }
}
```

Compiler semantic validation enforces the distinction:

- `FIREWALL_MARKER_INVALID` for a non-boolean marker;
- `NETWORK_FIREWALL_MARKER_CONTRADICTION` when a `network.firewall` explicitly declares `isFirewall=false`;
- `LOCAL_FIREWALL_MARKER_REQUIRED` when a non-network-firewall resource declares firewall `rules` or `defaultAction` without `isFirewall=true`.

Additional resource properties remain extensible under the existing schema design; this phase only makes the firewall-location marker explicit and independently testable.

## Cross-layer ordering

All previous truth boundaries remain authoritative. In particular:

- routing, neighbor, MAC/CAM, VLAN and STP decisions can stop the path before a downstream firewall is reached;
- NAT transformations change the tuple seen by downstream policy and conntrack;
- conntrack is still evidence used by an explicit stateful firewall rule, never a parallel allow engine;
- local-host policy is evaluated only when the resource is actually reached;
- a downstream local-host firewall cannot override an upstream network-firewall deny;
- a network-firewall allow does not imply the destination local-host firewall also allows the flow.

The Engine therefore can produce two distinct FIREWALL traces on one proven path: first a `NETWORK` trace and later a `LOCAL_HOST` trace. Ordered reachability remains authoritative.

## Propagation

The exact evidence chain is:

```text
Network Engine
→ ReachabilityDetails.policyDecisions[]
   → FIREWALL.firewallScope = NETWORK | LOCAL_HOST
→ ActiveProbeTranscript.policyDecisions[]
→ VisualJourneyModel.policyDecisions[]
   → policy.decision
→ Firewall/ACL X-Ray
```

No downstream layer reclassifies a firewall independently.

## Fail-closed presentation boundary

Visual Journey validates the Engine trace against the declared scenario resource before rendering it.

For a FIREWALL trace:

- a `network.firewall` resource must carry `NETWORK`;
- a non-network resource with `isFirewall=true` must carry `LOCAL_HOST`;
- missing, contradictory or manipulated scope is rejected with `VISUAL_JOURNEY_POLICY_TRACE_FIREWALL_SCOPE_MISMATCH`;
- an ACL trace is not allowed to carry firewall scope and is rejected with `VISUAL_JOURNEY_POLICY_TRACE_FIREWALL_SCOPE_INVALID`.

The UI does not repair a missing marker or infer scope from labels, rule names, topology position, operating-system type or visual appearance.

## Firewall/ACL X-Ray

The existing Firewall/ACL X-Ray now projects the Engine scope explicitly. The panel exposes `data-policy-firewall-scope` and displays `Firewall scope: NETWORK` or `Firewall scope: LOCAL HOST` while preserving the exact ordered rule table, selected policy, default-action provenance, truth and Phase-89 connection-state evidence.

The distinction is evidence, not decoration: the same rule identity on a host and on a network appliance remains two different policy locations in the Engine trace.

## Verification in this environment

Focused tests run before sealing this checkpoint:

- schema: **55/55 fixture expectations + 18/18 schema meta-validations PASS**, plus explicit source/normalized `isFirewall` checks;
- compiler: **69 functional + 83 adversarial + 2/2 generated-output schema validations PASS**;
- Engine: **250 functional + 133 adversarial + 24 regression + 22 regression-adversarial PASS**;
- Observation Wave 1: **88 functional + 11 adversarial PASS**;
- Active Probe: **163 functional assertions + 28 adversarial cases PASS**;
- Troubleshooting Notebook/Evidence Review/Remediation/Typed Remediation regression suites: **PASS**;
- Visual Journey: **26 functional + 71 adversarial + UI-contract PASS**;
- Canvas: **19 functional + 10 adversarial; device visuals 31 functional + 16 adversarial PASS**;
- branding, acceptance-contract and package-lock gate: **PASS**; package-lock still reports 33 required packages.

Final environment gates were also executed on the version-bumped Phase 90 source. `npm run test:foundation` is **RC 2 / BLOCKED** after passing through Canvas; its first stop is Layout TypeScript compilation because `elkjs/lib/elk.bundled.js` is not installed. `npm run check:browser-readiness` is **RC 77 / BLOCKED** and reports the pinned browser/toolchain dependency tree as absent. `npm run build` is **RC 2 / BLOCKED** on missing `elkjs` and `ajv`. These are environment/dependency blockers, not relabelled Phase-90 PASS results. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN** in this environment.

## Deliberate limitations

Phase 90 intentionally does not implement:

- forward-vs-return path comparison;
- reverse conntrack tuple reconstruction;
- automatic session creation, aging or expiry;
- live OS firewall inspection or host command execution;
- inferred firewall location from operating system, labels or topology;
- any AI/ML/LLM behavior.

The next authoritative Phase D checkpoint is **forward/return path comparison**, which must build on the Engine-produced routing/NAT/conntrack/policy traces rather than recomputing them in UI code.
