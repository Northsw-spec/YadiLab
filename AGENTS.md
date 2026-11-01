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

## Current project priority — FUNCTIONAL TOPOLOGY FIDELITY / RELEASE BLOCKERS FIRST (owner decision 2026-11-01)

**Binding new direction:** prioritize actual YadiLab defects: broken Linux releases or CI, incorrect/missing/extra imported devices, links, interfaces or ports, wrong visual Builder graph, unreliable app operation, false PASS/TRUE, unreliable modeled probes, data loss or workspace races. Hacker threat models and hypothetical vulnerabilities are **not the primary workstream**. Existing security and provenance regression gates remain mandatory and may not be weakened. The previous whole-repository security-audit-before-any-DOCX/ODT-import hold is superseded by this owner's later instruction.

**Highest product requirement:** Import a real network topology document and preserve **exactly source-supported node IDs, roles, endpoints and connections**, all the way through preview → mapping → compiled Builder → displayed graph. Router, firewall, switch, server, Windows/Linux PC and virtualization device classification must be grounded in explicit declarations or review. No missing edges, extra edges, duplicate nodes, invented ports, false PASS or fabricated physical connectivity. Lack of link evidence, ambiguous topology or unsupported document semantics MUST be shown as incomplete/needs review, **not** filled by guessing from IP, gateway, proximity or hostnames.

**Important honest current limit:** Existing structured CSV/TSV/XLSX/ODS/JSON mapping supports explicit `Connected To`/Links. GraphML/diagrams.net supports reviewed candidates. **Current DOCX/ODT IC-040 P1a/P1b supports only reviewed nodes, not document edges/interfaces.** Do not claim connected Office topology is supported until actual source-grounded mapping, real compilation and rendered graph parity tests pass. The owner authorizes these narrowly necessary import-function fixes/completion steps immediately instead of waiting for all ~1,446 tracked files to be reviewed.

**Default 'fortsätt' work order:** fix proven functional false-PASS and source-to-graph mismatch bugs first; verify exact all node/link/port identities in actual Builder and real Chromium; then finish specific, reviewed DOCX/ODT link mapping needed for truthful visualization; continue all other operational bug fixes. Track confirmed bugs in [AUDIT-007 issue #96](https://github.com/Northsw-spec/YadiLab/issues/96) and import feature gaps in [issue #3](https://github.com/Northsw-spec/YadiLab/issues/3). Read the [functional-first masterplan](docs/architecture/TOPOLOGY_FIDELITY_FUNCTIONAL_FIRST.md) before every coding stage.

**Evidence gates unchanged:** current protected main and actual source, frozen negative+positive oracles before production changes, exact PR-head Actions checks/logs all SUCCESS, expected-head protected merge, independent exact-main Linux release with mounted Chromium and two nonexpired artifact IDs. GitHub-hosted Ubuntu CI suffices for automated gates. Never claim an unverified visual graph, physical topology, or whole-source clean bill of health.

## AUDIT-007 — actual operational defect backlog, not an import blockade

The full source-file audit remains OPEN and its tracked inventory remains honest, but it no longer prevents bounded functional document-topology completion. Preserve verified P1–P7 repairs and existing security tests, investigate any confirmed bug regardless of severity, and prioritize wrong topology/false green/release blockers before speculative attacker risk. An unreviewed path never equals PASS.

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

