# Foundation v0.76.0

Phase 76 adds **Typed Remediation Actions / Safety Constraints**.

The Runtime remediation UI no longer asks learners to edit internal modeled paths or JSON values. It presents a bounded Windows/Linux action catalog with explicit parameters, validates OS/resource compatibility and values, then compiles the selected learner action to the same deterministic one-step Engine operation used by Phase 75.

New troubleshooting notebooks use schema 0.3.0 and can record immutable `typedAction` audit metadata. Legacy 0.1.0/0.2.0 notebooks remain supported. Typed action metadata must semantically match the committed Engine operation or notebook verification fails closed.
