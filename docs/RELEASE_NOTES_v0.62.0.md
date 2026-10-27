# Release notes — Foundation v0.62.0

Phase 62 implements deterministic three-way enterprise baseline merge and preservation.

Key additions:

- `enterprise-reimport-merge-plan.schema.json` and generated contract,
- `planEnterpriseReimportMerge`,
- `applyEnterpriseReimportMerge`,
- canonical merge-plan SHA-256,
- explicit `CURRENT` / `INCOMING` / `DELETE` review resolutions,
- fail-closed stale/tampered plan detection,
- baseline lineage bound into canonical identity,
- relationship-aware re-import diff,
- provenance/source pruning and preservation,
- post-merge full Enterprise Model verification,
- no-op re-import identity preservation,
- functional/adversarial merge regression suites.

Browser Import Helper UI remains a later phase. Scenario/fault overlays remain intentionally separate from imported baseline merge.
