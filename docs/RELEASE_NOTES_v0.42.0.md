# YadiLab Foundation v0.42.0 — verified browser release promotion boundary

Incremental development checkpoint built from the exact v0.41.0 release.

**Phase 42** introduces a dependency-free, fail-closed browser release
integrity verifier (`scripts/verify_browser_release.mjs`), integrated into
both the dependency-resolved browser builder and the loopback distribution
builder. A ready manifest alone can never promote a browser release:

- the manifest must have the expected format/version/build tool and exact
  runtime dependency pins from the authoritative policy;
- all browser distribution files must be listed once, present, regular
  (no symlinks), safe relative paths, and exact size/SHA-256 matches;
- the local JS bundle, boot-only HTML and required offline files must exist;
- licensing metadata must be **bundle-resolved**, never the direct-only baseline;
- the browser service worker's complete precache inventory must agree with
  the actual release assets and their SHA-256 hashes;
- staged *copied* browser files are reverified independently before release;
- the last good loopback distribution survives invalid browser artifacts
  and staging/build failures; shell-only fallback is allowed ONLY when no
  attempted `ui/dist` browser build exists.

The copied full-browser distribution is no longer overwritten with built-in
assets from the mutable development checkout after its manifest was hashed.
The new integrity gate is intentionally **not** evidence that React mounted;
the existing real Chromium/Parrot runtime gate remains mandatory. No Engine
or scenario schema changes. No fake npm locks, dependencies or synthetic
browser bundles are included in this checkpoint.

Targeted browser promotion integrity suite: **30 assertions PASS**.
Full Foundation regression: **PASS** (subject to final packaged readback).
Real npm registry, dependency-resolved React build and Parrot acceptance:
**BLOCKED** in this Debian sandbox. This is a **VERIFIED DEVELOPMENT
CHECKPOINT**, not a production **VERIFIED RELEASE**.
