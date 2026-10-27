# Phase 7 — Canvas projection

Version: 0.7.0

Phase 7 continues from the exact v0.6.0 checkpoint. The semantic model and Engine remain authoritative; canvas state is a one-way view/projection.

## Projection contract

`projectScenarioToCanvas()` maps:

- every semantic zone -> one zone node;
- every semantic resource -> one resource node;
- every semantic connection -> one semantic edge;
- resource zone membership -> React Flow `parentId`/`extent` projection;
- interface IDs -> stable `out:<id>` / `in:<id>` handle IDs;
- connection kind/properties -> edge view data.

The projection never creates semantic resources from layout data and never writes React Flow state back into the scenario model.

## Layout boundary

Phase 7 accepts an optional layout document but does not perform auto-layout. Missing coordinates are explicitly `unplaced`; they are not silently invented as canonical layout.

Foreign scenario layouts are rejected from use. Orphan layout entries are ignored with diagnostics. Phase 8 owns ELK auto-layout.

## React Flow boundary

`toReactFlowProjection()` emits a dependency-thin structural shape compatible with React Flow while keeping `@xyflow/react` out of core-model/Compiler/Engine code.

Declared UI dependencies for the later browser runtime:

- `@xyflow/react` 12.11.6;
- React 19.3.0;
- React DOM 19.3.0.

Runtime rendering itself remains a later UI-shell concern; Phase 7 verifies the deterministic model-to-canvas projection.
