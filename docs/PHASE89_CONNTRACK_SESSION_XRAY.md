# Phase 89 — Conntrack/Session X-Ray (v1.1.0-dev.10 candidate)

This checkpoint advances authoritative Phase D — Stateful Network Decisions with the third bounded vertical slice: explicit Engine-owned conntrack/session snapshot evidence, stateful-firewall binding, and X-Ray presentation. It does **not** implement a clock-driven session tracker, automatic connection creation/expiry, reverse-tuple reconstruction, or forward/return-path comparison.

## Truth boundary

Phase 89 uses explicit modeled state rather than inferred traffic history. A firewall resource may declare:

```json
{
  "conntrack": {
    "complete": true,
    "entries": [
      {
        "id": "ct-rdp",
        "source": "198.51.100.10",
        "destination": "rds01",
        "protocol": "tcp",
        "port": 3389,
        "state": "ESTABLISHED"
      }
    ]
  }
}
```

The modeled tuple is deliberately bounded to:

- literal IPv4 source address;
- destination resource identity;
- protocol (`tcp`, `udp`, `icmp`);
- destination port for TCP/UDP;
- explicit connection state (`NEW`, `ESTABLISHED`, `RELATED`, `INVALID`, or `UNKNOWN`).

Source ports, timers, TCP flags, sequence numbers, dynamic NAT reverse mappings and inferred packet history are not modeled by this checkpoint.

`conntrack.complete` is evidence provenance, not a cosmetic flag. With a structurally valid complete table, an exact tuple miss is a proven `FALSE` lookup. With an incomplete table, absence is not proof and the same miss is `UNKNOWN`.

## Engine-owned lookup

The Network Engine evaluates conntrack only on a reached firewall resource that declares the model. It compares the current Engine-observed tuple after all already-applied upstream transformations. Each row receives an immutable disposition:

- `MATCH`;
- `NO_MATCH`;
- `DISABLED`;
- `MALFORMED`;
- `INDETERMINATE`.

The Engine fails closed for malformed active rows, duplicate row IDs, ambiguous duplicate tuple matches, unsupported values or an explicitly selected `UNKNOWN` state. It never chooses a row in UI code.

A unique matching row with a known state produces `TRUE` and binds `selectedEntryId` plus the exact `connectionState`. A unique matching row whose modeled state is `UNKNOWN` preserves the row identity but produces `UNKNOWN`. More than one matching active row is ambiguous and produces `UNKNOWN` with no invented selection.

## Stateful firewall binding

Firewall rules remain the existing ordered policy engine. A rule may add one bounded predicate:

```json
{
  "connectionState": "ESTABLISHED"
}
```

Allowed rule-side states are `NEW`, `ESTABLISHED`, `RELATED` and `INVALID`. The rule still evaluates source, destination, protocol and port through the existing firewall semantics. Only when those predicates match does the Engine bind the rule to conntrack evidence:

- exact proven state match → `connectionStateMatch = TRUE`;
- complete-table miss or a different known state → `FALSE`, and ordered rule evaluation continues;
- no table, incomplete/unprovable lookup, malformed/ambiguous table or selected `UNKNOWN` state → `UNKNOWN`, and the stateful decision fails closed.

Conntrack does **not** independently allow traffic. An `ESTABLISHED` entry matters only because an explicit ordered firewall rule asks for `ESTABLISHED`. A stateless earlier rule remains stateless.

## Cross-layer ordering

Phase 89 preserves prior truth boundaries:

- a lower-layer upstream block stops evaluation before a downstream firewall is reached;
- therefore an upstream STP block emits no fabricated downstream conntrack/session trace or stateful firewall trace;
- an upstream SNAT rewrite changes the source address observed by a downstream conntrack lookup; the lookup must match the translated source, not the original one;
- conntrack cannot override a previous VLAN/MAC/STP/routing/neighbor/NAT/policy block.

Focused Engine tests explicitly prove both the STP suppression case and SNAT→downstream-conntrack source binding.

## Propagation

The exact evidence chain is:

```text
Network Engine
→ ReachabilityDetails.conntrackDecisions
→ ActiveProbeTranscript.conntrackDecisions
→ VisualJourneyModel.conntrackDecisions
   → conntrack.lookup
→ Conntrack/Session X-Ray
```

No layer downstream of Engine recomputes state.

## Fail-closed presentation boundary

Visual Journey rejects manipulated or internally inconsistent conntrack traces. Checks include resource/path/destination binding, one decision per resource, valid completeness/state/disposition values, ordered indexes, unique entry identities, selected-row consistency, decision-state consistency, truth/selection agreement and consistency between a stateful firewall rule's declared `connectionState`, `connectionStateMatch` and the Engine conntrack result.

A rejected transcript produces no trusted X-Ray. The UI does not repair or infer missing state.

## Conntrack/Session X-Ray

The UI projects only Engine-produced fields:

- firewall/resource identity;
- requested destination;
- lookup truth;
- complete/incomplete table provenance;
- observed source and destination port;
- selected entry identity;
- proven connection state;
- ordered entry rows and their source/destination/protocol/port matches;
- row dispositions and selected marker.

The Firewall/ACL X-Ray also displays the declared connection state and Engine-produced state-match truth for each relevant rule. The UI performs no conntrack lookup, session creation, session expiry or firewall evaluation.

## Compiler and schema contract

Source and normalized schemas define the conntrack table and row shapes. Compiler semantic validation additionally enforces literal IPv4 source addresses, declared destination resources, protocol/port relationships, unique IDs and supported states. A firewall rule that declares `connectionState` requires an explicit conntrack table on the same resource.

## Verification in this environment

Focused tests actually run on the Phase 89 implementation:

- `npm run test:engine`: **242 functional + 128 adversarial + 24 regression + 22 regression-adversarial PASS**;
- `npm run test:observation`: Observation Wave 1 **88 functional + 11 adversarial PASS** and Active Probe **157 functional + 26 adversarial PASS**;
- `npm run test:visual-journey`: **21 functional + 68 adversarial + UI-contract PASS**;
- `npm run test:schema`: **55/55 fixture expectations + 18/18 schema meta-validations PASS**, plus explicit inline conntrack structural checks;
- `npm run test:compiler`: **69 functional + 78 adversarial + 2/2 generated-output schema validations PASS**;
- `npm run test:canvas`: **19 functional + 10 adversarial + 31 device-visual functional + 16 device-visual adversarial PASS**;
- branding guard: **PASS**;
- acceptance-contract: **PASS**.

Checkpoint sealing verified the dependency/browser/Foundation boundary explicitly. `npm run check:package-lock` is **PASS** with 33 required packages and there are no dependency declaration changes from dev9. `npm run test:foundation` advances through Canvas with the Phase 89 Engine/Observation/compiler results above and then stops at Layout because the installed dependency tree is absent (`elkjs/lib/elk.bundled.js` cannot be resolved). `npm run check:browser-readiness` returns **RC 77 / BLOCKED** and reports the pinned browser/toolchain packages as not installed; `npm run build` is therefore also blocked by missing `elkjs`/`ajv`, not by a Phase 89 logic assertion. Parrot OS and final real Chromium/Firefox acceptance remain **NOT RUN** in this environment.

## Remaining Phase D work

Phase 89 intentionally leaves these items unresolved:

- automatic session creation, mutation, timeout/aging and expiry;
- source-port/full 5-tuple conntrack modeling;
- reverse tuple / automatic reverse NAT reconstruction;
- explicit local-host firewall versus network-firewall distinction from the authoritative Phase D deliverables;
- forward/return-path comparison.

The next checkpoint should follow the authoritative roadmap rather than expanding Phase 89 implicitly.

This is a development checkpoint, not a VERIFIED PRODUCT RELEASE.
