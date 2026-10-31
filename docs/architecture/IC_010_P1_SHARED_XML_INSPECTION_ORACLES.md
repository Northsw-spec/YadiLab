# IC-010 P1 — Frozen shared XML source-inspection oracles

**Scope:** first non-activating IC-010 vertical slice. Baseline: protected `main=7b4e54e3c2f9b294f4c1482f69b7925690d2b66c` (2026-10-31). This document precedes source implementation on this branch; downstream UI/file-picker and full IC-010 remain unfinished.

## Existing authoritative interfaces
- `enterprise-import/src/planned-format-profiles.ts`: 21 suffix hints, always BLOCKED; never an active adapter.
- `enterprise-import/src/adapters.ts`: precisely five active enterprise adapters (JSON/CSV/TSV/XLSX/ODS), not to be altered.
- `enterprise-import/src/{graphml-preview,nmap-xml-preview,nessus-v2-preview,drawio-structural-preview}.ts`: bounded, producer-specific, read-only XML parsers with SHA-256 of original bytes and no Engine mutation. Nmap's explicitly supported harmless stylesheet PI may be ignored by **Nmap alone**; other XML parsing constraints remain unchanged.
- `ui/app/main.mjs`: existing per-format dialogs remain authoritative for preview/review. No new generic XML activation.

## Frozen P1 acceptance
1. Add `inspectStructuredXmlSourceReadOnly(filename, bytes, explicitProfileId?)` as a *standalone* pure read-only classification/summary API, without changing existing parser, adapter registry, Builder, Runtime or UI.
2. Bounded to nonempty original bytes at most **2 MiB**. Accept only basename suffix `.graphml`, `.drawio`, `.nessus`, or `.xml`. No suffix-only success: classify with complete existing validated producer parser, not keyword scanning. Ambiguous `.xml` must succeed for **exactly one** supported Nmap/Nessus/draw.io parser. GraphML's `.graphml` profile remains distinct from generic `.xml`.
3. Resolve an optional explicit profile only if it is compatible with suffix **and** validated original bytes. Never fall back to another profile if explicit selection fails. Wrong/corrupt/unsupported/malformed/oversize source returns `BLOCKED` with fixed codes, not a partial model.
4. Positive outputs include profile and `TOPOLOGY_DECLARED` / `EVIDENCE_OBSERVED`, status `REVIEW_REQUIRED` / `PREVIEW_ONLY` / `EVIDENCE_ONLY`, original **SHA-256**, a typed document-level source locator, numerical counts only, and literal false model/Engine/physical verification/activation booleans. Do not return raw XML, labels, URLs, credentials, host addresses, findings or executable instructions.
5. Preserve Nmap profile's allowed stylesheet-reference prolog, but reject arbitrary processing instructions, DTD, XXE, malformed UTF-8, cross-profile content, filename NUL/path traversal and >2 MiB. No network or file system read/scan in the API.
6. Positive + adversarial tests against actual production compiled imports; independent Node SHA; original bytes unchanged; generic planned suffix hints **still BLOCKED**, five enterprise adapters unchanged.
7. Wire P1 test to both PR required CI and independent merged-main release; no CI_PASS claim until the exact test actually executes. No new UI controls in P1, therefore real file-picker E2E, consent/epoch validation and user visual acceptance are **NOT_RUN / IC-010 subsequent slices**.

## Explicitly excluded
No generic XML/YAML router, PDF/document parsing, scenario projection, Builder replacement, modeled probes, network scans, automatic diagram edges, scan host evidence promoted to Engine truth or UI change. The output is *verified profile metadata*, not a scenario.

## Failure oracle
Unexpected source content must produce a `BLOCKED` result with a static reason. Errors from an unavailable cryptographic runtime or other operational failure must not be mislabeled as an ordinary malformed source. Neither outcome can mutate model state.

**Next after P1:** integrate this bound profile result into a truthful, explicit user-facing import entrypoint with consent, source-change/Builder-change validation, typed per-element source locators and real Chromium file-picker tests. Revisit matrix/issue #3 on actual proof, never based only on source presence.
