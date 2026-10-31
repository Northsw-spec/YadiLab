# IC-020 P2c6 — scoped five-format exit audit and handoff

**Audited starting authority:** protected `main=8e43ee8341b1def9bea00ea75726889a592ce4b0` / tree `b04a3d49f28fdf5da730088bc4c31ecc37168fb2`, no open PRs, 2026-10-31. [P2c5 independent Linux release 41237691702](https://github.com/Northsw-spec/YadiLab/actions/runs/41237691702) completed SUCCESS on exact prior main. P2c5 release job log verified **293** independent source assertions plus real compiled Chromium all-five imported `FALSE/UNKNOWN` and contradictory-facts deny. Prior P1–P2c4 regression and AUDIT-006 mounted Chromium identity also PASS. [Frozen P2c6 acceptance](IC_020_P2C6_SCOPED_EXIT_ORACLES.md), [live versioned matrix](import-capability-matrix.v1.json), [masterplan](IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md), [issue #3](https://github.com/Northsw-spec/YadiLab/issues/3).

**Provisional scoped conclusion:** The audited *five-active-format* IC-020 functionality is evidenced, subject to this P2c6 PR's exact-head CI and a new completed-success postmerge independent Linux release. Those verification events must be recorded in issue #3 **after** they actually occur; this text does not pre-certify unrun checks. No production importer, parser, UI, Engine, runtime or dependency change was required for this audit PR.

## Required IC-020 gate evidence

| Requirement | Direct source/test evidence | Verdict for tested scope |
| --- | --- | --- |
| Five supported input choices / actual file picker, full original SHA-256 | `tests/browser/run_ic020_p1_core_source_freshness_tests.mjs`, `tests/acceptance/run_ic020_p1_core_inventory_real_browser.py` | **PASS_SCOPED** for JSON/CSV/TSV/XLSX/ODS |
| Explicit identities, roles, declared interfaces and links only | `enterprise-import/src/network-inventory.ts`, `workbook-mapping.ts`, P1 tests, P2c2 8-device/6-explicit-link six-sheet XLSX/ODS oracles | **PASS_SCOPED**; no network adjacency from IP/default gateway |
| Manual competing explicit link-source selection, no silent merge | `run_ic020_p2a_dual_link_review_tests.mjs` and `run_ic020_p2a_link_review_real_browser.py` | **PASS_SCOPED** for declared P2a variants |
| Re-import live diff and explicit replacement consent; no mutation on cancel | `run_ic020_p2b_reimport_review_tests.mjs` and `run_ic020_p2b_reimport_real_browser.py` | **PASS_SCOPED** |
| Saved read-only replay without automatic import approval | `run_ic020_p2c1_saved_report_replay_tests.mjs` and `run_ic020_p2c1_saved_report_real_browser.py` | **PASS_SCOPED** |
| Strict canonical six-sheet XLSX/ODS port/interface enforcement | `run_ic020_p2c2_multisheet_tests.mjs` and `run_ic020_p2c2_multisheet_real_browser.py` | **PASS_SCOPED** on canonical six-sheet fixtures |
| Competing inventory tables block; unmapped columns count w/o sensitive values | `run_ic020_p2c3_unmapped_inventory_tests.mjs` and `run_ic020_p2c3_unmapped_real_browser.py` | **PASS_SCOPED** for tested privacy/ambiguity variants |
| Source-specific IP/CIDR/prefix contradiction, ambiguous aliases, duplicate IDs | `run_ic020_p2c5_truth_tests.mjs` and `run_ic020_p2c5_truth_real_browser.py` | **PASS_SCOPED** for flat Devices JSON/CSV/TSV/XLSX/ODS |
| Imported Windows/Linux actual modeled Runtime with negative/unknown truth | P2c5 imported five-format full bytes, actual compiled Chromium `verdict FALSE` off-link ICMP, `verdict UNKNOWN` absent DNS, runtime scenario hash and no guest command, P2c5 source 293 | **PASS_SCOPED** on flat Devices variants |
| Explicit consent, stale original source/review denial, Builder unaffected by failed import | P1/P2a/P2b/P2c1/P2c5 actual source and Chromium tested workflows, SHA re-read `verifyNetworkTopologyOriginalForActivation` | **PASS_SCOPED** |
| Deterministic actual compiled Chromium end-to-end and release provenance | P1–P2c5 acceptance scripts in required CI and independent main release; AUDIT-006 actual mounted DOM code identity | **PASS_SCOPED** on previous exact-main P2c5 release, P2c6 rerun pending at initial authoring |

### Non-claims / exact coverage limit

- This **does not certify all 27 matrix profiles**. There are five active enterprise network adapters, one distinct native scenario JSON route, and 21 non-active planned/specialized hints. IC-030/040/050/... remain separate import plan work. Eight specialized source-only workflows are not magically active network converters.
- Real Chromium **flat Devices** imported Windows/Linux `FALSE`/`UNKNOWN` evidence applies to **each of the five** formats. Separate **canonical six-sheet** XLSX and ODS typed ports are tested; **only ODS** has specifically attested canonical six-sheet real Chromium modeled Runtime **interaction**, without required precise negative/unknown verdict. Canonical six-sheet XLSX/ODS negative/unknown Chromium verdicts are **NOT_ATTESTED for that separate subtype**.
- `FALSE` for off-link ping with no modeled route and `UNKNOWN` for DNS with no resolver are **Engine outcomes from particular declared fixture states**, not claims about all unavailable destinations or universal behavior. These probes do not send packets or run Windows/Linux commands.
- **Native Parrot, live/physical devices, arbitrary enterprise documents, security posture from scans, arbitrary unknown document semantics:** `NOT_RUN`/`NOT_ATTESTED`. Imported data never proves real-time reachability or physical adjacency.
- Original IC-000 `auditBaseline` and P2c4 `ic020Refresh` historical `NOT_ATTESTED` snapshots are **deliberately kept** to avoid falsifying the chronology. Separate `ic020CurrentEvidence` and `auditRefreshP2c6` are current source-backed views, not a retroactive change to past tests.

## Decision and next milestone

Once `test:ic020-p2c6-exit` and existing P1–P2c5 source and actual browser acceptance have run **SUCCESS** on the exact P2c6 PR-head, followed by protected merge and independent completed-success Linux release on exact new main, mark **IC-020 SCOPED COMPLETE** in issue #3; continue with **IC-030 GraphML and diagrams.net** from that *then-current* main and frozen IC-030 oracles. Overall `IMPORT-COMPLETE-001` issue #3 stays OPEN until IC-110 and owner acceptance. If any actual P2c6 check fails or new directly relevant requirement is unverified, leave IC-020 OPEN and fix rather than claiming the exit.

This PR is metadata, historical preservation, documentation and negative source-oracle maintenance only. No external guest execution, dependency/version bump or manual Parrot test.
