# Release notes v0.3.0 — Deterministic Engine Phase 3

This release continues directly from Foundation v0.2.0. No repository reset or schema/compiler rewrite was performed.

## Preserved from v0.2.0

- Phase 0 repository/rebranding foundation.
- Phase 1 authoritative Draft 2020-12 contracts and generated TypeScript types.
- Phase 2 deterministic compiler, exact capability/profile locks, semantic validation, canonical source SHA-256, and adversarial compiler tests.
- Layout remains presentation state outside canonical semantic scenario state.

## Added in v0.3.0

- Immutable runtime resource state.
- Safe schema-operation reducer (`set` / `remove`) with atomic batch application.
- Prototype-path hardening.
- TRUE/FALSE/UNKNOWN logic with deterministic composite semantics.
- NetworkEngine v1 with topology paths, firewall policy decisions, service/listener evidence, alternate path handling, and explainable blocking evidence.
- IdentityEngine v1 with memberships, effective permissions, authentication policy, and MFA decisions.
- RuleEngine v1 for all currently schema-defined rule operators.
- TestEngine v1 Foundation evaluators.
- Finding, objective, completion, and evidence evaluation pipeline.
- Engine strict TypeScript build.
- Engine functional and adversarial regression suites.

## Regression result

The complete v0.2.0 schema/compiler verification suite continues to pass together with the new Engine suites.

## Next phase

Phase 4: canonical-solution replay/regression framework.

The next phase must automatically prove:

```text
initial intended faults = expected
canonical operations = apply successfully
solved expectations = expected
required objectives = TRUE
completion = TRUE
```

Phase 4 must fail closed when a scenario cannot be proven solvable under the deterministic Engine.
