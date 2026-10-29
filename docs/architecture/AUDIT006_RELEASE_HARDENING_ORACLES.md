# AUDIT-006 remediation — frozen security oracles

**Status:** PREP ONLY / NOT TESTED. Canonical start `main=9bda61664d45f0d6116e99700c80e40ea04793f8` tree `91c9f64ddda5ea1a6094f2716754b1f028f2a3c8`. No open PRs. Read root `AGENTS.md`, issue #1, current `release-contract.mjs`, `build_browser_app.mjs`, UI mounting and release workflow. Preserve VERSION-005 version, historical code, all Engine semantics.

## Reproduced issues / priority
- **BUG-001 (high):** `git status --porcelain --untracked-files=no` permits extra untracked/ignored `asset-library/builtin/extra.svg` copied recursively into distributable artifact without Git tree provenance.
- **BUG-002 (medium):** `assertBundledRelease` only uses `js.includes` and can accept a token-only file without mounted UI identity. Current UI exposes full commit only as data/title, not directly in visible text.
- **UX-001:** `Run Modeled Probes` opens a panel, not executes probes; rename to `Open Modeled Probes`.
- README begins on a historical checkpoint; the current package is authoritative. Older docs should be explicitly indexed as historical, not rewritten or imported from archived code.
- `main` has `protected:false`. This connected GitHub app exposes read-only branch protection and GitHub private-repo rulesets are currently unavailable (GitHub 403: Pro plan or public). Document exact manual configuration; do not claim protection until readback proves it.

## Freeze acceptance
1. `readReleaseContract` rejects any non-indexed copied asset (including Git-ignored files) under `asset-library/builtin` and any non-indexed required `ui/public` source. Reject symlinks/special entries. Compiler esbuild metafile inputs outside `node_modules` must be index-tracked, regular, and root-contained. All copied static input paths must have Git provenance. Fail closed with fixed codes, no fabricated PASS.
2. Real temporary Git fixture: tracked base asset is accepted; truly untracked and ignored SVG both fail without changing HEAD; untracked esbuild-only source fails source-provenance gate; symlink fails. Existing modified tracked and expected-commit tests remain.
3. Real Chromium loads actual compiled app and checks mounted `app-frame`, *visible* UI version, checkpoint, short commit and matching full data-source-commit; interaction opens Import/Export menu. Inject a JS file containing only spoofed identity tokens: live browser assertion **must FAIL** even when static string check passes. Ensure clean browser context, loopback only, no remote network.
4. GitHub Actions PR workflow runs release identity, new adversarial tests, browser build, real Chromium identity/negative test, regressions. Independent post-merge Linux release workflow also runs the real Chromium gate **before** any final distribution ZIP upload. If installed browser unavailable, the release is BLOCKED, not PASS.
5. Refresh README top to dynamic version authority and current checkpoint status; preserve historical sections under explicit archival heading. Add concise `docs/CURRENT_PROJECT_STATUS.md` with GitHub source-of-truth, CI limitations, known open roadmap vs bugs, and branch protection instructions. Update issue #1 / #2 / #3 with real current facts; do not close broad backlog issues unless all items resolved.
6. Merge only exact final PR head with all applicable checks SUCCESS and unchanged main. Verify exact merged tree, independent Linux build SUCCESS and artifact; journal checkpoint. No Parrot-native PASS without such tests.

**Security boundary:** Git-index membership proves provenance under HEAD plus existing clean tracked status; it does not provide signed commits, software supply-chain trust or guarantee no post-build tampering without hashes and attested artifacts. Real Chromium proves rendered DOM/interaction in CI, not exhaustive user acceptance.
