# Phase 48 — browser-build template binding correction

Phase 48 continues from the exact v0.47.0 checkpoint under Masterprompt v1.2 VERIFIED / LOCKED.

## Audit finding

Reinspection of the packaged v0.47.0 source found a discrepancy between its verification text and its actual production build code. `scripts/build_browser_app.mjs` copied `ui/public/app-shell.js` into the full browser release, but its generated `index.html` still loaded only `./assets/app.js`. The v0.47 release verifier and synthetic fixture expected the bootstrap, so the synthetic integrity suite passed even though the production generator itself was not bound to that tested fixture.

This did not turn v0.47 into a product release — dependency resolution and real Chromium/Parrot acceptance were already BLOCKED — but it means the claimed Phase 47 production-build fix was not present in the packaged bytes.

## Phase 48 fix

- Added `scripts/browser-index-template.mjs` as the single testable renderer for dependency-resolved browser `index.html`.
- `build_browser_app.mjs` now imports and invokes `renderBrowserIndex({ title: branding.displayName, cssExists })`.
- The renderer emits local `./app-shell.js` before local `./assets/app.js`, preserves the booting marker, conditionally links local CSS, links only the packaged manifest, and HTML-text-escapes the title.
- The browser release verifier now rejects a release if the bootstrap is missing, the app bundle is missing, or the bootstrap appears after the app bundle.
- The browser release fixture itself now uses the same renderer, eliminating a divergent hand-written “correct” fixture.
- The Phase 41 cache-lifecycle test now checks the renderer output rather than searching for a booting literal inside the builder source.

## Regression evidence

- browser index template: 10 assertions PASS
- browser index template adversarial: 6 assertions PASS
- browser release promotion/integrity: 38 assertions PASS
- dependency/browser-build gate: 31 assertions PASS
- dependency/browser-build adversarial: 34 assertions PASS
- offline dependency snapshot: 28 assertions PASS
- sealed snapshot transport: 42 assertions PASS
- executable browser toolchain: 12 functional + 20 adversarial assertions PASS
- browser workflow fail-closed contract: 32 assertions PASS
- acceptance contract: PASS
- whole Foundation: 106/106 deterministic commands PASS in fail-fast segmented runs

## External boundary

The sandbox still has no genuine npm-generated `package-lock.json`, exact installed `node_modules` closure, or trusted populated npm snapshot. Therefore `build:browser` correctly exits 77/BLOCKED. No dependency-resolved React browser build, real server-stopped Chromium React offline reload, or Parrot OS x86-64 acceptance is claimed as PASS.
