# Phase 74 — Troubleshooting Objectives / Evidence Review

Foundation v0.74.0 adds explicit, learner-visible troubleshooting evidence objectives that can be reviewed deterministically against the Phase-72/73 Evidence Notebook.

## Boundary

Troubleshooting objectives are **not** Engine completion objectives, hidden instructor truth, root-cause labels, scores or grades. They are transparent scenario-authored requirements describing what observable evidence the learner is expected to collect.

The review engine reads only:

- the normalized scenario's `troubleshootingObjectives` contract;
- the verified exact-scenario Evidence Notebook;
- learner-visible observation/probe entry fields already stored in that notebook.

It does not read `faultOrigin`, generator ground truth, `canonicalSolution`, hidden instructor material or Engine-private causal state.

## Scenario contract

`troubleshootingObjectives` is optional and contains at most 64 objectives. Each objective declares:

- stable ID and learner-visible title;
- optional learner-visible description;
- whether the objective is required;
- `evidenceOrder`: `ordered` or `unordered`;
- one or more explicit evidence requirements.

Observation requirements may match category, target resource and/or exact learning-surface command. Active-probe requirements may match category, source, destination, protocol, port, DNS query name and/or explicit `TRUE` / `FALSE` / `UNKNOWN` verdict.

A requirement with no explicit matcher is rejected semantically. Resource references are compiler-validated and unknown targets/sources/destinations fail closed. Requirement IDs must be unique inside each troubleshooting objective.

## Deterministic review

The review engine is `foundation.evidence_review@0.1.0` with boundary `NOTEBOOK_ONLY_NO_DIAGNOSIS`.

Each requirement reports only:

- `SATISFIED`;
- `PENDING`;
- `OUT_OF_ORDER` for ordered objectives where matching evidence exists only before the required preceding evidence.

Satisfied requirements expose the exact matched notebook entry ID and sequence. The engine does not calculate percentages, points, weighted scores, grades, confidence or a preferred diagnosis.

For ordered objectives, requirements must be satisfied by strictly increasing notebook evidence sequence. For unordered objectives, any matching notebook entry may satisfy a requirement. Learner notes never satisfy evidence requirements.

The overall required-evidence status is one of:

- `NOT_CONFIGURED` when the scenario declares no required troubleshooting objective;
- `SATISFIED` when all required objectives are satisfied;
- `PENDING` otherwise.

Optional objectives never block required-evidence satisfaction.

The complete review result is content-addressed with a canonical SHA-256 `reviewIdentity` bound to the exact scenario hash, notebook identity, objective results and matched entries.

## Builder and Runtime

Builder exposes a dedicated **Troubleshooting evidence objectives JSON** authoring panel. Builder-side checks reject duplicate requirement IDs, empty matchers, unknown resource references and deletion of a resource still referenced by an evidence objective.

Runtime adds **Review collected evidence** inside the learner Evidence Notebook panel. The UI shows each objective and each transparent requirement with its deterministic status and matched notebook entry. Changing notebook identity invalidates the displayed review until it is run again.

## Non-goals

v0.74.0 does not add:

- automatic root-cause diagnosis;
- ranking or selecting learner hypotheses;
- troubleshooting scores, percentages, grades or weighted rubrics;
- automatic remediation;
- hidden instructor truth inside the review result;
- guest command execution, packets, sockets or terminal access;
- AI/ML/LLM inference.
