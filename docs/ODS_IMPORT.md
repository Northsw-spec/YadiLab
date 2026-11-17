# OpenDocument Spreadsheet import — explicit four-table ODS (PR #24)

## Scope and source identity

A single genuine **.ods** file may contain named worksheets `Devices` (required), `Interfaces`, `Links`, and `Zones` (optional). Each must have exactly the **same headers, in any order**, as the documented CSV files. Table and column order may differ. The importer does **not** guess network assets from arbitrary spreadsheet columns, IP, geography or nearby visual positions.

| ODS table | CSV contract | Exact column names |
| --- | --- | --- |
| Devices | Devices.csv | id, label, kind, x, y, zoneId |
| Interfaces | Interfaces.csv | nodeId, id, name, enabled, ipv4 |
| Links | Links.csv | id, aNode, aPort, bNode, bPort, enabled |
| Zones | Zones.csv | id, label |

The result is always a **validated canonical schema 1.0 document**. Richer fields (MACs, VLANs, static routes and arbitrary notes) are **not** imported or silently discarded; unrecognized additional columns or worksheet content are rejected.

## Physical ODF package and cell semantics

The import reads a real ODF ZIP archive, not XML masquerading as ODS. The first ZIP entry must be uncompressed `mimetype` with value `application/vnd.oasis.opendocument.spreadsheet`. Required files include `content.xml` and `META-INF/manifest.xml` with declared spreadsheet root and content entries. Supported optional package members are `styles.xml`, `meta.xml`, and `settings.xml`; unlisted/unknown ZIP entries, macros, external resources, ZIP duplicates and encryption are rejected.

Every data worksheet must be visible, explicitly named and contain a header row with exact named columns. Plain ODF text cells (`office:value-type="string"` with `text:p`) preserve IDs and Unicode, including intentional text line breaks and tabs. Literal numeric cells are accepted **only** for `x` and `y`, and boolean cells **only** for `enabled`. A number where an ID is required is not accepted (e.g. Excel-style numeric coercion/leading-zero loss). Unknown cell value types, spreadsheet formulas, rich markup, merged/covered cells, filtered/hidden rows or columns, unrecognized table objects or undocumented attributes are rejected rather than guessed.

ODF writers may compact repeated empty cells and trailing blank rows. Those are accepted only if **empty**, with no further populated rows after padding. Repeated nonempty cells/rows are rejected. The importer keeps the four-table row order and does not invent entities, links or inferred port attachments. All imported data goes through the existing `csv_import.TABLES` and `import_csv_tables` canonical validation chain.

## HTTP and Builder

`POST /api/import/ods` takes exactly `filename`, `projectName`, and `contentBase64` (base64-encoded raw file bytes). Limits are 5 MiB compressed, 12 MiB expanded, 5 MiB per part, 10 ZIP entries and 5000 populated rows per table; invalid input yields HTTP 422.

Builder's existing **Importera** accepts one `.ods` file, reads its bytes with `arrayBuffer()`, and invokes the local HTTP endpoint. **Only after the entire ODF and canonical project validate successfully** does Builder request permission to discard unsaved changes and replace the current workspace. An imported project stays unsaved until explicit **Save**. No hidden overwrite, automatic on-disk changes, or claims of real network reachability.

## Verification

`tests/ods_fixture.py` creates independent real ODF ZIP bytes with correct manifest/mimetype, reordered tables and columns, numeric/boolean/string data, Unicode, line breaks and repeated trailing blank cells. `tests/test_ods_import.py` independently compares the canonical result with the existing CSV importer; checks exact source IDs and link endpoints, missing/optional tables, disabled links, invalid cross-references, formulas, hidden rows/sheets/columns, bad cell types, repeated populated values, external macros, corrupt archives, duplicate entries, invalid requests and real loopback HTTP with unchanged existing saved-file SHA-256.

The actual Chromium `tests/browser_smoke.py` supplies binary ODS uploads over direct localhost HTTP, rejects a hidden sheet without touching the workspace, imports a valid ODS after explicit prompts, confirms **no autosave**, checks disk Save and real reopen, and verifies older CSV/XLSX project bytes remain unchanged.

## Known limits

This is **not** a general LibreOffice or OpenDocument converter. Some valid ODS documents containing extra metadata, embedded resources, styles with semantic meaning, subtotals, merged cells, formula results, date formatting, annotations, protected ranges, external links, macros, or non-canonical naming are intentionally unsupported and rejected. Styles and data ranges outside the four-table contract do not create declarations.
