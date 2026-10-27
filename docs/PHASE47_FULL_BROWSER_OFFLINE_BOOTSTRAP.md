# Phase 47 — full-browser offline bootstrap and server-stopped reload acceptance


> **Audit correction added in Phase 48:** the packaged v0.47.0 `build_browser_app.mjs` copied `app-shell.js` but its generated full-build `index.html` still loaded only `./assets/app.js`. The v0.47 claim that the production build loaded the bootstrap was therefore not supported by the packaged bytes. Phase 48 is the first checkpoint that actually binds the production build to the tested browser-index renderer and verifies script ordering.
Phase 47 continues directly from the exact verified v0.46.0 checkpoint under Masterprompt v1.2 VERIFIED / LOCKED.

## Defect found

The shell path already loaded `ui/public/app-shell.js`, which registers only the packaged local `./sw.js`. The dependency-resolved browser build generated a verified `sw.js`, but its generated `index.html` loaded only `./assets/app.js`; it neither copied nor loaded `app-shell.js`, and the React entry did not independently register the worker.

That meant a future full React build could pass bundle integrity and React-mount checks while never acquiring service-worker control. A real offline reload could therefore fail even though the release contained a valid service worker.

## Intended fix recorded in v0.47

- v0.47 **intended** for `build_browser_app.mjs` to copy `app-shell.js` and load it before the application bundle, but the packaged builder only completed the copy step; the generated index remained unbound.
- `browser-release-verifier.mjs` did require `app-shell.js`, a local `./sw.js` registration, and an index script tag.
- The browser release adversarial suite exercised a synthetic correct fixture, which is why the production-generator drift was not caught until the Phase 48 audit.

Phase 48 replaces this divergent fixture/build relationship with one shared renderer and verifies production binding.

## Target acceptance

The Phase 43 live Chromium workflow now has a second, dedicated packaged-launcher origin for offline proof. On real Parrot with a dependency-resolved browser release it must:

1. launch the packaged loopback binary on a fresh local port;
2. load the real React application online and require `data-app-runtime="ready"`;
3. wait for `navigator.serviceWorker.ready`;
4. reload once online and require an active service-worker controller;
5. terminate the dedicated loopback launcher;
6. reload the same page with no server available;
7. require the real Builder navigation and topology workspace to remount from the service-worker cache;
8. require service-worker control to remain active and write explicit offline evidence.

A static manifest, shell marker, synthetic DOM, or generated worker source cannot satisfy this gate.

## Current environment boundary

Focused Phase 47 structural/adversarial tests PASS, but this Debian sandbox still lacks the genuine npm lock/cache/node_modules closure. Therefore no dependency-resolved full browser release exists here and the server-stopped Chromium proof is not claimed as PASS. It remains part of the real Parrot OS x86-64 acceptance gate.
