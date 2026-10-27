# Release notes — Foundation v0.61.0

Phase 61 implements deterministic enterprise mapping review, user-confirmed versioned mapping profiles, explicit duplicate-entity source-row resolution and deterministic re-import diff.

Key additions:

- `enterprise-mapping-review.schema.json` and generated contract,
- `enterprise-reimport-diff.schema.json` and generated contract,
- `runEnterpriseMappingReview`,
- `applyMappingReviewDecisions`,
- `compareEnterpriseBaselines`,
- exact `USER_MAPPED` provenance semantics,
- fail-closed stale/invalid conflict resolutions,
- semantic vs provenance-only re-import change classification,
- functional/adversarial regression suites.

Automatic baseline merge and browser Import Helper UI are intentionally not claimed in this checkpoint.
