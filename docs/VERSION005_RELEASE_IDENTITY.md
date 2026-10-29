# VERSION-005 — verifiable release identity

Single source of truth is **`package.json`**: `version`, `yadilabRelease.checkpoint`, and `yadilabRelease.description`.

- `package-lock.json` is checked for consistency; it must never independently dictate the UI version.
- The browser UI imports the root package metadata through the bundler; no human-maintained UI version literals.
- Git `HEAD` commit and tree are read from a **real, clean repository checkout**. Source archives without a verifiable HEAD are deliberately prevented from producing a release. A closed inventory checks that all recursively copied built-in assets and actual local esbuild inputs are Git-indexed regular files; untracked/ignored additions are denied.
- The browser builder stamps `sourceCommit` and `sourceTree` into `build-marker.json`. The UI visibly renders the exact version/checkpoint and short Git commit, retaining the full commit in `data-source-commit`. Static bundle-token matching is **insufficient**: a dedicated real-Chromium gate asserts DOM-mounted visible identity, real menu interactions, and rejects token-only JavaScript prior to distribution.
- Linux packaging rechecks browser identity before and after copying. Distribution SHA256SUMS covers the marker and compiled JS. The launcher derives its version/checkpoint/commit from the checksum-validated marker rather than an independent hard-coded version.
- Do not mistake a valid label for functional acceptance; network probes still require separate Engine regression and Parrot acceptance checks.

## Official release instructions

Use a clean `git checkout` at the intended commit, with `node`, `npm`, `go`, and locked dependencies available. Run `npm ci`, `npm run test:release-identity`, `npm run build:browser`, `node scripts/verify_release_identity.mjs`, `npm run build:launcher`, followed by `(cd distribution/linux-x86_64 && sha256sum -c SHA256SUMS.txt)`. A checkout with modified tracked source or mismatched package-lock cannot build an attested release.

The release workflow MUST run `tests/acceptance/run_release_identity_real_browser.py` against an exact fresh compiled loopback build before packaging. A static `assertBundledRelease` pass alone does **not** certify visible UI identity. Native Parrot checks remain NOT_RUN when only Ubuntu CI passes; manual Parrot testing is optional under the repository CI-first acceptance policy. Existing IMPORT-003/004 commits are retained unchanged.
