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

## Mandatory checkpoint handoff

Record the current `main` SHA at start; branch/PR URL; scope and source paths; tests with actual PASS/FAIL/NOT_RUN; CI run URL; risk or unverified items; final code commit SHA; whether `main` includes it. Do not announce delivery as finished if any code exists only in a temporary environment. Do not mix Google Drive document upload with GitHub code delivery.

**Short rule:** GitHub = code and commits. Google Drive = research/plan documents. Temporary environments = never the only copy of a code change.
