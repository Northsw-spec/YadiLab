# YadiLab — current project index

**Authority:** [GitHub `main`](https://github.com/Northsw-spec/YadiLab/tree/main) is the only canonical source. `package.json` is the current version/checkpoint source, and `AGENTS.md` is the operating rule. Do not use historical ZIPs, old README headings, Drive documents or previous conversation summaries as code authority.

## Current software/release verification

- Follow the latest `.github/workflows/release-identity.yml` run for **exact current main SHA**; its SUCCESS proves only the tested Ubuntu environment and packaged Linux artifact. Required gate: Git-indexed copied/bundled assets; clean tracked source; locked dependencies; compiled source/marker hashes; **actual Chromium visible version, checkpoint, full source-commit DOM identity and an interactive menu**; rejection of a token-only JS bundle.
- Unit/adversarial `npm run test:release-identity` and `tests/acceptance/run_release_identity_real_browser.py` are independent evidence layers. A string `js.includes` or manifest identity alone never proves a mounted React UI.
- The installed GitHub connector can code, commit, open PR, read checks and merge after verified tests; it **cannot change repository branch protection**. Do not describe `main` as protected until a separate GitHub readback confirms it.

## GitHub issues, not automatically equivalent to bugs

- [#1 AUDIT-006](https://github.com/Northsw-spec/YadiLab/issues/1): original provenance defects plus remaining Masterprompt/CLI scope. Track both fixes and unresolved backlog separately.
- [#2 CONVERGENCE-PREP](https://github.com/Northsw-spec/YadiLab/issues/2): research/planning of simulation time, OSPF and reconvergence; not a proven defect.
- [#3 IMPORT-FORMATS-RESEARCH](https://github.com/Northsw-spec/YadiLab/issues/3): original research and continuous checkpoint journal. Nmap, Nessus, Ansible, draw.io, DOCX and ODT work is logged in comments. Broad importer registry is not automatically equivalent to every format adapter being supported.
- Historical failed GitHub Actions runs represent intermediate development attempts; they are **not** current CI PASS, nor evidence of present failure if corrected before merge.

## Required branch protection (repository owner action)

GitHub reported `main.protected=false` and returned 403 for private-repository rulesets: `Upgrade to GitHub Pro or make this repository public`. **Do not change repository visibility simply to obtain branch rules.** With a plan supporting private-repository branch protection, in GitHub open `Settings → Branches → Add branch protection rule` (or `Settings → Rules → Rulesets`) for `main`, require PR before merge, require status checks matching the current release/build gates, require branch up to date, block force-push/deletion and restrict bypass. Add reviewed required jobs only after confirming their exact stable check names. Then independently read back protection and verify a direct push is rejected. Until then, PR-before-merge and exact-head CI review are process controls, **not GitHub-enforced controls**.

## Documentation and history

The top README gives only dynamic source authority; its older extensive phase notes remain explicitly historical. Code-level plans and security oracles live in `docs/architecture/`. Research documents may be on Drive/Library; do not claim they have all been copied into GitHub or that research snapshots are source code. Commit concise architecture decisions or verified findings to this repository before relying on them for future work.

## Handoff for a new conversation

Fetch current `main`, tree SHA, open PRs, latest required CI and release run, the root `AGENTS.md`, `package.json`, and relevant `docs/architecture` PREP. Read source/tests directly, branch from exact fresh main, and document actual PASS/FAIL/NOT_RUN, artifact provenance and PR/head SHA; never assume historical versions or CI outcomes remain current.
