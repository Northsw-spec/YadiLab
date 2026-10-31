# IC-020 P2c4 — source-grounded capability reconciliation and exit-gate audit

**Checkpoint:** evidence/documentation/CI oracle only. **Result:** `IC-020 PARTIAL — NOT READY FOR IC-030`. No new importer, Engine behavior, parser, activated profile or externally directed network probe has been added. See [frozen tests](IC_020_P2C4_CAPABILITY_AND_EXIT_AUDIT_ORACLES.md), [capability matrix](import-capability-matrix.v1.json), [execution masterplan](IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md) and [issue #3](https://github.com/Northsw-spec/YadiLab/issues/3).

## Exact source authority

Starting protected `main`: `3c2d00d73c1204827c12be276b9d15855aadbd7f` / tree `25ab69f011f86dd22c4528b79846a8592f0e43e3` at 2026-10-31, 0 open PRs. Prior independent [Linux release 41234186594](https://github.com/Northsw-spec/YadiLab/actions/runs/41234186594) completed **success** on exactly that starting main. This is **historical previous-checkpoint** verification; new P2c4 PR and postmerge release status require independent confirmation before any P2c4 CI_PASS or RELEASE_VERIFIED label.

Production sources: `enterprise-import/src/adapters.ts`, `network-inventory.ts`, `workbook-mapping.ts`, `ui/src/browser/network-topology-import.ts`, `ui/src/browser/observations.ts`, `ui/app/main.mjs`. Executed CI contract: `.github/workflows/required-ci.yml` and `.github/workflows/release-identity.yml`.

## Five active sources — actual capability boundary

| Profile | Source-bound candidate and Builder | Source/Engine modeled Runtime | Imported-source real Chromium modeled Runtime | Remaining |
| --- | --- | --- | --- | --- |
| `builtin.json` | P1, P2a/P2b/P2c1/P2c3 source and browser regression; does **not** accept arbitrary JSON | Source-path modeled Runtime tested, not live hosts | **NOT_ATTESTED for this subtype** | Imported FALSE/UNKNOWN visible UI; contradictory typed facts |
| `builtin.csv` | P1/P2a–P2c3, explicit declared connections | Source-path Engine modeled probes | **ATTESTED: P1 CSV** | Imported FALSE/UNKNOWN visible UI; contradictory typed facts |
| `builtin.tsv` | P1/P2a–P2c3 source and browser ingestion | Source-path modeled Runtime tested | **NOT_ATTESTED for this subtype** | Imported FALSE/UNKNOWN visible UI; contradictory typed facts |
| `builtin.xlsx` | P1/P2a–P2c3; P2c2 real six-sheet typed interface/port negatives | P2c2 source-path Engine modeled probes | **NOT_ATTESTED for this subtype** | Imported FALSE/UNKNOWN visible UI; contradictory typed facts |
| `builtin.ods` | P1/P2a–P2c3; P2c2 real six-sheet typed interface/port negatives | P2c2 source-path Engine modeled probes | **ATTESTED: P2c2 ODS** | Imported FALSE/UNKNOWN visible UI; contradictory typed facts |

`tests/acceptance/run_ic020_p1_core_inventory_real_browser.py` selects all five formats and demonstrates Builder; its separate **CSV** case opens Runtime and invokes a modeled probe. `tests/acceptance/run_ic020_p2c2_multisheet_real_browser.py` demonstrates real multi-tab XLSX/ODS Builder, rejects unlisted/doubled interfaces and missing ports, and opens modeled Runtime and invokes a probe for **ODS**. `tests/browser/run_ic020_p2c2_multisheet_tests.mjs` executes separate Engine `TRUE/FALSE/UNKNOWN` route cases based on a constructed fixture; those are **not** browser checks of imported file-specific negative/UNKNOWN verdicts. `tests/acceptance/run_ic020_p2c3_unmapped_real_browser.py` tests JSON/CSV warning privacy and competing device-table blocks; source test covers JSON/CSV/TSV/XLSX/ODS.

**Important:** the five network-import sources are **not** all formats on disk. Native YadiLab scenario JSON is distinct, eight dedicated GraphML/diagrams.net/Ansible/DOCX/ODT/Nmap/Nessus paths retain their own guarded preview/review behavior, and the other planned profiles remain non-active. The original 27-row matrix's other 22 entries were not newly re-audited or promoted here.

## IC-020 masterplan exit criteria — checked against source and existing test claims

| Requirement | Evidence and tested boundary | Audit verdict |
| --- | --- | --- |
| Detect and parse five active formats with original source SHA | `run_ic020_p1_core_source_freshness_tests.mjs`; P1 compiled Chromium picker/Builder across five | **PASS for tested profiles** |
| Explicit device IDs, known type/OS, and only declared connections | `network-inventory.ts`, `run_ic020_p2c2_multisheet_tests.mjs`, P2c2 real Chromium six-sheet positive/negative | **PASS for tested variants; no arbitrary sheet promise** |
| Two explicit competing link sources resolved only by operator choice | P2a source-bound decision, P2a real Chromium regression | **PASS for tested source conflict** |
| Duplicate inventory tables do not silently win; unmapped fields disclosed without leaking values | P2c3 sources and compiled Chromium | **PASS for tested ambiguous tables/unsupported headers** |
| Typed links must reference explicitly declared ports when present in canonical six-sheet model | P2c2 source + Chromium workbook fixtures | **PASS for tested XLSX/ODS variants** |
| Source changed, user cancels, switches file or stale Builder | P1/P2a/P2b original reparse/recheck; compiled Chromium | **PASS for tested cases** |
| Read-only reimport diff, separate replacement approval and replay without auto-approval | P2b/P2c1 source + actual Chromium; no silent merge | **PASS for tested cases** |
| Imported OS-labeled Windows/Linux can run deterministic *modeled* probes | IMPORT-004 source + Chromium CSV; P2c2 source + Chromium ODS; no guest execution | **PARTIAL across five subtype browser runs** |
| Negative `FALSE` and `UNKNOWN` modeled-probe verdicts visible and correct after importing documented partial/contradictory sources | P2c2 Engine-only separate route fixture has `FALSE`/`UNKNOWN`; no matching imported-source compiled Chromium verdict oracle | **NOT_ATTESTED — blocking gate** |
| Contradictory document facts beyond duplicate tables, dual link sources, and typed port checks do not silently override (e.g. repeated device identities or incompatible typed declarations across rows) | Existing block/alias work covers selected conflict classes; no complete cross-row contradictory-facts browser acceptance established | **PARTIAL — blocking gate** |
| Genuine physical network / native Parrot behavior | Ubuntu GitHub Actions intentionally used instead of manual repetition | **NOT_RUN; not a requirement to repeat automatic checks** |

**Exit decision:** **KEEP IC-020 OPEN**. Do not announce complete network/probe acceptance or proceed to IC-030 solely on this P2c4 audit. Existing positive and privacy/port/ambiguity safety paths are valuable, but cannot fill the specifically unsatisfied negative/UNKNOWN and contradictory-facts end-to-end contracts.

## Next bounded checkpoint

`IC-020 P2c5`: freeze exact source-level and compiled Chromium oracles for (a) source-specific contradictory typed facts in supported JSON/CSV/TSV/XLSX/ODS inventories, without guessing precedence or leaking original confidential values, (b) explicit imported modeled Runtime `FALSE` and `UNKNOWN` transcripts with original source / Engine provenance, at least one realistic Windows/Linux source and a partial or impossible route, (c) cancellation/fail-closed with no active Builder/Engine mutation, and (d) previous P1–P2c4 regression suite. **Only after those evidence gates are actually green** can a fresh IC-020 exit review decide whether IC-030 is next. No Real Mode, guest command execution, OSPF milestone, adapter expansion or semantic rewrite is authorized by this document.

CI gate for P2c4: `npm run test:ic020-p2c4-matrix` is a read-only source/matrix/required-workflow and adversarial oracle; the existing P1–P2c3 real browser tests are still mandatory in both CI and release workflows. Native/physical network is NOT_RUN, never PASS.
