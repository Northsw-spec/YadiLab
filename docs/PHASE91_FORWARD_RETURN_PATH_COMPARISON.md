# Phase 91 — Forward / Return Path Comparison (v1.1.0-dev.12 candidate)

This checkpoint completes the listed authoritative Phase D — Stateful Network Decisions deliverables with an Engine-owned comparison of the forward network path and the independently evaluated return network path. It does **not** assume path symmetry, reconstruct an unmodeled TCP/UDP client ephemeral return port, create reverse conntrack tuples, simulate dynamic session lifecycle, or let the UI recompute routing/security truth.

## Truth boundary

The Network Engine remains the sole owner of reachability and path decisions. A normal forward `queryReachability()` now also produces an immutable `ForwardReturnPathComparisonTrace` in `ReachabilityDetails.pathComparison`.

The comparison binds:

- source, destination, protocol and requested service port;
- exact forward truth, forward path and forward blocking point;
- exact return truth, independently evaluated return path and return blocking point;
- `SYMMETRIC`, `ASYMMETRIC` or `UNRESOLVED` path classification;
- return evaluation mode and reverse-security modeling status;
- per-resource forward/return route-egress-interface comparisons;
- Engine-produced return route, neighbor, MAC/CAM, VLAN, STP, policy, NAT and conntrack traces when that reverse evidence can actually be modeled.

No presentation layer may infer a missing return hop, reverse firewall decision, reverse NAT transformation or session state.

## Independent return-path evaluation

The return path is evaluated from the original destination back to the original source. The Engine does not reverse the forward path array and does not assume that a bidirectional connection implies routing symmetry.

Consequently:

- identical reversed resource paths are classified `SYMMETRIC`;
- a valid but different return resource path is `ASYMMETRIC`;
- unresolved/indeterminate evidence remains explicit instead of being repaired downstream;
- routing decisions on the same resource expose whether the forward and return egress interfaces differ.

A directed/asymmetric topology can therefore show a different return router, while a symmetric topology can prove the exact reverse path.

## Reverse security boundary for TCP/UDP

A TCP/UDP service probe models the destination service port, for example client → server TCP/443. YadiLab does not currently model the client's dynamically selected ephemeral source port. Mirroring `443` onto the return destination would create a false reverse tuple.

Therefore a service-port query uses:

```text
returnEvaluationMode = NETWORK_ONLY
returnSecurityStatus = RETURN_TUPLE_NOT_MODELED
```

In this mode the Engine evaluates the return **network path** but deliberately does not emit reverse firewall-policy, NAT or conntrack decisions that require the missing tuple. Any attempt to insert such evidence is rejected by Visual Journey validation.

For a portless query such as modeled ICMP reachability, the Engine can use:

```text
returnEvaluationMode = FULL
returnSecurityStatus = MODELED
```

The reverse path still disables destination-listener checking because response traffic is not modeled as a new application-listener request.

## NAT/session implications

Phase 91 does not claim automatic reverse NAT or state reconstruction. Instead `natStateImplication` records the evidence boundary:

- `NONE` when no modeled forward NAT/session implication exists;
- `MODELED` where the return security/state evidence is fully modeled;
- `RETURN_TUPLE_REQUIRED` when forward NAT/conntrack evidence exists but a TCP/UDP reverse tuple cannot be proven without the missing ephemeral port.

This preserves Phase 88/89 truth without inventing reverse transformations or sessions.

## Cross-phase ordering

All earlier truth boundaries remain authoritative:

1. route / neighbor / MAC/CAM / VLAN / STP determine whether each direction can progress;
2. Phase 87 firewall/ACL and Phase 90 firewall-scope decisions remain Engine-owned;
3. Phase 88 NAT transforms only the tuple that the Engine actually modeled at that point;
4. Phase 89 conntrack matches only an explicit modeled session tuple;
5. Phase 91 compares the independently produced directional evidence; it does not override it.

An upstream STP or firewall block remains a real blocking point. A return path may fail or diverge even when the forward path succeeded.

## Propagation

The evidence chain is:

```text
Network Engine
→ ReachabilityDetails.pathComparison
→ ActiveProbeTranscript.pathComparison
→ VisualJourneyModel.pathComparison
→ Forward / Return Path X-Ray
```

Visual Journey validates the trace before projecting it to scenario connection IDs. The UI receives only validated, Engine-owned path/evidence structures.

## Fail-closed Visual Journey validation

Before rendering, Visual Journey requires that:

- comparison endpoints equal the transcript destination/source directions;
- protocol/service port equal the original probe;
- forward truth/path/blocking point exactly equal the original Engine transcript;
- the return path begins at the original destination and ends at the original source;
- the return blocking point belongs to the return path when present;
- symmetry classification agrees with the two paths;
- return evaluation mode and security status agree with whether a service port is modeled;
- `NETWORK_ONLY` contains no fabricated reverse policy/NAT/conntrack evidence;
- all return subtraces pass their existing route/neighbor/MAC/VLAN/STP/NAT/conntrack/policy validators;
- interface comparison rows exactly match Engine route traces.

Manipulated endpoint binding, false symmetry, invented reverse policy/state, invalid return mode or fake interface differences fail closed before rendering.

## Forward / Return Path X-Ray

The topology can render two simultaneous Engine-projected directional overlays:

- forward path;
- return path.

The X-Ray panel shows forward/return truth, path strings, symmetry state, return evaluation/security boundary, NAT/state implication and forward-vs-return route-interface differences. Asymmetric routing is surfaced as an evidence-backed warning rather than inferred from line geometry.

The UI does not run route search, invert connections, choose egress interfaces, reconstruct reverse NAT or infer session state.

## Focused verification before sealing

Pre-version-bump focused/core verification on the Phase 91 implementation:

- Engine: **263 functional + 136 adversarial + 24 regression + 22 regression-adversarial PASS**;
- Observation Wave 1: **88 functional + 11 adversarial PASS**;
- Active Probe: **176 functional assertions + 28 adversarial cases PASS**;
- Visual Journey: **29 functional + 77 adversarial + UI-contract PASS**;
- schema: **55/55 fixture expectations + 18/18 schema meta-validations PASS**;
- compiler: **69 functional + 83 adversarial + 2/2 generated-output schema validations PASS**;
- Canvas: **19 functional + 10 adversarial; device visuals 31 functional + 16 adversarial PASS**;
- branding, acceptance-contract and package-lock gate: **PASS**; package-lock reports 33 required packages.

The same core matrix was rerun after the `1.1.0-dev.12` version bump with the same PASS counts.

Final environment gates on that version-bumped source were also executed. `npm run test:foundation` is **RC 2 / BLOCKED** after passing through Canvas; the first stop is Layout TypeScript compilation because `elkjs/lib/elk.bundled.js` is not installed. `npm run check:browser-readiness` is **RC 77 / BLOCKED** and reports the pinned installed dependency tree absent. `npm run build` is **RC 2 / BLOCKED** on missing `elkjs` and `ajv`. These are environment/dependency blockers and are not relabelled as Phase-91 test failures or PASS results. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN** in this environment.

## Deliberate limitations

Phase 91 intentionally does not implement:

- TCP/UDP client ephemeral-port allocation;
- automatic reverse NAT/PAT reconstruction;
- automatic reverse conntrack tuple/session synthesis;
- conntrack creation, aging or expiry;
- live network probing or guest command execution;
- UI-owned routing/security calculations;
- any AI/ML/LLM behavior.

With this checkpoint the **listed Phase D deliverables are implemented**. The next authoritative roadmap phase is **Phase E — Host Stack & Core Services**, subject to this checkpoint being sealed and its environment-dependent release gates remaining honestly classified.
