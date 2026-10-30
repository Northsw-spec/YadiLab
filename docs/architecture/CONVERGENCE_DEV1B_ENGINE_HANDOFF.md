# CONVERGENCE Dev.1b — deterministic EventPlan-to-Engine handoff

**Source:** canonical GitHub main at checkpoint start; `engine/src/simulation-clock.ts` and `engine/src/state.ts` are unchanged. This checkpoint adds an explicit, bounded transactional adapter and is **not** an OSPF implementation.

## Verified starting behavior

- The Dev.1 scheduler is **inert**, binds to scenario ID/source hash/Engine revision, and sorts pending events by integer virtual milliseconds and insertion sequence.
- Engine applies a `ScenarioOperation` transactionally, increments `stateRevision` once per operation and rolls back a failed batch. The existing SaveState clock tick is the state revision, **not** elapsed simulation milliseconds.

## Dev.1b contract

1. `SimulationTransitionState` has explicit `formatId`, `schemaVersion=1.0.0`, original state revision, scheduler plan, applied event receipts and cancellation tombstones.
2. A single trusted, hardcoded handler kind `ENGINE_SIMULATION_MARKER` writes **only** `properties.__yadilabSimulationEventMarker` on the declared owner resource using existing Engine `applyOperation`. Imported data cannot inject an operation, path, handler or OSPF message.
3. Receipts identify the event ID, deterministic insertion sequence, due time, owning resource, before/after revision, and fixed provenance tag. Each processed event increments the Engine revision by exactly one; the scheduler's `baseStateRevision` follows the authoritative Engine revision atomically.
4. Cancellations require the exact owning resource ID, remove only its pending event, produce a tombstone and never increment Engine revision. Event IDs are reserved after cancellation or dispatch; replay is explicitly refused.
5. On invalid input, malformed/stale plan, foreign scenario, corrupt receipt, occupied reserved field, unknown event handler, backwards time, or actual Engine mutation failure, **return the original state and original plan**. The entire due-event batch is atomic; there is no partial success.
6. The bounded ledger (pending + applied + cancelled) never exceeds 4096 entries per transition session. The reserved Engine marker must match the latest receipt for each resource. There is no wall-clock dependency, network access, random behavior, side effect or external protocol execution.
7. A receipt is **evidence of this software's modeled marker**, not cryptographic authorization, a network packet, a real observation, or an authenticated real device. Future protocol handlers require separate schema, explicit ownership/validation, negative tests and Engine networking oracles.

## Required acceptance

- `npm run test:simulation-transitions` compiles the real Engine and verifies exact revision handoffs, owner-scoped cancellation, source-staleness and plan-tampering rejection, no duplicate dispatch, unchanged pre-existing reachability and **1,000 byte-identical complete transaction replays**.
- The mandatory `yadilab-required-ci` workflow runs these tests before its release and real Chromium acceptance. Other applicable PR workflows must stay green. A protected merge and independent post-merge Linux-release SUCCESS are separate gates.
- This component does **not** implement OSPF, dynamic routes, timers that impact network truth, a persistent simulation scenario schema, or a new public package format. Those require new verified contracts and tests in later work.
