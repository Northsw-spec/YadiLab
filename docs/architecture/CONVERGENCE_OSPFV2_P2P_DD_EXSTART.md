# CONVERGENCE OSPFv2 P2P DD ExStart — deterministic negotiation-only sidecar

## Authority and scope

- Authority: current GitHub `main` at checkpoint start, commit `70d5585c00f24494a4b6f30948ad0f1f5ce7a854`, after AUDIT-007.
- Primary protocol standard: [RFC 2328 §§10.1, 10.3, 10.6, 10.8, A.3.3](https://www.rfc-editor.org/rfc/rfc2328.html).
- This is a **synthetic, already-admitted** Database Description (DD) observation model. It does **not** parse or authenticate actual OSPF packets, validate physical links, send or retransmit DD packets, negotiate a complete database, inspect LSAs, establish Full adjacency, or install/withdraw routes.
- New sidecar `engine/src/ospf-p2p-dd.ts` composes the existing `ospf-p2p-hello.ts` without changing the old model. The pre-existing Hello/Dead logic remains the clock and neighbor-inactivity authority.

## State machine / correctness

- `IDLE`: Hello model is DOWN or INIT; no negotiated DD receipt. One-way discovery never establishes adjacency.
- `EXSTART`: synthetic two-way Hello observed on P2P and one `DD_INITIAL_TX_INTENT` emitted. This indicates only a modeled local desire to send an empty DD with I/M/MS bits set. No network data was transmitted.
- `EXCHANGE`: a synthetic **matching ExStart negotiation DD** was admitted, yielding master/slave and agreed sequence (`NegotiationDone`). This state does **not** claim that any database summaries have been exchanged or LSDB synchronized. Every later DD payload is rejected as `OSPF_DD_EXCHANGE_UNMODELED` until a future checkpoint explicitly implements Exchange processing.
- Numeric Router IDs determine role under RFC 2328: if remote RID is higher, remote I=1/M=1/MS=1 empty DD is accepted and local becomes SLAVE with remote sequence; if remote RID is lower, received I=0/MS=0 with exactly the local proposed DD sequence and empty headers is accepted and local becomes MASTER. Other patterns do not promote.
- RFC interface-MTU rejection: the received DD MTU must not exceed the configured local receive interface MTU; this model also constrains both to [68, 65535] in its bounded interface. Options byte is stored with the receipt; exchanging/changing OSPF optional capabilities is *not* modeled.
- DD sequence is an explicit deterministic positive unsigned 32-bit initial value (no random or wall-clock source). This is a synthetic trace and is not a claim that an RFC-recommended uniquely generated wire sequence was produced.
- A one-way Hello or Dead expiry clears negotiation. A new two-way Hello after expiry starts a fresh attempt, even if expiry and recovery happen inside the same operation. All external timestamps process existing due timers first (exact Dead deadline wins).
- Result operations and inspect functions validate parent source hash/revision, schema, timer ownership, local MTU/sequence bounds, DD flags, role/sequence receipt consistency and expected Router IDs. Malformed, stale and unsupported input fails with the **identical original session**, no partial Engine or scheduler mutation.
- The sidecar never updates EngineState, its `stateRevision`, reachability, routing table or UI network truth. Both OSPF models remain abstract training-sidecar models, not a fully simulated connected topology.

## Code and tests

- Engine module: `engine/src/ospf-p2p-dd.ts`; exported by `engine/src/index.ts`.
- Adversarial test suite: `tests/engine/run_ospf_p2p_dd_tests.mjs`, invoked by `npm run test:ospf-p2p-dd`.
- Mandatory PR gate: `yadilab-required-ci` now runs DD tests after Hello/Dead and before the release build. Independent `release-identity.yml` also runs the DD tests on `main`.
- Oracles include wrong peer/area, MTU overflow, non-boolean I/M/MS, invalid/overflow sequence, out-of-order time, nonempty LSA headers, wrong master-slave flag ordering, forged receipts, exact Dead expiry, post-expiry recovery, one-way reset, stale Engine source, unchanged reachability and 1000 identical end-to-end traces.
- Declare **CI_PASS** only after actual GitHub Actions SUCCESS at the exact PR head and independent release SUCCESS on post-merge main. No manual Parrot test is required for these pure Engine and Linux CI gates.

## Deliberately deferred next gates

1. Full RFC DD Exchange processing, options negotiation, duplicate handling, M-bit transitions, RxmtInterval and bounded retransmission.
2. Link-State Request/Update/Acknowledgment, LSDB and sequence/age/checksum ordering.
3. Type-1 and Type-2 LSAs, SPF routing, route installation/withdrawal and unambiguous route truth.
4. Broadcast DR/BDR, ECMP, actual convergence Timeline/X-Ray and negative routing oracles.

Never report `FULL`, converged routing, or actual peer authentication on the strength of these DD negotiation tests.
