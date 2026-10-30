# CONVERGENCE — bounded OSPFv2 LSR lifecycle and Fletcher-verified LSA byte receipts

## Canonical source and RFC authority

- Baseline: protected GitHub main `e77b27ac3126c1f35d9239fb919425f00a972a10`, tree `9e1b6aed2b31a87ff97da82dc868ee19849c5284`.
- [RFC 2328 §10.9](https://www.rfc-editor.org/rfc/rfc2328.html#section-10.9): one outstanding Link State Request packet; request beginning of list; retransmit outstanding requests at `RxmtInterval`; remove requested entries on qualifying updates. `LoadingDone` requires an already-complete DD exchange and the neighbor in Loading — neither condition is established in this slice.
- [RFC 2328 §12.1.7](https://www.rfc-editor.org/rfc/rfc2328.html#section-12.1.7), Appendix A.4.1: Fletcher-16 over the LSA excluding the first two `LS age` bytes, including the checksum field; expected running sums are zero modulo 255. Checksum=0 is invalid. Signed 32-bit LS sequence and header length/Type 1/2 identity are checked.
- [RFC 2328 §13.1](https://www.rfc-editor.org/rfc/rfc2328.html#section-13.1): requested remote instances may be replaced by newer valid instances. This slice refuses a received instance strictly older than the advertised header that motivated the request.

## Implementation and bounded guarantees

- `engine/src/ospf-lsa-binary.ts`: validates 24–4096 raw LSA bytes (integer octets only), generic 20-byte header, exact internal length, canonical Type 1/2 identity and reserved sequence, nonzero checksum, Fletcher-16 over bytes `2..length-1`; minimal Type 2 body shape. It **copies** accepted bytes and does **not** produce/repair checksums.
- `engine/src/ospf-lsr-lifecycle.ts`: one versioned, immutable-request-view session bound to an exact existing `OspfDdSummarySession` snapshot. Maintains verified raw-byte receipts, one outstanding LSR request *intent*, and virtual `RxmtInterval` retry *intents*. At most 8 identities per request, 8 full LSAs per synthetic response, 64 retries and 64 retry ticks per advance; bounded by the parent DD/LSDB snapshot.
- All Link State Updates are **synthetic and already admitted by the caller**. Sender/area must match the exact peer. Only identities contained in the currently outstanding LSR are accepted. No unsolicited flooding, packet framing, authentication, network transmission, LS Ack, LSDB write, route change, or SPF occurs.
- Each receipt must be a complete raw LSA with a valid Fletcher sum. Its canonical LSA identity must match the requested triple. For that identity, its instance must be at least as recent as the remote DD summary instance according to RFC 2328 §13.1. Partial packets fail atomically; no earlier valid member of a rejected batch is retained.
- Once a requested LSA is verified, its bytes are copied and stored. Every restored/read state revalidates all saved raw LSA checksums, identities, and comparison to the original advertised header. Any missing, forged, duplicated, or stale receipt is refused.
- The remaining requests are computed solely from the frozen, validated DD summary intent list minus verified completions. If some requested entries remain from the current packet, the single outstanding LSR packet tracks only those entries and retries **only** those. A subsequent request packet can be issued only when the first outstanding packet has been fully satisfied.
- Parent Hello/Dead virtual clock is authoritative. On exact deadline, inactivity wins ahead of an LSR retry. On one-way loss or Dead timer, all LSR outstanding intents and stored response receipts are discarded. All invalid input, stale source, retry overflow or excess work returns the identical original immutable session.
- `LSR_REQUEST_LIST_EMPTY` is a **snapshot-scoped request-intent state only**. It is emphatically not a `LoadingDone` neighbor event, `FULL` adjacency, complete DD database sync, updated live LSDB, authenticated real network peer or a new Engine routing fact.

## Regression, proof obligations and limitations

- `tests/engine/run_ospf_lsr_fletcher_tests.mjs`: **independently precomputed fixed raw bytes** for Type 1 and Type 2 LSAs with Fletcher sums; age-only change unchanged; flipped payload/checksum bytes, length mismatches, reserved LS sequence/type, adversarial identity/source, duplicate unsolicited response, older-than-advertised response, mixed valid/invalid batch rollback, retransmissions, partial response, one outstanding request rule, multiple packets, exact Dead timer tie, forged stored receipts, unchanged Engine reachability and 1,000 byte-for-byte identical end-to-end traces.
- `npm run test:ospf-lsr-fletcher` runs in unfiltered `yadilab-required-ci` for PRs and independently in the post-merge `linux-attested` workflow.
- Mark `CI_PASS` only on actual GitHub Actions SUCCESS for the exact checked PR head with runner logs confirming the new suite, then exact merged `main` release SUCCESS with real Chromium and release artifacts. Ubuntu Actions does not prove native Parrot operation.

### Deliberately deferred

Actual LS Update packet decoder and admission/authentication, Type 1/2 link-field semantics, comprehensive OSPF flooding/LS Acks, Link State Request response interleaving and unsolicited updates, a writable LSDB and MinLSArrival/MaxAge aging, DD M-bit exchange completion, explicit Loading/Full transitions, SPF, and dynamic routing. These need their own independent checkpoints and negative routing oracles.
