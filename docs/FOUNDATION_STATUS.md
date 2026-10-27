# YadiLab v1.0.1 candidate status

Release classification: **NOT YET VERIFIED PRODUCT RELEASE**. The locked v1.0.0 VERIFIED PRODUCT RELEASE remains the reference. v1.0.1 is a post-release visual-layout patch candidate that reserves an explicit zone-header band, rejects child geometry inside that band, clamps Builder drag-stop geometry below it, and adds real-browser overlap acceptance.

Inherited v1.0.0 release-gate baseline (v1.0.1 must rerun the complete gate on current Parrot before promotion):

- genuine npm v3 lock and exact 33-package closure: PASS;
- executable pinned React/ReactDOM/React Flow/Ajv/ELK/zip.js/TypeScript/esbuild toolchain: PASS;
- dependency-resolved local browser bundle and release-integrity preflight: PASS;
- native static Linux x86-64 loopback launcher/distribution: PASS;
- real Chromium mounted application and interactive Builder/Runtime workflow: PASS;
- IndexedDB, portable `.yadiprogress` and `.yadisession`, package round-trip and tamper rejection: PASS;
- server-stopped service-worker reload remounting the real React Builder: PASS;
- Firefox loopback render: PASS;
- Parrot target acceptance harness: PASS (`RC=0`);
- externally signed dependency snapshot using the pinned Ed25519 producer trust anchor: PASS; the private key remains external and is not shipped.

All required product-release gates are closed. Modeled observations/probes remain explicitly `NO_GUEST_COMMAND_EXECUTION`; no live connector, diagnosis inference, hidden solution exposure, CDN, or runtime internet dependency was added.

Authoritative architecture: YadiLab Masterprompt v1.3 VERIFIED / LOCKED.

Implemented checkpoints:

- Phase 0 — repository/policy foundation.
- Phase 1 — authoritative scenario contracts.
- Phase 2 — compiler/semantic validation.
- Phase 3 — deterministic Engine foundation.
- Phase 4 — canonical solution replay/regression.
- Phase 5 — PackageIO security/integrity/distribution layer.
- Phase 6 — headless CLI.
- Phase 7 — deterministic canvas/React Flow projection.
- Phase 8 — compound layout projection + validated ELK Layered backend boundary.
- Phase 9 — Builder/Runtime browser application foundation.
- Phase 10 — strict progress save/load + IndexedDB/PWA/offline foundation.
- Phase 11 — precompiled generic Linux x86-64 loopback launcher/distribution preparation.
- Phase 12 — fail-closed Parrot x86-64 acceptance harness and browser capability probe.
- Phase 13 — exact browser dependency policy, local-only browser build gate, React/React Flow entry source, and shell-vs-full-app acceptance hardening.
- Phase 14 — safe compiled-package browser session: PackageIO -> schema/version/layout gates -> RuntimeWorkspace.
- Phase 15 — Builder package export with mandatory PackageIO read-back/self-verification before download.
- Phase 16 — Runtime progress lifecycle: portable `.yadiprogress` import/export plus IndexedDB autosave/restore/clear through Engine SaveState.
- Phase 17 — deterministic Runtime state management: Undo/Redo/Reset, scenario-bound checkpoints, and replay.
- Phase 18 — Runtime explainability/panel completeness and correction of result-field rendering.
- Phase 19 — typed Builder Inspector and visual create/edit/duplicate/delete controls wired to the existing Builder command boundary.
- Phase 20 — structured Builder authoring panels for Tests, Findings, Objectives, Hints, Completion, Canonical Solution, and validation status.
- Phase 21 — Builder canvas interactions: semantic multi-select, immediate manual drag/resize projection, zone resize controls, and interactive connection creation routed through Builder commands.
- Phase 22 — portable Builder notes in the authoritative scenario contract, compiler normalization, semantic target validation, and browser authoring surface.
- Phase 23 — trusted built-in Asset Library: exact asset resolution/locks, reusable local SVG assets, Canvas/Builder palette integration, package lock cross-checks, and offline distribution serving.
- Phase 24 — trusted Capability/Domain Pack Runtime registry with exact-version availability gates before Builder preview or packaged Runtime play.
- Phase 25 — explicit schema-version compatibility and deterministic migration framework with `app migrate`; unsupported versions fail closed across compiler, CLI test, and browser Runtime.
- Phase 26 — dependency-free deterministic headless SVG preview renderer plus `app render` for normalized/source JSON with explicit LayoutDocument.
- Phase 27 — package-aware CLI command layer: SafePackageIO-gated inspect/test/render/unpack plus byte-identical current-version package migrate; binary ZIP adapter remains dependency-gated.
- Phase 28 — deterministic third-party license inventory and release provenance: exact license policy, generated notices/inventory, bundle-resolved esbuild inventory path, and distribution checksum/shipping gates.
- Phase 29 — fail-closed Scenario Certification Pipeline: canonical regression, semantic layout validation, Runtime compatibility, PackageIO build/readback, exact distribution/solution policy, and Builder export certification certificate.
- Phase 30 — deterministic Visual Validation: sibling overlap, parent-zone containment/overflow, canvas bounds, label fit, excessive coincident edges, unreasonable whitespace, and certification/auto-layout integration.
- Phase 31 — strict custom SVG sanitizer in PackageIO: passive allowlist, canonical namespace, active/remote-reference rejection, and identical write/read safety enforcement.
- Phase 32 — remaining named Foundation declarative tests plus Engine 0.5.0: port scan, password audit, virtualization management exposure, logging visibility/alert, backup restore, static parameter validation, and fail-closed unsupported-test semantics.
- Phase 33 — route/VLAN/ACL-aware NetworkEngine plus Engine 0.6.0: authoritative route tables, IPv4/IPv6 CIDR matching, VLAN membership gating, resource ACL policy, and fail-closed malformed/conflicting network state.
- Phase 34 — DNAT/port-forward-aware NetworkEngine plus Engine 0.7.0: required/optional NAT policy, external-to-internal port translation, explainable translatedPort metadata, and fail-closed malformed NAT state.
- Phase 35 — bounded IPv4 SNAT-aware NetworkEngine plus Engine 0.8.0: separate SNAT policy, source-aware downstream CIDR evaluation, combined DNAT/SNAT, exact explanation metadata, and fail-closed malformed/ambiguous source handling.
- Phase 36 — integrated Proxmox/OPNsense/Windows AD/RDS Golden Scenario: 10 resources, 10 declarative tests, canonical regression, end-to-end source-to-package certification, intact administrative reachability, fail-closed adversarial mutations, and isolated SNAT+DNAT CIDR verification.
- Phase 37 — fail-closed dependency supply-chain readiness: complete npm v3 lock closure, exact direct/transitive metadata and SHA-512 SRI policy, installed npm lock parity, and an offline Linux x86-64 developer cache handoff for genuine future browser bundling.
- Phase 38 — browser package media isolation: untrusted custom SVG/raster images from validated PackageIO assets use revocable Blob URLs in native image elements, with explicit lifecycle cleanup, a constrained img-src CSP, and fail-closed media initialization.
- Phase 39 — PNG/JPEG/WebP structural raster preflight (bounded dimensions and formats) across PackageIO writer/reader and browser media; malformed MIME/spoofed headers and forged-hash image payloads fail closed.
- Phase 40 — versioned release-scoped offline PWA precache and actual React mount attestation: deterministic content-hash-derived service worker names; strict static allowlist; upgrade without purging unrelated app caches; Parrot Chromium gate checks mounted Builder controls, not build manifest/static HTML alone.

- Phase 41 — service-worker byte integrity on install and cached fetch: manifest SHA-256 verification via WebCrypto, restricted same-origin responses, atomic failed-update rollback, corruption rejection and retention of the prior working offline release.

- Phase 42 — Browser Release Promotion Gate: exact manifest/asset/SW precache verification, resolved-license requirement, dependency-pin parity, symlink/traversal rejection, and fail-closed staged loopback distribution promotion without overwriting last known good.
- Phase 43 — Parrot live Chromium interactive acceptance: acceptance-only Playwright drives real React Builder compilation, React Flow layout, certified student export, Runtime tests/findings/remediation/completion, portable/IndexedDB progress, package round-trip, and forged-hash rejection. Independent ZIP and fail-closed contract selftests run in the ordinary Foundation suite; actual browser/Parrot execution remains externally BLOCKED until dependencies and target are available.
- Phase 44 — offline dependency snapshot attestation: complete transferred-cache inventory, exact source/dependency-policy/lock binding, per-file SHA-256 + size validation, symlink/path/unlisted-file rejection, and mandatory verification before `npm ci --offline`; real dependency acquisition/build remains an external gate.
- Phase 45 — sealed dependency transport: deterministic canonical ZIP_STORED archive, safe pre-extraction central-directory validation, basename-bound SHA-256 sidecar, direct ZIP import into the offline installer, and adversarial rejection of traversal/duplicates/symlinks/compression/tampering/case collisions; publisher authenticity remains external.
- Phase 46 — executable browser toolchain attestation: installed React/ReactDOM/React Flow/Ajv/ELK/zip.js/TypeScript/esbuild modules must execute deterministic probes; native esbuild transform is mandatory before browser bundling.
- Phase 47 — full-browser offline bootstrap + server-stopped reload acceptance: dependency-resolved releases must ship/load the local `app-shell.js` service-worker bootstrap, release verification rejects missing/remote bootstrap registration, and Parrot live acceptance must install/control the worker, terminate a dedicated packaged loopback launcher, reload, and remount the real React Builder from verified precache bytes.
- Phase 48 — browser-build/template binding correction: the packaged v0.47 build script was found not to invoke the claimed `app-shell.js` index path. Full browser index generation now lives in a directly tested renderer, the production build imports/invokes that renderer, the release verifier requires the service-worker bootstrap to precede the application bundle, and persistence regression checks the rendered output rather than stale build-source literals.
- Phase 49 — target-native optional dependency closure: Linux x86-64 policy explicitly binds `esbuild@0.28.2` to `@esbuild/linux-x64@0.28.2`; project lock, required closure, npm hidden lock, physical installed metadata, and offline snapshot lock counts must include the target-native package before readiness can pass.
- Phase 50 — sealed-snapshot producer coherence and offline replay: `development-platform.json` is semantically validated and cross-bound to manifest target/tool identities; the online snapshot producer must prove the populated npm cache by deleting the first install, replaying `npm ci --offline`, and rerunning readiness plus executable toolchain checks before sealing.
- Phase 51 — sealed-snapshot consumer coherence: before npm may consume transferred cache bytes, the offline Linux x86-64 consumer must use the exact Node and npm versions recorded by the producer in the verified snapshot manifest; mismatches fail closed with exit 77.

Verified in the current environment:

- complete Foundation semantic/regression suites through Phase 51;
- Builder Inspector functional/adversarial suites;
- Builder Authoring functional/adversarial suites;
- Builder Canvas Interactions functional/adversarial suites;
- Builder Notes functional/adversarial suites;
- Asset Library functional/adversarial suites and local SVG safety audit;
- CapabilityPackRegistry functional/adversarial suites and compiler-catalog exact-lock consistency;
- Versioning/migration functional/adversarial suites; current schema version is explicit and unsupported versions require a registered migration path;
- Headless renderer functional/adversarial suites and CLI render integration; output is deterministic local SVG with no script/external-resource references;
- Package-aware CLI semantics: student package initial-state testing, author package canonical regression, embedded-layout render, safe unpack, and current-version byte-identical package migrate;
- deterministic THIRD_PARTY_NOTICES + machine-readable inventory generation, exact dependency/license-policy consistency, and resolved-bundle inventory path tied to esbuild metafile inputs;
- loopback distribution ships and SHA-256 manifests license notices/inventory;
- Package CLI validation reuses PackageIO integrity/path/hash limits plus schema-version, Engine-version, capability-pack and layout gates before command execution;
- raw `manifest.json` bytes are preserved by PackageIO for faithful safe unpack;
- CLI `migrate` command plus version-aware validate/test gates;
- Runtime package-open and Builder preview fail closed when an exact capability pack/version is unavailable;
- capability packs remain trusted application/runtime modules; scenario packages cannot inject executable capability code;
- deterministic compiler asset auto-resolution plus explicit asset version/type diagnostics;
- package manifest ↔ normalized scenario asset-lock consistency;
- offline launcher serves trusted built-in assets from loopback;
- strict JSON object/array editing at Inspector boundary;
- immediate zone-parent cycle prevention;
- semantic edits invalidate stale compile state;
- stable IDs remain read-only in ordinary Inspector editing;
- Scenario Certification Pipeline functional/adversarial suites and Builder package-export certification gates; `selfVerified: true` now requires full canonical regression + layout/runtime/package readback certification;
- Visual Validation functional/adversarial suites; auto-layout and certification now fail closed on deterministic visual-layout errors;
- PackageIO custom SVG write/read sanitization gates, including attacker-built correctly hashed active-SVG rejection;
- Engine 0.5.0 named declarative-test coverage for all Masterprompt §28 Foundation examples, including static compiler parameter/reference gates and fail-closed rejection of unevaluated test types;
- Engine 0.6.0 route/VLAN/ACL-aware reachability with deterministic IPv4/IPv6 CIDR routing and fail-closed network-policy uncertainty;
- Engine 0.7.0 DNAT/port-forward-aware reachability with required/optional NAT policy and translated listener-port evaluation;
- Engine 0.8.0 bounded IPv4 SNAT/source-aware CIDR reachability, static/compiler SNAT validation, and composable forward-path DNAT/SNAT;
- Golden integrated scenario with independent source/normalized/layout schema validation, ten exact before/after test expectations, normal and adversarial SafePackageIO certification, and isolated combined DNAT/SNAT verification;
- all previously verified compiler/Engine/PackageIO/CLI/canvas/layout/browser/persistence/dependency/launcher/acceptance-contract gates remain PASS.

Blocked / not yet externally verified:

- genuine npm resolution/package-lock in this sandbox (registry access unavailable); the new cache-handoff scripts cannot acquire packages here and are not claimed to have completed an offline install;
- actual `ZipJsArchiveBackend` byte execution for CLI `.yadilab` input in this sandbox; package-command semantics are verified through the same SafePackageIO abstraction with MemoryArchiveBackend;
- actual installed `elkjs` execution;
- actual esbuild of the React/React Flow/Ajv/ELK/zip.js browser application;
- rendered full browser application acceptance;
- real Parrot OS x86-64 acceptance;
- successful Chromium/Firefox target acceptance on Parrot.

Phase 40 PWA cache/runtime attestation: 17 functional + 17 adversarial PASS with mocked CacheStorage/service-worker events; **does not constitute real browser execution**.
Current environment browser build readiness: BLOCKED by missing real package-lock/node_modules. Phase 37 adds developer-only offline handoff scripts; readiness metadata checks do not replace real npm SRI installation and production browser/runtime acceptance.
Current environment Parrot harness result: BLOCKED (non-Parrot host, exit 77).

This is a VERIFIED DEVELOPMENT CHECKPOINT, not a VERIFIED RELEASE.

Phase 41 generated PWA/service-worker integrity gate: 23 functional + 43 adversarial PASS in a Node WebCrypto/CacheStorage harness; PWA static contract 17 PASS; generated shell SHA-256 readback 29 PASS. The harness verifies generated worker behavior with actual byte hashes but is **not** proof that Chromium/Firefox or React successfully ran. npm/Parrot target gates remain BLOCKED/77 here.

Phase 42 browser release integrity: 30 targeted structural/adversarial assertions PASS, including preserved previous distribution on a forged ready manifest. The staging copy is independently rechecked and SHA256SUMS-verified before promotion; bundled React execution remains a separate Chromium/Parrot acceptance requirement.

Phase 43: independent browser package ZIP check (5 synthetic fixtures) + acceptance launcher/URL contract (27 negative/static assertions) PASS. Real interactive Chromium workflow was NOT executed successfully here: npm-dependent React bundle absent; current sandbox browser navigation also policy-blocked. Python Playwright is an acceptance-only tool, not a dependency of the production app.

Phase 44: dependency/browser-build gate 31 PASS + adversarial 34 PASS + offline dependency snapshot 28 PASS. Whole Foundation through v0.45.0: PASS / exit 0 in the current Debian sandbox, including the sealed transport layer. The local npm cache remains empty and the real browser dependency tree is not present, so browser-build/release and Parrot target gates remain BLOCKED/77 rather than being inferred from snapshot tests.


Phase 45 focused dependency state: dependency/browser-build gate 31 PASS + adversarial 34 PASS + Phase 44 snapshot 28 PASS + sealed transport 42 PASS. The sealed transport does not claim the missing real npm cache or Parrot execution; those remain external fail-closed gates.
Phase 46 executable-toolchain boundary: dependency metadata readiness is no longer sufficient. After npm ci, YadiLab must actually load and execute the pinned browser/toolchain modules. The attestation probes React element creation + ReactDOM server rendering, React Flow exports, Ajv schema compilation, ELK layout, zip.js constructors, TypeScript transpilation, and esbuild TypeScript transform. A missing dependency tree remains 77/BLOCKED; an installed but non-executable or incompatible toolchain is a real FAIL. The current sandbox remains BLOCKED because no genuine npm snapshot/install exists.

- Phase 52 — exact source-checkout identity binding: snapshot schema 1.1.0 binds canonical source paths, bytes and Unix modes before offline npm consumption.

- Phase 53 — transactional offline dependency install: source-identical staging keeps the live checkout untouched until dependency install, browser build and loopback distribution all verify; generated state promotion has rollback plus interrupted-process recovery.

- Phase 54 — signed dependency-snapshot provenance: snapshot schema 1.2.0 requires Ed25519 provenance bound to exact manifest/source/tool identity; only source-controlled public trust anchors are accepted, private keys are external, and forged ZIP + recomputed SHA sidecar still fails authenticity.

- Phase 55 — dependency-snapshot trust-anchor lifecycle: canonical trust schema 1.1.0, explicit fingerprint-confirmed public-key onboarding, active/revoked state, revoked-key rejection, and fail-closed external-key CLI ceremony.

- Phase 56 — trust activation and rotation ceremony: trust schema 1.2.0 stages new producer keys as pending, requires external-private-key proof of possession before activation, cryptographically validates stored activation proofs, and verifies checkpoint-coupled two-key rotation/revocation behavior.

- Phase 57 — operator key-material ceremony: atomic external Ed25519 key-bundle generation and verification with strict private/public file modes, cryptographic pair/fingerprint validation, canonical public ceremony metadata, and source-checkout binding.

- Phase 58: Normalized Enterprise Model + knowledge states + provenance + canonical baseline identity.


## Phase 59

Enterprise import now has a versioned adapter/mapping/report framework plus dependency-free JSON, CSV and TSV adapters. Inputs normalize into the Phase 58 Enterprise Model with exact source hashing, explicit mapping provenance, UNKNOWN/INVALID semantics, unmapped-field reporting and fail-closed conflicts. XLSX/ODS and later adapters remain future phases.


## Phase 60

Enterprise import adds safe XLSX and ODS adapters on top of the Phase 59 adapter framework. Workbook containers are bounded before XML consumption; DTD/custom entities, active content, external workbook/data sources, encrypted ODS members, duplicate archive paths and compression-ratio abuse fail closed. Physical sheet/row/column provenance is preserved. Cached formula values may be imported only with an explicit warning and formulas are never evaluated. Official XLSX/ODS example templates use the same normal adapter/mapping pipeline; no template-specific parser exists.

## Phase 61

Enterprise import adds deterministic mapping review and re-import diff. A parsed document can be inspected before baseline creation to show discovered tables/fields and classify each configured mapping as RESOLVED, MISSING or AMBIGUOUS. Only explicit exact/alias rules participate; no fuzzy or AI inference is trusted. User confirmations create a new versioned mapping profile and persist as USER_MAPPED provenance. Duplicate entity-ID conflicts remain blocking unless an explicit recorded resolution selects one exact source table/record. Re-import diff compares same-baseline identities deterministically and separates semantic changes from provenance-only changes. Automatic merge remains intentionally deferred.


## Phase 62

Enterprise re-import now supports deterministic three-way merge using a common imported ancestor, the current working baseline and the newly imported baseline. Unchanged current state accepts incoming changes automatically; current-only changes are preserved; equivalent concurrent changes converge; divergent concurrent changes require an explicit choice. Merge plans are schema-defined, deterministic and stale-plan checked. Applied merges prune unused provenance, retain required historical sources, re-run full Enterprise Model verification, and bind ancestor/current/incoming identities, merge-plan SHA-256 and explicit resolutions into baseline lineage. Re-import diff now includes relationships as well as entities and facts. Automatic merge never touches independent scenario/fault overlays.

- Phase 63 — browser Import Helper UI over the verified enterprise import stack.

# Foundation v0.64.0

Phase 64 adds the deterministic bridge from a verified normalized Enterprise Baseline into ordinary scenario-source, Compiler, Layout Engine and Canvas Projection. Import Helper can explicitly replace the current Builder scenario with the projected enterprise topology. Active scenario semantics are derived only from supported explicit/resolved facts; unresolved and unsupported enterprise knowledge remains preserved and visible through projection diagnostics rather than being guessed.

## v0.65.0 — Phase 65 Fault Injection Engine Core

- Fault Pack + Fault Overlay contracts implemented.
- Deterministic runtime injection core and persistent scenario variant materialization implemented.
- Fault packs/instances are content-addressed and exact-version bound.
- Preconditions, expected effects, negative controls, blast radius and reversibility are verified against real Engine state.
- Healthy baseline/scenario source is not mutated by injection/materialization.
- `faultOrigin` is preserved through the normal compiler.
- Full user-facing Fault Injection panel is deferred; this checkpoint establishes the verified semantic core.

## v0.66.0 — Phase 66 Fault Injection UI

Phase 66 exposes the verified Fault Engine Core through the browser without duplicating fault semantics in React. Runtime fault injection requires a SHA-256-bound preview of the exact request, supports compatible multi-fault overlays, records injection as one Runtime history step and allows fail-closed latest-fault rollback. Builder uses an isolated fault draft so healthy author source remains untouched until a new persistent scenario variant is explicitly materialized. Difficulty is displayed through the four declarative dimensions already carried by Fault Pack definitions rather than a derived opaque score.


## v0.67.0 — Phase 67 Fault Pack Expansion, Wave 1

Phase 67 expands `foundation.network.core` to 25 deterministic faults: five each for routing, VLAN/L2, DNS, DHCP and firewall/NAT. Fault definitions carry explicit preconditions, deterministic mutations, expected effects, blast radius/negative controls where applicable, observable symptoms, canonical restore-pre-injection recovery and the same four transparent difficulty dimensions introduced by the Fault Pack contract. Representative routing, VLAN, firewall and DNAT faults are regression-checked against actual Network Engine semantics; DNS/DHCP remain explicit state faults rather than fabricated protocol simulation. Same-layer incompatible faults fail closed, every built-in fault is rollback-tested, the real built-in pack is schema-validated, and the browser catalog regression requires all 25 faults. Windows/Linux-specific packs and deterministic multi-fault generation remain deferred.


## v0.68.0 — Phase 68 Windows + Linux Fault Packs

Phase 68 adds dedicated `foundation.os.windows@0.1.0` and `foundation.os.linux@0.1.0` packs with ten deterministic faults each. Windows coverage includes gateway/DNS/DHCP/host-firewall/interface state plus RDP, SMB, WinRM and network-profile faults; Linux coverage includes gateway/DNS/DHCP/host-firewall/interface state plus SSH, HTTP, NetworkManager and systemd-resolved faults. Fault Injection UI now selects the exact built-in pack explicitly. The Fault Engine also rejects active-overlay mutations that overlap the same target path (including parent/child paths), preventing silent cross-pack state overwrites while still allowing independent multi-pack faults on different resources/paths. Service/listener faults are verified through the existing Engine service semantics. Real OS command execution and the Diagnostic/Observation Engine remain deferred. The next recommended phase is deterministic compatible multi-fault/scenario generation.

## Phase 69

Deterministic multi-fault/scenario generation is now implemented for Builder variants through `foundation.multi_fault@0.1.0`. Same normalized baseline + seed + exact Fault Pack versions/identities + constraints replay to the same content-addressed generation plan. Selection uses bounded deterministic backtracking and fails closed on invalid preconditions, symmetric incompatibilities, mutation-path conflicts, semantic regression of previously selected fault effects/negative controls, aggregate changed-resource constraints, or failed exact combined recovery. Builder requires an isolated generated preview before persistent variant creation. Generated variants preserve generator ID/version/seed/plan identity in `faultOrigin.generation`. Command-level Diagnostic / Observation Engine behavior and temporal/intermittent fault scheduling remain future work rather than being simulated by explanatory text. Final Phase-69 whole-Foundation evidence is 161/161 explicit command exits at 0; separate signing/dependency/browser/Parrot product gates remain RC=77/BLOCKED and are not inferred from this development-checkpoint regression.

Phase 70 — Diagnostic / Observation Engine, Wave 1: Runtime now has a deterministic read-only observation layer (`foundation.observation@0.1.0`) with seven modeled Windows and seven modeled Linux command surfaces covering interface, routing, DNS, DHCP, host-firewall and service/listener evidence. Transcripts bind exact scenario hash/state revision/target/command and explicitly state `NO_GUEST_COMMAND_EXECUTION`; missing or malformed modeled values are never guessed. Runtime Browser UI exposes the observation console and direct evidence paths. Builder, unsupported targets and cross-OS commands fail closed. Real guest execution, automatic diagnosis, packet capture/Event Viewer/journalctl and temporal fault scheduling remain future independently verified work. The exact Foundation chain now contains 167 deterministic commands; final sealing requires explicit exit-0 evidence for IDs 0–166. External signing/dependency/browser/Parrot product gates remain RC=77/BLOCKED in the current environment and are not counted as PASS.

Phase 71 — Diagnostic / Observation Engine, Wave 2: `foundation.observation` advances to `0.2.0` and Runtime gains four active modeled probes per OS: ping, TCP-port test, DNS lookup and path trace. Probes reuse deterministic Network Engine reachability, add fail-safe host default-gateway/on-link and implicit ACL-default checks where modeled evidence is sufficient, expose path/blocking-point evidence, and perform resolver/resource/record-bound DNS lookup without guest execution or fabricated packets. Focused Wave-2 coverage is 104 functional + 21 adversarial assertions; Browser active-probe coverage is 7/7 functional + 7/7 adversarial. Wave-1 observation coverage remains 88 + 11 and 6/6 + 6/6. The exact Foundation chain now contains 171 deterministic commands; final sealing requires explicit exit-0 evidence for IDs 0–170. External signing/dependency/browser/Parrot product gates remain separate RC=77/BLOCKED in this environment.

### Phase 72 — Troubleshooting Session / Evidence Notebook

Authority remains Masterprompt v1.3 VERIFIED / LOCKED plus the approved Import Helper terminology override. Phase 72 adds a learner-owned, portable evidence notebook over Wave-1 observations and Wave-2 active modeled probes. Entries are ordered, Runtime-revision-bound and content-addressed, while hypotheses/next steps/conclusions remain explicit learner-authored notes. Portable `.yadinotebook` import is exact-scenario and identity checked; stale/duplicate/tampered evidence fails closed. The notebook remains separate from Engine state and never imports hidden fault/generator truth or canonical solution material. Focused coverage is 48 core functional + 18 adversarial and 7/7 Browser functional + 5/5 adversarial; schema coverage is 46/46 fixtures and 17/17 schemas. The exact `test:foundation` chain contains 175 commands; first complete whole-chain evidence is 175/175 explicit exit 0, with final sealing repeated after documentation freeze. Automatic diagnosis, grading/remediation and guest command execution remain explicitly unimplemented. External signing/dependency/browser/Parrot gates remain RC=77/BLOCKED in this environment.

### Phase 73 — Evidence Notebook Persistence & Replay

Authority remains Masterprompt v1.3 VERIFIED / LOCKED plus the approved Import Helper terminology override. Phase 73 adds a schema-defined content-addressed troubleshooting-session envelope binding exact scenario identity, Runtime SaveState and the verified learner Evidence Notebook. The existing Runtime Autosave action persists the combined session while retaining progress-only persistence for backward compatibility. Restore validates nested schemas, exact scenario/revision bindings, notebook canonical identity and session canonical identity; a present invalid combined session fails closed and cannot silently downgrade to progress-only restore. Replay preserves canonical notebook sequence and exact captured Runtime revisions without inferring chronology, causality or diagnosis. Focused Phase-73 persistence coverage is 50 functional + 14 adversarial assertions; schema coverage is 48/48 fixtures and 18/18 schemas. The exact `test:foundation` chain contains 177 deterministic commands and the first full verification produced 177/177 explicit exit 0. External signing/dependency/browser/Parrot product gates remain separate RC=77/BLOCKED. Final sealing is repeated after this identity-covered text is frozen.


### Phase 74 — Troubleshooting Objectives / Evidence Review

Authority remains Masterprompt v1.3 VERIFIED / LOCKED plus the approved Import Helper terminology override. Phase 74 adds optional learner-visible `troubleshootingObjectives` to scenario source/normalized contracts and deterministic notebook-only review through `foundation.evidence_review@0.1.0`. Ordered requirements preserve notebook evidence sequence; unordered requirements match any qualifying entry. The review returns only SATISFIED/PENDING/OUT_OF_ORDER requirement/objective states plus NOT_CONFIGURED/SATISFIED/PENDING required-evidence status, exact matched entry IDs and a canonical review SHA-256. Compiler and Builder reject empty matchers, duplicate requirement IDs and unknown resource references. Focused coverage before whole-Foundation sealing is 35 review functional + 14 adversarial, 6/6 Browser functional + 6/6 adversarial, compiler 69 + 63, and schema 51/51 fixtures + 18/18 schemas. The exact `test:foundation` chain contains 181 deterministic commands; the accepted first full run records 181/181 explicit exit 0 after an earlier preliminary syntax-error run was corrected and discarded. Snapshot transport remains 44/44 PASS, launcher and acceptance contracts PASS. No automatic diagnosis, scoring, grading, hidden-ground-truth review, remediation or AI/ML/LLM inference is introduced. External signing/dependency/browser/Parrot product gates remain separate RC=77/BLOCKED.


### Phase 75 — Troubleshooting Remediation / Verification Loop

Authority remains Masterprompt v1.3 VERIFIED / LOCKED plus approved existing Foundation terminology overrides. Phase 75 adds learner-driven modeled remediation over the existing Runtime operation/history path. Preview requires current-revision notebook evidence and binds exact scenario, state revision, notebook identity and operation. Commit appends an immutable remediation action to Notebook schema 0.2.0 while legacy 0.1.0 notebooks remain accepted. `foundation.remediation_review@0.1.0` compares exact before/after evidence signatures and reports only PENDING_AFTER_EVIDENCE, VERIFIED_IMPROVEMENT, REGRESSION_DETECTED or NO_VERIFIED_IMPROVEMENT. Focused coverage: remediation core 28 functional + 16 adversarial, remediation Browser UI 6/6 functional + 4/4 adversarial, schema 53/53 fixtures + 18/18 schemas, plus Phase-72/73/74 regressions. The exact test:foundation chain contains 185 deterministic commands; the accepted first full run records 185/185 explicit exit 0, with snapshot transport 44/44 PASS and launcher/acceptance PASS. All five external product gates remain separate RC=77/BLOCKED. No canonical-solution execution, hidden-ground-truth lookup, scoring, grading, AI/ML/LLM inference, guest execution or live connector is introduced.


### Phase 76 — Typed Remediation Actions / Safety Constraints

Authority remains Masterprompt v1.3 VERIFIED / LOCKED plus approved existing Foundation terminology overrides. Phase 76 adds `foundation.typed_remediation@0.1.0`, a bounded learner-facing Windows/Linux remediation catalog that compiles exact validated action parameters to the existing Phase-75 one-step Engine operation path. New Troubleshooting Notebooks use schema 0.3.0 with optional typed action audit metadata; legacy 0.1.0/0.2.0 notebooks remain accepted. Focused coverage is 41 typed-remediation functional + 30 adversarial assertions and 6/6 Browser functional + 4/4 adversarial, with schema 55/55 fixtures + 18/18 schemas and all adjacent Observation/Notebook/Evidence Review/Persistence regressions green. The exact `test:foundation` chain contains 189 deterministic commands; the accepted first full run records 189/189 explicit exit 0 with snapshot transport 44/44 PASS and launcher/acceptance PASS. External signing/dependency/browser/Parrot product gates remain separate RC=77/BLOCKED.


### Phase 77 — Guided Troubleshooting Workflow / Remediation UX

The Runtime now includes `foundation.guided_troubleshooting@0.1.0`, a learner-visible process map over Observation, Active Probe, Evidence Notebook, Evidence Review and Typed Remediation. It reports only process phases and step readiness; it never selects commands, targets, diagnoses, remediation actions or values. Matching after-evidence and verified improvement/regression are delegated to the existing deterministic remediation review. Workflow state is content-addressed. Focused tests: 8/8 functional + 6/6 adversarial. The accepted first Foundation run is 191/191 explicit exit 0; snapshot transport is 44/44 PASS and launcher/acceptance PASS. External signing/dependency/browser/Parrot product gates remain RC=77/BLOCKED. Final sealing is rerun on the frozen identity-covered source state.
- Phase 78 — built-in Guided Lab / Scenario Curriculum Wave 1: eight offline Windows/Linux troubleshooting labs for gateway, DNS, host-firewall and RDP/SSH service failures; learner-visible catalog/launcher with four transparent difficulty dimensions; normal compiler/Runtime launch; deterministic development acceptance proves broken baseline → typed remediation → same-probe recovery without exposing solution data in the learner manifest.


## Phase 79 — portable troubleshooting session hardening

Implemented `.yadisession` portable backup/recovery over the existing combined Runtime-progress + Evidence Notebook session envelope. Import is bounded, exact-scenario-bound, content-address verified and atomic; corruption/tampering/cross-scenario input fails closed before workspace mutation. Existing separate progress/notebook files and IndexedDB session autosave remain supported. Release classification is unchanged pending full/sealing regression and external product gates.

### Phase 88 — NAT/PAT transformation X-Ray

Phase D advances with an Engine-owned immutable NAT decision trace over the already implemented DNAT/SNAT semantics. `ReachabilityDetails.natDecisions` propagates exact ordered rule evaluation, selected translation identity, before/after source and port values, transformation disposition and fail-closed uncertainty through Active Probe and Visual Journey to a NAT/PAT X-Ray. The UI performs no NAT/PAT evaluation. DNAT preserves ordered first-match destination-port translation; SNAT preserves its existing whole-ruleset syntax prevalidation and continues to reject source-port PAT. Conntrack, reverse/return NAT and forward/return comparison remain unimplemented. Focused verification: Engine 220 + 114 + 24 + 22, Active Probe 149 + 25, Visual Journey 16 + 58 plus UI contract, schema/compiler/canvas/branding/acceptance/package-lock gates PASS. Full Foundation remains BLOCKED at the same missing installed `elkjs/lib/elk.bundled.js` dependency boundary; Parrot and final real Chromium/Firefox acceptance are NOT RUN.

### Phase 89 — Conntrack/session state X-Ray

Phase D advances with an explicit modeled conntrack/session snapshot owned by the Engine. `properties.conntrack = { complete, entries[] }` records bounded session evidence; an exact tuple lookup uses the Engine-observed source address, requested destination, protocol and destination port where applicable. A complete-table miss is provably `FALSE`; an incomplete-table miss, malformed/duplicate/ambiguous state or an `UNKNOWN` selected state remains `UNKNOWN`. Ordered firewall rules may declare `connectionState` (`NEW`, `ESTABLISHED`, `RELATED`, `INVALID`) and can match only when the Engine proves that state; conntrack never becomes a parallel allow engine. The same immutable `ReachabilityDetails.conntrackDecisions` trace propagates through Active Probe and Visual Journey to a Conntrack/Session X-Ray, and manipulated/internally inconsistent traces fail closed. Cross-phase tests prove upstream STP blocks suppress downstream conntrack evidence and downstream conntrack consumes the translated source observed after SNAT. No automatic session creation/aging/expiry, source-port tuple, reverse-tuple reconstruction, local-vs-network-firewall distinction or forward/return comparison is implemented in this checkpoint. Focused verification: Engine **242 + 128 + 24 + 22**, Active Probe **157 + 26**, Visual Journey **21 + 68** plus UI contract, schema/compiler/canvas/branding/acceptance/package-lock gates PASS. The final `test:foundation` run reaches and passes Canvas, then is **BLOCKED at Layout** because `elkjs/lib/elk.bundled.js` is not installed. Browser readiness returns **RC 77 / BLOCKED** for the absent pinned dependency tree; the top-level build is likewise blocked by missing `elkjs`/`ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN** and must not be relabelled PASS without execution.

### Phase 90 — Local host firewall vs network firewall distinction

Phase D now formalizes firewall location without adding a competing policy engine. `network.firewall` resources are Engine-owned `NETWORK` firewalls; non-network resources are `LOCAL_HOST` firewalls only when `properties.isFirewall=true`. Every FIREWALL `PolicyDecisionTrace` carries the immutable `firewallScope`, propagating through Active Probe and Visual Journey to Firewall/ACL X-Ray. Schema/compiler validation rejects malformed markers, contradictory network-firewall markers, and local firewall policies without the explicit marker; runtime evaluation and Visual Journey fail closed on unprovable or manipulated scope. Focused verification on the final version-bumped source: Engine **250 + 133 + 24 + 22**, Active Probe **163 + 28**, Visual Journey **26 + 71** plus UI contract, schema/compiler/canvas/branding/acceptance/package-lock gates PASS. `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** because `elkjs/lib/elk.bundled.js` is not installed; browser readiness is **RC 77 / BLOCKED**, and top-level build is **RC 2 / BLOCKED** by missing `elkjs`/`ajv`. Parrot and final real Chromium/Firefox acceptance are **NOT RUN**. Forward/return path comparison remains the final unimplemented Phase D deliverable.


### Phase 91 — Forward / return path comparison

Phase D's listed deliverables are now complete with an Engine-owned `ForwardReturnPathComparisonTrace`. The Engine independently evaluates destination→source return routing rather than reversing the forward path or assuming symmetry, classifies `SYMMETRIC`/`ASYMMETRIC`/`UNRESOLVED`, records forward-vs-return route-interface differences, and propagates the immutable comparison through Active Probe and Visual Journey to a dual-path X-Ray. For TCP/UDP service-port probes the client ephemeral return port is not modeled, so reverse security is intentionally `NETWORK_ONLY / RETURN_TUPLE_NOT_MODELED`; reverse firewall/NAT/conntrack evidence is not fabricated. Portless probes can use full reverse security evaluation while still skipping listener semantics for response traffic. Final version-bumped verification: Engine **263 + 136 + 24 + 22**, Active Probe **176 + 28**, Visual Journey **29 + 77** plus UI contract, schema/compiler/canvas/branding/acceptance/package-lock gates PASS. `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** because `elkjs/lib/elk.bundled.js` is not installed; browser readiness is **RC 77 / BLOCKED**, and top-level build is **RC 2 / BLOCKED** on missing `elkjs`/`ajv`. Parrot and final real Chromium/Firefox acceptance are **NOT RUN**.

### Phase 92 — Host Stack process / socket / service view

Phase E begins with an Engine-owned Host Stack microscope. `properties.hostStack = { complete, processes[], sockets[] }` can explicitly model process/PID, TCP/UDP socket rows, local/remote endpoints, socket state and process/service ownership. The Engine derives immutable bind scope and bounded service/socket selection evidence, propagates it through Active Probe and Visual Journey, and the browser renders service/process/socket tables without guest discovery or UI-owned inference. Legacy service-only scenarios remain compatible as `SERVICE_DECLARATIONS` and never fabricate process/socket ownership. Schema/compiler/runtime/presentation boundaries fail closed on malformed, duplicate or contradictory ownership state. Final version-bumped verification: Engine **281 + 145 + 24 + 22**, Active Probe **191 + 29**, Visual Journey **30 + 83** plus UI contract, schema/compiler/canvas/branding/acceptance/package-lock gates PASS. `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** because `elkjs/lib/elk.bundled.js` is not installed; browser readiness is **RC 77 / BLOCKED**, and top-level build is **RC 2 / BLOCKED** by missing `elkjs`/`ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN**. This checkpoint intentionally does not implement the later Phase E DNS chain, DHCP DORA, full listener/service-state semantics, TCP state machine, UDP/ICMP failure distinctions or MTU/PMTUD.

### Phase 93 — DNS Chain X-Ray

Phase E advances with an Engine-owned immutable DNS chain over the existing modeled resolver configuration. `queryDnsChain` binds exact source/query, configured resolver order, literal resolver address mapping, resolver network/gateway truth, DNS service state, modeled A-like records, selected resolver and answer/resource mapping. Active Probe no longer owns a competing resolver loop; it renders Engine truth. Visual Journey validates the trace fail-closed before exposing a DNS Chain X-Ray, and the UI performs no DNS resolution, resolver selection or record matching. A resolver blocked by network/policy truth terminates at `NETWORK_BLOCKED` without inspecting service/records or fabricating an answer. Compiler validation now rejects malformed authored resolver lists and DNS service/record shapes while duplicate modeled records remain runtime ambiguity owned by Engine. This slice intentionally does not implement recursive DNS/CNAME semantics, real DNS traffic or DHCP DORA. Final version-bumped verification: Engine **300 + 157 + 24 + 22**, Active Probe **194 + 29**, Visual Journey **36 + 89** plus UI contract, Compiler **69 + 110 + 2/2 output schema**, schema/canvas/branding/acceptance/package-lock gates PASS. `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** because `elkjs/lib/elk.bundled.js` is not installed; browser readiness is **RC 77 / BLOCKED**, and top-level build is **RC 2 / BLOCKED** by missing `elkjs`/`ajv`. Parrot and final real Chromium/Firefox acceptance are **NOT RUN**. Full details are recorded in `docs/PHASE93_DNS_CHAIN_XRAY.md`.



### Phase 94 — DHCP DORA X-Ray

Phase E advances with an Engine-owned modeled DHCP DORA chain over explicit local L2 topology and explicit server offer state. `queryDhcpDora` proves Discover and Offer-return paths with VLAN/STP-aware L2 truth, reads explicit server enabled/pool/offer/options state, and emits immutable DISCOVER/OFFER/REQUEST/ACK truth. Active Probe exposes modeled Windows `ipconfig /renew` and Linux `dhclient -v` without guest execution; Visual Journey validates the trace fail-closed and DHCP DORA X-Ray performs no server selection, address allocation or relay inference. Multiple valid Offers, malformed/incomplete state and unprovable paths remain `UNKNOWN`; exhausted pools and proven L2 blocks are `FALSE`. Cross-phase verification proves STP blocking prevents downstream DHCP server/pool/offer evidence from being consumed. DHCP relay, dynamic lease synthesis/mutation, T1/T2, renew/rebind, declined-address conflict handling and real DHCP traffic remain deliberately NOT MODELED. Final version-bumped verification: Engine **318 + 167 + 24 + 22**, Active Probe **210 + 32**, Visual Journey **44 + 97** plus UI contract, Compiler **69 + 126 + 2/2 output schema**, schema/canvas/branding/acceptance/package-lock gates PASS. `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** because `elkjs/lib/elk.bundled.js` is not installed; browser readiness is **RC 77 / BLOCKED**, and top-level build is **RC 2 / BLOCKED** on missing `elkjs`/`ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN**. Full details are in `docs/PHASE94_DHCP_DORA_XRAY.md`.

### Phase 95 — Listener / Service State semantics

Phase E advances by separating listener truth from service declaration state. `queryListenerServiceState` consumes the existing Host Stack projection: explicit complete TCP `LISTEN` / UDP `BOUND` socket evidence is authoritative, complete absence proves no listener, partial absence remains `UNKNOWN`, and malformed ownership fails closed. Service enabled/disabled/mixed/unknown state remains separately visible and cannot create or suppress socket truth. Legacy service-only scenarios retain declaration-only compatibility without fabricated socket IDs. Reachability propagates the immutable decision through Active Probe and Visual Journey; Listener / Service State X-Ray displays both truths and highlights mismatches without UI-owned inference. Final version-bumped verification: Engine **344 + 177 + 24 + 22**, Active Probe **218 + 32**, Visual Journey **44 + 97** plus UI contract, Compiler **69 + 126 + 2/2 output schema**, schema/canvas/branding/acceptance/package-lock gates PASS. `test:active-probes` passes **218 + 32** then is **RC 2 / BLOCKED** at browser compilation on missing `elkjs`; `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** on the same missing pinned dependency; browser readiness is **RC 77 / BLOCKED**, and top-level build is **RC 2 / BLOCKED** on missing `elkjs`/`ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN**. The next listed Phase E deliverable is the **TCP state machine**.


### Phase 96 — TCP State Machine X-Ray

Phase E advances with a bounded Engine-owned TCP lifecycle microscope over explicit Host Stack socket evidence. `queryTcpStateMachine` binds exact source/destination/port, distinguishes listener-only from source-bound session rows, exposes current lifecycle states and a canonical transition table, and preserves `CONNECTION_REFUSED` when a reached destination has no proven TCP listener. TCP session states require explicit peer identity; malformed/incomplete rows fail closed. Active Probe propagates the immutable trace and Visual Journey validates exact socket projection, selection, state set and canonical transitions before rendering TCP State Machine X-Ray. Sequence/ACK progression, retransmission/RTO, timers and automatic socket-state mutation remain explicitly `NOT_MODELED`. Final version-bumped verification: Engine **363 + 187 + 24 + 22**, Active Probe **225 + 32**, Visual Journey **44 + 97** plus UI contract, Compiler **69 + 131 + 2/2 output schema**, schema/canvas/branding/acceptance/package-lock gates PASS. `test:active-probes` passes **225 + 32** and is then **RC 2 / BLOCKED** at browser compilation on missing `elkjs`; the Layout gate is independently **RC 2 / BLOCKED** on the same missing pinned dependency, browser readiness is **RC 77 / BLOCKED**, and top-level build is **RC 2 / BLOCKED** on missing `elkjs`/`ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN**. The next listed Phase E deliverable is **UDP/ICMP failure distinctions**.

### Phase 97 — UDP / ICMP Failure Distinctions

Dev18 status: **LOCAL VERIFIED / PARROT PENDING**. Engine-owned immutable classification over existing reachability/listener/policy/NAT truth distinguishes UDP deliverability, no listener, policy/network blocks, incomplete snapshots and UNKNOWN; ICMP proves only the request path. Reply, ICMP wire type/code/unreachable evidence, timeout and retries remain NOT_MODELED. The existing source-gateway diagnostic is now Engine-owned, and Observation/Journey/X-Ray consume its final classification without deciding failures. Multi-BOUND delivery ambiguity fails closed; STP and firewall decisions remain authoritative before endpoint state. Journey uses diagnostic terminal events rather than fabricated packet receipt/drop markers.

New coverage: **34 functional + 36 adversarial + 11 cross-phase Engine assertions**, **38 + 10 Active Probe**, **58 + 14 Journey**, and **21 actual React-render X-Ray contract assertions**. Prior core counts remain Engine 363 + 187 + 24 + 22, Active Probe 225 + 32, Journey 44 + 97, Compiler 69 + 131; schema 55/55 + 18/18. Full Foundation's 196-command chain completed through the last gate with explicit exit 0 using pinned Python and Go 1.23.2 offline. Browser bundling PASS: 30 hashed local files, 23 resolved runtime components. The local preserved pinned dependency graph matches dev17; no package fetch or dependency-version change was needed. The dev17 missing-elkjs/ajv environment blockers no longer apply in this restored workspace. This does not revise the historical dev17 test results.

Parrot OS and final real Chromium/Firefox acceptance remain **PENDING / NOT RUN**. No release signing operation or private release key is used. Next authoritative deliverable: **Phase E MTU/PMTUD**, not started. See `docs/PHASE97_UDP_ICMP_FAILURE_DISTINCTIONS.md` and checkpoint audit/test results.
