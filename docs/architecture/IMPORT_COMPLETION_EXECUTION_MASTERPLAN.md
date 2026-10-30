# IMPORT-COMPLETE-001 — YadiLab multi-format import completion masterplan

**Status:** ACTIVE PRODUCT PRIORITY / IMPLEMENTATION ROADMAP, not a claim that any pending format is complete.
**Decision:** Complete the scoped import → review → topology/observations → model/probes workflow before starting new discretionary OSPF/SPF/convergence development. Repair a security vulnerability, broken release, or required CI immediately when necessary. Any other priority exception requires an explicit project-owner direction and a documented decision on GitHub issue #3.
**Canonical tracking issue:** [#3 — import implementation](https://github.com/Northsw-spec/YadiLab/issues/3).
**Authority:** [AGENTS.md](../../AGENTS.md) and **current protected `main`**. This roadmap specifies the *next work*, never a historical checkout, complete-feature certificate, or alternate source code.
**Audit-only baseline, 2026-10-31:** `main=94711af3ce9243c78e6ce8e73f96d8850e8cf2df`, tree `7145d7880bd2a464779cc96d47c42380b77d2c11`, protected with required `yadilab-required-ci`; no open PR. **These hashes MUST NOT be used as the base for later tasks.**

## 1. User-visible product goal and scope

An IT technician/consultant can choose a **local, supported document or tool export**, see its correctly identified profile and limitations, inspect safely extracted network-relevant content, resolve ambiguous identities/roles/ports/connections manually, review exact source provenance, and explicitly choose to create or update a YadiLab Builder/Runtime scenario **where that operation is semantically justified**. They can visualize only supported, source-grounded facts and execute **modeled probes against the activated Engine scenario** when the scenario has known endpoint types and sufficient configuration. An imported file alone **never** causes a real network scan, changes host configuration, verifies a physical cable, manufactures an active service, asserts a green PASS, or starts a live Real Mode probe.

Not every supported format should produce a runnable network. A Nessus scan, PCAP, EVTX or log is **observed evidence**, not a declaration of topology or Engine state. Safe completion for such profiles is read-only inspection, explicit reviewed association to an existing model, overlay/evidence, faithful replay/export, and NO automatic activation. Unsupported or ambiguous information remains `UNKNOWN`, `UNMAPPED` or `REVIEW_REQUIRED`.

This goal **does not promise** correct automatic interpretation of any arbitrary file, scanned page, pictorial diagram or proprietary vendor extension. Supported producer/profile versions and their limitations are explicit. For a future real-infrastructure probe, require a separately verified, user-authorized Real Mode workflow and target permissions; never infer such authority from a document.

## 2. Current main evidence and starting capability matrix (NOT a completion certificate)

*Authoritative implementation and actual acceptance must be rechecked at the start of EVERY subsequent checkpoint.* Do not copy historical test results as current CI truth.

| Family / example suffix | Confirmed code already on this audit main | Gap before user goal |
| --- | --- | --- |
| Native scenario `.json`; enterprise `.json`/`.csv`/`.tsv` | Native source import and five enterprise adapters; structured mapping, Builder projection, import helper | Reconfirm complete UI → review → compile → Runtime modeled probes, reimport, rollback and real Chromium acceptance per selected subtype |
| Excel `.xlsx` and OpenDocument spreadsheet `.ods` | Active enterprise adapters; Network Excel/CSV quick import with exact declared links; `IMPORT-004` modeled probes | Profile-specific UI end-to-end parity and realistic negative/large datasets; avoid claims for arbitrary proprietary sheets |
| `.graphml` | Read-only graph preview plus explicit manually reviewed GraphML-to-Builder candidate mapping; no inferred physical cables | Audit/complete single coherent visible confirmation, provenance, save/reload/replay, activated scenario and modeled probes only if safe |
| diagrams.net `.drawio` | Strict structural/compressed read-only parsing, bounded vertex ordinals, manually reviewed references to existing Builder, source-bound replay (P1–P6) | No generic diagram → network scenario conversion; add only explicitly reviewed typed nodes/relationships with documented semantics |
| Word `.docx`, OpenDocument Text `.odt` | Bounded table structure, consented cell review, manually reviewed references, original-source replay (P1–P6) | No general DOCX/ODT table → modeled device/link mapping; integrate reviewed network tables safely without copying confidential free text |
| Nmap `.xml`, Nessus `.nessus` | Read-only scan/report evidence; review associations, bounded navigation and replay | Complete shared evidence overlay/UX and safeguards against observation → unearned Engine PASS/TRUE |
| Ansible static inventories `.ini`/`.yaml`/`.yml` | Strict read-only inventory previews, reviewed host-to-Builder references, saved replay/ordinal navigation | Unify field mapping/explicit scenario candidate activation only for supported declared network facts; no playbook execution |
| `.pdf` | Planned format profile only; no confirmed active PDF network-table importer | Digital text/table-first bounded parser, provenance and review; scanned PDF / images / OCR and hand-drawn topology do not become inferred infrastructure |
| Visio `.vsdx`; GNS3 `.gns3`/`.gns3project`; EVE-NG `.unl`; Cisco CML profile `.yaml` | Planning/profile declarations | Producer-specific safe parsers, reviewed semantic edges/segments and independent profile acceptance |
| Terraform `.tf`/`.tfstate`; vendor `.cfg`/`.conf`/`.txt`; HTML `.html`; logs `.log`/`.jsonl` | Planning/profile declarations | Scoped, redacted, read-only producer-specific parsing; reviewed facts, never execute code or reveal secrets |
| PCAP/PCAPNG `.pcap`/`.pcapng`; Windows EVTX `.evtx` | Planning/profile declarations | Bounded passive evidence with frame/record limits, source/time context and reviewed association; no conversion into physical topology truth |

**Critical distinction:** `enterprise-import/src/adapters.ts` registers only five baseline adapters: JSON, CSV, TSV, XLSX, ODS. `planned-format-profiles.ts` deliberately marks other profiles BLOCKED in that generic registry. Specialized previews and review flows implemented elsewhere **must not be reported as absent** merely because they are not in this registry; equally they **must not be reported as full active import** merely because a parser or UI exists. The target is a *coherent profile-based entrypoint* preserving both truths.

Starting evidence: `enterprise-import/src/{adapters,planned-format-profiles,graphml-review-mapping}.ts`; `ui/src/browser/{import-helper,network-topology-import}.ts`; `docs/{IMPORT001_NETWORK_EXCEL_CSV_TOPOLOGY_CHECKPOINT,IMPORT004_MODELED_PROBES_AFTER_DOCUMENT_IMPORT,PHASE64_ENTERPRISE_TOPOLOGY_PROJECTION}.md`; test suites and browser workflows; issue #3. Historical architecture PREPs are evidence of prior intended contracts, not a license to revert finished behavior.

## 3. Mandatory single-source import pipeline (target contract, not automatically implemented)

`FILE SELECT → PROFILE DETECT (signature + structure + producer variant, never suffix alone) → BOUNDED PARSE → SOURCE HASH + TYPED ORIGINAL LOCATORS → CLASSIFY (TOPOLOGY_DECLARED / CONFIG_DOCUMENTED / EVIDENCE_OBSERVED) → PREVIEW → REVIEW ambiguous facts, IDs and relationships → VALIDATE approved mapping and conflicting facts → EXPLICIT CONFIRM → SOURCE-BOUND PROJECTION (only where eligible) → BUILDER + COMPILER + LAYOUT → EXPLICIT MODELED RUNTIME + PROBES (only when supported) → EVIDENCE / REIMPORT / REPLAY`.

This is a **logical contract**, not a mandate to replace the five stable adapters or flatten incompatible files to table cells. A profile can stop at `PREVIEW_ONLY`, `REVIEW_REQUIRED`, `EVIDENCE_ONLY` or `UNSUPPORTED`. All transitions must be shown in the UI with accurate reason codes.

- One discoverable Import / Export entrypoint with accessible names for profiles, file chooser, status, source type, preview, explicit confirmation, errors, and supported completion level. Retain established quick-import/Builder/Runtime features. Any file chooser dialog must reset stale consent on file change and cancel.
- Profile detection is based on a bounded file signature/container structure, exact schema/root and producer version; reject wrong extensions, ambiguous generic `.xml` / `.yaml`, corrupt archives and unrecognized subtypes. Do not relax global DTD/XXE/ZIP rules to accept one format.
- Original-source locators must be typed (table/sheet/cell, GraphML node/edge, diagram page/vertex, XML scan host, report host, Ansible inventory host, PDF page/table/row, etc.), versioned and source SHA-256-bound. Intermediate normalized workbook coordinates cannot masquerade as original document coordinates.
- Preserve the distinct classes: `DECLARED` may be modeled only after explicit facts/approval, `DOCUMENTED` requires source-specific mapping and review, `OBSERVED` remains evidence and **never** directly installs Engine truth. Every projected connection must be explicitly declared and interpreted; a drawn line, IP/subnet proximity or Nmap open port is not automatically a physical link or current service.
- Importing never modifies the running lab on file selection/preview/failure. Approved projection uses existing `EnterpriseBaseline → ScenarioSource → Compiler → Layout → Canvas` or existing network-workbook path. The user intentionally chooses **Replace Builder / Apply reviewed mapping** and separately **Open modeled Runtime + Probes** when eligible. It must be possible to inspect without activation.
- Preserve original source identity for source-bound export/replay and subsequent reimport/merge; compare full source and current Builder just before applying, not only at first preview. Avoid copying secrets or whole raw documents to scenario packages, UI labels, logs, public CI artifacts or telemetry.
- Truth vocabulary visible in the English UI: `DECLARED`, `DOCUMENTED`, `OBSERVED`, `MODELED`, `REVIEW_REQUIRED`, `UNMAPPED`, `UNKNOWN`, `BLOCKED` and truthful probe outcomes. No green checks from parsing or association alone.
- Modeled probes (ping/TCP/DNS/DHCP/path) call the existing deterministic observation/Engine APIs, do not execute Windows/PowerShell/Linux guest commands and may produce `FALSE` or `UNKNOWN`. Real Mode remains separately isolated and authorized; an import is never an implicit permission to scan external addresses.
- Keep parser resource caps, explicit offline/no-network behavior, secret masking, macro/external-link/embedded-code denial, archive bomb defense, and malicious source/filename/JSON/prototype injection adversarial tests for **each** profile.

## 4. Ordered execution checkpoints — smallest safe vertical slices

The following order is the default when the user says **“fortsätt”**. At each checkpoint inspect fresh main, issue #3, relevant source/tests and open PRs, then choose the first **unfulfilled** acceptance contract. Do **not** reimplement a previously completed P1–P6 parser merely because a historical plan says PLANNED. Break large tracks into as many isolated PRs as needed; every PR has an explicit test oracle, source authority, and no unrelated OSPF work.

### IC-000 — live capability and regression inventory (FIRST)
Generate a source-cited inventory of each scoped profile's detect / parse / preview / review / projection / Builder / Runtime/probe / replay / UI / current CI status. Include actual module paths, exact browser paths, tested vs not tested, and explicit outstanding acceptance. Reconcile `planned-format-profiles.ts` BLOCKED notices with already-existing specialty parsers without globally registering formats prematurely. Create a small machine-readable, versioned capability matrix only after the shape and tests are agreed. Avoid unverified claims of complete format support.

**Gate:** every row grounded in live source/tests/CI; no current implementation silently omitted; baseline five adapters and import probes regressions PASS; no new import activation.

### IC-010 — shared profile entrypoint and source/provenance contracts
Introduce bounded profile detection, typed original-source locators, state-machine transition/status vocabulary, review/consent, stale-source/Builder invalidation and discriminated projections. Reuse existing modules; avoid a universal XML/YAML parser and preserve five legacy adapters byte-for-byte at public contracts. Show status in a coherent import UI with safe blocked/unsupported explanations and real browser file-picker controls.

**Gate:** all source profiles dispatch without ambiguity, malicious/wrong/huge files BLOCK, original fields stay isolated, cancel/reimport/failed validation never mutates Builder or Engine; established five paths still work.

### IC-020 — complete the core network inventory path and probes
For `.json`, `.csv`, `.tsv`, `.xlsx` and `.ods`, verify and correct the *complete* source-appropriate visible journey: imported devices/interfaces/explicit links, unmapped/conflicts, manual review, compile, Layout/Builder, Runtime probe-eligible Windows/Linux endpoints, negative results/UNKNOWN, reimport and report replay. Test a representative realistic IT-consultant network workbook and partial/contradictory data; never fabricate links from default gateways.

**Gate:** full real Chromium workflow including file chooser and explicit consent, no truth change on cancel/failed import, independent expected nodes/links, probe transcript ground truth and adversarial data tests.

### IC-030 — GraphML and diagrams.net (.drawio)
Build on existing GraphML reviewed mapping and draw.io P1–P6. Provide reviewed source-bound typed device roles, optional explicitly consented **modeled** connections only where graph syntax and user decision justify them, preserving uncertain/untyped objects as generic. Compressed/multi-page/ordinal handling remains bounded. Verify originals and Builder against stale mapping before activation. No direction/arrow or diagram decoration silently implies copper/fiber adjacency.

**Gate:** each selected profile can either produce a reviewed candidate (with explicit uncertainty) and pass compile/Canvas/optional modeled probes, or visibly BLOCK with exact reason; negative cross-source and spoofed-drawing cases, real Chromium acceptance.

### IC-040 — DOCX and ODT network tables
Preserve P1–P6 structural/consent, secret blockers, zero-content reference sidecars and replay. Add a **separate explicit approved data-to-network mapping** for supported tables (device ID/type/IP/interface/declared peer), with source-aligned locators, redaction, conflict review and provenance. Do not conflate prior reference-only features with value import. Never mine arbitrary prose for cables, passwords or topology. Consent to inspect a single cell is not blanket consent for entire document.

**Gate:** benign documented table → reviewed Builder scenario with correct resources, or rejected/unknown without leakage; DOCX/ODT fixture variants, malicious package/secret cases, fresh-source revalidation, actual browser UI and independently checked original-cell mapping.

### IC-050 — PDF digital network documentation, not OCR speculation
Introduce a named, versioned **digital text/table PDF subset** after a threat model and dependency decision. Handle bounded pages, text layers, cells/coordinates, encrypted/embedded files, complex table order and malformed objects safely. Confirm extracted source locations, solicit user review for ambiguous rows and build the same controlled mapping as IC-040. A scanned PDF, photograph, vector diagram or uncertain layout must result in `UNSUPPORTED_PROFILE` / `REVIEW_REQUIRED` rather than invented nodes/ports. Image/OCR understanding is a *separate*, optional future profile with stronger evidence, not implicitly enabled.

**Gate:** positive real text-table PDF, adversarial/malformed/secret negative fixtures, deterministic source-bound review/Builder projection when justified, UI/browser and regression proof. No broad claim that “all PDF files import as networks.”

### IC-060 — Ansible INI/YAML and network configuration declarations
Extend existing P1–P6 Ansible inventory previews and reviewed host associations to coherent, safe typed **inventory** mapping. Only explicit static host/group/declared-address facts; dynamic inventory/plugins, commands, playbooks, Jinja evaluation and credentials never execute. Separately plan Cisco CML YAML based on **its own** syntax/profile, not a suffix-wide YAML importer.

**Gate:** static source → reviewed documented inventory/eligible scenario candidates; unknown/host alias/secret/dynamic constructs remain blocked or unmapped; no network links fabricated from group membership; browser and source-replay tests.

### IC-070 — Nmap XML and Nessus reports as observed evidence
Complete discoverable review overlays and source-bound replay using existing P1–P6. Preserve reported scan time, ports/status/severity and differences from present modeled Engine state. When a user associates an observed host with a Builder resource, label it as an operator review, not verified physical identity. No observed “open port” becomes an active modeled listener or successful probe by itself.

**Gate:** real browser evidence workflow, source SHA/replay, bounded reports, wrong-time/identity/conflicting-state/XXE tests and unchanged Engine truth.

### IC-080 — Visio, GNS3, EVE-NG and Cisco CML
Independently research supported producer versions first, then build versioned, bounded importers for `.vsdx`, `.gns3` / `.gns3project`, `.unl` and CML YAML. Inspect declared nodes/ports/links/segments with semantic differences (e.g. hypervisor/veth vs physical cable) and user review. Never run appliance images, scripts, commands, emulators or imported projects.

**Gate:** per-producer positive/hostile fixtures, network-mapping semantics and unmodeled fallbacks, explicit Builder confirmation, real Chromium proof, no side effects. Do not claim all GNS3/Visio extensions work automatically.

### IC-090 — Terraform, device configs, HTML tables and log exports
Design separate profile-bound, read-only parsers for `.tf`, `.tfstate`, supported `.cfg`/`.conf`/`.txt` vendor variants, static `.html` tables and `.log`/`.jsonl`. Secrets in Terraform state, credentials, tokens and private addresses must not enter public exports or test logs. No Terraform plan/apply, script evaluation, remote fetch or browser HTML execution. Config observations require explicit trust/type annotation; logs are temporal evidence.

**Gate:** secrets redacted, producer/version uncertainty visible, reviewed source association or explicitly scoped configuration mapping, deterministic negative tests and real browser where user-interactive.

### IC-100 — passive captures and Windows event logs
Implement bounded, offline, **passive** `.pcap`/`.pcapng` and `.evtx` profile subsets with frame/record/time/source limits. Avoid packet replay, host scanning, executable decoders and interpreting observed conversations as topology ground truth. Visual overlays are source-bound and operator-reviewed, not active Engine truth.

**Gate:** hostile/truncated/oversize capture fixtures, passive parsed evidence, lossless original references where permitted, no secrets leak, no automatic links, actual browser usability and regression proof.

### IC-110 — cross-format reconciliation, final product acceptance and closeout
Bring all supported profiles under a coherent discoverable UI, with a **truthful feature-capability table**, safe saved-source replay, mapping conflict review and explicit Builder/Runtime transitions **for eligible profiles only**. Run combined multi-format conflict tests (Excel vs Nmap vs Nessus vs Ansible) that refuse to turn weak evidence into Engine truth; reimport/rollback cross-version; big inputs; deterministic Engine and visual projection; release artifact mounted real Chromium; offline/locked dependency and negative trust checks. Document clearly which proprietary subprofiles and scanned PDF/OCR remain unsupported.

**Project closeout requires:** each **scoped profile** has individually verified deliverable semantics and actual CI evidence, or an owner-approved documented explicit exclusion; matrix/status, UI and code agree; no unresolved security-critical format blockers; evidence-only profiles are **not** misreported as runnable networks; current protected main and independent postmerge Linux release pass. **Do not close issue #3 merely because the five existing adapters work or all format names appear in the UI.**

## 5. Required acceptance and evidence contract for EACH format checkpoint

Before code:
1. Fetch fresh protected `main` SHA/tree, current root `AGENTS.md`, this plan, `package.json` and issue #3; inspect open PRs and actual code/test paths. Historical ZIP, Google Drive research, old comments and old README are NOT code bases.
2. Record exact format/profile/subtype, required input and output (imported Builder topology? read-only evidence?), security budget, allowed semantics, source locator and official/frozen independent positive **and adversarial negative** expected results. Freeze acceptance in a short format-specific ADR or test oracle **before** implementation.
3. Identify the next unmet smallest vertical milestone; keep versioned interfaces additive, preserve working routes, UI, Engine and prior import flows. No speculative convenience transformations or unreviewed dependencies.

During code:
4. Commit bounded implementation, tests, UI integration and documentation on a new branch from fresh main; never bypass protection. Use distinct parser/semantic/Builder/model/real-browser tests; include malicious, oversized, secrets, wrong-origin, consent and rollback paths. Record exact source SHA and provenance.
5. Assert all deliberate truth barriers: parsed ≠ authorized; declared ≠ physically verified; observed ≠ current truth; mapping review ≠ Engine success; simulation ≠ real packet/host scan. `UNKNOWN` is valid expected output.

Merge/release:
6. A PR may be squash-merged only after all required status checks on **its exact head SHA** are SUCCESS and relevant test logs prove the new oracle actually ran. Historical failed Actions runs remain failures, never relabeled. On merge, verify new protected main SHA/tree and separately completed-success independent exact-SHA Linux release (including actual mounted Chromium and uploaded artifact IDs).
7. Update issue #3 with start/end Git SHA, PR, exact test/check/run links, supported/partial/blocked profiles, remaining risks, and **next unmet milestone**. Refresh the capability matrix only from verified implementation, not a commit title or an optimistic plan.
8. User-approved GitHub Actions Ubuntu verification suffices for automated coding checkpoints. Parrot-native, real hardware, real enterprise files or human visual judgement stay `NOT_RUN` unless separately proven; do not require manual Parrot repetition of already-covered CI.

## 6. Governance, handoff and how to change this plan

- This file is the canonical **active development priority and ordered acceptance contract** for import completion. Root `AGENTS.md` points here; `docs/CURRENT_PROJECT_STATUS.md` and issue #3 link to it. For a new conversation, the shortest correct handoff is: **read AGENTS → latest main → this plan → issue #3 → package/version and current source/tests/CI → select next unmet IC checkpoint**.
- For a generic “fortsätt” on YadiLab while import completion is active, continue the **next unmet import task**, **not** discretionary new OSPF/SPF convergence work. Previously merged OSPF code stays intact and its regression tests remain mandatory. Security repairs, required-CI/release repairs or an explicitly instructed different task take priority, but document any deferral/exception in issue #3.
- Progress statuses are `PLANNED`, `IMPLEMENTED`, `TESTED`, `CI_PASS`, `USER_ACCEPTED`, `BLOCKED` and optionally `NOT_APPLICABLE` per **profile and capability**, never one global “all formats PASS.”
- Owner-approved modifications to ordering/scope or a justified format exclusion must be implemented by a reviewed PR changing this file (and issue #3), preserving rationale and backward compatibility. Comments and old masterplans cannot silently override this active document. No blanket requirement to add unnecessary parsers or to enable destructive Real Mode actions.
- The import-completion priority expires only when the **IC-110 closeout** above is demonstrated on current main and the owner accepts closure of issue #3, or when the owner explicitly changes project direction. Then OSPF/SPF may resume from verified current GitHub state, not old code.

**Implementation references:** [existing import PREP](IMPORT_FORMATS_PREP_001_ADR_AND_BASELINE.md), [existing real modeled probes](../IMPORT004_MODELED_PROBES_AFTER_DOCUMENT_IMPORT.md), [Enterprise projection](../PHASE64_ENTERPRISE_TOPOLOGY_PROJECTION.md), [current status index](../CURRENT_PROJECT_STATUS.md), [research/implementation issue #3](https://github.com/Northsw-spec/YadiLab/issues/3). All are subordinate to current actual source and this active priority decision.
