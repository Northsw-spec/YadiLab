# Foundation v0.75.0

Phase 75 adds **Troubleshooting Remediation / Verification Loop**.

Learners can now save current modeled evidence, preview an explicit modeled remediation operation, commit it as one Runtime history step, save after-evidence and deterministically review matching before/after evidence. The workflow is learner-driven and never reads canonical solution or hidden fault truth.

New notebooks use schema 0.2.0 with immutable `remediation_action` entries; legacy 0.1.0 notebooks remain accepted. A remediation preview is bound to exact scenario hash, Runtime revision, notebook identity and operation. Review produces only transparent before/after transition states and no score, grade or inferred diagnosis.
