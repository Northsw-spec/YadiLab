# DOCX-P4: reviewed cell-to-existing-resource references, zero-value JSON sidecar

**Source authority:** current main `b1fbd1b761ab789d3bec543035d8969e013eab70`, tree `79a691b1f2452c00416e36877ced892567ce3ddf`. This frozen contract precedes coding. Follow `AGENTS.md` exact-head GitHub CI rule.

## Existing patterns and standards

- `enterprise-import/src/ansible-ini-association-review.ts`: pure sidecar-only review with exact source/revision and explicit non-verified acknowledgement.
- `enterprise-import/src/docx-cell-disclosure.ts`: full bounded DOCX revalidation, original SHA256, exact typed cell locator, conservative secret screening; **no perfect secret detection**.
- `ui/app/docx-cell-disclosure-review.mjs`: one disclosed cell only after explicit operator consent; disclosure state resets on new cell or file.
- Office Open XML WordprocessingML table semantics: https://learn.microsoft.com/en-us/office/open-xml/word/working-with-wordprocessingml-tables
- OWASP file validation guidance: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

## Narrow positive acceptance oracle

Only **one** previously P3-reviewed cell can be linked to **one existing** Builder resource at a time. The operator first chooses a cell, acknowledges P3 disclosure and reveals it locally; next selects a concrete Builder resource, checks a **separate unchecked P4 association acknowledgement**, and explicitly clicks **Export reviewed DOCX reference (JSON)**. No automatic matching, no multiple selections, no automatic topology.

At export, use CURRENT Builder model (scenarioId, sourceRevision, resourceId list); reject stale model snapshots, removed resources, duplicate resources, invalid/prototype-like IDs. Independently re-read selected local DOCX at export, re-validate P3 source hash/locator/sensitivity and require revalidated value EXACTLY matches the currently disclosed value. Never trust the preview alone. The sidecar `yadilab.docx-reviewed-cell-references` schemaVersion `1.0.0` has status `REVIEWED_ASSOCIATIONS_ONLY`, `engineVerified:false`, `physicalTopologyVerified:false`, provenance source profile/sha/semanticTrack, target scenarioId/sourceRevision/resourceId, source typed locator, and `USER_ASSERTED_ASSOCIATION_NOT_VERIFIED`. **No DOCX cell content**, no per-cell hashes, no masked/truncated text, no address, no passwords, no embedded file payload, no interpretation of physical links or Engine PASS in JSON.

P4 is an external downloaded sidecar, NOT a Builder source edit and NOT a model/Engine/observability import.

## Negative acceptance oracle

Block if: no successful P3 reveal; consent revoked; no resource selected; no Builder; wrong/stale revision or scenario; invalid or duplicate resource IDs; same file name with changed source bytes; forged/off-range source locator; P3 credential-blocked cell; invalid ZIP/DTD/macro/external relationship; stale async review; token/secret inadvertently included in exported sidecar. Changing cell/file must reset P4 selection and second acknowledgement; close/reopen resets all. Runtime has no Builder target.

Independent Node/SSR and compiled Chromium tests must inspect exported JSON, demonstrate source byte/locator correctness, ensure Builder JSON before/after deep-equal, and assert no cross-origin requests or JS errors. Existing P1-P3 and GraphML/Ansible/Nmap regression CI on exact head. GitHub CI SUCCESS suffices: no manual Parrot test.

## Privacy caveat

This is NOT bulk DOCX import, not a claim of comprehensive secrecy detection, nor proof that the operator-selected source cell corresponds to an actual device. Sidecar contains only one user-declared **reference** to source location and existing modeled identity, never the content itself.
