# ANSIBLE-INI-P3 — frozen reviewed-association contract and negative oracles

**Source authority:** GitHub `main=f5f5a2280abc411cee4a720f375c7236d48dc05e` at checkpoint start; tree `e5c01f28f3c998c08aa9171eed2b214bc2deaacb`. Root AGENTS.md applies. No archive/Drive code imports.

## Primary documentation and real code
- Ansible built-in INI inventory plugin: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/ini_inventory.html
- Ansible inventory guide: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html
- Existing INI P1 typed `AnsibleIniHost.locators[]`, original SHA-256, directGroups and explicit groupChildren; P2 browser panel.
- Existing YAML P3 validator/sidecar and audited current Builder `scenarioId`, `sourceRevision`, `resources[].{id,label}`.

Ansible group inheritance, multi-group host declaration and aliases are **inventory semantics**, not proof of physical cable/asset identity/IP reachability. Host-line values and `:vars` values follow different Ansible typing; P1 interprets only bounded literal `ansible_host` and deliberately does not export other variables. Association review MUST NOT broaden that parser profile.

## New strictly separate P3 sidecar
`formatId=yadilab.ansible-ini-inventory-associations`, `schemaVersion=1.0.0`; `status=REVIEWED_ASSOCIATIONS_ONLY`; explicit `engineVerified=false`, `physicalTopologyVerified=false`, `semanticTrack=CONFIG_DOCUMENTED`. Retain exactly source profile, original SHA-256, current Builder scenarioId/sourceRevision, reviewed source host ordinal, inventory name, REPORTED_NOT_VERIFIED/UNKNOWN literal connection address, explicit directGroups, **all original typed INI locators**, selected modeled resource ID, and `USER_ASSERTED_ASSOCIATION_NOT_VERIFIED`.

Typed provenance locator is exactly `{kind:"ansible-ini-host",sourceSha256,lineNumber,section,hostKey}`. For ungrouped hosts, require one source locator section `ungrouped` and no direct groups. For grouped hosts, each locator's section must match its corresponding direct group, with unique groups and increasing integer source line numbers. A multi-group host retains each direct declaration; parent-child `:children` relationships remain configuration metadata, never network edges.

## Fail-closed implementation
- Default choices unassociated. Require at least one explicitly chosen visible host and unverified-identity acknowledgment before export.
- Cap explicit selection to first **80** hosts, and reject hidden host selection in domain layer. Each selected host and target ID unique; resource must exist in current Builder model.
- On every download click the caller MUST resnapshot current Builder source, *not* trust a captured modal prop, to check scenarioId, sourceRevision, IDs. Stale source SHA or sourceRevision blocks without sidecar.
- Reject malformed profile/status/semantic track/SHA, invalid locators, fake line numbers, duplicate provenance groups, wrong source/hash/host key, inconsistent declared address truth, duplicate/unknown model resources, malformed decision, missing consent and explicit same target assigned twice.
- No automatic identity inference from IP/name/group membership. No model mutation, no Engine call, no Ansible execution/network requests. Sidecar-only download via existing downloadJson, no secret vars (including original raw lines), no original raw source, no ScenarioSource properties.
- Runtime inspection available, but its associations cannot be exported; only Builder mode.
- React text escaping; limit visible selections; source-switch clears selections and acknowledgment. Independent real Chromium tests must download real JSON sidecar and verify original Builder export deep-equal before/after.

## Frozen independent tests BEFORE implementation
1. Valid declared host (including ungrouped), original source SHA, original 1-based line locator; sidecar flags and no modeled network truth.
2. Multi-group source host: all typed original locators preserved in original order, no inherited-group link inference; deterministic sorting of independently selected hosts.
3. Sensitive synthetic source: no `SECRET_INI_*_CANARY_DONT_EXPORT` or private key path in downloaded JSON, UI, errors or diagnostics.
4. Negative: stale SHA/scenario/revision, absent acknowledgment, no selection, ordinal outside preview or >=80, unknown/duplicate target and repeated host, malformed/duplicated typed locators, wrong source hash/host key/section, invalid 1-based line number or provenance order, group list inconsistent, spoofed address truth, forbidden source/model shape, runtime model null.
5. Browser SSR: unlinked default, disabled download until selected and acknowledged, escaped labels, duplicate target blocked, 80-host cap; no setWorkspace/cable/probe path.
6. Real compiled Chromium: select original INI file, inspect existing Builder resource options, choose, acknowledge, download **real** v1 JSON, validate provenance and negative duplicate target, compare original Builder exports before/after. Old P2 INI, YAML, GraphML and Nmap workflows separately green.
7. Exact-HEAD PR CI required before merge. Merged-main Linux build provenance required separately. User's Parrot hardware acceptance remains NOT RUN until physically performed.

## Future constraints
This document freezes P3 behavior, not a new Ansible full grammar or Engine observation. Original P1/P2 should remain active. No CI PASS may be inferred from presence of test files.
