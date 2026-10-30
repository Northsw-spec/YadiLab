# CONVERGENCE — OSPFv2 Type 1/2 LSA header comparison and request-intent plan

## Source authority and scope

- GitHub protected `main` at start: `e80e23937ad47af5a1d72b73465b845f1505bbda`, tree `ec4bdae7c1574f350eea22dc4a79f8eb1c8d9125` (2026-10-30).
- Based on [RFC 2328 §10.6](https://www.rfc-editor.org/rfc/rfc2328.html#section-10.6), [§10.9](https://www.rfc-editor.org/rfc/rfc2328.html#section-10.9), [§12.1](https://www.rfc-editor.org/rfc/rfc2328.html#section-12.1), [§13.1](https://www.rfc-editor.org/rfc/rfc2328.html#section-13.1), Appendix B (MaxAge=3600 s, MaxAgeDiff=900 s).
- This checkpoint deliberately implements a **read-only metadata sidecar**. The existing DD Exchange sidecar still rejects nonempty DD LSA headers; this module **does not change that behavior** and is **not integrated with a wire-admitted DD packet parser**.
- The caller provides synthetic remote summary *header snapshots that are assumed externally admitted*. They are not proof that any peer exists, packet was received, checksum verified against body, router is connected, or LSDB synchronized.

## Contract

1. Model only canonical Type 1 (router-LSA) and Type 2 (network-LSA) headers, one area belonging to the exact Engine-bound exchange session. Type 3–5 are explicitly rejected as outside the first-slice scope, not silently ignored.
2. LSA identity is `(LS type, Link State ID, Advertising Router)`. Compare *instances of the same identity* with §13.1 precedence: higher signed LS sequence, larger nonzero unsigned checksum, MaxAge (if only one is 3600), younger age if difference **strictly greater than 900 seconds**, otherwise equal. The reserved sequence `0x80000000` is refused. Header length/options/IP addresses/Type 1 Router ID consistency are validated.
3. Normalized local header snapshot is immutable by construction (copied canonical metadata and sorted LSA keys). Remote batch input is also copied/sorted. Duplicate LSA keys within a batch or across batches fail closed rather than reconciling or inventing flooding semantics.
4. If the local header is **missing**, or the advertised remote instance is strictly newer than the local header, the sidecar records a deterministic `Link State Request intent` for *only the LSA identity*. Local newer or RFC-equivalent instances do not generate requests.
5. Request intents contain only LSA type, Link State ID, Advertising Router and reason (`MISSING_LOCAL` or `REMOTE_NEWER`). They are **not** protocol packets, LSA bodies, installed LSAs, acknowledgements, or completed database exchange.
6. The plan binds to an exact valid Exchange snapshot: scenario ID/hash, Engine revision, area, resource IDs, master/slave role, current DD sequence, accepted DD count, and virtual timestamp. Any changed/stale Engine/Exchange snapshot refuses future batches; a newly validated plan must be created.
7. Every plan read recalculates the request-intent ledger from validated local and remote arrays to reject forged or inconsistent plans. Maximum: 256 local headers, 256 remote headers, 32 headers per batch, 16 batches. Repeat batch IDs, invalid identifiers, malformed IP, checksum zero, noncanonical headers, unsupported types, overflow and over-budget batches fail atomically with original unchanged plan.
8. No EngineState writes, simulation-time advancement, actual Link State Request sending, LSDB changes, LSA flooding, SPF, route installation, `ExchangeDone`, `LOADING`, or `FULL` are performed.

## Test and verification criteria

- Source: `engine/src/ospf-lsdb-summary.ts`; public Engine exports in `engine/src/index.ts`.
- Tests: `tests/engine/run_ospf_lsdb_summary_tests.mjs`; command `npm run test:ospf-lsdb-summary` required unconditionally in `yadilab-required-ci` and in the independent post-merge release.
- Positive and adversarial tests: exact 900/901-second boundary, signed sequence ordering, checksum precedence, MaxAge dominance, canonical identity, Type 1/2-only limits, missing/older/newer/equal local headers, stable sorted deduped requests, forged ledger, stale Engine and Exchange binding, header/batch/total ceilings, unchanged reachability and 1000 deterministic end-to-end JSON-identical replays.
- Only mark `CI_PASS` after actual GitHub Actions logs show successful execution for the exact PR check SHA and separate post-merge release SHA. Actual network device, Parrot-native execution, and any eventual FULL adjacency are **NOT_RUN**.

## Next separate checkpoints

- Source-verified integration of nonempty DD summaries with actual bounded DD page admission and sequence/Options checks.
- LSA body validation and Fletcher checksum verification; LSDB update rules, LS Ack/flooding and request retransmission.
- Only after correctly modeled ExchangeDone and all requests satisfied: explicitly test transitions toward Loading/Full. Preserve routing truth unless dedicated SPF and route mutation oracles prove it.
