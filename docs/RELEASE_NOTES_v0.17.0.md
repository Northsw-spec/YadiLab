# Release notes v0.17.0 — deterministic Runtime state management

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.17.0 continues directly from exact-byte verified v0.16.0.

Added:

- Runtime Undo and Redo over immutable EngineState snapshots;
- branch-safe history: a new operation after Undo clears the Redo branch;
- Reset scenario as an undoable Runtime transition;
- deterministic named Runtime checkpoints bound to the exact scenario hash;
- checkpoint restore with cross-scenario rejection;
- deterministic replay from initial scenario state using an explicit operation sequence;
- progress-file restore establishes a new session-history baseline instead of importing stale Undo/Redo/checkpoint state;
- Runtime view-model/UI controls for Undo, Redo, Reset, Create checkpoint, and Restore last checkpoint.

Architecture boundary:

- scenario definition remains immutable and separate from mutable Runtime state;
- Runtime history is session-only and is not inserted into scenario source or the portable SaveState contract;
- Engine operations remain the only path for semantic state mutation;
- evaluation is recomputed from Engine state after Undo/Redo/Reset/checkpoint restore/replay.

Verification:

- Runtime history functional suite: 59 assertions PASS;
- Runtime history adversarial suite: 28 assertions PASS;
- complete Foundation regression through Phase 17: PASS.

External dependency-resolved rendered-browser execution and real Parrot OS x86-64 acceptance remain explicit unclaimed gates.
