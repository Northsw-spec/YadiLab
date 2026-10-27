# Phase 65 — Fault Injection Engine Core

Phase 65 implements the deterministic, AI-free fault-injection foundation required by Masterprompt v1.3.

## Core invariants

- Healthy scenario / imported enterprise baseline remains reusable and immutable.
- Fault behavior is declared in versioned, content-addressed Fault Packs.
- Runtime injections and persistent scenario variants are distinct overlay modes.
- A fault definition uses named bindings rather than hard-coded resource IDs.
- Preconditions must be TRUE before mutation.
- Mutations are transactional and resolve to ordinary Engine `set` / `remove` operations.
- Seeded `choice` values are deterministic for the same seed + fault + mutation identity.
- Expected effects and negative controls are verified against actual Engine state after mutation.
- Blast radius is measured from real before/after resource state.
- Exact inverse operations are captured and test-replayed before a fault is accepted as reversible.
- Unsafe inverse rollback is refused after later Runtime state changes; Runtime history/checkpoints remain the safe recovery path.
- Persistent variants are ordinary scenario-source documents with materialized fault state and `faultOrigin` provenance.
- The compiler preserves `faultOrigin` into the normalized scenario.

## Fault Pack 0.1 contract

A pack binds `packId`, exact semantic version, domain, canonical SHA-256 identity and reusable fault definitions. Faults declare:

- target bindings and accepted resource types,
- preconditions,
- incompatibilities,
- mutations,
- expected effects,
- negative controls,
- observable symptoms and hidden truth,
- restore-pre-injection recovery mode,
- blast-radius bounds,
- visibility policy,
- explicit difficulty dimensions,
- tags and learning objectives.

Phase 65 supports literal and seeded-choice `set` mutations plus `remove` mutations. More domain-specific value generators can be added later without changing the overlay model.

## Fault Overlay 0.1 contract

An overlay binds exact scenario revision and contains ordered fault instances. Each instance binds:

- exact fault-pack version and pack identity,
- exact fault/version,
- uint32 seed,
- resolved target bindings,
- resolved operations,
- captured inverse operations,
- before/after state revisions,
- verified effects/negative-controls,
- changed-resource blast radius,
- per-application SHA-256.

The entire overlay also has a canonical SHA-256 identity. Semantic verification checks overlay identity, instance hashes, pack-lock consistency, revision arithmetic/order and canonical changed-resource ordering.

## Built-in starter pack

`fault-packs/builtin/network-core.json` currently provides conservative generic examples:

- `routing.remove_default_gateway`
- `firewall.force_default_deny`

These are deliberately small. Phase 65 is the engine contract; broader Windows/Linux/routing/VLAN/DNS/DHCP/NAT/service/security Fault Packs belong to later expansion phases.

## Persistent variant materialization

A `SCENARIO_VARIANT` overlay can be materialized into a new scenario-source without mutating the healthy source. The variant stores `faultOrigin` and uses captured inverse operations as the author-side canonical recovery sequence.

## Not claimed in Phase 65

- full Fault Injection UI/panel,
- deterministic multi-fault generator UI,
- temporal/intermittent schedule execution,
- broad domain Fault Pack library,
- Diagnostic/Observation Engine,
- dependency-resolved live React execution,
- Parrot OS acceptance.
