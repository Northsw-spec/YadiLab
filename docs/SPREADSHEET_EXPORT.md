# Export current network documentation to XLSX / ODS (PR #27)

## Contract and user flow

Builder exposes **Exportera XLSX** and **Exportera ODS** beside the existing **Exportera JSON** action. The export uses the current *in-memory* project, including explicitly declared unsaved edits. It does not require Save, mutate working state, or change the local server's stored project files.

`POST /api/export/spreadsheet` requires exactly:

```json
{"project": {"schemaVersion":"1.3","name":"...","zones":[],"nodes":[],"links":[]},
 "format": "xlsx"}
```

The project above illustrates request structure only; empty networks are rejected. `format` is exactly `xlsx` or `ods`. A successful response contains a generic download filename and **base64 of actual XLSX/ODS binary bytes**. The browser constructs a Blob and starts an explicit file download. A server success only means the file bytes were created; browser acceptance tests independently verify actual download to disk. This is **not** the application's persistent Save operation.

The writer serializes only canonical, validated, declared facts into the documented table schema. Worksheet order is `Project` (1.3 only), `Devices`, `Interfaces`, `Links`, `Zones`, `StaticRoutes` (1.3 only). All declared identifiers, explicit link endpoints, interface enablement and IPv4, MAC and VLAN state, and ordered static-route records are preserved. The serializer is shared with the tested demo-template writers; export never copies demo facts into a user project. The actual strict XLSX/ODS importers parse the resulting binary file **before** it is returned, and any changed canonical data causes a hard HTTP 422 error.

## Supported versions and losslessness

**Schema 1.0** exports to the original four sheets. **Schema 1.3** exports with `Project!A2 = 1.3`, extended interfaces and static routes. No implicit upgrade of **schema 1.1/1.2** occurs; they return 422 until their exact data semantics receive their own interchange contract.

The current table contract cannot distinguish optional properties *absent* from properties explicitly set to `null` or a present-but-empty `staticRoutes: []`. Export therefore **rejects explicit null MAC/VLAN and explicit empty staticRoutes**, rather than silently dropping them. Missing optional properties are allowed. Empty networks, unsupported XML control characters, unsupported versions, invalid projects, or more than 5000 records in a table are rejected. Actual import limits (ZIP members, compressed size and XML size) remain binding. This is intentional fail-closed behavior, not a suggestion to replace unknown data with defaults.

The workbook does **not** contain a name column in the existing schema contract. Import asks for `projectName`; enter the original name if you require identical canonical `name` on roundtrip. Numeric coordinates may appear as Excel/ODS numeric cells; their arithmetic value is preserved. Source ID strings (including leading zeros) remain strings, never numeric spreadsheet identifiers.

## Verification

`tests/test_spreadsheet_export.py` checks canonical 1.0/1.3 roundtrip through genuine ZIP bytes and independently parsed ODF/OOXML, exact declared IDs/links, MAC/VLAN/routes, disabled ports/links, Unicode/XML special characters, rejection of unsupported/ambiguous versions and null facts, corrupt source model and invalid format, deterministic export and actual HTTP with unchanged stored disk SHA until explicit Save.

`tests/browser_smoke.py` obtains **real Chromium downloads** from both export buttons, persists the binary bytes, verifies their checksum equals the actual HTTP payload and that real XLSX/ODS parser roundtrips to the previously saved canonical project. It then uploads those exact bytes through the two import flows, verifies no autosave, explicitly saves actual project files and reopens them with matching SHA-256. The complete regression uses Chromium `DIRECT_HTTP` in CI.

## Known boundaries

A downloaded XLSX/ODS is **documentation**, not proof of network traffic, physical cabling, or external reachability. Arbitrary Excel/ODS layouts, formulas, macros, hidden data, additional device properties and inferred network connections remain unsupported. The original JSON export remains available where the spreadsheet contract cannot represent the canonical data without loss.
