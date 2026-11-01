# AUDIT-007 — FULL CODEBASE BUG-FIRST MASTERPLAN (owner mandatory)

**Status:** OPEN SOURCE DEFECT BACKLOG; operational topology/release correctness now outranks hypothetical security risk (owner 2026-11-01). Follow [functional-first masterplan](TOPOLOGY_FIDELITY_FUNCTIONAL_FIRST.md).
**Superseding priority:** Wrong documented nodes/links, missing/extra connections, false PASS, graph rendering mismatches and broken releases first. Maintain old safety regressions, but no speculative hacker-centric side quest. Necessary reviewed DOCX/ODT topology features are allowed now; old blanket import freeze below is historical wherever contradictory. This file does not certify all source files reviewed.
**Authority:** Current protected main, root [AGENTS.md](../../AGENTS.md), [functional-first plan](TOPOLOGY_FIDELITY_FUNCTIONAL_FIRST.md), issues #96/#3 and this remaining full-code audit backlog.
**Baseline of this decision only:** `main=b835d66193a4bd9d27fbbf5e79e485674c244769`, tree `915416e3c04ec1af2d800315f16766178ea303f6`, independent exact-main [Linux release #41313177977](https://github.com/Northsw-spec/YadiLab/actions/runs/41313177977) SUCCESS, Linux artifact `13086253792`, DOM artifact `13086482668`. These are historical start references, **not** pinned future code bases.

## 1. Meaning of ALL bugs

The goal is to **find, document, reproduce and fix every identifiable defect in the whole current codebase**, not only high-severity ones and not only known failures in Engine, JSON, or DOCX/ODT. Every defensible bug report must receive evidence-based triage. Fix verified defects even when minor; preserve valid counterexamples. All credible suspicions must be resolved through reproduction or documented disproof before the audit can close. Never use a passing CI suite to declare unknown parts of the code bug-free.

No finite review can logically guarantee the absence of every unknown bug. The measurable outcome is **complete documented file-level review coverage, no known outstanding confirmed defects, no unresolved credible suspicions, source-bound negative regression evidence, protected merge and exact-main independent releases, with explicit owner acceptance**. There is no silent severity-based escape hatch or unapproved 'accepted risk' classification.

## 2. Scope and inventory discipline

The [tracked-file audit register](AUDIT_007_SOURCE_FILE_INVENTORY.tsv) catalogs **the entire Git tree's files, not merely a selective 719-path estimate**. Initial status is `UNREVIEWED` for each tracked path; inventory inclusion is NOT code review. Source/test scripts, workflows, build configs, Go and TypeScript/JavaScript modules, CI, launchers, package data/fixtures, user-facing HTML/CSS, and security-significant documents must be considered. Modules that do not contain executable code may receive a documented `NOT_APPLICABLE` disposition **only after a substantive relevance check**. No glob-based silent exclusion; review dependency boundaries as well as individual files.

At every revision checkpoint, compare the active protected `main` recursive tree against the inventory. Newly added/changed paths return to `UNREVIEWED` or `RE_REVIEW_REQUIRED`; deleted paths are tombstoned with evidence; renamed paths are independently reviewed. Record each exact path, blob SHA, reviewer method, dependent modules, cases tested, findings/issue IDs, last reviewed main SHA and disposition. Do not label files `REVIEWED` purely because a test or workflow passed.

Maintain an issue ledger in [#96](https://github.com/Northsw-spec/YadiLab/issues/96) linked to path/line, reproduction with expected versus actual, severity and security/network impact, frozen first-oracle commit, valid counterexamples, PR head, required check logs, protected merged main SHA, Linux release run, DOM identity and artifact IDs. Finding states: `UNREVIEWED`, `SUSPECTED`, `REPRODUCED`, `ORACLE_FROZEN`, `PATCHED_IN_PR`, `CI_PASS`, `PROTECTED_MERGED`, `INDEPENDENT_RELEASE_VERIFIED`, `DISPROVED_WITH_EVIDENCE`, `BLOCKED`. The label `DISPROVED` requires a concrete test or source proof, not dismissal.

## 3. Comprehensive review waves (risk first, all files eventually)

1. **Integrity, trust and source provenance:** JSON/CSV/TSV/XLSX/ODS special keys, canonical hashing, signatures/release provenance, object inheritance/prototype handling, external/untrusted data boundaries and verified private-data non-leakage. Previously fixed AUDIT-007 P1/P2a/P2b/P3 are a baseline, not permission to skip remaining callers.
2. **Engine network correctness:** IPv4/IPv6/CIDR, routing, ACL/firewall, NAT, DNS, DHCP, ARP/VLAN/L2, MTU, TCP/UDP, OSPF/SPF, topology transformations, negative proofs and UNKNOWN vs true/false/green PASS; check cross-module semantics, malformed inputs, overflows and modeling accuracy.
3. **UI, Builder, Runtime and state races:** actual browser DOM/input escapes, source/consent revocation, stale asynchronous file and workspace states, imports, compile/layout transitions, persistence/export, package identity, runtime truth, reimport and race gates.
4. **ALL structured import formats and evidence pipelines:** DOCX/ODT/ZIP/XML, Excel/ODS, CSV/TSV/JSON, GraphML, diagrams.net, Nessus/Nmap, Ansible/YAML, and every supported or partially supported converter, validator, reporter/replay or association. Distinguish a *security defect repair* from new import functionality; repairs proceed, feature expansion stays frozen.
5. **Compiler/Validator/enterprise integration:** canonical schema and derived facts, Builder projections, capabilities, scenario validation, deep copy/merge, layouts, rendered graph, dataflow/probe eligibility, certification, fixtures and generated contracts.
6. **Linux/Go launcher, package I/O and distribution:** path traversal, file and process lifecycle, local HTTP security, ZIP/archive budgets, build inputs, hashes, startup/shutdown/reboot semantics and packaging.
7. **Supply chain and CI:** pinned dependencies/licences, GitHub Actions/workflow concurrency, branch protection and status gates, exact commit/source-to-UI release identity, mirrored Ubuntu APT, Chromium test completeness and artifact lifetime.
8. **Integration and audit closeout:** re-run every preserved source and adversarial regression, compiled real Chromium, independent Linux release, controlled negative examples and cross-module test matrices; reconcile source-file ledger and issues on current `main`.

Waves are a priority order, not a completeness waiver: repeat/expand when findings cross boundaries. All source files must eventually be reviewed, including lower-risk utility code.

## 4. Per-defect fail-closed workflow

1. Obtain current protected `main` and identify an exact source path and suspected behavior; never reconstruct from old chat or release ZIPs.
2. Reproduce with a minimal executable **negative regression** and an unaffected positive counterexample. Freeze the independent tests/oracles in a *first* new PR branch commit; classify inability to reproduce as SUSPECTED, not FIXED.
3. Modify only what the evidence justifies. Keep the rest of Engine/Dev11/import/security/AUDIT-006/Chromium regression tests intact. Do not weaken correct oracles to fabricate a PASS; a test assumption demonstrably wrong may be corrected with a separate, recorded rationale and retest.
4. Read every current PR-head check-run and the actual relevant Actions job logs. On `queued`, `in_progress`, `failure`, `cancelled` or `skipped`, do NOT merge; investigate evidence and correct within the same bounded PR if safe. Read current main again before any merge.
5. Squash merge with `expected_head_sha` only after all exact-head checks are `COMPLETED/SUCCESS` and main is reconciled. No branch-protection bypass.
6. Independently verify exact merged main Linux `push` release, real mounted Chromium DOM identity/source matching, negative security and each new regression, plus two non-expired Linux/DOM evidence artifact IDs. Record all IDs/SHAs and residual risks in #96; link paused import issue #3.
7. Audit remaining dependency callers and files. A fixed input parser does not prove that every consumer treats UNKNOWN correctly.

GitHub-hosted Ubuntu Actions is the accepted automation environment. No routine manual Parrot tests, external network probes or invented runtime/network attestation.

## 5. Current functional acceptance — superseding earlier import hold

Directly fix real operational bugs and reviewed document-topology gaps without waiting for all tracked code paths to pass security audit. Full-source audit remains OPEN, never declared finished by a few passing tests. For source-declared links require exact edge set equality from source → Builder → compiled model → rendered graph; no invented physical cables or automatic green objective. Retain Engine/Dev11/old negative tests, exact PR-head CI and independent Linux+DOM release evidence. Highest next task: concrete false topology/false PASS/release blocker, not hypothetical exploit research.
