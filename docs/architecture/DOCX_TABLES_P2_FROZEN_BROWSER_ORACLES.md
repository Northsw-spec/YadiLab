# DOCX-TABLES-P2 — frozen real-browser structure-only inspection contract

Authoritative source: current GitHub main on checkpoint entry, `831475adae16311b02392891b1702f958a94efce`; source tree `9e3e44636aab62a620f5bb043ce1da2e15e57828`. This document is an implementation contract, **not a claim of tests passing**.

## Inherited P1 limits and truth

Use ONLY existing `previewDocxTableStructure` narrow strict OOXML parser (no new permissive parser, no automatic active import adapter). P1 returns typed cell locators, dimensions, source SHA256, and text lengths, **not cell content**. `CONFIG_DOCUMENTED`, `REVIEW_REQUIRED`, `canActivate=false`. No physical topology, device identities, network links, Engine PASS, executing macros, external links or document data interpretation. Preserve all working GraphML/Nmap/Ansible/workbook imports.

## P2 UI oracle before coding

- Add English-only `Inspect Word DOCX (structure only)` in existing Import / Export menu. Isolated modal `data-docx-panel="CONFIG_DOCUMENTED"` with visible `Choose .docx file` control, close/cancel and Escape. No user permission required for local file parsing. Never call `setWorkspace`, `fetch`, `onActivate`, or Engine; no JSON sidecar/CSV or scenario export.
- Bridge accepts only basename matching `.docx` case-insensitively (not path), bounded length 1..16 MiB, validates actual ArrayBuffer byte length; file extension alone cannot authorize parsing. Future malformed-source failures must be visible by **stable sanitized error code** (not user-provided XML paths/values).
- On success, only filename (safe React-escaped text), source SHA256, table and row counts, column counts, **per-cell numerical text lengths** and typed locator positions are displayed. No `textContent` or preview of real original document paragraphs/cells (not even a truncated sample), no clickable references or remote asset loads; any secret canary in document XML must be absent from DOM, console logs and downloaded Builder JSON.
- Invalid, malformed, unsupported, DTD, external relationships: entire preview blocked, no partial/stale display. Switching files resets previous preview; closing dialog is passive. A stale asynchronous file response cannot overwrite a newer request. No active import and no mutation of Builder output.
- Use real Chromium against **built** app to upload a synthetic locally generated 2x2 DOCX with secrets and independent source SHA256; verify exact counts/locators, no raw text, escape filename, unchanged Builder export before/after; reject malformed ZIP, DTD, macro, external link and invalid extension, recover; close/reopen resets.
- Independent Node bridge and SSR tests, strict source regression and actual CI Chromium. GitHub Ubuntu exact-head CI SUCCESS suffices to advance project per `AGENTS.md`; no manual Parrot gate.

## Known limitation

P2 is a **structural document inspection UI**, not usable preview/mapping of document table **values**. Unlocking cell text requires a separate explicit P3 privacy/redaction design and tests. Do not describe this as full DOCX table import, verified network documentation, or activated topology.
