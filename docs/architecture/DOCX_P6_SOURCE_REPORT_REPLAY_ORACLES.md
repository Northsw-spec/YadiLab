# DOCX-P6 — frozen safe replay validation of exported P4/P5 reference reports

Authority: GitHub main 62c21f5472c9a12de3ede7f77df40b05936af203 / tree f8e7a6e96d6ecbf03a618ed645167d71cced2ad4. This ADR is a PREP contract and confers no PASS. Prior P4 one-reference and P5 bounded 2–10 reference sidecars are export-only.

## Scope and standards

Local user selects both an original .docx and an already-exported .json P4 or P5 report. Default is idle. Separately unchecked acknowledgement before reading; explicit Verify source references button. No network requests, arbitrary filesystem reads, scenario import, Builder mutation, Engine execution or file writes. Retain separate P2/P3/P4/P5 flows. Schema and provenance must be checked against current source and current existing Builder identities and revision.

GitHub original code sources: enterprise-import/src/docx-cell-disclosure.ts (P3: exact original ZIP SHA256/typed source locator and conservative cell-value screening), docx-association-review.ts (P4 user-declared association, no values), docx-multi-reference-review.ts (P5 no-value report and structural limits), ui/app/main.mjs (Builder source and revision), AGENTS.md (CI-first acceptance).

OWASP File Upload Cheat Sheet https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html and RFC 8259 https://www.rfc-editor.org/rfc/rfc8259 (JSON) inform bounded untrusted-input handling. JSON parsing itself confers no trust. No parsing of unbounded JSON or accepting arbitrary uploaded scripts.

## Positive verification contract

- Read at most 64KiB JSON with strict UTF-8 decoder, only filename basename ending .json, no path or slash; reject empty/oversized, malformed JSON, arrays, extra keys, invalid version/format, elevated truth flags, text values, duplicate or out-of-bounds locators. Input DOCX 4 bytes to <=16MiB with P3 checks; SHA must exactly equal exported source hash. Current Builder must match scenarioId/sourceRevision and explicit resource IDs. Viewer uses actual compiler-independent schema checks, not stored booleans.
- For each reference re-run existing P3 validation with original DOCX bytes, full P1 ZIP/XML/content and source SHA/secret filter. Derive exact original P4 sidecar through existing P4 pure review against CURRENT model and compare canonical JSON structural equality with uploaded sidecar, including warnings and all keys. For P5, reconstruct all P4 sidecars, run existing P5 pure aggregate and compare canonical JSON structure of uploaded report. Never trust claimed status or embedded source positions.
- Return only `REFERENCE_REPLAY_MATCH` with integer reference count and source-level SHA256, `engineVerified:false`, `physicalTopologyVerified:false`, `identityVerified:false`, `modelMutated:false`. No cell contents or hashes of individual cells in response, console, UI, JSON, URLs, telemetry, downloads or thrown diagnostics. Validity means the unverified operator references match the current original document and Builder identifiers. No statement that actual asset identity/physical network topology is true.
- UI in Import / Export: Inspect saved DOCX references (read-only), isolated modal with two file pickers and separate verification consent. Selecting either file immediately clears status and consent; closing/reopening also clears it. Show only status/reference count/source SHA and truth-boundary wording; no uploaded report JSON is rendered. Errors are stable diagnostic code only; avoid filename content in error messages. Block in runtime/no Builder.

## Negative and browser oracles

- Unconsented and single-file attempts do not inspect. Same filename with different DOCX bytes blocks exact SHA. Changed Builder revision, removed resource, duplicate target, modified warnings, invented fields, status=verified, physical flags, bad UTF-8, malformed JSON, wrong extension, oversized JSON, wrong ZIP, unsupported P1 shapes, DTD and suspicious cell content must block. No partial match.
- Independent real P4 and P5 sidecars created from real synthetic DOCX ZIP fixtures and P3/P4/P5 functions; verify both kinds. Negative tests must not rely on the renderer producing fake PASS. SSR controls default unchecked/disabled; actual built Chromium file choosers, consent, PASS UI, changed source block, file reset, Builder canonical JSON deep equality, no cross-origin network requests or browser errors.
- Existing P2–P5 actual Chromium and GraphML/Nmap/Ansible regressions must be all SUCCESS on exact PR head before merge, and exact merged-main Linux release must complete SUCCESS. GitHub Ubuntu Actions suffices; no manual Parrot acceptance is needed.

## Limits

Replay is local evidence of structural source/model consistency, not proof of authorization, real network topology, correct modeled resource identity, or confidentiality. The P3 secret filter cannot guarantee that all sensitive values are identified. No unreviewed report automatically activates or edits Builder.