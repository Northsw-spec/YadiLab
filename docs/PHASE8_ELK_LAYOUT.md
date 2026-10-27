# Phase 8 — ELK Layered auto-layout boundary

Version: 0.8.0

Phase 8 continues from the exact v0.7.0 checkpoint.

## Architecture

Layout remains a derived projection. Scenario/Engine state does not contain React Flow or ELK state.

The Phase 8 pipeline is:

```text
NormalizedScenario
  -> pure LayoutGraph projection
  -> LayoutBackend
  -> backend-output validation
  -> optional manual overrides
  -> LayoutDocument
  -> Phase 7 canvas projection
```

## Pure graph projection

`buildLayoutGraph()` maps zones/resources into a compound hierarchy and semantic connections into layout edges. Resource interfaces receive globally unique input/output port identifiers.

Defined initial dimensions are stable constants so the same semantic input produces the same layout input.

## Backend contract

`LayoutBackend` isolates the model from the layout library. Backend output must contain exactly one valid geometry result per semantic zone/resource with matching parent hierarchy.

The validator rejects:

- missing nodes;
- duplicate nodes;
- unknown nodes;
- non-finite/zero/negative geometry;
- parent hierarchy mismatches;
- backend exceptions.

## ELK adapter

`ElkLayoutBackend` dynamically loads `elkjs/lib/elk.bundled.js` and requests:

- `layered` algorithm;
- rightward direction;
- compound hierarchy handling;
- stable spacing/padding;
- fixed-order ports.

The declared dependency is `elkjs` 0.12.0.

## Manual overrides

Manual user coordinates/dimensions are applied after generated layout and marked `manualOverride: true` in the layout document. Unknown override IDs are ignored with diagnostics. Manual overrides therefore remain separate from generated topology semantics.

## Runtime verification boundary

The sandbox does not contain installed npm packages. Backend-independent layout projection, output validation, deterministic document creation, and manual override behavior are runtime-tested. The actual `elkjs` module cannot be executed here, so ELK library-byte execution remains pending a dependency-resolved environment and is not labelled verified by this checkpoint.
