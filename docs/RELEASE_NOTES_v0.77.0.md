# Foundation v0.77.0

Phase 77 adds **Guided Troubleshooting Workflow / Remediation UX**.

Runtime now presents a deterministic process map across the existing troubleshooting tools: collect evidence, review learner-visible objectives, record a learner hypothesis, choose a typed remediation, collect matching after-evidence and verify the before/after result.

The workflow is explicitly `PROCESS_GUIDANCE_NO_DIAGNOSIS`. It does not choose a target, command, probe, diagnosis, remediation or value. Its content-addressed workflow identity is bound to the exact Runtime revision, notebook identity and deterministic review identities.
