# ANSIBLE-YAML-P3 — approved engineering contract and negative oracles

**Code authority:** current GitHub `main` at start `5c22a490bd12c9c886dc43c6b0b01405d09e8d8c`. This document is a source-adjacent design gate; do not import historical ZIPs or use Google Drive as code storage.

## Grounding in actual source
- `enterprise-import/src/ansible-yaml-preview.ts` presents **CONFIG_DOCUMENTED** (NOT live verification) with `ansible.inventory.static.yaml.v1`, SHA-256 of original bytes, distinct inventory hosts, optional **reported**, never verified, `ansible_host`, groupPaths and source-hash-bound per-membership locators. Hidden vars are deliberately excluded; no raw YAML or secret tokens must be in the association sidecar.
- `enterprise-import/src/nmap-association-review.ts` offers proven pattern of explicit user-selected host-to-existing-Builder-resource links with sidecar, acknowledgment and stale source revision checking, not automatic Engine truth.
- `ui/app/main.mjs` has canonical Builder source `scenarioId`, `sourceRevision`, `resources[].{id,label}`, and a downloadJson export path. The Ansible UI currently only receives a read-only file inspector callback; no active importer.
- `schema/scenario-source.schema.json` is strict and does not authorize added inventory identity/Engine/evidence assertions. Do NOT modify ScenarioSource schema to smuggle inventory declarations.

## P3 decision
Add `yadilab.ansible-inventory-associations` v1.0.0 **separate downloaded JSON sidecar**. It represents *human-selected, unverified references* from declared inventory hosts to currently modeled Builder resource identifiers. Each entry retains original inventory SHA, host name, host index, reported connection address or UNKNOWN, all typed YAML source group-path locators and human-selected modeled resource ID. No arbitrary vars, Jinja expression, credentials, inventory run commands or raw source are copied. Group ancestry is never interpreted as a cable.

**Explicit consent and fail-closed:** default unlinked. Export is disabled until at least one selection and explicit acknowledgment that identities and addresses are unverified. Reject source/profile mismatch, invalid or missing locators, duplicate/conflicting target IDs, duplicate host decisions, unknown resources, invalid model IDs, stale scenarioId/sourceRevision or changed original source SHA. Only the first 80 UI-visible hosts can be explicitly mapped; validator also forbids unreviewable host indexes >=80. Re-check the CURRENT Builder snapshot on submit, not only the snapshot captured at dialog open. Runtime workspace may inspect but never associate.

**No mutation:** review function returns only data. UI export callback calls existing browser downloadJson, never setWorkspace, Engine actions or Nmap APIs. No implicit matching based on same hostname/IP, group names, role, subnet, network service or topology. No green Engine PASS or verified physical link asserted.

## Frozen test oracles to implement in this order
1. P3 unit validator: valid association to existing resource with original SHA, declared address status, all host locators, unverified flags and deterministic canonical ordering. Verify original YAML preview and current model not mutated, no exported secrets or ScenarioSource fields.
2. Negative tests: stale source hash/model revision/scenario identity, unknown target, duplicate host/target, absent ack, invalid locator group path/hash/host key, out-of-range/hidden host, duplicate resource ID, invalid Builder context; each result BLOCKED without sidecar.
3. Browser contract/SSR: no default preselection, disabled export until consent, escaped labels, no workspace mutation callback; up to 80 hosts shown.
4. Real compiled YadiLab Chromium: open actual YAML source, select an existing modeled Builder resource, consent, download and parse true sidecar, reject duplicate target, export original Builder scenario before/after and prove deep equality. Existing P2 YAML files and Nmap/GraphML positive and hostile browser workflows must remain green.
5. Exact SHA GitHub Actions CI PASS on import regressions, Ansible real Chromium, Nmap real Chromium, GraphML real Chromium before merge. Then merged-main Linux build/hash/attested release PASS separately.

**Not claimed:** arbitrary YAML import, Cisco CML, dynamic Ansible inventory plugin execution, network discovery, actual machine identity validation or manual Parrot acceptance. Absence of a PASS is NOT_RUN or BLOCKED.
