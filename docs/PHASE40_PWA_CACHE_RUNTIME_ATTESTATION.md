# Phase 40 — PWA release cache integrity / runtime attestation

Baseline: original exact v0.39.0 ZIP (SHA-256 eaab8827b335ac7788732bd01591e0dbe53d9c05337d584f5c311aeda2c0be78). No prior release modified.

## Implemented

- `scripts/pwa-cache-lib.mjs` generates release-scoped, content-addressed immutable CacheStorage names based on sorted local asset hashes; rejects duplicate, traversal, remote or malformed paths.
- Both shell and future **dependency-resolved full** browser build use the same deterministic service worker generator. Neither performs arbitrary same-origin dynamic caching: only allowlisted packaged files are intercepted, and foreign caches are untouched.
- `install` precaches all immutable local files before a new worker is eligible to activate. `activate` removes only this app's old release caches and its known legacy shell/browser cache keys. An interrupted install does not purge an active release. An active tab's update lifecycle remains browser-managed; no forced `skipWaiting()` or `clients.claim()`.
- Full browser HTML now declares `booting`, not `ready`. A dedicated DOM-attestation helper invoked in React's post-commit effect asserts `ready` only when actual Builder app controls and workspace are mounted. Unmount revokes readiness.
- Parrot acceptance now checks an actual Chromium `--dump-dom` run of the app page and requires the mounted React Builder UI. The previous static HTML marker check has been replaced by a test requiring the opposite: static HTML must **not** claim successful runtime startup.
- `tests/persistence/run_cache_lifecycle_tests.mjs` executes generated worker source in an isolated VM with mocked CacheStorage/fetch, tests deterministic upgrade/recovery/cache allowlist/foreign cache preservation, and exercises the DOM-attestation helper. Static/sandbox test is not a replacement for real Chromium acceptance.

## Explicitly not verified here

- The genuine dependency-resolved React/React Flow/Ajv/ELK/zip.js browser build cannot run without an authentic npm lock, real package integrity, and installed dependencies. The readiness/build gate correctly exits 77/BLOCKED.
- Actual browser service-worker update lifecycle and mounted React page still need Chromium/Firefox on real Parrot x86-64; the Parrot gate correctly exits 77/BLOCKED on this Debian build host.
- This release does not claim offline browser visual/functional acceptance; it is a verified development checkpoint only.
