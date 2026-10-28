# DOCX-TABLES-P3 — Frozen per-cell deliberate disclosure and secrecy contract

Start: GitHub current main `5f022cadf9df24c1226eedd423b75853d673e9ba`, tree `23353179e21e8eb2c4a2276d46c605e6effcccde`. Branch `feat/docx-tables-p3-explicit-cell-review`. This ADR is pre-implementation, not test evidence.

## Research waves

1. Microsoft WordprocessingML reference: https://learn.microsoft.com/en-us/office/open-xml/word/working-with-wordprocessingml-tables — ordinary cell text lives in the bounded `document/body/tbl/tr/tc/p/r/t` path; Word includes other possible constructs. Only the already-established **P1 plain-table subset** may be considered.
2. OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html — suffix/MIME alone cannot validate file content; layered validation, size/ZIP-bomb budget, no automated code execution or external references. Reuse strict P1 ZIP/XML validations and do not persist raw document content.
3. Privacy limit: **No heuristic can guarantee that a benign-looking literal is not a password or personal information.** P3 therefore requires individual local operator disclosure, warns that confidentiality remains operator responsibility, and blocks obvious credentials and suspicious values/columns; it does not claim perfect sensitive-data detection.

## New feature vs inherited P2

- P2 default is still **structure only**. No filename/file-cell text revealed by simply choosing DOCX. Keep existing P2 selectors, P2 Chromium truth assertions, source SHA256, and Builder JSON unchanged.
- P3 adds **explicit selectable cell locator, unchecked-by-default disclosure consent, and one separate click** in read-only DOCX modal. Reveal only ONE cell at a time; other cell texts stay masked. Consent is reset on each new source or modal opening. Switching source or cell clears previous disclosure. Show only in the current local modal; never export, log, persist, setWorkspace, write scenario, call Engine, fetch URLs or include secrets in error messages.
- Backend revalidates original P1 DOCX package at disclosure click, independently compares the current original byte SHA256 and exact typed locator to the source preview; a stale/replaced file or forged position FAILS CLOSED. Same XML parse, ZIP limits and P1 grammar; no field evaluation.
- Narrow **literal display candidate**: nonempty printable ASCII 1–128 code units, ordinary safe network inventory labels/numbers/IPv4-like values; no links, HTML markup/control chars/URLs/emails, long high-entropy tokens, credential/key/password/secret/bearer-like values, or a cell in a password/token/credential-labeled table column/row. The test oracle must include a *benign-looking password in a column labeled Password*, which must block. Reject with only a stable diagnostic code, no substring of original data.
- Conditional user disclosure DOES NOT certify that data are non-sensitive. UI warning is explicit: **Only reveal cells you are authorized to view; sensitive values may not always be detected.** The resulting preview is `CONFIG_DOCUMENTED`, `REVIEW_REQUIRED`, `canActivate=false`; no verified asset identity, physical topology or Engine PASS.
- No sidecar or export in P3. Any future transformation/mapping requires a separately frozen schema and human review.

## Independent negative and browser oracles

1. Default P2 SSR/Chromium source/DOM/Builder export contains NO original cell strings, even though raw file was selected. P3 controls default unselected and unchecked.
2. After selecting exact 0:1:0 and acknowledging, explicit click displays `node01` only. No other cell contents appear, even with one secret canary in same row. Toggle consent off, switch cell/source, reject malformed source or close/reopen -> value disappears.
3. Selecting 0:1:1 when source has a secret canary returns `DOCX_CELL_SENSITIVE_BLOCKED` with NO raw secret value in DOM/logs. Other tests: `Password` header + benign-looking literal, URL/email, markup, newline, large value, token/high entropy, forged/wrong source SHA, invalid indexes, wrong part, different source same filename, zip bomb, DTD, unsupported nested cell, file-size/reparse.
4. Existing GraphML/Nmap/Ansible/YAML/INI and Excel/CSV/ODS regressions; actual compiled app Chromium file-selection, independent original SHA, no external network requests, no JS errors, Builder JSON identical before/after and no scenario/Engine mutation; CI exact-head success before merge. Ubuntu CI suffices; Parrot manual test NOT REQUIRED.

## Threat-model decision

This is a deliberately conservative **operator-visible, local-only, per-cell disclosure**, not an assurance that automatic secret detection is comprehensive. No auto-reveal of all table values or automatic document-to-network import is authorized in P3.
