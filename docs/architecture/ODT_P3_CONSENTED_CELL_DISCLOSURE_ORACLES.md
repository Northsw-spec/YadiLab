# ODT-P3 — frozen consented one-cell local disclosure security and browser oracles

**Source authority:** latest GitHub main `ea2f518901985659cd198cff6e7da12cb926a96b`, tree `212dfd1a0f1a44fae50481ce0e19fddbfb432de0`. This contract is committed before any implementation. No claims of CI success here.

## Existing verified mechanisms

- ODT-P1/P2: strict original OASIS ODT ZIP first STORED mimetype, manifest/MIME, bounded XML and table grammar; `previewOdtTableStructure` only source original SHA256, typed locators and lengths.
- DOCX-P3: `docx-cell-disclosure.ts`, strictly local one cell after a fresh full source validation + exact SHA/typed locator, conservative value/header/row label secret blocking.
- `ui/app/odt-structure-panel.mjs`: P2 structure-only modal, reused unchanged in default flow; select file creates a new review lifetime.
- OWASP file upload guidance and OASIS ODF 1.3 packages/schema: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html , https://docs.oasis-open.org/office/OpenDocument/v1.3/OpenDocument-v1.3-part2-packages.html , https://docs.oasis-open.org/office/OpenDocument/v1.3/OpenDocument-v1.3-part3-schema.html .

## Positive oracle

- P2 remains default **masked**; P3 is an optional separate panel below the structure summary. Source content is never automatically visible on file selection.
- One selected table/row/cell locator at a time; default selection empty and checkbox unchecked. Selecting a cell does not reveal it. Explicit checkbox acknowledgment PLUS button click required to reveal that ONE cell. No bulk API, no DOM injection.
- At click re-read exact original browser-local .odt, strict max 16MiB, validate *entire* P1 original ZIP/manifest/ODF structure, require exact SHA256 equality with P2 result and source-bound **exact-shaped typed locator**. Then parse original `content.xml` with same bounded zip and XML parsing and extract only selected plain text:p. Verify UTF-16 code unit length equals P1 structural preview.
- Block obvious passwords, secrets, tokens, long random-looking or credential-like strings, URLs/e-mails, markup and nonconservative characters, and cells within password-/secret-named first-row header or first-column row labels. Errors are stable diagnostic codes only and may not include the value or path. A filter is only a safeguard, not a guarantee of non-sensitivity.
- Render only selected value ephemerally in React. Changing cell or file, clearing consent, hiding, closing, reopening, failing P3, or stale asynchronous read clears old value. No persistence, export, Builder/Engine changes, real topology claims or network requests. `REVEALED_UNVERIFIED`, `CONFIG_DOCUMENTED`, canActivate:false, engineVerified:false, physicalTopologyVerified:false.

## Negative oracle

- Same apparent filename with changed bytes must fail original-source SHA check. Forged locator kind/part/hash/extras/fraction/out-of-range blocks. An unacknowledged call must reject even for benign cell. Changing cell cancels old in-flight result. Uploading another source immediately hides old value and consent, even if SHA/file name is the same.
- Reject unsupported/repeated/nested/merged ODT, DTD, external/script members, malformed ZIP, wrong mimetype/manifest, budget overflow from P1 for P3 too. HTML, Base64-like, long tokens, password header/row, secret canaries never shown.
- Independent actual ODT ZIP positive and malicious tests using test-only custom ZIP writer, SSR masked UI, exact source SHA/provenance, no other values in one-cell disclosure, and actual built Chromium clicks for consent, selection, secret blocks, file/source switch, hide/close/reopen, unchanged Builder canonical JSON and no external browser requests or JavaScript errors.
- All exact-head triggered GitHub Actions for P1/P2, DOCX, GraphML, Nmap, Ansible and broad import MUST be green; then merge and independently verify Linux release exact merged main SHA, uploaded artifact. User-approved GitHub Actions SUCCESS is sufficient; no manual Parrot test requirement.

## Truth/security limitation

The conservative filter cannot guarantee discovery of all confidential values. P3 is a consciously authorized local reveal, not a safe-to-publish certification, automatic ODT import, identity proof or verified physical network topology.