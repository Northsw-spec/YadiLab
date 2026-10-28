# IMPORT-FORMATS-PREP-001 — architecture decisions and baseline evidence

Status: **INITIAL APPROVED-PLAN IMPLEMENTATION / NO NEW FORMAT ENABLED** (2026-10-28)
Code authority: **ONLY CURRENT `main` IN `Northsw-spec/YadiLab` AT THE BEGINNING OF EACH CHECKPOINT**.
Research/planning: `YadiLab_Import_Implementation_Masterplan_v1.0_2026-10-28` (Google Drive / YadiLab).
Read-only snapshot examined for this checkpoint: `main=7d425fc82e4bb24c0cbcc4d5ec9aeb1d0c986ecb`, tree `b1848bc995f0df796cdaafe8935fb545dadfc671`.
**The snapshot is NOT a future release base. No old ZIP, release, historical commit, or Luna source has been imported.**

## PREP-000 — observed baseline (do not invent PASS)

GitHub Actions URL: https://github.com/Northsw-spec/YadiLab/actions/runs/40614815774 (Ubuntu 24.04, Node 22; actual GitHub logs).
- `npm ci`: PASS (CI job step 5).
- `npm run test:release-identity`: PASS (step 6).
- First import fixtures (19 assertions in `run_network_topology_import_checkpoint.mjs`): PASS (part of step 7).
- `npm run test:network-topology-import` overall: **FAIL**. `run_network_topology_checkpoint_tests.mjs` line 33 required literal `"data-development-checkpoint": "IMPORT-004"`; actual current `ui/app/main.mjs` binds `"data-development-checkpoint": releaseIdentity.checkpoint` and `package.json` reports `VERSION-005`. Assertion failed; this is a **stale test expectation**, not evidence of an import malfunction.
- `test:imported-probes`, `test:dev11-ui`, compiled browser/launcher/Parrot: **NOT RUN** in this CI attempt because earlier step failed.
- The old repo-wide `README.md` headings can be historical; never infer the current version from README or release ZIP filenames.
- A GitHub Actions job log is **not** a substitute for negative tests in the new adapter nor for actual Parrot acceptance.

## ADR-001 — candidates, provenance and observed-evidence separation

**Decision for first implementation:** Keep existing `EnterpriseImportAdapter.parse` and `ImportDocument` unchanged for five current adapters. Do not fabricate a GraphML `table-cell` locator. For later graph/document adapters use a *separate*, versioned candidate and source-locator contract; bind back to `EnterpriseBaseline` only when the appropriate schema/path is reviewed. Keep observed Nmap/Nessus/PCAP data read-only in a separate evidence contract, not direct Engine mutations.
Alternatives rejected for now: (a) replacing old adapters; (b) flattening observations to synthetic devices and fabricated links.
**Gate:** a missing locator/ambiguous mapping yields REVIEW_REQUIRED/BLOCKED; new types must round-trip old serializations or supply explicit migration fixtures. No code change under this ADR in PREP-001.

## ADR-002 — format identification and dispatch

**Decision:** The existing five adapters and MIME dispatch remain authoritative and unchanged until regression tests pass. Any later format profile is named and versioned (e.g. `graphml.standard.v1`), checks filename hints AND bounded internal structure/signature and supported producer variant, never identifies generic `application/xml` or `application/yaml` as automatically importable. Profile ambiguity blocks.
Alternatives rejected: suffix-only acceptance and a single universal XML/YAML interpreter.
**Gate:** spoofed extension or wrong XML root must BLOCK; unsupported producer variants remain explicitly UNSUPPORTED_PROFILE; tests show old five formats unchanged.
Dependency questions for each parser remain **OPEN** until official-format fixture and security review.

## ADR-003 — secrecy, redaction, export

**Decision:** Never execute imported code or display/export raw secret values from Terraform state, device configurations, log tokens or automation inventories. Preserve a source hash and typed location while redacting secret contents on export. Treat evidence as local and read-only by default.
Alternatives rejected: serializing raw source data into public/student scenario packages.
**Gate:** synthetic secrets cannot appear in exported JSON/ZIP, preview, error output, logs or persisted notebook; threat-model any cached raw bytes. Redaction policy exact patterns/allowlists **PENDING**.

## ADR-004 — dependencies/offline/Parrot

**Decision:** Prefer existing checked-in code and locked dependencies. Re-evaluate current `xml-lite.ts` and `workbook-archive.ts` per producer format; never disable XXE/DTD/zip-bomb restrictions globally. A new dependency needs a separate locked version/license/security, size, and reproducibility decision.
Alternatives rejected: automatically adding a general parser/npm package and assuming it is safe.
**Gate:** clean `npm ci`, no remote runtime fetch, adversarial budget fixtures, independently evidenced browser and Parrot status. Existing `parseSafeXml` rejects DTD; Nmap prolog compatibility must be solved in a bounded format-specific way.

## ADR-005 — UI, activation, rollback and proof

**Decision:** Preserve the existing `Import Excel / CSV → Network Topology` button and other functioning import paths. Introduce future profiles through PREVIEW → REVIEW → VALIDATE → explicit CONFIRM only. No active source/workspace mutation on cancel/error; observations are not Engine truth. Results are tagged per profile, not per extension.
Alternatives rejected: loading a diagram and instantly turning all edges into physical cables or any Engine PASS.
**Gate:** real browser file-picker and confirmation tests, abort/rollback tests, exact before/after workspace identity, and independent DOM tests (not searching compiled JS token strings).

## PREP-001 implementation scope and test honesty

Only fix the proven stale **test expectation** to bind to the *current source-of-truth metadata*. Do not change import engines, adapter registration, network inference, schema, product version or existing user workflows. The static test must verify actual **source binding** to `releaseIdentity.checkpoint`, not a hardcoded older checkpoint or token-only string; this static contract does **not** claim DOM acceptance. Run source/import regression plus a real DOM check at the appropriate release gate. Use an isolated feature branch and require positive CI evidence before merging.

## PREP-002 / CORE-001 next gates (not implemented here)

1. Specify positive/negative/safety fixtures and exact expected graph semantics **before** adding GraphML parser code.
2. Add a fail-closed versioned profile registry only after format-specific ADR/security tests.
3. Add GraphML support in its **own** checkpoint. Never claim that this PREP-001 creates support for GraphML or any other new format.
4. At each future work start, reread `main`, compare diff, run existing import regressions and refuse stale base changes.

**Current feature lifecycle:** PREP-000 observed = BLOCKED at CI failure; PREP-001 proposed fix = not yet CI-verified; all new formats = PLANNED/NOT_IMPLEMENTED.
