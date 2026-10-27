# Foundation v0.74.0

Phase 74 adds **Troubleshooting Objectives / Evidence Review**.

Scenario authors can now declare transparent `troubleshootingObjectives` describing exactly which learner-visible observation/probe evidence should be collected and whether that evidence must appear in notebook order. The compiler preserves these objectives into the normalized Runtime scenario while rejecting empty matchers, duplicate requirement IDs and unknown resource references.

Runtime can review the verified Phase-72/73 Evidence Notebook against those objectives through `foundation.evidence_review@0.1.0`. Requirements report only `SATISFIED`, `PENDING` or `OUT_OF_ORDER`, with exact matched notebook entry IDs where applicable. Required objectives produce a transparent `NOT_CONFIGURED` / `SATISFIED` / `PENDING` overall status. No score, grade, root-cause selection, hidden ground truth or AI inference is introduced.

Focused Phase-74 coverage before whole-Foundation sealing is 35 Evidence Review functional + 14 adversarial assertions and 6/6 Browser functional + 6/6 adversarial. Compiler coverage is 69 functional + 63 adversarial assertions. Schema coverage is 51/51 fixture expectations and 18/18 Draft 2020-12 schemas. The exact Foundation chain contains 181 deterministic commands.

This remains a VERIFIED DEVELOPMENT CHECKPOINT candidate, not a product release. External snapshot signing, dependency readiness, executable browser toolchain, dependency-resolved browser build and Parrot OS x86-64 target acceptance remain fail-closed external gates in the current environment.
