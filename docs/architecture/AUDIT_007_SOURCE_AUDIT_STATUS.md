# AUDIT-007 — verified YadiLab source audit: historical milestones and current priorities

**Scope:** Persistent audit handoff for all future coding conversations. [Issue #96](https://github.com/Northsw-spec/YadiLab/issues/96) remains the live findings/checkpoint tracker; [AGENTS.md](../../AGENTS.md) is the mandatory workflow policy. This document distinguishes *historical as-of snapshots* from current checks. No blanket certification of YadiLab source code is claimed.

## 1. Audit baseline and method

At the initial audit start on **2026-11-01**, IC-040 P1a [PR #95](https://github.com/Northsw-spec/YadiLab/pull/95) had protected squash-merged into `35b05d51c7ce0e15fced925e0b30a47c8f2e0fb5`. Independent exact-main [Linux release #41272058035](https://github.com/Northsw-spec/YadiLab/actions/runs/41272058035) was SUCCESS, including actual mounted Chromium release identity and unexpired package/DOM evidence. No open PRs at that historical starting point.

The initial recursive repository inventory contained **1,522 tree entries**, around **719 plausible source/test code file paths** by a first-pass filename filter. Neither figure equals files *fully reviewed*. Focus first on security, Engine false-positive network truth, import source provenance, JSON integrity, unsafe file parsing and tests/CI provenance. Never attribute a specific bug to “Luna” or another author without reliable history.

Evidence states: `UNREVIEWED → SOURCE_GROUNDED → REPRODUCED → PATCHED_IN_PR → CI_PASS → MERGED → INDEPENDENT_RELEASE_VERIFIED`. Freeze a reproducible negative oracle before editing relevant production files. Never treat a passing subset or historical log as certification of unreviewed modules. Protected main, actual job logs, negative regressions and artifacts are authoritative.

## 2. Historical issues and delivery milestones (2026-11-01)

The checkpoints below *supersede earlier provisional in-progress statements* such as “3/4 PR checks”, “P1 release is still running”, and “PR #99 not yet merged”. Those statements were accurate at their own earlier moments only.

| Wave | Source issue and fix | Protected merged main | Independent exact-main release | New focused assertions |
| --- | --- | --- | --- | --- |
| P1 [#97](https://github.com/Northsw-spec/YadiLab/pull/97) | `engine/src/ip.ts`: rejected malformed IPv6 hextets, ambiguous leading-zero IPv4 and empty CIDR `/` widening to `/0`; `engine/src/json.ts`: retained own JSON `__proto__` safely during deep clone | `33f263c22238646916b314066aa67d79e57e47a8` | [#41273228061](https://github.com/Northsw-spec/YadiLab/actions/runs/41273228061) SUCCESS; Linux artifact `13070247873`, DOM artifact `13070158364` | 91 |
| P2a [#98](https://github.com/Northsw-spec/YadiLab/pull/98) | `compiler/src/canonical-json.ts`, `enterprise-model/src/canonical.ts`, `compiler/src/helpers.ts`: distinct own-key JSON can no longer canonicalize/hash-collide by dropping `__proto__`; safe clone/merge without inherited authority | `31a53931cf49332ebb1eca59902e07881c629850` | [#41273893456](https://github.com/Northsw-spec/YadiLab/actions/runs/41273893456) SUCCESS; Linux artifact `13071050710`, DOM artifact `13071225381` | 39 |
| P2b [#99](https://github.com/Northsw-spec/YadiLab/pull/99) | CSV/TSV/JSON and XLSX/ODS shared table-field dictionaries preserve special literal field names and original locators; reject malformed quoted-field suffixes | `e222a2154c1fcebd2084f03a421abc8dbce45759` | [#41276876077](https://github.com/Northsw-spec/YadiLab/actions/runs/41276876077) SUCCESS; Linux artifact `13071656776`, DOM artifact `13071068940` | 137 |

All listed artifact IDs were independently read back from GitHub and reported **expired=false** with expiry **2027-01-30** at the recorded inspection. The P2b actual job log at main `e222a2154c1fcebd2084f03a421abc8dbce45759` confirms P2b 137, P2a 39, P1 91, IC-040 P1a 278 source-only, real compiled Chromium, mounted DOM identity and AUDIT-006. These results apply to the stated commits, not any future branch.

### Historical P2b first-head test failure (not a production-acceptance failure)

At P2b initial head, required CI failed because a new test expected `IMPORT_MALFORMED_QUOTE` for input `"alpha""tail`. In CSV this is an escaped quote with a missing final closing quote, so `IMPORT_UNCLOSED_QUOTE` was the correct denial. The test was narrowly repaired; a genuinely terminated quote followed by unquoted junk `"alpha""tail"junk` was separately tested as `IMPORT_MALFORMED_QUOTE`. The negative fail-closed cases were preserved. Latest final P2b head later passed 4/4 PR checks and independently passed postmerge release.

### Integrity limits

A collision in canonical JSON and unsafe `__proto__` data handling are source-provenance/integrity bugs. They were **not** evidence of bypassing all release protection, branch protection or arbitrary code execution. XLSX/ODS coverage in the *new P2b suite* exercises the shared physical-row mapper; the new suite did not generate ZIP fixtures for both formats, although existing independent ZIP regressions were left intact.

## 3. Superseding owner direction — FULL-REPOSITORY BUG-FIRST, import PAUSED (2026-11-01)

The earlier instruction in this section, "P3 then IC-040 P1b", is now **historical**, not the current recommendation. P3 was later independently release-verified ([PR #100](https://github.com/Northsw-spec/YadiLab/pull/100), merged `f800cc64ba912f40e841fb38b3cc66b6635c501f`). IC-040 P1b was subsequently implemented and independently verified ([PR #101](https://github.com/Northsw-spec/YadiLab/pull/101), exact-main Linux [release #41313177977](https://github.com/Northsw-spec/YadiLab/actions/runs/41313177977), main `b835d66193a4bd9d27fbbf5e79e485674c244769`, Linux artifact `13086253792`, DOM artifact `13086482668`). These milestones do **not** imply the remaining source is free of defects.

**NEW binding direction:** Finish the **entire** AUDIT-007 source audit and correct **every reproduced source defect** before adding ANY further DOCX/ODT/import feature. No exception merely because only high-risk defects were initially targeted. The source baseline contains more tracked code paths than the initial approximately 719 heuristic; see the [complete tracked-file inventory](AUDIT_007_SOURCE_FILE_INVENTORY.tsv) and [file-level audit masterplan](AUDIT_007_BUG_FIRST_MASTERPLAN.md). Audit areas include all Engine/Compiler/Validator/Enterprise/Builder/Runtime/import adapters/ZIP/dependency/launcher/workflow/security relevant code and configuration.

Required file-level coverage, issue-based suspected→reproduced→test-frozen→fixed→CI→independent-release verification, and explicit zero-known-unresolved-defect plus owner-approval exit gate are defined in [AGENTS.md](../../AGENTS.md) and [AUDIT-007 bug-first masterplan](AUDIT_007_BUG_FIRST_MASTERPLAN.md). Never imply a guarantee that no unknown defects exist. Keep [AUDIT-007 issue #96](https://github.com/Northsw-spec/YadiLab/issues/96) ACTIVE and [import issue #3](https://github.com/Northsw-spec/YadiLab/issues/3) PAUSED until the actual source audit is complete.

## 4. Permanent handoff / checkpoints

At every handoff: fetch fresh protected `main` and open PRs; reread [AGENTS.md](../../AGENTS.md), [import masterplan](IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md), issue #96 and issue #3. Record exact main SHA/tree, last frozen-oracle commit, PR head, all check-run status and real job logs, no removed negative tests, expected-head merge, independent postmerge release SHA, mounted DOM proof and two unexpired artifact IDs. Track unknown/reproduced/fixed bugs distinctly. Use Ubuntu GitHub Actions; no routine manual Parrot tests. Do not add status-only source commits after release.

The original user-supplied audit narrative is retained here as a chronological record, updated with the final outcomes that superseded its intermediate statuses.
