# Phase 79 — Portable Troubleshooting Session Backup / Recovery

Phase 79 hardens release/session recovery without changing Engine truth or troubleshooting semantics.

## Boundary

`PORTABLE_SESSION_EXACT_SCENARIO_NO_SOLUTION`

A portable troubleshooting session is a local JSON backup using the `.yadisession` extension. It contains the already-verified Phase-73 troubleshooting session envelope: exact Runtime `SaveState` plus the learner-owned Evidence Notebook. It does not add or derive `canonicalSolution`, `faultOrigin`, hidden fault truth, curriculum acceptance data, instructor solution data, scoring, AI/ML/LLM output, live connector data or guest-command execution.

## Export

`createTroubleshootingSessionDownload(...)` first creates the ordinary content-addressed troubleshooting session snapshot. Export is therefore bound to:

- exact `scenarioId` and `scenarioHash`;
- exact Runtime `stateRevision` and nested SaveState;
- exact notebook identity and entries;
- canonical troubleshooting-session SHA-256 identity.

The browser exposes **Export session backup** in Runtime. Existing progress and notebook exports remain available.

## Import / recovery

`loadTroubleshootingSessionFile(...)` restores only after all of these checks pass:

1. filename ends in the configured `.yadisession` extension;
2. local text size does not exceed the conservative 8 Mi-character limit;
3. JSON parses successfully;
4. troubleshooting-session schema passes;
5. nested SaveState schema passes;
6. nested notebook schema passes;
7. exact scenario ID/hash matches current Runtime;
8. envelope revision matches nested SaveState revision;
9. notebook scenario binding and notebook identity match;
10. canonical notebook SHA-256 recomputes exactly;
11. canonical session SHA-256 recomputes exactly;
12. restored Runtime revision equals the sealed envelope revision.

No Runtime or notebook state is applied before verification completes. Failure is atomic and fail-closed. The browser exposes **Import session backup**.

## Backward compatibility

Phase 79 does not change the troubleshooting-session schema version. Existing Phase-73+ IndexedDB sessions remain valid. `.yadiprogress` and `.yadinotebook` remain supported as separate portable artifacts. Built-in curriculum labs need no special session format: their exact scenario source hash provides the same binding as other scenarios.

## Verification

New focused tests:

- portable session functional: 20 assertions;
- portable session adversarial: 8/8 assertions.

Adjacent Phase-72/73 notebook/session, Phase-78 curriculum, schema, branding and browser regressions are required before release sealing.
