# Phase 77 — Guided Troubleshooting Workflow / Remediation UX

Foundation v0.77.0 adds a deterministic process-guidance layer over the existing Observation, Active Probe, Evidence Notebook, Evidence Review and Typed Remediation capabilities.

## Boundary

The guided workflow is **process guidance only**. It does not infer a diagnosis, choose a target, choose a command/probe, recommend a remediation, select a remediation value, read canonical solution material or reveal hidden fault truth.

Engine identity: `foundation.guided_troubleshooting@0.1.0`  
Boundary: `PROCESS_GUIDANCE_NO_DIAGNOSIS`

The workflow consumes only learner-visible Runtime state plus the canonically verified troubleshooting notebook and the existing deterministic Evidence Review / Remediation Review results.

## Guided phases

The workflow can report only these high-level phases:

- `COLLECT_EVIDENCE`
- `REVIEW_EVIDENCE`
- `FORM_HYPOTHESIS`
- `REMEDIATE`
- `COLLECT_AFTER_EVIDENCE`
- `VERIFICATION_COMPLETE`
- `CONTINUE_INVESTIGATION`

Each phase gives a generic process instruction. It never names the fault, preferred target, preferred command, preferred probe or remediation value.

## Deterministic step model

The Runtime panel renders six transparent steps:

1. Collect baseline evidence.
2. Review learner-visible evidence objectives.
3. Record the learner's hypothesis.
4. Preview and commit a typed remediation if the learner's evidence supports it.
5. Collect matching after-evidence.
6. Verify the before/after remediation result.

Step states are only `COMPLETE`, `READY`, `WAITING`, `OPTIONAL` or `ATTENTION`.

Evidence objectives remain optional when a scenario does not configure them. The workflow does not introduce a hidden completion rubric.

## Revision and notebook semantics

- Current baseline evidence must come from the relevant Runtime revision.
- Learner notes never count as observation/probe evidence.
- After a remediation, matching after-evidence is determined by the existing Phase-75 Remediation Review contract.
- A different post-remediation check does not falsely satisfy the before/after pair.
- `VERIFIED_IMPROVEMENT` becomes `VERIFICATION_COMPLETE`.
- `REGRESSION_DETECTED` or `NO_VERIFIED_IMPROVEMENT` becomes `CONTINUE_INVESTIGATION` without recommending the next fix.
- Notebook tampering or scenario/hash mismatch fails closed.

## Workflow identity

The guided workflow has its own canonical SHA-256 identity covering the exact scenario identity, Runtime revision, notebook identity, evidence-review identity, remediation-review identity when present, phase and rendered step state.

The same Runtime + notebook state therefore produces the same workflow identity. Changing evidence, learner notes, remediation or Runtime revision changes the identity.

## Runtime UX

The Guided troubleshooting workflow panel is shown before the Observation and Active Probe tools. It acts as a progress map for the existing learner workflow rather than a wizard that performs actions.

The lower-level Observation, Probe, Notebook, Evidence Review and Typed Remediation controls remain explicit and user-operated.

## Explicit non-goals

v0.77.0 does not add automatic troubleshooting, root-cause inference, suggested fixes, hidden scoring, grading, canonical-solution lookup, guest command execution, live connectors, real endpoint/network mutation or AI/ML/LLM assessment.
