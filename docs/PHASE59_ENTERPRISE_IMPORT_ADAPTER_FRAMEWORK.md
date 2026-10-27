# Phase 59 - Enterprise Import Adapter Framework

Authority: YadiLab Masterprompt v1.3 VERIFIED / LOCKED.

Phase 59 builds the first source-format adapters on top of the Phase 58 Normalized Enterprise Model. Source format is deliberately kept outside Runtime semantics.

## Implemented

- trusted, versioned `EnterpriseImportAdapter` contract;
- exact media-type adapter selection with fail-closed ambiguity/unsupported handling;
- dependency-free UTF-8 JSON, CSV and TSV adapters;
- RFC4180-style quoted CSV/TSV record parsing including escaped quotes and quoted line breaks;
- deterministic header normalization used only for explicit ALIAS/USER_MAPPED matching;
- versioned mapping-profile Draft 2020-12 schema;
- explicit mapping classes: `EXACT`, `ALIAS`, `USER_MAPPED`;
- import-report Draft 2020-12 schema with READY/BLOCKED status, diagnostics, unmapped fields, conflicts and transparent counts;
- exact raw-source SHA-256 and content-addressed `src_<sha256>` IDs;
- canonical mapping-profile SHA-256;
- per-imported-value provenance including source locator, raw-value hash, mapping ID and mapping class;
- entity provenance references;
- deterministic creation of normalized entity/fact IDs;
- required-field blocking versus optional explicit `UNKNOWN` handling;
- explicit `INVALID` facts when values cannot be deterministically converted;
- conservative duplicate-entity conflict reporting rather than silent merge;
- transparent unmapped-field reporting;
- same source bytes + same adapter/mapping/options replay to the same baseline identity;
- format-independent semantic result tests across CSV, TSV and JSON.

## Safety and determinism boundary

Adapters parse DATA only. They do not execute source-provided code, do not mutate Runtime state, do not fuzzy-merge entities, and do not fabricate missing infrastructure facts. JSON source structure, delimited quoting, header ambiguity, missing structural fields, invalid values, entity collisions and media-type mismatch all fail closed or remain explicitly UNKNOWN/INVALID as defined by the mapping profile.

## Next phase

The next recommended checkpoint is the spreadsheet adapter layer: safe XLSX + ODS parsing into the same adapter document contract, followed by multi-sheet mapping and import dry-run/report fixtures. No spreadsheet-specific semantic state may be introduced.
