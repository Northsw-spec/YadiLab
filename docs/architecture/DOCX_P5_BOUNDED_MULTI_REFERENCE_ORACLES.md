# DOCX-P5 — frozen bounded multi-reference report and browser oracles

**Source of truth**: current GitHub main 8962398cf769936942d756b00befd29eb495cb60, tree 912fc9011a7445b0882962a0c620f7bc979e3507. This is a pre-implementation frozen test contract, not a PASS statement. P1-P4 are already implemented, including P3 source-bound single-cell consent and P4 zero-value one-reference sidecar.

## Design decision

Provide an **additive** independent P5 multi-reference report for **2–10 individually operator-reviewed cells** from **one** local DOCX and **one** existing Builder scenario/revision. Never bulk-disclose cell values. Do not infer topology. Each row requires explicit review of its desired individual cell locators; no automatic row expansion.

Process per reference: P3 operator chooses one cell, checks consent, clicks reveal; P4 operator selects one existing resource and separately acknowledges unverified association; P5 offers Add reviewed reference to report next to existing P4 single export. P5 staging performs P3 full-file validation and current P4 model review, and stores **only P4 zero-content sidecar** (no cell text/hash) in ephemeral React state. Then repeat for another cell, separately acknowledge and export multi-reference report. Never reuse consent automatically.

Up to ten queued, unique table/row/cell locator AND unique Builder target. Show queued positions and target IDs, not cell text. Queue is tied to exact file source SHA256, Builder scenario and source revision. File switch or modal close discards queue. Builder identity/revision changes must invalidate report; no remapping. Queue is never persisted or exported without a final explicit click and separately unchecked acknowledgment.

## Export security and provenance

At final click, re-read same local DOCX and re-run P3 full ZIP/XML/SHA/sensitive validation on **every** queued locator without displaying returned text. Repeat P4 exact current Builder review for each. Fail entire export atomically for source change, stale revision, missing resource, invalid locator, newly blocked secret, malformed ZIP or over-budget source. No partial reports, raw values, untrusted filenames or errors containing content. Each queue member is P4 sidecar, never P3 disclosed value.

Pure P5 serializer requires 2–10 valid and precise P4 sidecars, no duplicates, same source SHA and model identity, appropriate single-cell typed locator, resource IDs, reviewed status, and false verification flags. Fixed schema yad ilab.docx-reviewed-multi-references (without space: yad ilab -> yad ilab; actual ID defined in code as yadilab.docx-reviewed-multi-references), schemaVersion 1.0.0, status REVIEWED_ASSOCIATIONS_ONLY, engineVerified:false, physicalTopologyVerified:false. Output only source-level SHA and typed locators with existing resource IDs. No cell values, content hashes, inferred links or Engine verdict.

## Negative and browser oracle

- P2 preview has no text; P3 one-cell disclosure and P4 one-item export still work. Queue not available without Builder and P4 acknowledgment. Final export disabled before two entries or final acknowledgment.
- Selecting a new cell revokes P3/P4 consent but preserves P5 metadata-only queue. Switching source file clears queue even if filename is identical.
- Duplicate source cell or destination blocks; 11th item blocks; malformed sidecar/unknown properties, forged cell locator, source SHA/model mismatch, stale revision all block.
- Builder canonical JSON exact deep equality before/after upload, staging, download. No other-origin browser requests or JavaScript crashes.
- Actual GitHub Actions Chromium interaction tests on compiled YadiLab plus independent negative/SSR tests and all existing format regressions. Exact-head GitHub Actions SUCCESS required. No manual Parrot requirement.

## Truth boundary

Only operator-selected document-cell references. Not proof of identity, physical network, routing, reachability, or Engine PASS. P3 secrecy filter does not guarantee detection of all sensitive values. No automatic full-row disclosure or persistent secrets.