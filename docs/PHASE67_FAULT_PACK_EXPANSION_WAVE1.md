# Phase 67 — Fault Pack Expansion, Wave 1

YadiLab Foundation v0.67.0 expands the verified Phase 65/66 fault system from two built-in examples into the first broad deterministic network troubleshooting fault pack. The Fault Engine and Fault Injection UI contracts remain unchanged: Phase 67 is content expansion plus permanent regression coverage, not a parallel fault runtime.

## Scope

The built-in `foundation.network.core` pack is upgraded from `0.1.0` to `0.2.0` and now contains 25 faults, exactly five in each Wave-1 domain family:

### Routing

- `routing.remove_default_gateway`
- `routing.set_wrong_default_gateway`
- `routing.blackhole_primary_route`
- `routing.set_wrong_next_hop`
- `routing.disable_primary_route`

### VLAN / L2

- `vlan.replace_membership`
- `vlan.set_wrong_access_vlan`
- `l2.disable_switch_port`
- `l2.force_stp_blocking`
- `l2.restrict_trunk_vlans`

### DNS

- `dns.replace_resolvers`
- `dns.remove_all_resolvers`
- `dns.set_wrong_search_domain`
- `dns.disable_server`
- `dns.corrupt_primary_record`

### DHCP

- `dhcp.disable_client`
- `dhcp.set_wrong_gateway`
- `dhcp.set_wrong_dns`
- `dhcp.set_wrong_prefix`
- `dhcp.exhaust_server_pool`

### Firewall / NAT

- `firewall.force_default_deny`
- `firewall.default_action_deny`
- `firewall.disable_primary_rule`
- `nat.disable_primary_dnat`
- `nat.wrong_translated_port`

## Deterministic fault contract

Every built-in fault is content-addressed and keeps the same Phase 65 contract:

- explicit target bindings;
- explicit resource-type and state preconditions;
- deterministic literal or seed-selected mutations;
- explicit expected effects and negative controls;
- declared blast radius;
- observable symptoms separated from hidden truth;
- canonical restore-pre-injection recovery;
- declarative incompatibility relationships where same-layer faults must not be combined;
- the four transparent difficulty dimensions only: layers, dependency depth, evidence visibility and remediation constraints.

No scalar or inferred difficulty score is introduced.

The pack identity for `foundation.network.core@0.2.0` is:

`a67a18975d78db22f9fed76c4edd0ca0902d2b46e0302025d2f1ffeaf394362a`

## Network semantics and state semantics

Where the current Network Engine already has authoritative semantics, faults mutate fields that are directly consumed by that engine:

- routing faults exercise route action, enabled state and next-hop selection;
- VLAN/L2 faults exercise VLAN membership and switch-port state represented in the scenario model;
- firewall faults exercise default policy and rule enablement;
- NAT faults exercise DNAT enablement and translated listener ports.

DNS and DHCP are intentionally modeled as explicit deterministic resource state in this wave. Phase 67 does not pretend that the current reachability engine resolves DNS or runs a DHCP lease protocol. Their faults therefore rely on exact preconditions/effects/recovery and observable state rather than fabricated packet-engine semantics. Later OS-specific packs may bind these same fault concepts to Windows/Linux observability and commands without changing the core fault contract.

## Fault versus diagnosis

A fault definition is not a diagnosis oracle. Phase 67 deliberately separates:

1. injected ground truth;
2. resulting state/effect;
3. what evidence is visible to the learner;
4. canonical recovery.

For example, a DNS fault can produce an application-level name-resolution symptom while routing remains intact. The learner must still establish which layer is broken from available evidence; the UI does not expose an arbitrary diagnosis score.

## Safety and compatibility

The two pre-existing built-in faults remain available under the same IDs. Phase 67 does not change healthy scenario source, preview-token binding, Runtime overlay semantics, Builder draft isolation, rollback rules, persistent variant materialization or `faultOrigin` behavior.

Same-layer faults that would create ambiguous or self-overwriting state are explicitly incompatible. No-op candidate resolution remains fail-closed. Rollback must restore exact pre-injection resource bytes/state through the Phase 65 inverse-operation mechanism.

## Permanent verification

Phase 67 adds two permanent suites:

- `tests/fault-engine/run_fault_pack_wave1_tests.mjs`
- `tests/fault-engine/run_fault_pack_wave1_adversarial.mjs`

The functional suite verifies pack identity, exact domain counts, required fault metadata, injection/effect/control behavior, exact rollback and direct Network Engine semantic changes for representative routing, VLAN, firewall and DNAT faults.

The adversarial suite verifies wrong-resource rejection, missing preconditions, no-op blocking and declared incompatibility enforcement.

The actual built-in pack is also validated against the Fault Pack JSON Schema by `tests/run_schema_checks.py`, not merely through fixture-only schema tests. The browser Fault Injection UI regression requires all 25 built-in faults to appear in the catalog.

Phase 67 also makes the existing offline snapshot transport regression more robust in constrained CI by generating its adversarial ZIP mutation set in a single Python interpreter invocation. The same 44 transport assertions and exact fail-closed mutations remain; only repetitive interpreter startup is removed.

## Explicit non-goals for Wave 1

Phase 67 does not yet add:

- Windows-specific fault packs;
- Linux-specific fault packs;
- a deterministic multi-fault/scenario generator;
- temporal/intermittent fault scheduling;
- probabilistic faults;
- AI/ML/LLM-based fault selection or diagnosis;
- hidden scalar difficulty scoring.

Those remain later phases.
