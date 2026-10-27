# YadiLab Foundation v0.40.0 — release-scoped PWA caching and real-runtime attestation

Built incrementally from the exact v0.39.0 checkpoint SHA-256 `eaab8827b335ac7788732bd01591e0dbe53d9c05337d584f5c311aeda2c0be78`.

The current shell and the future dependency-resolved browser bundle now generate versioned, hash-derived offline service workers, never dynamically caching arbitrary same-origin requests and never deleting unrelated apps' caches. The generated full browser HTML says `booting`; a React post-commit helper marks it `ready` only if actual UI controls have mounted. The Parrot harness adds a Chromium DOM acceptance gate for the mounted Builder interface.

New PWA release/cache-runtime tests: **17 functional + 17 adversarial assertions**. All existing Foundation tests remain mandatory. Actual full browser bundling and real Parrot acceptance remain BLOCKED externally in this environment; do not label this a product VERIFIED RELEASE.
