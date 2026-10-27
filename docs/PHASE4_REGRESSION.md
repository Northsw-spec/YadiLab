# Phase 4 — Canonical Solution Replay and Regression

Version: 0.4.0

This phase extends the existing v0.3.0 deterministic Engine. It does not replace the schema/compiler/Engine work from earlier phases.

## Goal

A scenario with a canonical solution is not Foundation-verified merely because the operations can be applied. The regression framework must prove the complete state transition:

```text
initial scenario
  -> intended initial expectations match
  -> scenario is not already complete
  -> canonical solution applies atomically
  -> solved-state expectations match
  -> required objectives are TRUE
  -> completion is TRUE
```

## Added contract: expectedSolved

Scenario tests now support an optional `expectedSolved` truth value in addition to `expectedInitial`.

Example:

```json
{
  "id": "direct_rdp",
  "type": "network.reachability",
  "params": {
    "from": "attacker",
    "to": "rds01",
    "protocol": "tcp",
    "port": 3389
  },
  "expectedInitial": "TRUE",
  "expectedSolved": "FALSE"
}
```

This lets the compiler/regression pipeline explicitly verify behavior after remediation instead of inferring success only from completion.

## Canonical replay

`replayCanonicalSolution()`:

- creates a fresh immutable initial state;
- rejects a missing canonical solution;
- applies the complete canonical operation list through the existing atomic `applyOperations()` reducer;
- returns no partial solved state if an operation fails;
- preserves the original initial state;
- reports exact operation count.

## Regression gates

`runScenarioRegression()` evaluates deterministic ordered gates.

Initial phase:

- at least one `expectedInitial` assertion must be present;
- every declared initial expectation must match exactly;
- completion must be `FALSE`, proving the scenario is not already solved.

Solution phase:

- canonical solution must exist;
- every operation must apply atomically.

Solved phase:

- at least one `expectedSolved` assertion must be present;
- every declared solved expectation must match exactly;
- every required objective must be `TRUE`;
- completion must be `TRUE`.

`UNKNOWN` never silently satisfies a `TRUE` or `FALSE` expectation.

## Preservation test

The Foundation acceptance fixture now contains two network tests:

1. External attacker -> RDS TCP/3389 is initially reachable and must become blocked.
2. Management workstation -> RDS TCP/3389 is legitimate and must remain reachable before and after remediation.

The canonical solution changes only the perimeter firewall rule. The regression suite therefore demonstrates that the intended exposure is fixed while required legitimate management traffic remains functional.

## Adversarial coverage

Phase 4 rejects or fails verification for:

- missing canonical solution;
- missing initial expectations;
- wrong initial expectation;
- missing solved expectations;
- wrong solved expectation;
- invalid canonical state path;
- unknown canonical operation target;
- ineffective canonical remediation;
- required objective not satisfied;
- completion not satisfied;
- `UNKNOWN` solved result where an exact outcome was required.

## Scope boundary

Phase 4 proves deterministic semantic solvability for the currently implemented Foundation Engine capabilities. It does not claim package integrity, CLI behavior, UI behavior, ELK rendering, React Flow projection, or Parrot OS end-to-end acceptance. Those remain later phases.
