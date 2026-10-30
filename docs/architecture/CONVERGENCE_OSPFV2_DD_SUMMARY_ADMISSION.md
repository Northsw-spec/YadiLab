# CONVERGENCE — synthetic DD summary admission bound to Exchange

## Canonical starting point
- GitHub protected `main` at start: `5aeb1a928b975784a55eebe2abf0973c9492a6ee`, tree `9fb6e1f03d64ae700bd5465b5a89138b7309c575`.
- RFC 2328 §10.6: an accepted *next-in-sequence* DD packet's LSA headers populate the neighbor Link State Request list only after LSA recency comparison (§13.1). A duplicate is processed as a duplicate and does not introduce a new database-summary page.
- Exact bound: already-admitted **synthetic** DD metadata, Type 1/2 LSA headers and deterministic request *intents*, **not** OSPF wire parsing, authenticated packet acceptance, actual Link State Request transmission, LSDB updates, SPF, route installation or FULL.

## Architecture
The new `engine/src/ospf-dd-summary-admission.ts` owns a single versioned `OspfDdSummarySession` containing the unchanged `OspfP2pExchangeSession`, immutable canonical local LSA header snapshot, previously accepted remote DD summary pages, and an exactly rebound `OspfLsdbSummaryPlan`.

- Prior to calling the existing `receiveOspfP2pExchangeDescription`, validate a bounded matching `lsaHeaderCount` and actual supplied header array. In ExStart **only empty** DD summary headers are admissible. Types outside 1/2 are deliberately unsupported.
- Internally project only **sequencing metadata** with `lsaHeaderCount=0` to the pre-existing Exchange sidecar (whose contract continues to reject nonempty DD). This is a **projection for a sequencing oracle**, not a claim that the old API admitted an actual packet, verified the headers, or handled a wire DD frame. The new adapter owns and checks the original, unchanged full header batch and does not export the projection as wire evidence.
- **Only** on a genuinely accepted new Exchange DD with accepted-counter increment of exactly one: add the original DD packet's bounded metadata and its LSA headers to the page ledger. Reconstruct the canonical LSDB comparison against all prior pages at the new exact Engine/Exchange snapshot. If duplicate, require the header payload to match the previous accepted page; preserve the request ledger and return existing master's ignore / slave's repeat-response intents.
- A modeled `SeqNumberMismatch`, loss of 2-way Hello, or inactivity expiry destroys every previous remote DD page and request intent. Fresh NegotiationDone begins a new empty comparison; no stale LSA identities return.
- Each page is correlated with the exact DD sequence `initial + page ordinal`, peer Router ID, area, options, I/MS, MTU, virtual timestamp and authoritative last-received packet metadata. Invariant checks rebuild the entire request plan from local and remote header inputs on **every read**, rejecting corrupt/forged ledgers. Any mismatch fails with the **unchanged original** session, not a partial transaction.
- Existing EngineState, revision, resource properties and reachability are immutable throughout. The sidecar emits only synthetic intent/provenance records. No automatic `ExchangeDone`, `LOADING`, `FULL`, outgoing DD pagination or network truth inference.
- Bounds inherit previous model: at most 16 accepted remote summary pages, 32 LSA headers per page, 256 remote LSA headers total, 256 local header entries. Duplicates never consume another slot.

## Verification and source
- New implementation: `engine/src/ospf-dd-summary-admission.ts` and public exports in `engine/src/index.ts`.
- Tests: `tests/engine/run_ospf_dd_summary_admission_tests.mjs`; `npm run test:ospf-dd-summary-admission`.
- Mandatory unfiltered PR gate `yadilab-required-ci` and independent `linux-attested` source regression both run this suite.
- Negative oracles: wrong header count, invalid Type 5, unknown peer/area, high MTU, forged historical sequence, forged request ledger, mismatching duplicate data, stale Engine source, over-budget pages, mismatch reset, one-way Hello and Dead cleanup; master/slave ordering, retransmit-intent isolation, unchanged Engine reachability and 1000 byte-identical end-to-end replays.
- Mark `CI_PASS` only after exact PR-head GH Actions SUCCESS and separate post-merge Linux release SUCCESS, both confirmed from logs and artifacts. Ubuntu CI does not assert native Parrot execution.

## Deferred follow-ups
- Full DD packet decoding, body checksum and authentication; Type 3/4/5 LSA semantics, area/stub options.
- Actual outgoing database summary list and M-bit exchange termination, ExchangeDone and Loading/Full state, Link State Requests/Updates/Acks, Fletcher checksum and LSA freshness, flooding, SPF and dynamic route installation.
- All such capabilities require independent schema/implementation, RFC-grounded adversarial tests and actual Engine network-truth oracles before any simulated success claim.
