# Phase 43 — actual Parrot browser workflow acceptance

This is a developer/QA-only procedure, **not** a runtime installation step.
End users do not need Python, Playwright, npm, or TypeScript to run a shipped
application with its built local assets.

1. On a trusted internet-connected Linux x86-64 development machine, create
   a complete npm snapshot using `scripts/prepare_offline_browser_cache.sh`
   and transfer it to the Parrot build machine. Only use the matched
   dependency-policy and exact-source checkout; follow Phase 37's README.
2. On Parrot, install the transferred bundle with
   `scripts/install_offline_browser_dependencies.sh /path/to/snapshot`.
   This must pass real dependency readiness, actual esbuild bundle, and
   browser release promotion before target acceptance begins.
3. In a separate Python test virtual environment with trusted offline wheels
   (or an authorized test network), install `playwright==1.57.0`. Use the
   **system Chromium**; no Playwright-managed browser download is required.
   `python3 -m pip download --dest wheelhouse playwright==1.57.0` can prepare
   wheels on a compatible connected development machine. This pinned QA
   version has only been import-tested here; target Chromium compatibility
   remains to be proven on Parrot.
4. Run `bash scripts/run_parrot_acceptance.sh`. The live workflow is now a
   mandatory gate in addition to initial browser mount, secure-context,
   IndexedDB, service worker, Firefox render and loopback checks.
5. A missing real browser bundle or testing dependency returns BLOCKED; any
   broken actual application interaction returns FAIL. Inspect the generated
   Parrot report; only all required PASS results justify target acceptance.

Selftests that work without any browser or Python Playwright:

`python3 tests/acceptance/run_live_browser_workflow.py --selftest`

`python3 tests/acceptance/run_browser_workflow_contract_tests.py`

Do not label the current Foundation checkpoint as Parrot-verified until a
live target run completes successfully and its report is retained.
