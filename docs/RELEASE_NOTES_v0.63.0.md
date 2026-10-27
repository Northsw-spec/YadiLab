# Release notes — Foundation v0.63.0

Phase 63 implements the first browser **Import Helper UI** over the deterministic enterprise import stack.

Key additions:

- local XLSX/ODS/CSV/TSV/JSON source selection,
- deterministic media-type/extension gate,
- local mapping-profile loading and export,
- mapping-review display for tables, fields and RESOLVED/MISSING/AMBIGUOUS states,
- explicit USER_MAPPED review decisions with mapping-profile version bump,
- baseline import report and normalized baseline identity display,
- unmapped-field and uncertainty review,
- exact source-record conflict selection for duplicate entity IDs,
- re-import entity/relationship/fact diff display,
- Phase 62 three-way merge-plan display,
- explicit CURRENT/INCOMING/DELETE merge choices,
- browser helper functional/adversarial contract tests,
- permanent “Import Helper UI” terminology override without modifying the byte-locked Masterprompt v1.3 artifact.

Baseline-to-topology projection remains a separate next step; this checkpoint does not claim that imported enterprise entities are already converted into the visual scenario canvas.
