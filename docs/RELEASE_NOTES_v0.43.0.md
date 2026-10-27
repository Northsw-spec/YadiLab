# YadiLab Foundation v0.43.0 — real interactive-browser acceptance gate

Incremental Phase 43 built **only** on the exact verified v0.42.0 ZIP.
Masterprompt v1.2 remains LOCKED; Engine and scenario schema are unchanged.

The existing Parrot gate could previously accept a real React *mount* without
proving that the visible application worked. Phase 43 adds an **acceptance-only**
Python Playwright Chromium workflow to `scripts/run_parrot_acceptance.sh`.
It must actually execute these UI actions against the loopback-served,
**dependency-resolved** browser build:

- mount real Builder controls; compile a real scenario and render React Flow;
- download and JSON-parse source; download a certified student `.yadilab`;
- independently inspect the downloaded ZIP, its manifest sizes/SHA-256, matching
  scenario/layout IDs, and the **absence** of student reference-solution data;
- preview Runtime, verify initial tests and finding, apply the canonical-type
  remediation through the visible Runtime configuration UI and verify
  revision, reevaluation and completion;
- download portable progress, save/restore IndexedDB autosave, perform an
  undoable reset, and reload the exported progress file;
- reopen the actual exported `.yadilab` via the browser file input;
- mutate `scenario.json` while preserving the original manifest/hash and verify
  that the browser rejects it without leaving Builder mode.

Both the independent ZIP-verification helper and the exact-loopback/shell
fail-closed tests run **without Playwright** as part of `test:foundation`.
Python Playwright is required **only for the real target acceptance run**;
it is not shipped with or needed to run the finished application.
The script never fabricates a PASS from a synthetic browser bundle. Missing
Playwright, absent real browser release, or administrative Chromium policy
returns explicit BLOCKED (exit 77), not a false success.

**Current verification boundary:** independent ZIP verifier 5 fixtures PASS;
fail-closed workflow contract 27 assertions PASS; full prepackage Foundation
regression PASS. Real Chromium navigation is administrator-blocked in this
sandbox, registry access remains unavailable, and the current host is not
Parrot. Real browser interaction and Parrot acceptance are **not verified**.
This remains a VERIFIED DEVELOPMENT CHECKPOINT, not a VERIFIED PRODUCT RELEASE.
