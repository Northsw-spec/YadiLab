# CONVERGENCE Dev.1 — protocol-neutral deterministic event plan

**Classification:** Engine scheduler foundation, not OSPF or dynamic routing implementation. The source of truth is current GitHub main plus the tested PR commit; this design note is not a separate code authority.

## Verified pre-existing contracts (2026-10-30)

- engine/src/state.ts defines EngineState as scenarioId, scenarioHash, stateRevision, resources. createInitialEngineState returns stateRevision=0; applyOperation increments revision on a successful resource-state mutation; applyOperations is atomic.
- engine/src/save-state.ts currently emits clock: { mode: "virtual", tick: state.stateRevision }. That is a revision counter, **not real modeled elapsed time**. Do not reinterpret existing saves or their tick as milliseconds.
- engine/src/regression.ts replays canonical operations and evaluates their outcomes; it has no event scheduler or OSPF protocol.
- Existing reachability uses declared topology and resource properties. Never turn imported evidence, timer scheduling, or a future event by itself into TRUE/FALSE network truth.

## New boundary

- A simulation event plan binds to scenarioId + sourceHash + exact base stateRevision. A changed Engine revision or source invalidates the plan, rather than silently rebinding it.
- Virtual time is an integer millisecond counter starting at zero, with no wall-clock, randomness, callbacks, or network dependency. Equal-due-time events dispatch by stable insertion sequence.
- Scheduling, canceling, advancing, and plan inspection are pure operations. No Engine-state modification, auto-apply, protocol packet, route change, OSPF neighbor state, UI animation, or claimed connectivity occurs.
- Event IDs are unique; kinds follow a narrow uppercase token format. Optional resource targets must be present in the current Engine snapshot. Negative/overflow/unsafe/noninteger time and hostile or stale plans fail closed.
- Maximum pending queue is 4096 events. All plan reads revalidate format, source, revision, counter, order, IDs and bounds, including restored or untrusted event plans.
- No EventPlan format is yet added to scenario JSON, SaveState, or package export. A later design must explicitly version schema and define revision-transitions, persistence, cancellation ownership, event handlers, protocol domains and target compatibility before integration.

## Acceptance / separate limitations

- npm run test:simulation-clock compiles current Engine and runs fixture-based positive/negative tests plus 1000 byte-identical replay outcomes. The check is part of yadilab-required-ci before browser and release checks.
- Existing Engine, import/probe, release identity and mounted Chromium tests must remain green on the exact PR head. Post-merge Linux build is independent evidence for the new main commit.
- Success of this checkpoint proves a bounded *inert deterministic queue*, **not** working OSPF, simulated network time progression or reconvergence. Do not conflate schedule outputs with network observations.
- Future Dev.1 integration requires explicit, tested state-transition ownership and replay across revisions; Dev.2+ may add OSPF P2P, broadcast/DR-BDR, SPF and UI later, with independent adversarial gates.
