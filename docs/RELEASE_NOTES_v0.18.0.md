# Release notes v0.18.0 — Runtime explainability and panel completeness

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.18.0 continues directly from exact-byte verified v0.17.0.

Added / corrected:

- read-only Runtime detail presenter for Mission, Tests, Findings, Evidence, Progress, Hints, and Learning/Objectives;
- Engine explanations are surfaced instead of reducing results to unexplained verdict labels;
- explicit TRUE/FALSE/UNKNOWN states preserved through presentation;
- Runtime progress presentation includes completion explanation, state revision, Undo/Redo depth, and checkpoints;
- Runtime view-model exposes all required Masterprompt surfaces: Mission, Topology, Inspector, Configuration, Tests, Findings, Evidence, Progress, Hints, Learning;
- corrected browser source to use `finding.state` and `objective.state` rather than nonexistent `finding.active` / `objective.truth` fields.

Architecture boundary:

- presenter layer is read-only and cannot mutate RuntimeWorkspace or Engine state;
- no UI-derived verdicts; states and explanations come from Engine evaluation;
- UNKNOWN is never silently coerced to FALSE.

Verification:

- Runtime explainability functional suite: 37 assertions PASS;
- Runtime explainability adversarial suite: 10 assertions PASS;
- complete Foundation regression through Phase 18: PASS.

External dependency-resolved rendered-browser execution and real Parrot OS x86-64 acceptance remain explicit unclaimed gates.
