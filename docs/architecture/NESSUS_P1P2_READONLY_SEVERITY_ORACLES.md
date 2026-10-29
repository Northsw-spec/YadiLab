# NESSUS-P1/P2 — frozen .nessus v2 read-only severity-summary contract

**PREP status at first commit: PLANNED / NOT IMPLEMENTED / NOT TESTED.** Source of truth at checkpoint start: `main=0e4b653b0c2a4737c56b3d433fff5365aac3b3fd`, tree `ae92b0142cce2089abd5658d77cbaa31b0d86eed`. Do not use historical artifacts as code base. Observe `AGENTS.md`.

## Scope and semantic boundary
Add **only** a local, read-only, consent-free *aggregate structural* summary of Tenable Nessus v2 XML `.nessus` exports: number of ReportHost sections, number of ReportItem entries, and counts for severity 0–4. No IPs, DNS names, plugin names, plugin output, description, solution, references, per-host identifiers, host tags, credential data, raw XML, vulnerability text, or per-finding IDs in returned structured result/UI/errors/JSON. Input may transiently contain all such text; never persist it. No export or file persistence. No scan, probe, Builder/Engine mutation, network calls, inferred physical links, or asset identification. Trust boundary: **EVIDENCE_OBSERVED** at source scan time; severity is exporter-declared, NOT independently validated vulnerability status.

## Accepted producer profile
Independent fixture mimics Tenable-documented `NessusClientData_v2 / Report / ReportHost / HostProperties / ReportItem`. Accept exactly one root `NessusClientData_v2`, one `Report`, zero or one `Policy` before Report, zero or more `ReportHost`; per ReportHost zero or one `HostProperties` and zero or more `ReportItem`. Do not interpret host-identifying tag or plugin subtree contents; treat those as opaque and never use them to infer truth. Require `ReportHost.name` as non-empty (bounded to 512 code units) for structural validity, but never output it. Require each ReportItem numeric `severity` in 0..4; `pluginID` positive integer, `port` 0..65535 and `protocol` nonempty bounded 32 when present (do not export these). Reject unrecognized root-level/host-level elements; do not reject additional ReportItem attributes/children, which contain vendor plugin metadata. Do not attempt to validate every Nessus producer variant: unsupported cases block.

## Limits and fail-closed security
Max bytes: 2 MiB input at file picker AND parser (Uint8Array); strict UTF-8, no BOM/non-XML PIs/DTD/ENTITY/custom entities, no NUL; reuse the existing bounded `parseSafeXml` without changing its global behavior. Maximum 256 `ReportHost` and 10,000 `ReportItem`. The parser must not interpolate untrusted XML into exception text. Verify `.nessus` basename-only extension, normal size and returned `ArrayBuffer` before parsing. Source SHA-256 must be computed over **original full bytes**. No HTML injection or network activity. No partial result after a failed file selection. Closing dialog invalidates async updates; repeat selection resets preview. Keep source bytes out of React component state (only aggregate metadata is stored).

## Positive oracle
One standards-shaped synthetic Nessus v2 XML with two hosts and severity items [0,2,4,3] yields host count 2, finding count 4, severity [1,0,1,1,1], source SHA equality, immutable read-only `EVIDENCE_ONLY` / `EVIDENCE_OBSERVED` / `canActivate:false` / `engineVerified:false` / `physicalTopologyVerified:false`. User-visible summary includes no source strings beyond filename (sanitize filename display) and full-document SHA.

## Negative oracles
Wrong root, fake Nmap XML, no Report or duplicate Report, extra root/host children, duplicate HostProperties, missing host name, severity outside 0..4 / malformed values, missing plugin ID or invalid port or protocol as per accepted profile, 257 hosts, 10001 findings, invalid UTF-8, oversized bytes, invalid extension, wrong return type, DTD/entity/stylesheet PI, bad nesting. Include secrets, malicious HTML, host identifiers and plugin output in fixture, assert absolutely absent in DOM/render/export/log. For real Chromium on an actual built app, select valid and invalid files and verify error recovery, modal reset, no cross-origin requests/errors, unchanged canonical Builder source, no Engine activation.

## Regression and acceptance
Run TS compiler, pure independent XML cases, SSR UI assertions, real compiled Chromium file chooser + negative cases, current Nmap/GraphML/Ansible/DOCX/ODT source/browser regressions at exact PR head. Do not infer Parrot-native acceptance from Ubuntu CI. Approved merge only with exact-head GitHub Actions SUCCESS; separately verify merged-main release and artifact. If the build fails, preserve PR and document BLOCKED.

## Evidence and design references
- Tenable's official `nessus_export` documentation: https://developer.tenable.com/docs/export-file-formats — root, Report, ReportHost, ReportItem; exporter-declared attributes.
- OWASP XML External Entity Prevention: https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html
- Project `enterprise-import/src/nmap-xml-preview.ts`, `xml-lite.ts`, and `ui/app/nmap-observation-panel.mjs` are the **current** source reference, not authority to assume a valid Nessus profile.
