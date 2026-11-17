# Explicit XLSX workbook import (first bounded Excel format)

## Intended use and scope

A network consultant may receive documentation as an XLSX workbook. This implementation accepts **one explicit interchange format**, not arbitrary exported Excel documents or inferred network facts. It is the *same* schema 1.0 four-table contract already used by the CSV importer:

| Worksheet name | Required | Exact header cells (any order) |
| --- | --- | --- |
| `Devices` | Yes | `id,label,kind,x,y,zoneId` |
| `Interfaces` | No | `nodeId,id,name,enabled,ipv4` |
| `Links` | No | `id,aNode,aPort,bNode,bPort,enabled` |
| `Zones` | No | `id,label` |

Each worksheet's first row contains **all and only** its defined headers. Further rows contain explicit data. Blank *cells* are represented as empty CSV fields; completely empty records and gaps in declared row numbering are rejected. Only declared `Links` rows create physical links; a matching IPv4 address, geographical zone, name or screen position never creates a port/cable.

The only supported canonical result is **schema version 1.0**, so MAC bindings, VLAN settings, static routes, custom notes, additional columns and worksheet annotations are **not** silently imported. A workbook carrying them is rejected (unsupported columns/parts) until a separate versioned contract is implemented. No data may be guessed or dropped.

## XLSX byte-level contract

`POST /api/import/xlsx` accepts exactly `filename` (one `.xlsx`), `projectName` (1–120 characters), and `contentBase64` (standard base64 of the raw ZIP bytes). Hard limits: **5 MiB compressed**, **12 MiB total expanded**, **5 MiB per XML part**, **24 archive entries**, and **5001 rows per sheet** (header + 5000 data records).

The standard OOXML workbook manifest and local worksheet relationships identify the named sheets. Sheet order, generated worksheet filenames, and column order are not assumed. The importer recognizes normal inline strings, plain shared strings, numeric coordinates, and native boolean `enabled` cells; all device/port/link IDs remain literal **text** to avoid Excel's numeric normalization destroying leading zeros. Unsupported numeric identity cells, formulas/cached formula values, cell errors, rich-text shared strings, hidden sheets/rows/columns, merged cells, drawings, external links, embedded objects/macros, unexpected worksheet parts, out-of-range/duplicate coordinates, malformed XML, corrupt ZIP archives, duplicate archive members and unsupported OOXML package parts are rejected with HTTP 422 rather than skipped.

`network_core/xlsx_import.py` converts the declared cell matrix to CSV records **in memory**, using the exact `csv_import.TABLES` schema and existing `import_csv_tables`. Only that existing path creates and validates the canonical graph, its identities, explicit zone references, endpoints and boolean states. No second model/import validation implementation and no filesystem writes.

## UI and Save

In the Builder choose **Importera**, select one XLSX, and enter a project name when asked. The browser sends the raw workbook bytes, never `File.text()` (which would corrupt binary data). On **successful complete validation**, Builder asks whether to discard unsaved changes and separately whether to replace the workspace. Cancel, invalid documents and HTTP 422 preserve existing working document and actual stored bytes. An accepted import remains **unsaved** until the user clicks **Save**.

The XLSX import itself does not prove external reachability, authentic device inventory, or that Excel's presentation is correctly configured; it only confirms the declared table content conforms to the import model.

## Verification

`tests/xlsx_fixture.py` creates genuine OOXML ZIP workbooks independently of the import parser, with both inline/shared-string cells, native numeric coordinates and booleans, reordered columns and worksheets. `tests/test_xlsx_import.py` tests comparison against the existing CSV importer, exact IDs and endpoints, optional empty tables/no implicit links, Unicode and multiline names, duplicate IDs, bad references, wrong headers, numeric ID loss, formulas, hidden data, out-of-range cells, external parts, damaged ZIP and real loopback HTTP with unchanged saved files until explicit Save.

`tests/browser_smoke.py` supplies those **real binary XLSX bytes** through Chromium's actual file-upload input and local HTTP, verifies invalid hidden sheets are rejected without data loss, validates a reordered shared-string workbook, confirms it does **not** autosave, then explicitly saves a real project file and reopens it through the UI while preserving the previous CSV project's SHA-256.
