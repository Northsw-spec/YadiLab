# Phase 60 — safe XLSX and ODS enterprise import

Masterprompt authority: v1.3 VERIFIED / LOCKED.

Phase 60 extends the Phase 59 trusted/versioned Enterprise Import Adapter Framework with first-release spreadsheet containers while keeping the normalized Enterprise Model format-independent.

## Supported workbook media types

- XLSX: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- ODS: `application/vnd.oasis.opendocument.spreadsheet`

Legacy binary XLS, XLSM/macro-enabled workbooks and arbitrary office containers are not accepted by these adapters.

## Archive boundary

Spreadsheet containers are opened through a generic archive backend. Production uses the already pinned `zip.js` implementation; workbook semantics do not depend on zip.js APIs. Tests inject an independent Node-only ZIP backend so XML/tabular behavior can be verified without pretending the external npm dependency gate is satisfied.

Before workbook XML is consumed, the archive layer enforces:

- relative forward-slash paths only;
- no traversal/absolute/drive-letter paths;
- no duplicate file paths;
- bounded member count;
- bounded compressed/decompressed size;
- bounded per-file size;
- bounded compression ratio;
- declared vs actual decompressed size consistency.

## Safe XML boundary

A constrained local XML parser is used for workbook semantics. It:

- decodes only standard/numeric XML entities;
- rejects DTD/ENTITY declarations;
- rejects non-XML processing instructions;
- rejects malformed/duplicate attributes;
- bounds nesting depth and node count;
- performs no external entity/schema/resource resolution.

## XLSX behavior

The adapter reads workbook/sheet relationships, sheet XML and shared/inline strings. It:

- detects multiple sheets by their real workbook names;
- maps each imported value to a `table-cell` provenance locator (`sheet`, physical `row`, Excel column letters);
- rejects VBA, ActiveX and embedded OLE parts;
- rejects external workbook/data relationships;
- never follows external hyperlinks;
- never evaluates formulas;
- imports a cached formula value only with `IMPORT_WORKBOOK_CACHED_FORMULA_VALUE` warning;
- treats a formula without a cached value as missing with a warning.

## ODS behavior

The adapter reads `content.xml`, validates the ODS mimetype when present, and inspects the manifest. It:

- detects multiple named sheets;
- preserves physical cell provenance;
- handles bounded repeated rows/columns without uncontrolled expansion;
- rejects Basic/Scripts active content;
- rejects encrypted members;
- rejects external table/data sources;
- ignores ordinary hyperlinks without fetching them and emits a warning;
- never evaluates formulas; cached values follow the same warning rule as XLSX.

## Header selection

Default header row is physical row 1. Deterministic options may specify:

- `headerRow: N` for all sheets;
- `headerRows: { "Sheet Name": N }` for per-sheet overrides.

The selected row must contain unique non-empty headers after deterministic Unicode/whitespace normalization.

## Official template

`examples/enterprise-import/` contains XLSX and ODS templates plus a matching mapping profile. The template demonstrates:

- multi-sheet detection;
- required vs optional fields;
- explicit `UNKNOWN` for undocumented gateway;
- per-cell provenance;
- unmapped-field reporting.

The template is an offline convenience, not a special-case parser. It uses exactly the same adapter/mapping/normalization pipeline as arbitrary supported workbooks.

## Security/semantic non-claims

This phase does not claim:

- execution/evaluation of Excel/Calc formulas;
- VBA/macro support;
- external workbook refresh;
- legacy `.xls` parsing;
- dependency-resolved production zip.js execution in the current sandbox;
- browser Import Helper UI completion;
- Parrot/browser acceptance.

Those remain separate gates/phases.
