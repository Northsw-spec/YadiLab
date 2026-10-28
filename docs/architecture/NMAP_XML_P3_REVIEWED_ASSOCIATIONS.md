# NMAP-XML-P3 — reviewed association sidecar (implementation checkpoint)

**Authority:** GitHub `Northsw-spec/YadiLab` current `main` at checkpoint start, `dd0c2f91cf61c60c62351a6836eaf439c23c2e6c`. The SHA is evidence of the start point, **not** a permanent old codebase to restore. The [root AGENTS.md](../../AGENTS.md) applies.

## Source inspection

- `enterprise-import/src/nmap-xml-preview.ts` outputs **scan-time EVIDENCE_OBSERVED**, source SHA-256, typed host locators and status. It does not produce `ScenarioSource` or Engine assertions.
- `ui/app/nmap-observation-panel.mjs` already presents these observations as read-only, safely escaped React text.
- `schema/scenario-source.schema.json` is **strict** and does not have an approved field for Nmap evidence/asset identity. Inserting untyped scan results into `resources[].properties`, resource IPs or Engine state would confuse modeled and observed truth.
- `ui/app/main.mjs` already has an explicit `downloadJson` helper and an authoritative Builder workspace with source scenario ID, source revision and resource IDs.

## Decision

Implement independent `yadilab.nmap-observation-associations` v1.0.0 sidecar:
- User must *explicitly select* the modeled resource for each Nmap observed host. Default = no association.
- The user must independently acknowledge that this is not verified asset identity.
- Reject stale mismatched Nmap hash, scenario identity and Builder revision, unknown resource IDs, duplicate host decisions and duplicate resource targets. No guessing from same IP, hostname, subnet, services, vendor or topology.
- Each association retains original `nmap-host` locator, source SHA, host ordinal, observed IPv4/status, observed port count, explicit user-selected target resource ID and the literal assertion `USER_ASSERTED_ASSOCIATION_NOT_VERIFIED`.
- Deliberately omit raw NSE scripts, passwords, full hostnames, service banners and other potentially sensitive raw scan content from the exported sidecar. Export only the minimum needed to identify an existing scan record and human decision.
- Do not write to canonical `ScenarioSource`, Builder, Engine, links, route or runtime. The sidecar JSON is downloaded from the browser and is NOT a trusted asset identity or Engine verdict.
- Review is only available while an existing Builder model is open; Runtime remains read-only observation inspection.
- Initial UI renders/permits explicit selection of only first 80 host observations, with all other observations unassociated. Only one observed host per modeled resource is allowed in v1 to fail closed on ambiguous many-to-one identity.

## Gates

- Independent unit tests for exact provenance, deterministic ordering, user acknowledgment, stale source/Builder revision, duplicates, unknown resource IDs, and no ScenarioSource/Engine mutation.
- React render tests: default unassociated, disabled export pending consent, XSS-safe labels, no workspace callback.
- Real Chromium: select host + modeled target, check consent, download actual JSON and inspect its contents; test duplicate-target BLOCKED; export original Builder before/after to establish exact equality. Preserve P2 valid, malformed/XXE, stylesheet-ignore and GraphML real-browser acceptance.
- GitHub Actions success required on **exact PR head** for import regression, Nmap real Chromium and GraphML real Chromium before merge; clean merged-main Linux build must then be reported separately.
- Target Parrot manual acceptance remains **NOT RUN** unless actually executed on target hardware.

## Explicit non-goals

No IP/hostname-based auto-association; no resources or links created; no persistent hidden workspace association, silent merge, evidence-to-Engine state promotion, or green PASS inferred from an observed open TCP port. A separate sidecar is a provenance-aware *human decision*, not a verified connection.
