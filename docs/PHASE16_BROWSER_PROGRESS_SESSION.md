# Phase 16 — Browser Runtime progress lifecycle

Phase 16 continues directly from v0.15.0. It does not introduce a second save model; the browser session layer uses the existing Engine `SaveState`, `createSaveState`, and `restoreSaveState` contracts.

## Portable progress path

```text
RuntimeWorkspace
  -> createSaveState()
  -> portable JSON .yadiprogress
  -> File API read
  -> authoritative save-state schema validation
  -> Engine restoreSaveState()
  -> deterministic reevaluation
  -> RuntimeWorkspace
```

The scenario definition is not replaced by a progress file. A progress file contains mutable runtime state bound to the exact scenario hash, scenario schema version, and Engine version.

## Autosave path

```text
RuntimeWorkspace
  -> createSaveState()
  -> ProgressStore
       -> IndexedDB in browser
       -> MemoryProgressStore in deterministic tests
  -> exact scenarioHash lookup
  -> schema validation
  -> Engine restoreSaveState()
```

IndexedDB is local convenience storage, not a backup. Runtime exposes an explicit portable progress export using the centrally configured progress extension.

## Fail-closed compatibility

Restore remains atomic and rejects incompatible state. The existing Engine checks remain authoritative for:

- scenario hash mismatch;
- scenario schema version mismatch;
- Engine version mismatch;
- invalid state revision;
- missing or extra resources;
- embedded resource identity mismatch.

The browser layer additionally normalizes:

- malformed JSON;
- schema-invalid progress;
- IndexedDB/store read, write, and delete failures;
- missing autosave for the exact scenario hash.

The browser session layer does not weaken or duplicate Engine compatibility semantics.

## Browser integration

Runtime source now exposes:

- Export progress;
- Load progress;
- Autosave now;
- Restore autosave;
- Clear autosave.

The real browser integration uses `IndexedDbProgressStore` where `indexedDB` is available and validates imported/stored saves with the authoritative `save` schema before Engine restore.

## Verification

Added:

- 36 progress-session functional assertions;
- 28 progress-session adversarial assertions;
- portable file round-trip;
- exact-scenario autosave round-trip;
- schema-validation-before-restore checks;
- Engine compatibility diagnostic preservation;
- atomic failure checks;
- store failure normalization;
- browser source integration checks.

All earlier Foundation suites remain mandatory and pass in the v0.16.0 worktree.
