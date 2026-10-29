# NESSUS-P3 — frozen source-bound manual host-ordinal references (CI-only, no Nessus installation)

**PREP — NOT TESTED at initial commit.** Source of truth: `main=c09db305272101b2571c1364c78ea0415d083137` tree `51e818fc77e2d8dfb29ec95f76069d97d7626a21`. Read `AGENTS.md` at each checkpoint. Existing P1/P2 is severity-only with no raw host/IP/plugin data returned; P3 may not weaken it.

## Precise scope
A local user **optionally** declares that a specific **ordinal ReportHost position** in the original `.nessus` file should be linked as an **unverified reference** to one **existing Builder resource**. No asset identity is established: host ordinal alone is not a unique real-world host identifier. Never infer a connection, vulnerability, observed IP, port state, asset role, Engine success, vulnerability confirmation or physical topology.

Default is no association. Require open Builder scenario, one selected in-range host ordinal (0–min(hostCount,20)-1) and a distinct existing resource ID; each choice and final export requires explicit acknowledgment of unverified status. Hard maximum 20 references even though P2 handles ≤256 host sections. Host labels in UI are "ReportHost #N" only; **never display host name, IP, tag, pluginID, plugin_output or finding text**.

At export re-read **original entire file**, re-run P1/P2 strict ≤2MiB / UTF-8 / XML DTD/ENTITY/PI and source SHA256, require exact preview SHA, host count, overall finding count and severity counts. Do not trust constructed client preview. Re-check current Builder scenario ID, revision and resources at export; stop on stale changes. Sidecar is a separate local download, not an import. Explicit `EVIDENCE_OBSERVED` and negative flags. Sidecar only source SHA, profile, current model identity, sorted typed source locators `{kind:"nessus-report-host", sourceSha256, hostOrdinal}`, selected resource IDs, `USER_ASSERTED_ASSOCIATION_NOT_VERIFIED`, warnings and negative truth flags. **No source text, host name, IP, plugin data, credential values, vulnerability content or per-host finding counts in output.** No model changes.

## Positive oracles
- Independently constructed valid synthetic Tenable Nessus v2 XML, two ReportHosts and non-sensitive ordinal choices, existing Builder resources, valid acknowledgment, source SHA and P2 counts match, export exactly one or two sorted, metadata-only references. No installed Nessus, network access, subscriptions or credentials are needed.
- Real compiled Chromium uploads synthetic fixture, selects ordinal 0 → modeled resource, acknowledges, downloads sidecar, checks bytes and exact unchanged Builder canonical JSON; repeat file invalidation and no consent / runtime absence.

## Adversarial / negative oracles
- No consent, missing Builder, stale SHA, scenario/revision, missing/duplicate resource, forged resource prototype names, duplicate ordinal/target, missing/out-of-range/fractional ordinals, >20 selection, invalid P2 shape, secret text insertion in source (never leaked to UI/output), different bytes with original filename, DTD/entity/invalid UTF8/oversized file, duplicate host or malformed XML. Export failure emits only stable error codes and no partial download; no raw source in console, errors, DOM or exported JSON.
- Existing Nessus P1/P2, Nmap, ODT, DOCX, GraphML and Ansible tests remain intact. New exact-head actual Chromium workflow plus all current PR workflows MUST be SUCCESS before merging; then exact merged-main Linux release. GitHub Ubuntu CI suffices under AGENTS.md; Parrot manual NOT_RUN by design.

## Format source and security reference
Official Tenable: https://developer.tenable.com/docs/export-file-formats (NessusClientData_v2 / Report / ReportHost / ReportItem). Project `enterprise-import/src/nessus-v2-preview.ts`, `ui/src/browser/nessus-v2-file-preview.ts`, `enterprise-import/src/nmap-association-review.ts`; OWASP XXE and input bounds. Format support is limited to *already validated P2 subset*, not every Tenable export version. P3 must not introduce vendor runtime dependencies.
