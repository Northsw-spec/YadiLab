# ODT-P6 — frozen read-only saved-reference replay oracles
Status: PREP / NOT IMPLEMENTED / NOT TESTED at initial commit. Authority at PREP: main `15c3fd9fd6d4e0f4509c8860b7bf52feb54eb59d`; source tree `41c6bc31e05206a58d1b39faa8f4374135ec64c9`. Project policy: AGENTS.md.

## Scope and limits
A local operator may deliberately inspect an already exported ODT-P4 single-reference or ODT-P5 bounded 2–10-reference metadata-only JSON against the **original exact .odt bytes** and the **current existing Builder scenario/sourceRevision/resources**. Original ODT values must never be displayed, logged, exported or persisted by replay. A saved report's status and flags confer no trust. Match is evidence only of source bytes, document locators and currently modeled Builder reference IDs, not real device identity, measured network facts, or Engine success. No scenario import, Builder edits, Engine runs, network calls, or local storage.

The user selects two local files independently and ticks an initially-unchecked acknowledgment before a manual Verify action. Any file replacement, modal close/reopen, missing Builder or changed generation invalidates prior status/consent. In-progress async results from stale generations must not render.

## Immutable positive cases
- Exactly preserved P4 and P5 exports generated via actual P3/P4/P5 validation of real OASIS-compliant ODT fixtures reproduce **canonical exact structured JSON**, including warnings, schemaVersion, semanticTrack, source SHA256, typed original cell locators, targets and negative trust flags.
- P4 one locator and P5 2–10 unique locators/targets are re-disclosed using existing full ODT P1/P3 bounded ZIP, mimetype/manifest/content.xml and sensitive-content gates before P4 association regeneration against the current model; P5 then reaggregates with existing pure P5 function.
- Report input: basename .json with strict UTF-8 and byte limit 64KiB; ODT basename .odt with 16MiB limit, no path traversal or filename echoes. Canonicalization bounded by depth/node/key/array limits. Comparison must include every original report key and warning.
- Result: `REFERENCE_REPLAY_MATCH`, source-level SHA256, format ID, 1 or 2–10 reference count, `CONFIG_DOCUMENTED`, `identityVerified:false`, `physicalTopologyVerified:false`, `engineVerified:false`, `modelMutated:false`. No individual cell text or cell-value hash.

## Mandatory negative / adversarial oracles
No consent; absent Builder or either file; wrong type/extension, path separator, malformed/oversized/invalid UTF-8/array/extra fields/deep JSON; unsupported format/version; tampered warnings, assertion, elevated trust flags; changed source bytes under same filename; invalid ODT ZIP/mimetype order/compression/DTD/manifest; credential header or sensitive cell; missing/duplicate/forged resource; changed Builder scenario/revision; 0/1/11 P5 refs, duplicate source/target; out-of-bounds locator. **All fail closed** with stable diagnostic codes and no partial MATCH.

## CI and real browser
Independently generate OASIS ODT ZIP and reference JSON through production P3/P4/P5 functions in source tests; include SSR negative controls. On an actual compiled YadiLab Chromium instance, exercise source upload, P4/P5 export (two independent cell permissions), saved JSON selection, consent, successful replay and tamper / wrong-original failures; verify modal reset, absence of raw values and exact unchanged canonical Builder JSON. Run existing ODT P2–P5, DOCX P2–P6, GraphML, Nmap and Ansible regressions at the same exact PR-head SHA. GitHub Actions SUCCESS is the authorized acceptance gate for tested Ubuntu behaviors. Verify main merge SHA and independent Linux artifact after merge.

## Sources
- Actual YadiLab source: `enterprise-import/src/odt-tables-structural-preview.ts`, `odt-cell-disclosure.ts`, `odt-association-review.ts`, `odt-multi-reference-review.ts`; real DOCX-P6 source is design reference, **not** substitute ODT validation.
- OASIS OpenDocument specification (ODT ZIP/mimetype/content.xml conventions).
- OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- RFC 8259 JSON: https://www.rfc-editor.org/rfc/rfc8259
