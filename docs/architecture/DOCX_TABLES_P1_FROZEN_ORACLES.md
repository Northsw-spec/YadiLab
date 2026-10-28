# DOCX-TABLES-P1 — frozen narrow structural oracle (before implementation)

Status: P1 architecture and independent acceptance contract. Authoritative coding base is current GitHub main at checkpoint start: `3d0871263496f7d9a230033c8e40f35962e46633`; no archive code imported.

## Primary specifications reviewed

- ECMA-376 (OOXML): https://ecma-international.org/publications-and-standards/standards/ecma-376/
- Microsoft WordprocessingML table construction: https://learn.microsoft.com/en-us/office/open-xml/word/working-with-wordprocessingml-tables
- Packaging relationships and content types: ECMA-376 Part 2, Open Packaging Conventions.

## Positive oracle

Only `office.docx-tables.structural.v1` is introduced, with `CONFIG_DOCUMENTED`, `REVIEW_REQUIRED`, `canActivate:false`. The `word/document.xml` document part is determined by a *single* internal package-level `officeDocument` relationship pointing to exactly `word/document.xml` and a matching main-document content-type Override; no arbitrary package target or links are followed.

A self-contained DOCX ZIP with correct [Content_Types].xml, _rels/.rels, word/document.xml, WordprocessingML namespace, 1 table with 2 rows and 2 cells per row must return exactly 1 table, two row summaries, 4 cell locators `{kind:"docx-table-cell",sourceSha256,part:"word/document.xml",tableOrdinal:0,rowOrdinal,cellOrdinal}`. Every summary records structural length only (no cell value, address, password or text). Original raw byte SHA256 must equal independent Node crypto; deterministic reparse must have identical output.

## Bounded P1 subset

- ZIP max 16 MiB compressed source, 128 archive members, 32 MiB advertised expanded, 4 MiB member, max compression ratio 100. XML input bounded independently, max 1 MiB document XML.
- Up to 20 direct body tables, 200 rows/table, 16 cells/row, 2000 total cells, 4096 Unicode code units/cell; no automatic interpretation.
- Support only plain direct body `w:tbl` / `w:tr` / `w:tc` and `w:p` / `w:r` / `w:t` cell paragraphs, including run fragments. No nested tables, `gridSpan`, `vMerge`, external package relationships, revision markup, embedded objects/media interpretations, alternate chunks, field code evaluation, textboxes, macros or custom XML execution.
- **Security decision:** P1 outputs *only structure, integer text lengths and typed locators*, not raw Word table text, secret-bearing fields, HTML, sanitized excerpts or hashes of individual cells. There is no UI file picker and no scenario activation. Future P2 content-preview behavior requires independent secrets/redaction design and real Chromium tests. This is deliberate, not a claim of fully supported DOCX.
- Never register as active workbook adapter nor mutate existing builders, source workspace, links, Engine, observability or existing formats.

## Negative oracle (strict full-source block)

Reject wrong ZIP, missing metadata, duplicate paths, traversal, wrong main relationship, externally targeted relationship, wrong content type, macro/embedding, DTD, unexpected namespace, nested/merged tables, unsupported child shapes/revisions, excessive rows/cells/text/XML, and invalid source bytes. No partial structural preview. Negative diagnostics must not contain document text, secret canaries or arbitrary attacker paths.

## Verification

Exact-head CI: TypeScript build; independent synthetic ZIP fixtures generated with existing locked @zip.js/zip.js; byte-hash, shape, deterministic, negative budget/macro/link tests; prior CSV/XLSX/ODS and GraphML/Nmap/Ansible regressions, Git release metadata. CI PASS on GitHub Ubuntu is sufficient for the coding checkpoint; no user Parrot gate. Later UI P2 and actual Chromium test are **NOT INCLUDED** in P1.
