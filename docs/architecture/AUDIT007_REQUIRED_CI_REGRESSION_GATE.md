# AUDIT-007 — Required pre-merge regression gate

Status: Proposed in branch `audit007-required-regression-gate`; do not mark PASS until exact GitHub Actions results are read.

## Why

The previously protected `yadilab-required-ci` covered OSPF Hello/Dead, simulation clock, topology import, release identity, and real Chromium DOM identity, but did **not** execute the full `npm run test:engine` regression suite, Dev11 UI regression, or the native Linux launcher/build prior to merge. On 2026-10-28, three historical main release runs failed for stale checkpoint assertion, incomplete runtime dependency policy and tracked generated metadata modifications. These were later fixed, but required PR coverage remained incomplete. See [AUDIT-007 issue #61](https://github.com/Northsw-spec/YadiLab/issues/61).

## PR gate coverage (unconditional, one stable required check)

`yadilab-required-ci` remains the **same job name** for existing branch protection. The workflow fires on **all PRs to main**, not path-filtered subsets. The commands must genuinely run and propagate nonzero exits.

| Category | Gate command | Why |
| --- | --- | --- |
| Dependency policy | `run_dependency_tests.mjs` and `run_dependency_adversarial.mjs` | Lock/policy consistency, including unexpected runtime dependencies |
| Engine baseline | `npm run test:engine` | Foundation, adversarial, L2 storm, MTU/PMTUD and regression tests |
| UI | `npm run test:dev11-ui` | Visual journey and Dev11 topology/runtime regression |
| Go launcher | `go test ./launcher/...` | Native launcher unit tests |
| Existing security/simulation gates | Previous required CI commands unchanged, plus `test:release-evidence` | No replacement of earlier oracles |
| Browser | Browser build, integrity/commit verification, `test:import003-ui` | Actual browser release and checkpoint-specific UI |
| Linux distribution | `npm run build:launcher`, `sha256sum -c`, `YADILAB_TEST_ONCE=1 bash start-yadilab.sh` | Pre-merge native binary and loopback HTTP identity smoke |
| Repository metadata | `git diff --exit-code` on tracked dependency/license manifests and package files | Fail if a build silently changes critical tracked metadata |
| Browser mounted DOM | Existing independent Playwright/Chromium attestation | Real browser exact-source identity, not token-only JS assertions |

Ubuntu GitHub Actions is the CI verification environment. This does not claim to verify graphics/desktop behavior under Parrot or every possible network behavior.

## Evidence and release promotion

1. Review PR diff; do not write to protected `main` directly.
2. Obtain **SUCCESS** for the exact PR-head/merge-check run's `yadilab-required-ci`, inspect steps and logs, and do not infer test success from job configuration.
3. Confirm protected merge without bypass and record merge commit SHA.
4. Check independent `linux-attested` post-merge release against new exact `main` SHA and confirm artifacts before closing #61.
5. If tests fail, fix code or test setup in a new PR commit and re-check; never assert PASS from unexecuted steps.

The required job cannot prove every optional path-filtered workflow ran, or substitute for a future systematic CI/test coverage review.
