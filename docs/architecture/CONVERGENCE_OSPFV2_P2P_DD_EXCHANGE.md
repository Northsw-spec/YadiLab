# CONVERGENCE — OSPFv2 P2P DD Exchange (bounded sequence and retry sidecar)

## Authority, version, scope

- Base source: protected GitHub `main` at `1007a2e0f0be3468d843c177c1962c9c6e37d77d`, tree `d71a73c47aa9aef6e129f374105f9228899bd9d2` (2026-10-30).
- Standards reference: [RFC 2328, §10.3 (SeqNumberMismatch), §10.6 (DD reception), §10.8 (DD sending)](https://www.rfc-editor.org/rfc/rfc2328.html).
- New versioned pure sidecar `engine/src/ospf-p2p-exchange.ts` composes, but does not replace, the existing `ospf-p2p-hello.ts` and `ospf-p2p-dd.ts`. Those files retain their previous API and tests.
- Synthetic input is **already associated and admitted** externally. There is no packet decoder, cryptographic authentication, physical adjacency evidence, actual transmission, database summary list or LSDB, LSA parsing, ExchangeDone, Loading, Full, SPF, or route insertion. Every emitted `*_TX_INTENT` is **only a software intent**; this is not an actual sent DD packet.
- `dd.phase === "EXCHANGE"` still means only master/slave NegotiationDone. Exchange packets cannot prove a completed database exchange and never promote to `FULL`.

## Modeled RFC decisions

1. Initial negotiated ExStart DD receipt fixes the deterministic master/slave role, options byte, and agreed DD sequence. Locally higher Router ID = master, lower = slave; the parent DD model is the source of that decision. On entry to Exchange, master emits an abstract new empty-DD transmit intent with sequence one greater than the agreed sequence; slave replies with the agreed sequence.
2. Consecutive DD observations are duplicates if `I/M/MS/options/DD sequence` are identical (§10.6). The master ignores a duplicate. The slave emits an intent to resend its previous DD response. Neither case increments the accepted packet counter or the sequence.
3. Otherwise, received `I` must be false, MS must be consistent with remote peer role, and Options must match negotiation. Master expects a response echoing its outstanding DD sequence; slave expects the next sequence (previous+1). Violations produce a traceable `SeqNumberMismatch` model event, tear down Exchange to ExStart, clear the outstanding intent/ledger and increment the locally proposed initial sequence, as in §10.3. The module does not silently accept invalid ordering.
4. Only a correctly ordered, **empty** DD creates an abstract next-response intent. Every nonempty LSA-header list is rejected as `OSPF_EXCHANGE_LSA_HEADERS_UNMODELED`. No actual LSA summary or requests are ever implied. `M=0` alone never produces ExchangeDone.
5. Master has one outstanding abstract sequence and retries the same sequence at `RxmtInterval` until an acknowledgement arrives. A new correct acknowledgement increments the sequence and resets the retry deadline. Slave has **no retransmission clock**: it responds only to new or duplicate master DD observations. These are virtual-time trace intents, not network frames.
6. The parent Hello/Dead clock is authoritative. An inactivity deadline takes precedence over a simultaneous retry or a newly observed DD. A one-way Hello, Dead expiry, or new negotiation clears any old Exchange ledger. Rejected malformed/foreign/too-large-MTU and unsupported packet data leave the original session unchanged; valid protocol mismatches intentionally perform the RFC reset.
7. Source ID/hash/revision, timer ownership, format/version and ledger invariants are checked before each call. On over-budget advance or timestamp/sequence overflow, the entire operation is rejected and the original session is returned. Limits: 128 new empty DD observations, 128 master retries per session, 64 retries per `advance`, `RxmtInterval` 1–60 seconds (integer whole seconds). Time is virtual integer milliseconds; no wall-clock or randomness.
8. The Engine state, resource properties and reachability truth are never modified. Protocol receipt/trace data is **model provenance only**, not cryptographic evidence of connected routers.

## Source and mandatory verification

- `engine/src/ospf-p2p-exchange.ts`, exported through `engine/src/index.ts`.
- `tests/engine/run_ospf_p2p_exchange_tests.mjs`, `npm run test:ospf-p2p-exchange`.
- Test oracles: both roles; master acknowledgement/next sequence; slave next-sequence response; exact retry deadlines; duplicate handling; options/MS/I/sequence mismatch; stale state/forged ledger; MTU/header/noninteger rejection; Dead/one-way recovery; bounds; unchanged Engine state/reachability; 1000 byte-identical end-to-end replays.
- Required pre-merge `yadilab-required-ci` and independent post-merge `linux-attested` include the new regression command. Existing full Engine, real Chromium, Linux launcher, importer and dependency checks must remain green.
- `PASS` is established only from actual GitHub Actions logs on the exact PR check run and post-merge SHA. Ubuntu CI is not native Parrot testing.

## Deferred

Real DD database summary pagination, Link State Requests/Updates/Acks, LSA freshness and LSDB exchange, ExchangeDone transition to Loading/Full, live routing, OSPF area topology, broadcast DR/BDR, ECMP, and convergence UI. Do not infer any of these from successful tests of this bounded model.
