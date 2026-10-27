# Phase 69 — Deterministic Multi-Fault / Scenario Generator

YadiLab Foundation v0.69.0 adds a deterministic Builder-side scenario generator over the verified Phase 65–68 Fault Engine and exact-versioned built-in Fault Packs.

## Generator contract

The generator is locked as:

- generator ID: `foundation.multi_fault`
- generator version: `0.1.0`
- persisted author-side artifact: `infrastructure-cyber-lab.fault-generation-plan@0.1.0`

Generation binds the exact normalized scenario hash, explicit uint32 seed, exact Fault Pack IDs/versions/content identities and normalized constraints. The same normalized inputs + seed + pack versions must reproduce the same plan and overlay.

The plan is content-addressed with `planIdentity` and records:

- requested fault count and normalized constraints;
- exact pack locks;
- selected fault IDs/versions;
- resolved target bindings;
- per-fault derived seeds;
- changed resources;
- expected learner-visible symptoms;
- hidden instructor truth;
- learning objectives and the four explicit difficulty dimensions;
- Engine revisions before/after each fault;
- whether that fault's preconditions already held on the healthy baseline;
- final overlay identity;
- combined changed-resource set;
- reference investigation order;
- exact reverse recovery order;
- resolved canonical recovery operations;
- verified final-state revision and solvability marker.

A generated persistent scenario variant also stores `faultOrigin.generation` with the exact generator ID, generator version, generation seed and plan identity. Manual fault variants remain valid and do not require generator metadata.

## Compatibility and search

Generation is not a blind random sampler.

For each step YadiLab enumerates deterministic eligible binding assignments, then validates each candidate through the real Fault Engine. A candidate is rejected when any of the following applies:

- Fault Pack identity/semantic verification fails;
- binding/resource type is invalid;
- declared preconditions do not hold;
- declared incompatibility applies in either direction among selected faults;
- active target/path or parent/child mutation overlap would occur;
- the new fault's own expected effects or negative controls fail;
- the new state causes any previously selected fault's expected effects or negative controls to stop being true;
- aggregate changed-resource constraints are exceeded;
- exact reverse recovery no longer restores baseline state.

Candidate order is seed-derived and deterministic. Phase 69 uses bounded deterministic backtracking rather than a greedy first-hit algorithm: if the first seeded path reaches a dead end, the generator tries the next deterministic candidate. It fails closed when no compatible requested combination exists or when bounded search limits are exceeded.

## Constraints

The core generator supports explicit constraints for:

- fault count;
- distinct fault definitions (default: required);
- allowed domains;
- allowed target resource types;
- allowed fault IDs;
- excluded fault IDs;
- maximum total changed resources;
- min/max bounds for the existing explicit difficulty dimensions:
  - layers;
  - dependency depth;
  - evidence visibility;
  - remediation constraints.

There is still no scalar or AI-generated difficulty score.

## Builder UI

Builder Fault Injection now contains a **Deterministic scenario generator** section.

The author chooses:

- one or more exact built-in Fault Packs;
- fault count;
- uint32 generator seed.

**Preview generated variant** is mandatory. Preview is isolated from healthy source and displays the exact selected faults, pack locks, fault seeds/bindings, plan/overlay identities, changed resources and combined learner-visible symptoms. Instructor ground truth is inside an author-only details surface.

**Create generated scenario variant** is allowed only from the still-current verified preview token. Scenario/source revision drift, plan tampering or preview-token drift fails closed.

## Investigation-order boundary

Phase 69 records a transparent `referenceInvestigationOrder`, but does not pretend that command-level diagnostic causality exists before the Diagnostic / Observation Engine.

Each step is marked either:

- `INDEPENDENT_STABLE_ORDER` when its preconditions already held on the healthy baseline; or
- `PRECONDITION_DEPENDENCY` when its preconditions only became true after prior generated changes.

This is deterministic ground-truth metadata for authors, not a fabricated `ipconfig`, `route print`, `journalctl`, PowerShell or shell transcript.

## Solvability and recovery

Every successful generated plan has already passed:

1. every individual Fault Engine precondition/mutation/effect/negative-control/blast-radius/reversibility gate;
2. intermediate preservation of all previously selected fault effects/negative controls;
3. final preservation of every selected fault effect/control;
4. exact combined reverse recovery to the original baseline resource state;
5. plan/overlay/scenario identity binding.

The materialized scenario variant uses the same verified combined reverse recovery as its ordinary `canonicalSolution`.

## Non-goals

v0.69.0 does not introduce:

- temporal/intermittent scheduling;
- link/service flapping;
- deterministic packet loss/latency schedules;
- a command-level Diagnostic / Observation Engine;
- real Windows/Linux guest command execution;
- AI/ML/LLM runtime decisions;
- probabilistic Runtime truth;
- opaque difficulty scoring.

Temporal/chained scheduling and command-level diagnostic observations remain later phases.
