# Release notes v0.59.0

Phase 59 adds the deterministic Enterprise Import Adapter Framework required by Masterprompt v1.3.

The checkpoint introduces versioned mapping profiles and import reports plus dependency-free JSON, CSV and TSV adapters. All source formats emit the same intermediate record model and normalize into the Phase 58 Enterprise Baseline model. Exact source hashes, mapping-profile hashes, field-level provenance, mapping classes, explicit UNKNOWN/INVALID states, unmapped-field reporting and duplicate-entity conflicts are preserved.

This checkpoint does **not** claim XLSX/ODS/GraphML/Nmap XML support yet. It also does not change the existing external browser dependency / Parrot acceptance blockers.
