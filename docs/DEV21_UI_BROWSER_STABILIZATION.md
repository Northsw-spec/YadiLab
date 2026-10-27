# dev21 — UI and browser stabilization

Version: `1.1.0-dev.21`
Baseline: `1.1.0-dev.20` / source identity `17d85506c701e7805436482411df66b768005ceac960ed3262d7797729d10a7f`.

This checkpoint is limited to UI/layout, localization, browser acceptance and
launcher/runtime hardening. Engine-owned network truth and the dependency graph
are unchanged.

## Verified repairs

- Removed the unthemed React Flow `MiniMap` that produced the white topology
  overlay; retained and dark-themed the useful zoom/fit controls.
- Bound the application to `100dvh`, kept the topology and right column inside
  the remaining workspace height, and made the right column the independent
  vertical scroller.
- Replaced the wrapping free-form toolbar with a bounded responsive grid so the
  topology remains useful at 1920×1080 and 1366×768.
- Kept the Visual Journey inside the stable topology viewport and verified
  Play, Pause, Replay, Step, renderer, speed and Forward/Return X-Ray behavior.
- Completed the principal Swedish presentation labels without changing schema
  keys, IDs, Engine enums, protocol identifiers or machine-readable truth.
- Added a local favicon reference so the real browser console remains free of
  the previous 404 error.

## Runtime and launcher

The browser build now contains `build-marker.json` with the exact dev21 marker.
`start-yadilab.sh` verifies distribution checksums, identifies an occupied or
stale port, starts the static loopback launcher, verifies the marker over HTTP,
and only then opens Chrome/Chromium. `Start-YadiLab.desktop` resolves its own
directory through `%k`, including paths with spaces. The default origin is the
dev21-specific `http://127.0.0.1:18231/`.

Browser-build and loopback-distribution promotion remain transactional: staged
bytes are completely verified before the previous working release is replaced.

## Acceptance

The dev21 real-browser acceptance uses the already-installed Selenium and
system Chrome/Chromium as acceptance-only tooling. It verifies secure context,
IndexedDB, Cache API, service worker, actual React mount, viewport dimensions,
independent right scrolling, accordion stability, Journey interaction, absence
of the MiniMap overlay, refresh behavior and console errors. Firefox retains the
existing headless render gate.
