# Release notes v0.9.0 — Builder/Runtime browser foundation

YadiLab Foundation v0.9.0 continues directly from v0.8.0.

## Added

- framework-neutral Builder workspace and command layer;
- mission metadata editing;
- zone/resource/connection authoring with explicit safe deletion behavior;
- multi-select and Inspector property edits;
- tests/findings/objectives/hints/canonical-solution authoring operations;
- current-compile gating before Runtime preview;
- Runtime workspace backed by actual Engine state/evaluation;
- runtime reset and deterministic configuration operations;
- Builder and Runtime view-model panel contracts;
- standard File/Blob JSON import/export boundary;
- Phase 8 auto-layout integration with separate manual overrides;
- browser functional and adversarial suites.

## Preserved

All Phase 0-8 verification remains in `npm run test:foundation`. React/React Flow remain projections/adapters; canonical semantic state remains outside UI state.

## Boundary

The checkpoint validates browser/application controllers and DOM/File contracts without claiming an actually rendered Firefox/Chromium/PWA runtime. Real browser + Parrot acceptance remains pending.
