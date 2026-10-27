# Phase 75 — Troubleshooting Remediation / Verification Loop

Foundation v0.75.0 adds a learner-driven remediation loop on top of the Phase-72/73 Evidence Notebook and Phase-70/71 modeled observation/probe engines.

## Boundary

Remediation is explicit modeled Runtime state editing, not guest command execution and not a live connector. The learner supplies the operation. The remediation code does not read `canonicalSolution`, `faultOrigin`, hidden fault truth, generator ground truth, instructor notes, or any AI/ML/LLM system.

The explicit boundary is `LEARNER_OPERATION_NO_SOLUTION`.

## Controlled operation surface

A remediation is exactly one existing Engine `set` or `remove` operation. To protect scenario/resource identity, learner remediation may modify only:

- `properties.*`
- `interfaces.<index>.addresses` (and a concrete address index)
- `interfaces.<index>.mac`

Resource identity/type/label metadata is immutable through this workflow.

Before commit the learner must already have at least one saved observation or active probe from the exact current Runtime revision. Preview is non-destructive and binds scenario identity, Runtime revision, notebook identity and the exact operation. Any state/notebook/operation change invalidates the token.

Commit uses the normal Runtime history operation path, so one remediation is one undoable Runtime history step.

## Notebook contract

Troubleshooting Notebook schema 0.2.0 adds `remediation_action` entries while the verifier continues to accept legacy 0.1.0 notebooks. New notebooks are created as 0.2.0.

A remediation entry records:

- before and after Runtime revision,
- exact learner operation,
- canonical operation SHA-256,
- modeled value state before and after,
- optional learner note,
- explicit no-solution boundary.

The notebook identity covers the remediation entry. Phase-73 session persistence automatically covers the new notebook content without introducing a second Engine truth source.

## Before / after verification

`foundation.remediation_review@0.1.0` compares only notebook evidence surrounding one remediation action.

Matching requires the same observation signature or active-probe signature at the exact before and after Runtime revisions. Active probe transitions are classified as:

- `RESTORED` — before was not TRUE and after is TRUE,
- `REGRESSED` — before was TRUE and after is not TRUE,
- `CHANGED` — truth changed without a proven restoration/regression,
- `UNCHANGED`.

Observation pairs can prove transcript configuration change but do not by themselves prove health.

Overall review status is only:

- `PENDING_AFTER_EVIDENCE`
- `VERIFIED_IMPROVEMENT`
- `REGRESSION_DETECTED`
- `NO_VERIFIED_IMPROVEMENT`

There is no scalar score, grade, root-cause inference or automatic solution recommendation.

## Explicit non-goals

v0.75.0 does not add real PowerShell/shell remediation, host/network scanning, live connectors, automatic canonical-solution execution, temporal fault automation, hidden grading, or AI/ML/LLM assessment.
