# Phase 66 — Fault Injection UI

Phase 66 adds the first user-facing Fault Injection surface over the deterministic Phase 65 Fault Engine Core.

## Core rule

The UI does not reimplement fault semantics. It calls the same Fault Engine functions used by headless tests. Pack integrity, target validation, preconditions, deterministic mutation resolution, expected effects, negative controls, blast radius and rollback safety remain core-engine responsibilities.

## Runtime workflow

Runtime mode supports:

1. choose a fault definition,
2. choose every declared target binding,
3. choose an unsigned 32-bit seed,
4. preview the exact fault request,
5. inspect actual changed resources and resolved operations,
6. inject only the exact request that was previewed,
7. append compatible faults to the same overlay,
8. rollback the latest fault when Runtime state has not advanced,
9. otherwise fall back to Runtime history/checkpoints.

Every successful injection is recorded as one Runtime history step even when the underlying fault contains several Engine operations.

## Mandatory preview token

Preview computes a SHA-256 token over:

- scenario ID/hash,
- current state revision,
- exact pack ID/version/identity,
- fault ID,
- canonical target bindings,
- seed,
- overlay mode,
- active overlay identity.

Injection recomputes that token and fails closed if anything changed after preview. This prevents a UI preview from authorizing a different request.

## Builder variant draft

Builder mode never mutates the healthy scenario while faults are being prepared. Instead, it creates an isolated draft Engine state from the current compiled scenario. Multiple faults may be added to the draft overlay. Only the explicit **Create faulted scenario variant** action materializes a new ordinary scenario-source document with `faultOrigin` and the Phase 65 canonical recovery sequence.

If the Builder source revision or compiled scenario hash changes, the draft is stale and must be recreated.

## Difficulty presentation

Fault definitions already contain four explicit dimensions:

- layers,
- dependency depth,
- evidence visibility,
- remediation constraints.

The UI shows these dimensions directly. Phase 66 deliberately does not collapse them into a hidden or arbitrary scalar score.

## Divergence handling

An active Runtime overlay is bound to exact Engine revisions. If the analyst uses ordinary Runtime operations, Undo/Redo, Reset or checkpoint restore after injection, direct fault rollback/additional injection may no longer be safe. The UI surfaces that divergence and the engine fails closed. The existing Runtime history/checkpoint mechanism remains the recovery path.

## Not claimed in Phase 66

- temporal/intermittent fault scheduling,
- deterministic random multi-fault scenario generator,
- large Windows/Linux/routing/VLAN/DNS/DHCP/NAT/service/security Fault Pack library,
- Diagnostic/Observation Engine,
- live dependency-resolved React execution,
- Parrot OS acceptance.
