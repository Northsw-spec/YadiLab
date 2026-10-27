# Release notes v0.47.0 — full-browser offline bootstrap


> **Audit correction added in Phase 48:** the packaged v0.47.0 `build_browser_app.mjs` copied `app-shell.js` but its generated full-build `index.html` still loaded only `./assets/app.js`. The v0.47 claim that the production build loaded the bootstrap was therefore not supported by the packaged bytes. Phase 48 is the first checkpoint that actually binds the production build to the tested browser-index renderer and verifies script ordering.
YadiLab Foundation v0.47.0 continues directly from the exact verified v0.46.0 ZIP. Masterprompt v1.2 remains VERIFIED / LOCKED.

## Corrected

- dependency-resolved browser builds now actually load the packaged service-worker bootstrap;
- ready-release verification requires the bootstrap and rejects remote/non-local worker registration;
- the live Chromium workflow now contains an explicit server-stopped offline reload proof using a dedicated packaged loopback launcher;
- offline PASS requires the real React Builder to remount from verified cached bytes after that launcher has terminated.

## Verification

- browser release promotion integrity: **36 assertions PASS**;
- browser workflow fail-closed contract: **32 assertions PASS**;
- acceptance contract: PASS;
- complete Foundation through Phase 44 snapshot: PASS before the monolithic execution limit;
- deterministic commands 83–103: PASS in separate continuation runs, including Phase 45, Phase 46, notices, release verification, launcher/acceptance and Builder suites.

The genuine npm dependency closure is still absent here, so the dependency-resolved browser build, actual server-stopped Chromium reload, and Parrot OS x86-64 target acceptance remain correctly BLOCKED/unclaimed. This is a VERIFIED DEVELOPMENT CHECKPOINT, not a VERIFIED PRODUCT RELEASE.

## Historical correction

Phase 48 reinspection found that the exact v0.47.0 packaged `build_browser_app.mjs` did not actually load `app-shell.js` in its generated full-build index. Any v0.47 statement claiming that production linkage should be read as an intended change that was not present in the packaged bytes. The actual production binding first appears in v0.48.0.
