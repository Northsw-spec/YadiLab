# Phase 97 — UDP / ICMP Failure Distinctions (v1.1.0-dev.18)

## Scope and authority

This slice implements the next Phase E deliverable in section 32 of the authoritative Living Topology specification. Dev17 is the sole source baseline; no older WIP implementation is merged. Masterprompt v1.3 and the locked v1.0.0 release remain unchanged.

The Engine classifies existing decisions. It does not introduce a second network engine, packet capture, live sockets, UDP handshake, synthetic session, retry timer or ICMP packet generator. Scenario/compiler/schema input contracts remain unchanged: existing hostStack, policy, NAT, route, VLAN and STP state are sufficient.

## Engine semantics

`queryReachability` returns an immutable `UdpIcmpFailureDecisionTrace` for UDP destination-port and portless ICMP requests. `networkTruthBeforeListener` records the Engine's network/security gate separately from endpoint-listener truth. Unknown upstream UDP/ICMP evidence stops before reading destination listener state. Existing TCP/any semantics remain unchanged.

| Engine evidence | Distinction |
| --- | --- |
| Network/security TRUE + Phase95 UDP listener TRUE | DATAGRAM_DELIVERABLE |
| Network/security TRUE + complete no-listener evidence | NO_LISTENER |
| Network/security TRUE + Phase95 SERVICE_DISABLED listener result | SERVICE_DISABLED |
| Explicit policy FALSE before destination listener | POLICY_BLOCKED |
| Other proven upstream FALSE, including no topology path/STP/route | NETWORK_BLOCKED |
| Portless ICMP forward path TRUE | REQUEST_PATH_REACHABLE |
| Reached destination with unresolved partial listener snapshot | SNAPSHOT_INCOMPLETE |
| Incomplete, malformed or ambiguous evidence | UNKNOWN |

UDP is connectionless. Deliverability is not an observed receive or application response. Legacy service-only truth remains explicitly `SERVICE_DECLARATIONS`; no BOUND socket identity is fabricated. Multiple matching BOUND socket candidates remain UNKNOWN because socket-distribution/reuse semantics are not modeled. Phase95 listener truth itself remains separate from this delivery ambiguity.

The trace binds source, destination, protocol, requested UDP port, exact Engine-translated destination port/source where supplied, final truth, network/security truth, policy truth and listener model/disposition/truth. Policy truth is NOT_EVALUATED when no policy decision exists; an unvisited UDP listener is NOT_EVALUATED, while ICMP listener state is NOT_REQUIRED.

The pre-existing source-default-gateway diagnostic has been moved unchanged from Observation into `source-gateway-engine.ts`. `queryReachabilityWithSourceGateway` orchestrates the existing reachability query and this Engine-owned gate. If the gate blocks a modeled active probe, the Engine emits the final classification and discards unproven downstream decision evidence. Observation does not choose a failure reason. This retains existing Windows/Linux wrong-gateway diagnostics without introducing presentation-owned network truth.

NAT's effective port/source are preserved even when a reached destination has no listener. STP and policy blocks remain decisive before listener evidence; no UDP diagnostic bypasses a blocked switch port.

## NOT_MODELED boundaries

There is no explicit wire-level ICMP failure evidence in the current model. Therefore ICMP type/code, Destination/Port Unreachable, Echo Reply, UDP/application reply, timeout and retries are always NOT_MODELED. No failure is automatically called a timeout. Reverse-path comparison is topology/security analysis, not evidence of a transmitted reply.

MTU/PMTUD, fragmentation, Packet Too Big/Fragmentation Needed, TTL expiry, packet timing, loss/jitter/latency, retransmission, MSS and real host inspection are outside this slice.

## Exact propagation and presentation

Engine → Active Probe → Visual Journey → UDP / ICMP Failure X-Ray preserves the exact trace.

Windows exposes an explicitly modeled destination `Get-NetUDPEndpoint` projection; Linux exposes a modeled destination `ss -lunp` projection. Both combine Engine path and listener evidence without executing commands or claiming a successful on-wire UDP response. Existing ping/path probes carry the Engine classification and explicitly NOT_MODELED reply/timing evidence.

Journey checks the unique bound Engine query evidence, all copied decision collections, tuple/source/destination/protocol, exact summary and independent Host Stack/listener/NAT/STP/policy contracts. Engine-owned validation rejects added wire/timer fields, malformed/duplicate evidence and contradictory classifications. Validation checks semantic integrity, not cryptographic authenticity of an externally supplied transcript.

Diagnostic terminal events (`udp.failure`, `icmp.failure`) carry the exact Engine classification. They replace generic packet arrival/drop markers for these probes and remain complete under scrub/replay/reduced motion. UNKNOWN or blocked journeys do not animate unproven future hops.

The contextual X-Ray shows protocol/endpoints, original/effective UDP port, network/security gate, policy, listener model/disposition/truth, final distinction and NOT_MODELED wire/reply/timer fields. React only renders validated Journey data. Rendered UI-contract tests exercise the actual React component and escaping; they are not final Chromium/Firefox acceptance.

## Verification

Status: **LOCAL VERIFIED / PARROT PENDING**. Full `npm run test:foundation` completed through the final Journey gate with exit 0, pinned Python (`jsonschema 4.26.0`) and `go1.23.2 linux/amd64`, with dependency/toolchain network access disabled. The command chain contains 196 top-level commands plus nested tests.

Phase97 coverage: Engine 34 functional + 36 adversarial + 11 cross-phase assertions; Active Probe 38 functional + 10 adversarial; Journey 58 functional + 14 adversarial; actual React-render X-Ray contract 21 assertions. The unchanged prior core suites also pass: Engine 363 + 187 + 24 regression + 22 regression-adversarial; Active Probe 225 + 32; Journey 44 + 97; Compiler 69 + 131 plus 2/2 output-schema; schema 55/55 fixtures and 18/18 meta-validations. Counts are assertions, not claims of that many independent scenarios.

Offline browser application bundling completed successfully with 30 hashed local files and 23 resolved bundled runtime components. The resolved bundle license inventory/notices are retained separately as build evidence; canonical source notices keep the direct-baseline format required by the repository's source-notice tests. A post-build notice test initially failed because bundling had rewritten these source files; regenerating the canonical notices using the existing script restores that invariant without changing the tests. Both notice suites then pass. No dependency declarations or versions changed; the complete lock graph is identical to dev17 apart from project root-version metadata. The preserved local dependency tree has the same pinned graph. No package was fetched.

The initial aggregate invocation produced an incomplete log despite an exit-0 process result and is not used as proof of full Foundation coverage. The final rerun has all mandatory terminal markers and explicit `FOUNDATION_EXIT=0`; its complete log is retained in checkpoint test artifacts.

Final gate results and exact commands are also recorded in the accompanying checkpoint audit/test-results artifacts. Parrot OS and final real Chromium/Firefox acceptance remain PENDING / NOT RUN. This is not a VERIFIED PRODUCT RELEASE. The next authoritative Phase E deliverable is MTU/PMTUD (section 32; related coverage in section 10.10); it is not started here.
