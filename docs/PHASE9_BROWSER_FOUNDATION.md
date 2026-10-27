# Phase 9 — Builder/Runtime browser foundation

Version: 0.9.0

Phase 9 continues from the exact v0.8.0 checkpoint. It adds the browser-facing application/session boundary without moving semantic authority into React, React Flow, or transient UI state.

## Authority boundary

```text
Builder
  edits ScenarioSource
      ↓ compile
NormalizedScenario
      ↓
Runtime EngineState + EngineEvaluation
```

The Builder source remains authoring data. Runtime mutations never rewrite Builder source. Canvas selection, panel state, layout coordinates, and manual drag/resize overrides remain view/layout concerns rather than semantic truth.

## Builder foundation

Implemented framework-neutral browser controllers support:

- mission title/briefing/language metadata edits;
- create/edit/delete zones;
- create/edit/delete/duplicate resources;
- explicit safe cascade behavior for referenced resources/non-empty zones;
- create/edit/delete semantic connections;
- multi-selection with deterministic filtering;
- typed resource property edits;
- tests, findings, objectives, hints, and canonical solution authoring;
- compiler validation through the real Phase 2 compiler;
- Runtime preview only after a current successful compile;
- separate manual layout overrides for drag/resize semantics;
- Phase 8 auto-layout invocation behind `LayoutBackend`;
- JSON source import/export using the standard File/Blob browser baseline.

Intermediate Builder states may be semantically incomplete, but invalid data is never silently normalized into a verified scenario. The compiler remains the authoritative validation gate.

## Runtime foundation

Runtime preview is created only from a successfully compiled `NormalizedScenario` and creates a fresh independent `EngineState`.

Runtime supports:

- deterministic Engine operations;
- reevaluation after every successful operation;
- reset to canonical initial state;
- view-only selection;
- topology projection from normalized model + separate layout document;
- Mission, Topology, Inspector, Configuration, Tests, Findings, Evidence, Progress, Hints, and Learning panel contracts.

Runtime operations cannot modify Builder `ScenarioSource` or its revision counter.

## Browser file baseline

The browser file helper uses:

- file-like `.text()` reading (compatible with the standard File API);
- JSON parsing with explicit errors;
- Blob-based download descriptors;
- object-URL creation, click, and revocation through an injected browser host.

No File System Access API dependency is introduced.

## Layout integration

`autoLayoutBuilder()` requires a current successful compile, calls the existing Phase 8 `LayoutBackend`, applies manual overrides after generated layout, validates the result, and stores only the derived `LayoutDocument` in the UI workspace.

Manual coordinates never modify scenario source.

## Runtime verification boundary

This checkpoint validates the framework-neutral browser/application logic in Node with DOM type contracts and injected browser/layout adapters. It does not claim a real Firefox/Chromium rendered React application yet. Actual browser DOM/PWA/IndexedDB/service-worker acceptance remains a later target and must be tested on supported browsers/Parrot before being labelled verified runtime behavior.
