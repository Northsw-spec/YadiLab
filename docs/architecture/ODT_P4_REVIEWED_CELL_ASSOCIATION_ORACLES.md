# ODT-P4 — frozen one-cell to existing Builder resource sidecar contract

**Authoritative baseline:** GitHub `main=8169c7609fff301a5ff503541912c3ae3a24d37d`, source tree `fa418f82d197852bb22c964b8f598d90d9ab2e17`. PRE-implementation contract, not a claim of test success. Respect AGENTS.md and only current-main source. Sources examined: ODT-P1/P2 OASIS ZIP/XML bounded parser; `odt-cell-disclosure.ts` P3 exact SHA, one-value secret filter; existing DOCX-P4 `docx-association-review.ts`, `docx-reviewed-cell-association.mjs`, `docx-structure-panel.mjs`; GitHub Actions acceptance policy.

## Functional acceptance

- User chooses and explicitly reveals ONE ODT cell via P3. Only then optional P4 panel appears. User explicitly selects an **already modeled** Builder resource and ticks a **second, unchecked** assertion that this linkage is operator-declared and unverified. Click **Export reviewed ODT reference (JSON)**. No automated semantic matching, inventory creation, links or Builder/Engine modifications. Runtime mode has no Builder target.
- Export occurs only after **re-reading the original local ODT** and rerunning the complete P3 source/ZIP/mimetype/manifest/XML + secret/label validation with exact P3 source SHA and typed cell locator. The second review's **actual text must be equal to the explicitly shown P3 value**, and original source/file selection generation must still be current. Old or switched file, wrong original SHA, source XML changed, edited locator, newly blocked secret => block.
- On export revalidate **CURRENT Builder snapshot** (not only the one displayed on panel): exact scenarioId, sourceRevision, distinct valid IDs and membership of one selected target. Duplicate/prototype-like resource IDs or stale/removed target => block.
- Sidecar is downloadable **external JSON only**: formatId `yadilab.odt-reviewed-cell-references`, schemaVersion `1.0.0`, status `REVIEWED_ASSOCIATIONS_ONLY`, source profile `office.odt-tables.structural.v1`, original ODT file SHA256, typed source table/row/cell locator, semanticTrack `CONFIG_DOCUMENTED`, target current scenarioId/revision/resourceId, association assertion `USER_ASSERTED_ASSOCIATION_NOT_VERIFIED`, `engineVerified:false`, `physicalTopologyVerified:false`, warning of unverified factual identity. **No original cell contents, cell-level SHA, snippets, inferred IPs, passwords, or complete original document in JSON.** No source/Engine/Builder changes.
- On P3 hide/selection/file change, second consent/target reset and association panel unmounts. Closing/reopening resets all. No persistence and no remote network access.

## Negative and independent tests

- Positive with independently built **real OASIS ODT STORED mimetype ZIP** and benign `node01`, exact typed locator and original SHA; sidecar deterministic, secret-free. Wrong consent, wrong source SHA, stale model/revision, removed target, invalid/duplicate/prototype IDs, altered P3 truth flags/locators and bad source => fail closed with code-only diagnostics.
- Sensitive ODT cell and a benign literal under Password column remain blocked by P3 before P4; changing file to another .odt (even same filename) clears all P3/P4 local state and revalidation fails when original bytes changed. Single export must not be possible before both consents.
- Independent TypeScript/Node/SSR test, actual compiled GitHub Ubuntu Chromium file upload/reveal/choose-target/second-consent/download, inspect downloaded JSON for schema and **no raw text**, verify Builder source canonical JSON deep equality before/after, no JS errors/remote requests. Run P1-P3, DOCX, GraphML, Nmap, Ansible regressions on exact PR commit; require all-green CI before squash merge and exact merged-main Linux release CI SUCCESS with uploaded artifact. No user manual Parrot gate.

## Scientific caution

P4 proves only an **operator-selected reference**, not true device identity/physical topology or Engine PASS. P3 sensitive marker filtering cannot guarantee all secrets are detected. This checkpoint adds ONE reference sidecar, not P5 multi-reference or replay.
