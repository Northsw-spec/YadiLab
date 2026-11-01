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

## Active import-completion priority — mandatory for future conversations

**Current owner-approved development order:** Finish YadiLab's scoped multi-format network-document import and visualization workflow **before starting discretionary new OSPF/SPF/convergence features**. The canonical active execution plan is [IMPORT-COMPLETE-001](docs/architecture/IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md), tracked in [GitHub issue #3](https://github.com/Northsw-spec/YadiLab/issues/3). This is an implementation priority and acceptance contract, not evidence that every planned format already works.

At the **start of every new YadiLab coding session**, and whenever the owner says "continue"/"fortsätt" without changing scope:
1. Fetch **current protected main**, branch/tree SHA, `package.json`, applicable checks, the actual relevant source/tests and open PRs.
2. Read **this AGENTS.md**, the active import masterplan and issue #3 before choosing work. Select the **first unfinished import checkpoint** based on current source and actual CI evidence, not a historical ZIP, chat memory, README, plan-status labels or old PREP documents.
3. Implement small, separately evidenced import PRs using source-bound review, negative/security tests, actual browser and current release verification. Record checkpoint/CI/merge/release evidence and remaining work in issue #3.
4. Preserve already implemented OSPF/SPF code, existing import adapters, Engine truth and mandatory regressions. Do not opportunistically start new OSPF/SPF milestones until the import plan's **IC-110 closeout** is verified and approved, or the owner explicitly changes priority. Security/CI/release-critical repairs are permitted exceptions; note them in issue #3.

A document parser or planned registry entry never equals full import, network visualization or probe support. Imported scans, reports and observations must never be converted into fabricated physical links, current service state or Engine PASS/TRUE. Ubuntu GitHub Actions remains sufficient for automated checkpoints; do not invent native Parrot or actual-network test evidence.

Updates to this active priority or its acceptance criteria must be made by reviewed, documented GitHub changes and reflected in issue #3. Root AGENTS controls developer workflow; the plan controls import sequence and semantic scope. Neither overrides fresh current main code as source authority.

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

