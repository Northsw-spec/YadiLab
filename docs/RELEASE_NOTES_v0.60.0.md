# Release notes — Foundation v0.60.0

Classification: VERIFIED DEVELOPMENT CHECKPOINT candidate until final packaging/readback completes.
Authority: Masterprompt v1.3 VERIFIED / LOCKED.

## Phase 60

Safe first-release spreadsheet adapters:

- XLSX (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
- ODS (`application/vnd.oasis.opendocument.spreadsheet`)

Both normalize into the existing Enterprise Import / Normalized Enterprise Model pipeline.

### Implemented

- asynchronous import-adapter contract for archive-backed formats;
- generic bounded workbook archive layer using production zip.js through the existing archive abstraction;
- independent injected test ZIP backend so workbook semantics are tested without fabricating npm dependency readiness;
- constrained XML parser with no DTD/custom entities/external resolution;
- XLSX workbook/sheet relationship resolution;
- ODS content/manifest parsing;
- multi-sheet detection using real sheet names;
- physical `table-cell` provenance (`sheet`, row, column);
- global and per-sheet header-row selection;
- XLSX shared/inline string, boolean, numeric, string and cached-formula value handling;
- ODS string/numeric/boolean/date/time/cached-formula value handling;
- bounded ODS repeated row/column expansion;
- external workbook/data links blocked;
- normal hyperlinks never fetched and ignored with warning;
- XLSX VBA/ActiveX/OLE content rejected;
- ODS Basic/Scripts and encrypted members rejected;
- duplicate/traversal/oversized/high-ratio archive content rejected;
- offline XLSX + ODS enterprise import templates and mapping profile.

### Deliberately not implemented/claimed

- formula execution;
- VBA/macros;
- external workbook refresh;
- legacy binary `.xls`;
- full browser Import Helper UI;
- dependency-resolved zip.js execution in the current sandbox;
- Parrot OS/browser acceptance.
