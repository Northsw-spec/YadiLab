# YadiLab — permanent source-code authority and checkpoint policy

**Status:** Mandatory project operating rule. Applies to all developers, coding agents, CI changes, scripts, and future checkpoints. This is an instruction for how to work, **not** a pin to a historical code version.

## Source of truth

1. **ONLY current `main` in `https://github.com/Northsw-spec/YadiLab` is the authoritative source-code base.** Before beginning every checkpoint, fetch `main`, record its HEAD/tree identity, examine the actual code, and base a fresh GitHub branch on that current HEAD. If `main` changes, re-check and reconcile before merging.
2. **All new code belongs in GitHub.** This includes source files, automated tests, fixtures, configuration, workflows, migrations, and code-related documentation. Push/commit changes to a GitHub branch during the checkpoint. A coding checkpoint is **not complete** until its changes exist on GitHub and the commit ID has been read back and verified. Approved and tested changes should be integrated into `main` using a reviewed pull request; document deliberate exceptions.
3. **Never treat local environments as durable storage.** Files in an agent runtime, a temporary container, an attachment, a workspace or a chat are temporary. If GitHub upload/commit fails, the checkpoint is **BLOCKED / NOT DELIVERED**; never report it as delivered or leave new source code solely outside GitHub.
4. **Google Drive is for research and planning documents, not a codebase.** Put masterplans, research papers, architecture essays and other non-code reference documents there. Do **not** store newly authored application code, patches, source ZIPs, or working repositories in Drive as a fallback. When code-level ADRs, schemas or developer instructions affect implementation, version-control those files in GitHub; user-facing reports may also exist in Drive.
5. **Never reconstruct or import historical code.** Old Luna-produced ZIPs/releases, chat excerpts, local copies, and instructions in older roadmaps that nominate a historical “source checkpoint” have **zero source-code authority**. Those documents may inform functional requirements after current-code verification; they cannot override rule (1).
6. **No fabricated verification.** Distinguish `PLANNED`, `IMPLEMENTED`, `TESTED`, `CI_PASS`, `USER_ACCEPTED`, and `BLOCKED`. A file or test existing is not evidence of PASS. Link actual test run and commit IDs. Negative/adversarial tests, existing regressions, clean Git build, browser behavior and user Parrot acceptance are distinct gates.
7. **Preserve existing functions.** Never replace a functioning subsystem just because an old document describes something else. Additive, bounded changes to the current implementation are preferred. Don't make false physical topology or Engine truth inferences from source files, scans or documents.
8. **Release identity comes from current package and Git, not this document.** Never hard-code an old version, checkpoint, SHA or build base here. Release labels, provenance and checkpoint completion must be grounded in current GitHub metadata.

## Current project priority — AUDIT-007 BUG-FIRST / import on HOLD (owner decision 2026-11-01)

**MANDATORY ORDER: (1) whole-repository defect discovery, reproduction, repair and verified closeout; (2) only then resume DOCX/ODT and other document-import features; (3) only after approved import IC-110 may discretionary new OSPF/SPF be considered.** The owner explicitly superseded the former "finish import first / resume P1b after the four initial bug groups" recommendation. This order applies to **every** "fortsätt"/"continue" message without a new explicit owner instruction.

**Primary work tracker:** [AUDIT-007 issue #96](https://github.com/Northsw-spec/YadiLab/issues/96), [full-source bug-first masterplan](docs/architecture/AUDIT_007_BUG_FIRST_MASTERPLAN.md), [source-file inventory](docs/architecture/AUDIT_007_SOURCE_FILE_INVENTORY.tsv). [Import issue #3](https://github.com/Northsw-spec/YadiLab/issues/3) and [IMPORT-COMPLETE-001](docs/architecture/IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md) are **PAUSED**, not canceled; previously merged import functionality and regressions stay intact.

At the **start of each new YadiLab coding session**, and whenever the owner simply says "fortsätt":
1. Fetch the actual protected `main` SHA, tree, open PRs, prior exact-main release and logs; read **this AGENTS.md**, AUDIT-007 masterplan, current file inventory and issue #96. Use only current GitHub source, not old agent outputs.
2. Select the next **UNREVIEWED or open suspected/reproduced source finding** according to risk and dependency order. Scope each wave, inspect actual code, reproduce failure with fixed oracles and valid counterexamples **before changing production**. Avoid speculative fixes.
3. Fix every confirmed defect, including correctness, reliability, integrity, information disclosure, network truth, provenance, race, parser, CLI/launcher, CI and dependency failures, in bounded, independently verified PRs. **Do not silently defer minor confirmed bugs.** For mistaken hypotheses, record the evidence and mark FALSE_POSITIVE; for unverified candidates use SUSPECTED/UNKNOWN, not PASS.
4. Reconcile all tracked source/test/scripts/build/workflow/config entry paths against the latest Git tree and maintain explicit file-level review coverage. A passing existing test suite alone is NOT a file review. Every new/changed source path re-enters the audit as appropriate.
5. Require all exact PR-head checks and actual logs PASS, protected expected-head merge and independent exact-main Linux release (real Chromium + mounted identity + Linux and DOM evidence artifact IDs) before marking the respective fix RELEASE_VERIFIED. No manual Parrot acceptance unless a truly human/physical-only property is explicitly required.
6. Keep DOCX/ODT **new feature work frozen**, including IC-040 follow-ons, and do not start new discretionary OSPF/SPF until the separate audit closeout gate is met. Existing IC-040 P1a and P1b releases remain historical completed checkpoints, not permission to start the next import stage.

**Resumption gate:** all planned source-file review coverage explicitly completed on up-to-date main; every discovered credible finding resolved as REPRODUCED-and-fixed-with-test-and-independent-release or disproved with evidence; **zero known unresolved confirmed defects and zero untriaged credible suspicions**; cross-module and adverse real-browser/regression gates green; audit #96 has a complete owner-readable risk/coverage report and **explicit owner approval** to resume import. Never promise a mathematically bug-free program or treat absence of a reported bug as a clean audit. If coverage or tests cannot be completed, mark BLOCKED, keep import on hold, document why and seek an explicit revised decision.

Imported observations may never become fictitious physical links, live host state or Engine TRUE/PASS. GitHub-hosted Ubuntu CI suffices for reproducible automated checkpoints; do not invent Parrot or actual-network execution evidence.

## AUDIT-007 — complete source-defect review before any new feature (2026-11-01)

This is a **full scope owner priority**, not a temporary high-severity exception. Prior AUDIT-007 P1/P2a/P2b/P3 are historical verified repair waves, and IC-040 P1b was already independently release-verified. **Neither closes the rest of issue #96**. Any old instruction to immediately return to P1b after P3, or continue import while unreviewed source/bugs remain, is superseded by the above mandatory gate.

Coverage includes Engine/OSPF/NAT/ACL/DNS/DHCP and all simulated network truth; Compiler, Validator and canonical JSON/hash identity; Enterprise model/projection/import and every file format; Browser/Builder/Runtime and asynchronous file/workspace races; ZIP/package I/O and secrets; Go/Linux launcher/process handling; scripts, third-party dependencies, CI/workflows/release/provenance and security-relevant configuration. Review at **file/flow boundary level**, not just one run of tests or an approximate initial count of 719 files. Triage all credible findings; investigate all confirmed defects regardless of perceived severity. Freeze fail-closed counterexamples before source fixes, never weaken independent tests to obtain PASS, never merge on queued/failure/cancelled checks, never bypass protected main.

Maintain full evidence and remaining scope in [AUDIT-007 #96](https://github.com/Northsw-spec/YadiLab/issues/96). Keep [import issue #3](https://github.com/Northsw-spec/YadiLab/issues/3) explicitly ON_HOLD. The [full audit plan](docs/architecture/AUDIT_007_BUG_FIRST_MASTERPLAN.md) controls review waves, file inventory, defect ledger and release acceptance. Any risk acceptance/exclusion requires the **owner's explicit decision**; the assistant must not quietly mark a reproducible defect "accepted" to pass the audit. No new UI/document-import/OSPF work until owner approves the audit exit gate.

## YADILAB-CI-CONCURRENCY-001 — verified PR-supersession policy

**Permanent owner decision (2026-11-01). Status: CI_PASS / PROTECTED_MERGED / INDEPENDENT_RELEASE_VERIFIED.** The current `main` includes verified workflow-scoped PR cancellation. [PR #93](https://github.com/Northsw-spec/YadiLab/pull/93) passed **43/43** latest-head checks and protected squash-merged; its exact-main [independent Linux release #41267693694](https://github.com/Northsw-spec/YadiLab/actions/runs/41267693694) completed SUCCESS with actual compiled Chromium, mounted DOM identity and Linux artifacts. A controlled second commit cancelled **42 obsolete PR check-runs**, while the replacement head passed independently. This evidence applies to that exact delivery, not to future commits.

**Mandatory enduring rules:**
1. Use top-level `concurrency` and `cancel-in-progress` to cancel only older unfinished runs superseded by newer commits to the **same PR and same workflow**. Group identity must isolate other PRs and workflows; cancellation is PR-only.
2. Never automatically cancel or suppress protected `main`, Linux/postmerge/tagged releases, or independent manual/dispatch evidence. The required `yadilab-required-ci` branch-protection check remains mandatory; never bypass it.
3. Preserve full pinned `playwright install --with-deps chromium`, Engine, import, negative security, package, AUDIT-006 and provenance tests. CANCELLED is not PASS. The latest PR head must independently complete all required checks before a protected merge.
4. Every future workflow expansion or change must update and rerun `tests/ci/run_pr_concurrency_contract_tests.mjs`, then verify exact PR-head tests and an independent release. Preserve actual run/commit/artifact evidence in issue #3. GitHub-hosted Ubuntu CI is sufficient for automated work; no routine manual Parrot tests.

**Frozen original policy oracles:** [YADILAB_CI_CONCURRENCY_001_FROZEN_ORACLES.md](docs/architecture/YADILAB_CI_CONCURRENCY_001_FROZEN_ORACLES.md).

## Mandatory checkpoint handoff

Record the current `main` SHA at start; branch/PR URL; scope and source paths; tests with actual PASS/FAIL/NOT_RUN; CI run URL; risk or unverified items; final code commit SHA; whether `main` includes it. Do not announce delivery as finished if any code exists only in a temporary environment. Do not mix Google Drive document upload with GitHub code delivery.

**Short rule:** GitHub = code and commits. Google Drive = research/plan documents. Temporary environments = never the only copy of a code change.

## CI-first acceptance policy (user-approved 2026-10-28)

1. **Actual GitHub Actions SUCCESS on the exact checked commit is sufficient verification to continue coding checkpoints.** The project owner does not need to repeat equivalent tests manually on Parrot.
2. Never fabricate coverage: record exactly which features and host environments were exercised. Ubuntu CI can prove only its tested behaviors; it is not evidence of target-native Parrot functionality.
3. Request human involvement **only** when a feature genuinely needs subjective visual/usability feedback, live user-only access, physical peripherals/hardware, or another property impossible to test credibly in CI. Explain the concrete reason before asking.
4. Do not block normal code development or merging solely because optional Parrot user acceptance was not run. Maintain and improve automated real-browser CI, negative security oracles, source/commit identity, and release integrity checks.
5. This user-approved principle supersedes earlier *procedural* Parrot-manual-check gating language in historical plans; it does not weaken security tests or turn NOT_RUN into PASS.

