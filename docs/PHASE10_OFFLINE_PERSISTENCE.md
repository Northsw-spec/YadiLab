# Phase 10 — Offline progress persistence / PWA delivery foundation

Version: 0.10.0

Phase 10 continues directly from the exact v0.9.0 checkpoint.

## Save/progress contract

Runtime progress uses the existing authoritative `save-state.schema.json` contract. A save records:

- exact scenario source hash;
- scenario schema version;
- exact Engine version;
- runtime state revision;
- deterministic virtual clock tick;
- mutable resource state;
- completed objectives;
- test evidence summary.

`createSaveState()` serializes a deep-cloned snapshot. `restoreSaveState()` is strict and atomic.

A save is rejected when:

- scenario hash differs;
- schema version differs;
- Engine version differs;
- state revision is invalid;
- resource set differs from the scenario;
- a resource's embedded ID does not match its map key.

The loader never silently accepts an incompatible save.

## Browser progress workflow

Runtime can:

- create a portable save snapshot;
- export it as JSON using the centralized `progressExtension` branding value;
- read a progress file through the standard file `.text()` contract;
- restore it only after strict Engine compatibility validation;
- immediately reevaluate tests/findings/objectives/completion from restored Engine state.

The portable export remains the user's backup. Browser storage is not treated as permanent backup.

## IndexedDB boundary

`ProgressStore` defines a small persistence interface. Two implementations exist:

- `MemoryProgressStore` for deterministic tests;
- `IndexedDbProgressStore` for real browser autosave using an injected `IDBFactory`.

The IndexedDB database/store names are generic and rebrand-neutral. Save values are cloned at the boundary.

`requestPersistentStorage()` supports `navigator.storage.persist()` semantics through an injected interface and surfaces `true`, `false`, or unsupported (`undefined`) without pretending persistence is guaranteed.

## PWA/offline delivery foundation

`scripts/generate_pwa_manifest.mjs` generates `ui/public/manifest.webmanifest` from centralized branding.

The generic service-worker foundation:

- caches only same-origin GET resources;
- has no CDN or hardcoded remote URL;
- ignores cross-origin requests;
- keeps cache naming product-neutral;
- provides a local cache-first fallback boundary for the eventual bundled app shell.

## Verification boundary

This checkpoint verifies save compatibility, serialization/restoration, portable export/import, memory-store persistence semantics, persistent-storage request handling, save-schema validity, and static PWA/offline constraints.

Actual IndexedDB transactions, service-worker lifecycle, browser installability, cache behavior, and offline operation are not claimed runtime-verified in this sandbox. Those require real Firefox/Chromium browser acceptance and later Parrot acceptance.
