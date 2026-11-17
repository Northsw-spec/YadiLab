# Downloadable schema 1.3 workbook templates and diagnostics (PR #26)

## How to use

In Builder, under **Sparade projekt**, choose **Excel-mall (.xlsx)** or **Calc-mall (.ods)**. These are real files delivered by the local server at:

- `GET /api/templates/xlsx` → `network-schema13-demo.xlsx`
- `GET /api/templates/ods` → `network-schema13-demo.ods`

Each response uses a binary MIME type, an attachment filename, an explicit byte length and `Cache-Control: no-store`. It does not read, create or overwrite any stored project. Your browser decides where downloads are placed; the application does not claim that download succeeded without browser acceptance evidence.

Both workbooks follow the **same** schema-1.3 table definitions used by the XLSX and ODS importers (see [SPREADSHEET_V13.md](SPREADSHEET_V13.md)). They contain six sheets: `Project`, `Devices`, `Interfaces`, `Links`, `Zones`, and `StaticRoutes`. Example data includes a client, two switches, VLAN 10 access ports and a trunk with explicitly allowed VLANs 10 and 20, a router and a static route to the example subnet 203.0.113.0/24.

**Every device and link is explicitly labeled `DEMO` or named `demo-...`.** These are fictitious documentation examples using reserved documentation IPv4 networks, *not* information collected from a real environment. The router's example WAN interface is deliberately **not connected**, and the static route is not a promise of reachability. Replace or delete all demo rows with your own verified facts before using the workbook as inventory. Remember to keep IDs consistent across worksheets and to document physical links only in `Links`.

Import the edited file with **Importera**. The complete workbook is validated **before** Builder asks whether to replace existing unsaved work. A successful import stays unsaved until the user explicitly selects **Save**.

## Error messages

For explicitly versioned MAC, VLAN, IPv4 and static-route configuration failures, the importer maps canonical model object indices back to their **original worksheet rows** and the **actual header order**. Examples:

- `Interfaces!F2 (mac): ...` — MAC cell F2 on the Interfaces sheet, not some generated default MAC
- `Interfaces!H3 (accessVlan): ...` — VLAN ID at H3
- `StaticRoutes!D2 (nextHop): ...` — declared gateway at D2
- `Project!A2 (schemaVersion): ...` — wrong version marker
- `Interfaces!1 (header): ...` — wrong columns in the first row

The reference uses spreadsheet row numbers (header row = 1). A reordered column is reported at its **new physical column**, not its old canonical position. The parsers also report the actual sheet/cell for unsupported XLSX/ODS cell data and sheet/header violations. Where a source location cannot be proved, the underlying validator error is preserved without guessing. No automatically proposed repair is applied.

An invalid workbook returns HTTP 422 and cannot replace the working project or change saved data.

## Independent verification

`tests/test_spreadsheet_templates.py` performs real ZIP/XML inspection, downloads both binary files over localhost HTTP and reimports them through the actual XLSX/ODS readers, comparing canonical equality and retained MAC/VLAN/route facts. Negative tests verify invalid and reordered-column data really produce accurate source cell references.

`tests/browser_smoke.py` uses **real Chromium downloads**, saves the returned bytes to disk, reuploads exactly those bytes, verifies the resulting schema-1.3 working project and no autosave, and explicitly saves/reopens a real file with unchanged SHA-256 for all prior projects. Compiled-CI tests are required to use **DIRECT_HTTP**.
