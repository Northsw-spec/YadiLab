# Foundation v0.72.0

Phase 72 adds **Troubleshooting Session / Evidence Notebook** over the deterministic Observation Engine.

Highlights:

- portable `infrastructure-cyber-lab.troubleshooting-notebook@0.1.0` schema;
- centralized `.yadinotebook` file extension;
- scenario ID/hash binding and canonical SHA-256 notebook identity;
- explicit learner-controlled capture of Wave-1 observations and Wave-2 active probes;
- canonical ordered entry IDs and Runtime revision binding;
- per-transcript SHA-256 identity;
- learner-authored hypothesis, next-step and conclusion entries;
- duplicate same-revision transcript rejection;
- stale transcript capture rejection after Runtime state drift;
- schema/identity/scenario validation on portable import;
- notebook export/import does not mutate Engine state;
- hidden fault truth, generator ground truth and canonical solution material are not imported into the learner notebook;
- no automatic diagnosis, grading, remediation or guest command execution is introduced.

Classification remains **VERIFIED DEVELOPMENT CHECKPOINT, NOT VERIFIED PRODUCT RELEASE** until the external dependency/browser/Parrot gates are satisfied.
