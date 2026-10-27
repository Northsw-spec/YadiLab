# Foundation v0.73.0

Phase 73 adds **Evidence Notebook Persistence & Replay**.

Runtime progress and the Phase-72 learner Evidence Notebook can now be persisted together in a content-addressed, exact-scenario troubleshooting session. The existing Autosave action writes the combined session while retaining the older progress-only record for backward compatibility. Restore verifies the session schema, embedded SaveState, embedded notebook, exact scenario/revision bindings, notebook SHA-256 and session SHA-256 before restoring either part.

A present but invalid combined session fails closed and cannot silently downgrade to progress-only restore. Progress-only fallback is used only when no Phase-73 session exists. Replay preserves canonical notebook evidence sequence and exact captured Runtime revisions without sorting revisions into a fabricated chronology or inferring diagnosis.

Focused Phase-73 persistence coverage is 50 functional + 14 adversarial assertions. Schema coverage increases to 48/48 fixture expectations and 18/18 Draft 2020-12 schemas. The exact Foundation chain contains 177 deterministic commands.

This remains a VERIFIED DEVELOPMENT CHECKPOINT candidate, not a product release. External snapshot signing, dependency readiness, executable browser toolchain, dependency-resolved browser build and Parrot OS x86-64 target acceptance remain fail-closed external gates in the current environment.
