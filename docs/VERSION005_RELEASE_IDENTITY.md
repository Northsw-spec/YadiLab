# VERSION-005 — verifiable release identity

Single source of truth is **`package.json`**: `version`, `yadilabRelease.checkpoint`, and `yadilabRelease.description`.

- `package-lock.json` is checked for consistency; it must never independently dictate the UI version.
- The browser UI imports the root package metadata through the bundler; no human-maintained UI version literals.
- Git `HEAD` commit and tree are read from a **real, clean repository checkout**. Source archives without a verifiable HEAD are deliberately prevented from producing a release.
- The browser builder stamps `sourceCommit` and `sourceTree` into `build-marker.json`, and the immutable Git commit into the rendered UI (data-source-commit). Both are validated against the compiled JS before promotion.
- Linux packaging rechecks browser identity before and after copying. Distribution SHA256SUMS covers the marker and compiled JS. The launcher derives its version/checkpoint/commit from the checksum-validated marker rather than an independent hard-coded version.
- Do not mistake a valid label for functional acceptance; network probes still require separate Engine regression and Parrot acceptance checks.

## Official release instructions

Use a clean `git checkout` at the intended commit, with `node`, `npm`, `go`, and locked dependencies available. Run `npm ci`, `npm run test:release-identity`, `npm run build:browser`, `node scripts/verify_release_identity.mjs`, `npm run build:launcher`, followed by `(cd distribution/linux-x86_64 && sha256sum -c SHA256SUMS.txt)`. A checkout with modified tracked source or mismatched package-lock cannot build an attested release.

Only promote an app after the compiled browser probe and user acceptance have passed. Existing IMPORT-003/004 commits are retained unchanged.
