# YadiLab — v1.8.0-dev.12 (IMPORT-002)

**Current development checkpoint (not yet user verified).** The user-verified Dev11 source remains immutable in Git history at `8fbf429f2eeab83066ae78d49d64ff9483868b2e` (source ZIP SHA-256 `cce1deddc0b28b5b1b1c0aa467731d9cbfa2aa6be65f2db088c46c93846372d1`). IMPORT-001 is `2a4360f62e1562de186a9be9582bbe33737e34dd`. This successor fixes Excel import discovery by exposing **Import Excel / CSV → Network Topology** permanently in the MAIN ACTIONS area (not in a collapsed menu); it includes the existing explicit preview and confirm flow. Version, start-script marker and browser build marker are now `1.8.0-dev.12 / IMPORT-002`. Portable Linux package uses port `18234` by default to avoid confusing old `18233` servers/browser profiles with the current build. See `docs/IMPORT002_DIRECT_EXCEL_CSV_ENTRYPOINT.md`. No `.docx`/PDF-table import is implied.

---

## Earlier project documentation (historical)

# YadiLab v1.1.0-dev.23


## dev23 Synchronized Event X-Ray

`v1.1.0-dev.23` makes X-Ray an explicit, always-visible projection of the same canonical Engine event currently selected by Packet Journey. The X-Ray has no independent cursor: Play, Pause, forward/backward Step, scrub and Replay all move Journey and X-Ray together. The base X-Ray always shows exact event identity, decision family, current/source/target resource, active/projected connection, protocol/port, Engine truth, provenance, evidence references and event summary.

Host Stack, listener/service and TCP microscope evidence now receive explicit canonical timeline events (`hoststack.decision`, `listener.service`, `tcp.state`) so those detailed panels appear only when their Engine event is current. DNS, DHCP and UDP/ICMP detailed X-Ray are likewise event-bound rather than Journey-wide static truth. No route, service, process, packet, return traffic or decision is inferred by the UI. See `docs/DEV23_SYNCHRONIZED_EVENT_XRAY.md`.


## dev22 Canonical Packet Journey v2

`v1.1.0-dev.22` starts the post-dev21 Living Visualization program without changing Engine truth or the dependency graph. It formalizes one canonical deterministic playback contract over Engine-projected events and adds a separate packet-outcome contract for `destination_reached`, `dropped` and `unknown`. A verified destination arrival can render a small green `✓` for 4000 ms; a verified exact drop point can render a red `✕` for 4000 ms; UNKNOWN or an unlocated failure never receives a fabricated success/drop marker. Multi-hop playback must stop at the Engine-owned blocking point and must never animate through later topology nodes after a verified drop.

The outcome marker is presentation-only transient state. It does not alter Engine truth, evidence, routing, policy, NAT, conntrack or service semantics. A green marker means only that Engine evidence proves the modeled packet/request path reached the destination; it is not an automatic claim of application success. See `docs/DEV22_CANONICAL_PACKET_JOURNEY_V2.md`.


## dev21 UI/browser stabilization

`v1.1.0-dev.21` stabilizes the bounded viewport, compact responsive toolbar, independently scrolling control column, Visual Journey reachability and React Flow theming. It removes the unthemed default MiniMap, completes the principal Swedish presentation labels, and ships a fail-closed Parrot file-manager launcher with an exact HTTP build-marker check. No dependency graph or Engine semantics change.

YadiLab v1.1.0-dev.23 development checkpoint line under Masterprompt v1.3 VERIFIED / LOCKED plus the authoritative Living Topology & Visual Simulation Specification v1.0. Phase A Living Packet Journey and Phase B Real Device Visuals are complete. Phase C contains Engine-backed Routing X-Ray, ARP/ND X-Ray, MAC/CAM/FDB switching, VLAN/access/trunk, and STP/BPDU forwarding/blocking. Phase D now contains Engine-owned Firewall/ACL X-Ray, immutable DNAT/SNAT transformation traces with NAT/PAT X-Ray, explicit Engine-owned conntrack/session snapshot lookup with stateful-firewall binding and Conntrack/Session X-Ray, an Engine-owned distinction between network firewalls and local host firewalls, and Engine-owned forward/return path comparison with explicit asymmetry/interface evidence. Automatic session lifecycle and reverse TCP/UDP service-tuple reconstruction remain deliberately unmodeled; TCP/UDP return security is reported as NETWORK_ONLY when the client ephemeral return port is unavailable. Phase E now contains Engine-owned Host Stack process/socket/service evidence, DNS chain truth, modeled local-L2 DHCP DORA, listener/service-state semantics that keep explicit socket-listener truth separate from service enabled/disabled declarations, and a bounded Engine-owned TCP state-machine microscope over explicit Host Stack socket lifecycle state. Phase 97 adds Engine-owned UDP/ICMP failure distinctions, exact Active Probe/Journey propagation and UDP / ICMP Failure X-Ray without fabricated replies, ICMP packets or timeouts. See `docs/PHASE97_UDP_ICMP_FAILURE_DISTINCTIONS.md`. The locked v1.0.0 VERIFIED PRODUCT RELEASE remains the production reference.


## dev19 UI maintenance

`v1.1.0-dev.21` continues the UI-maintenance line. It does not start a new network-modeling phase and does not change dependencies. The topology canvas is viewport-stable and independent of the right-side panel height; the right-side control/results column owns its vertical scrolling. Collapsing all right-side panels therefore cannot resize or remove the topology canvas. High-level visible UI section headings are localized to Swedish while internal Engine identifiers, truth values, data attributes, and model semantics remain unchanged.

Phase 80 begins the Living Packet Journey vertical slice: deterministic Engine-backed path visualization, directional arrows, PDU/particle/flow-pulse renderers, arrival/drop states, and Journey Player controls. See `docs/PHASE80_LIVING_PACKET_JOURNEY.md`.

Phase 82 begins Routing & Switching X-Ray with an explicit Engine route-decision trace, Active Probe/Visual Journey propagation, route-decision timeline events and an in-place routing table overlay that never recalculates the winner in UI code. See `docs/PHASE82_ROUTING_XRAY.md`.

Phase 83 adds explicit modeled ARP/ND neighbor-table state, deterministic Engine neighbor decisions, exact Active Probe/Visual Journey propagation, fail-closed trace validation and an in-place ARP/ND table overlay. Missing neighbor state remains absent or UNKNOWN and never produces an invented MAC address, cache hit or resolution. See `docs/PHASE83_NEIGHBOR_XRAY.md`.

Phase 84 adds explicit modeled MAC/CAM/FDB state, deterministic Engine source-learning and destination-forwarding traces, exact Active Probe/Visual Journey propagation, known-unicast branch selection and explicit unknown-unicast/broadcast flood fan-out. The UI never learns a MAC, selects a port or constructs a flood set. VLAN/access/trunk semantics are added in Phase 85; STP, MAC aging and multicast-membership semantics remain later Phase C work. See `docs/PHASE84_MAC_CAM_XRAY.md`.

Phase 85 adds Engine-owned access/trunk classification, allowed/native VLAN handling, tagged/untagged frame state, deterministic tag add/remove/preserve decisions, VLAN-aware MAC flooding, exact Active Probe/Visual Journey propagation, and separate VLAN-decision plus trunk/access-port X-Ray tables. The UI projects Engine truth only and performs no VLAN inference. See `docs/PHASE85_VLAN_TRUNK_XRAY.md`.

Phase 86 completes the current authoritative Phase C switching order with explicit STP/RSTP/MSTP bridge identity, port role/state, modeled BPDU direction, Engine-owned forwarding/blocking decisions, STP-filtered flood sets, exact Active Probe/Visual Journey propagation, and an in-place STP/BPDU X-Ray. Partial, malformed, ambiguous or manipulated state fails closed; the UI performs no root election or port-state calculation. See `docs/PHASE86_STP_BPDU_XRAY.md`.

Phase 87 begins Phase D — Stateful Network Decisions with Engine-owned ordered firewall/ACL decision traces, explicit match/no-match/disabled/malformed/indeterminate/not-evaluated rule rows, default-action provenance, exact Active Probe/Visual Journey propagation, manipulated-trace fail-closed validation, and an in-place Firewall/ACL X-Ray. The UI never evaluates firewall or ACL policy. NAT/PAT, conntrack/session state and forward/return comparison are intentionally out of scope for this checkpoint. See `docs/PHASE87_FIREWALL_ACL_XRAY.md`.

Phase 88 adds Engine-owned DNAT/SNAT transformation traces with ordered rule dispositions, exact before/after source and port values, strict preservation of existing DNAT first-match and SNAT fail-closed prevalidation semantics, Active Probe/Visual Journey propagation, manipulated-trace rejection, and an in-place NAT/PAT X-Ray. Source-port PAT, conntrack/session state, automatic reverse NAT and forward/return comparison remain explicitly out of scope. See `docs/PHASE88_NAT_PAT_XRAY.md`.

Phase 89 adds explicit modeled conntrack/session snapshots with completeness provenance, deterministic Engine tuple lookup, `NEW`/`ESTABLISHED`/`RELATED`/`INVALID` state binding to ordered firewall rules, exact Active Probe/Visual Journey propagation, manipulated-trace rejection, and an in-place Conntrack/Session X-Ray. The Engine does not auto-create, age or expire sessions, and this phase does not reconstruct reverse tuples or compare forward/return paths. See `docs/PHASE89_CONNTRACK_SESSION_XRAY.md`.

Phase 90 formalizes the existing firewall-location model: `network.firewall` is Engine-classified as `NETWORK`, while `properties.isFirewall=true` on a non-network-firewall resource is Engine-classified as `LOCAL_HOST`. The scope is carried immutably in FIREWALL policy traces through Active Probe and Visual Journey into Firewall/ACL X-Ray; schema/compiler/runtime/presentation boundaries reject contradictory or unprovable scope rather than guessing. See `docs/PHASE90_LOCAL_NETWORK_FIREWALL.md`.

Phase 91 completes the listed Phase D deliverables with Engine-owned forward/return path comparison. The Engine independently evaluates the return network path instead of assuming symmetry, classifies `SYMMETRIC`/`ASYMMETRIC`/`UNRESOLVED`, exposes per-resource route-interface differences and propagates the immutable comparison through Active Probe and Visual Journey to a dual-path X-Ray. For TCP/UDP service probes, reverse firewall/NAT/conntrack truth is intentionally `NETWORK_ONLY / RETURN_TUPLE_NOT_MODELED` because the client ephemeral return port is not modeled; no downstream layer fabricates it. See `docs/PHASE91_FORWARD_RETURN_PATH_COMPARISON.md`.

Phase 92 begins Phase E — Host Stack & Core Services with an Engine-owned process/socket/service view. Scenarios may declare `properties.hostStack = { complete, processes[], sockets[] }`; the Engine projects process/PID, socket protocol/local bind/state, bind scope, explicit process/service ownership and selected service/socket evidence without guest discovery or UI inference. Legacy service-only scenarios remain supported and are explicitly labeled `SERVICE_DECLARATIONS` with process/socket ownership `NOT MODELED`. Malformed, duplicated or contradictory ownership state fails closed. This checkpoint does not implement the later Phase E DNS chain, DHCP DORA, full listener/service-state semantics, TCP state machine, UDP/ICMP failure distinctions or MTU/PMTUD. See `docs/PHASE92_HOST_STACK_PROCESS_SOCKET_SERVICE_VIEW.md`.

Implemented through Phase 79 (see `docs/FOUNDATION_STATUS.md`). Earlier work includes: authoritative contracts, compiler, deterministic Engine, canonical regression, safe PackageIO, headless CLI, canvas projection, compound layout boundary, Builder/Runtime browser foundation, strict progress saves and IndexedDB/PWA foundation, loopback Linux distribution, fail-closed Parrot acceptance, dependency-locked full-browser-build gate, safe `.yadilab` package open/export, Runtime history/explainability, typed Builder Inspector/authoring panels, Builder canvas interactions including semantic multi-select, live manual layout overrides, zone resize, interactive connection creation, and portable Builder notes carried through schema/compiler/import/export without affecting Engine outcomes.

Run Foundation verification:

```bash
npm run test:foundation
```

Check real browser dependency readiness:

```bash
npm run check:browser-readiness
```

Exit code `77` means BLOCKED and must never be relabelled PASS.

When dependency readiness is PASS:

```bash
npm run build:browser
npm run build:launcher
```

On the required Parrot OS x86-64 target:

```bash
bash scripts/run_parrot_acceptance.sh
```

Every completed v1.1.0 development checkpoint is packaged with SHA-256 and uploaded to Google Drive `YadiLab/Development` before the next phase begins.

Phase 35 adds bounded IPv4 SNAT and source-aware CIDR filtering (forward path only). See `docs/PHASE35_IPV4_SNAT.md`.

Phase 36 adds a deterministic end-to-end Proxmox + OPNsense + Windows AD/RDS + logging + backup Golden Scenario acceptance case, with isolated SNAT/DNAT downstream CIDR probes. See `docs/PHASE36_INTEGRATED_ACCEPTANCE.md`.

## Phase 37: offline browser-dependency handoff

The sandbox cannot resolve npm registry DNS, so **the real browser bundle remains BLOCKED**. Phase 37 hardens lockfile and installed-package consistency and includes an optional Linux x86-64 *developer-only* procedure to prepare a real npm cache on a trusted internet-connected machine and install/build entirely offline on the target builder. See `docs/PHASE37_OFFLINE_BROWSER_DEPENDENCIES.md` and `npm run check:package-lock`. Normal application end users never need npm or Node.

## Phase 39: bounded raster header preflight

PNG/JPEG/WebP package assets now require conservative local structural/header checks at both PackageIO write/read and browser Blob creation. This rejects simple spoofed image MIME, malformed/truncated container headers, oversized declared dimensions, CRC-corrupted PNG and unsupported animation. It is deliberately **not** full compressed-pixel decoding; native browser decoders remain authoritative for visual renderability. See `docs/PHASE39_RASTER_PREFLIGHT.md`.

## Phase 41: authenticated-by-release-hash PWA asset verification

The generated offline service worker now checks actual same-origin response
bytes against the exact SHA-256 content manifest before precaching or serving
release assets. A failed update never deletes the previous cache; user files
and arbitrary dynamic HTTP responses are never cached. This verifies internal
release consistency, **not publisher identity/signatures**, nor a rendered
React/browser/Parrot acceptance test. See
`docs/PHASE41_PWA_BYTE_INTEGRITY.md`.


## Phase 50: sealed-snapshot producer coherence and offline replay

Dependency snapshot preparation now treats `development-platform.json` as verified evidence rather than an opaque hashed file. Producer metadata must describe Linux x86-64 with syntactically valid Node/npm/kernel identities, and the snapshot manifest `target`/`preparedWith` values must be derived from and remain identical to that metadata. The trusted online producer also destroys its first `node_modules` install and performs a fresh `npm ci --offline` from the populated snapshot cache, then reruns dependency readiness and executable browser-toolchain checks before any manifest can be sealed. See `docs/PHASE50_SNAPSHOT_PRODUCER_COHERENCE.md`.

## Phase 51: sealed-snapshot consumer coherence

The offline installer now treats the producer's Node/npm identity as part of the sealed dependency contract. Before npm may inspect the transferred cache or run `npm ci --offline`, the consuming host must be Linux x86-64 and its exact `node --version` and `npm --version` must match `snapshot-manifest.json -> preparedWith`. Mismatches fail closed with exit 77 rather than silently changing the installation engine. See `docs/PHASE51_SNAPSHOT_CONSUMER_COHERENCE.md`.

## Phase 49: target-native optional dependency closure

For the mandatory Linux x86-64 target, dependency readiness now explicitly requires the native `@esbuild/linux-x64@0.28.2` package to be declared by `esbuild`, present in the npm v3 lock, included in the required closure, and present in npm's installed hidden lock/physical package metadata. This moves a missing-native-package failure earlier into the sealed dependency handoff while retaining the Phase 46 executable esbuild transform as a separate mandatory gate. See `docs/PHASE49_TARGET_OPTIONAL_CLOSURE.md`.

## Phase 54: signed dependency-snapshot provenance

Sealed dependency transports now require source-trusted Ed25519 provenance in addition to the transport SHA-256 sidecar. The detached signature binds the exact snapshot manifest, source-checkout identity, Linux x86-64 target, and producer Node/npm identity. Private signing keys are forbidden inside the YadiLab checkout; the v0.54.0 trust store intentionally contains no test/producer key, so real snapshot production remains fail-closed until an operator deliberately provisions a public trust anchor in a reviewed checkpoint. See `docs/PHASE54_SIGNED_SNAPSHOT_PROVENANCE.md`.

## Phase 55: snapshot trust-anchor lifecycle

The source-controlled producer trust store now has a canonical schema with explicit `active`/`revoked` lifecycle state. Trust onboarding requires an external Ed25519 public key plus a separately supplied expected `ed25519-sha256:<fingerprint>`; the derived fingerprint must match before the trust store can change. Revoked keys remain recorded but cannot sign or verify new dependency snapshots. The production trust store remains intentionally empty until a real operator public key is provisioned through this reviewed ceremony. See `docs/PHASE55_SNAPSHOT_TRUST_LIFECYCLE.md`.


## Phase 56: trust activation and rotation ceremony

Public-key onboarding is now a two-step trust ceremony. A new Ed25519 producer key is first staged as `pending`; it cannot sign snapshots until the matching external private key proves possession and creates a cryptographically verifiable activation proof stored in the canonical trust store. Rotation is checkpoint-coupled because the trust store is part of source-checkout identity: use an overlap checkpoint with both proven keys active, then revoke the old key in a subsequent checkpoint and create a fresh signed dependency snapshot for that new source identity. See `docs/PHASE56_TRUST_ACTIVATION_ROTATION.md`.


## Phase 57: operator key-material ceremony

A dedicated operator-key tool can create a dependency-snapshot producer Ed25519 key bundle outside the application checkout using an atomic sibling-stage/rename flow. The private key is created with exact mode `0600`; the public key, fingerprint and public ceremony record use `0644`. Verification proves the Ed25519 private/public pair, exact fingerprint, canonical ceremony metadata and the source-checkout identity from which the ceremony was initiated. Existing destinations, symlink escapes, insecure private-key permissions, mismatched key pairs, altered fingerprints/records and source-identity drift fail closed. v1.0.0 pins the reviewed public producer trust anchor while keeping the private key external. See `docs/PHASE57_OPERATOR_KEY_MATERIAL_CEREMONY.md`.


## Phase 58: normalized Enterprise Model

The first Masterprompt v1.3 implementation checkpoint adds the format-independent enterprise baseline contract, explicit knowledge states, per-fact provenance, content-addressed source identities, and deterministic canonical baseline identity. Format-specific enterprise import adapters intentionally come next and must target this same model. See `docs/PHASE58_NORMALIZED_ENTERPRISE_MODEL.md`.

Phase 59 adds the first trusted/versioned import adapter layer: dependency-free JSON/CSV/TSV parsing, mapping profiles, import reports/conflicts, exact source hashing, per-field mapping provenance, explicit UNKNOWN/INVALID handling and deterministic replay into the same Enterprise Model. See `docs/PHASE59_ENTERPRISE_IMPORT_ADAPTER_FRAMEWORK.md`.


## Phase 60: safe XLSX and ODS enterprise import

Enterprise Environment Import now accepts safe XLSX and ODS spreadsheet containers through the same versioned adapter/mapping pipeline as JSON/CSV/TSV. Multi-sheet discovery, physical cell provenance, explicit header-row options, cached-formula warnings, bounded ZIP/XML parsing, active-content rejection and external-data-link rejection are included. Ordinary hyperlinks are never fetched and are ignored with a warning. Offline example templates and a matching mapping profile live in `examples/enterprise-import/`. See `docs/PHASE60_SAFE_WORKBOOK_IMPORT.md`.

## Phase 61: deterministic mapping review and re-import diff

Enterprise Import can now perform a side-effect-free mapping review before baseline creation. Existing exact/alias selectors are evaluated deterministically against discovered tables/fields; required missing or ambiguous mappings become `REVIEW_REQUIRED`, never fuzzy-guessed. Explicit user decisions create a new versioned mapping profile and are preserved as `USER_MAPPED` provenance. Duplicate entity-ID conflicts may be resolved only through a recorded exact source-table/row selection. A deterministic re-import diff compares verified baselines by semantic entity/fact keys and separates semantic changes from provenance-only changes. Automatic merge is intentionally not implemented in this phase. See `docs/PHASE61_IMPORT_MAPPING_REVIEW.md`.


## Phase 62: three-way re-import merge and baseline preservation

Phase 62 adds deterministic three-way re-import merge over ancestor/current/incoming baselines. It preserves current working changes when customer data is unchanged, auto-applies incoming changes when current state is untouched, detects convergence, and requires explicit review when both sides diverge. Merge lineage is bound into the resulting Enterprise Baseline identity. Relationships are first-class in both re-import diff and merge.


## Phase 63: Import Helper UI

Phase 63 adds the first deterministic browser **Import Helper UI** over the verified enterprise import/review/diff/merge engines. It opens XLSX/ODS/CSV/TSV/JSON locally, previews deterministic mappings, records explicit USER_MAPPED decisions, shows import diagnostics/unmapped fields/conflicts, exposes UNKNOWN/CONFLICTING/INVALID baseline facts, previews re-import diff, and collects explicit three-way merge resolutions. React does not reimplement import semantics; it calls the same trusted adapter/mapping/merge code used by headless tests. See `docs/PHASE63_IMPORT_HELPER_UI.md`.


## Enterprise topology projection (Phase 64)

A verified Enterprise Baseline can be deterministically projected into the ordinary scenario/compiler/layout/canvas pipeline from Import Helper. Missing or conflicting enterprise facts are preserved rather than guessed.

### Fault Injection Engine Core (v0.65)

YadiLab now includes a deterministic fault core built around versioned Fault Packs and non-destructive Fault Overlays. Runtime faults and persistent scenario variants resolve to ordinary Engine operations, verify expected effects/blast radius/recovery, and preserve exact origin metadata. The full user-facing Fault Injection panel is a later UI phase.

## Fault Injection UI (Phase 66)

The browser now exposes the deterministic Fault Engine through a dedicated Fault Injection panel in both Builder and Runtime. Preview is mandatory and cryptographically bound to the exact scenario revision, Engine state revision, pack identity, target bindings, seed, mode and active overlay. Runtime supports multi-fault overlays and safe latest-fault rollback; Builder uses an isolated draft and materializes a new scenario only after explicit confirmation. Difficulty remains visible as four explicit dimensions instead of an arbitrary score. See `docs/PHASE66_FAULT_INJECTION_UI.md`.

## Deterministic multi-fault/scenario generator (Phase 69)

Builder can now generate compatible multi-fault training variants from exact locked Fault Packs using an explicit uint32 seed. Generation is content-addressed and reproducible, uses bounded deterministic backtracking, preserves all selected faults' declared effects/negative controls at intermediate and final states, verifies exact combined reverse recovery, and requires an author preview before materialization. Generated variants record generator ID/version/seed/plan identity in `faultOrigin.generation`; no scalar difficulty score, AI runtime decision, temporal scheduler or fabricated OS-command diagnostics are introduced. See `docs/PHASE69_DETERMINISTIC_MULTI_FAULT_GENERATOR.md`.

## Phase 70 — Diagnostic / Observation Engine, Wave 1

Runtime now provides deterministic modeled Windows/Linux diagnostic observations for routing, DNS, DHCP, interfaces, host firewall and service/listener state. Familiar command names such as `ipconfig /all`, `route print`, `Get-NetTCPConnection`, `ip addr`, `ip route`, `resolvectl`, `nft` and `ss` are a pedagogical interface only: every transcript is explicitly marked `NO_GUEST_COMMAND_EXECUTION` and is derived solely from the current Engine state. Missing/malformed model data is shown explicitly instead of guessed, and the observation channel cannot access hidden fault/generator ground truth. See `docs/PHASE70_DIAGNOSTIC_OBSERVATION_ENGINE_WAVE1.md`.

## Phase 71 — Diagnostic / Observation Engine, Wave 2

Runtime now adds deterministic active modeled probes beside the Phase-70 configuration observations: Windows/Linux ping, TCP-port checks, DNS lookups and path traces. Connectivity reuses the verified Network Engine, while host-side off-link/default-gateway and ACL-default semantics are applied only when the modeled evidence is sufficient. DNS resolution uses declared resolver resources and records only. Every result is explicitly `ACTIVE_MODELED_PROBE` + `NO_GUEST_COMMAND_EXECUTION`; no packet, socket, DNS request or guest command is actually executed. See `docs/PHASE71_DIAGNOSTIC_OBSERVATION_ENGINE_WAVE2.md`.

## Phase 72 — Troubleshooting Session / Evidence Notebook

Runtime now provides a learner-owned, scenario-bound evidence notebook over the verified Wave-1 observations and Wave-2 active modeled probes. Saved evidence is ordered, revision-bound and content-addressed; manual hypotheses, next steps and conclusions are separate learner entries. The portable `.yadinotebook` document is bound to the exact scenario hash and a canonical notebook SHA-256 identity. Stale transcripts, duplicate same-revision evidence, cross-scenario imports, schema-invalid documents and identity tampering fail closed. The notebook never imports hidden fault truth, canonical solution material or automatic diagnosis. No guest command execution is introduced. See `docs/PHASE72_TROUBLESHOOTING_EVIDENCE_NOTEBOOK.md`.

## Phase 73 — Evidence Notebook Persistence & Replay

Runtime autosave now persists ordinary Runtime progress and the learner Evidence Notebook together in a content-addressed exact-scenario troubleshooting session. Restore validates the combined envelope, embedded SaveState, embedded notebook, scenario/revision bindings, notebook identity and session identity before reinstating both Runtime and notebook state. A present tampered session fails closed instead of silently falling back to progress-only restore; progress-only fallback remains available only when no combined session exists, preserving backward compatibility. Replay follows notebook evidence sequence while retaining exact captured revisions without inventing chronology or diagnosis. See `docs/PHASE73_EVIDENCE_NOTEBOOK_PERSISTENCE_REPLAY.md`.


## Phase 74 — Troubleshooting Objectives / Evidence Review

Scenario authors can now declare transparent learner-visible evidence requirements over the Phase-72/73 Evidence Notebook. Objectives can require ordered or unordered observation/probe evidence and match explicit category/resource/protocol/port/DNS/verdict fields. Runtime review reports only `SATISFIED`, `PENDING` or `OUT_OF_ORDER` with exact matched notebook entries and a content-addressed review identity. No score, grade, automatic diagnosis, hidden fault truth or AI inference is introduced. See `docs/PHASE74_TROUBLESHOOTING_OBJECTIVES_EVIDENCE_REVIEW.md`.


## Phase 75 — Troubleshooting Remediation / Verification Loop

v0.75.0 adds learner-driven modeled remediation with mandatory current-revision before evidence, non-destructive preview tokens bound to notebook/state/operation, one-step Runtime-history commit, immutable remediation notebook entries, and deterministic matching of before/after observation or active-probe evidence. Active probes can prove `RESTORED` or `REGRESSED`; observation transcripts can prove modeled configuration change. No canonical solution lookup, hidden truth, scoring, grading, AI/ML/LLM, guest command execution or live network connector is introduced.


## Phase 76 — Typed Remediation Actions / Safety Constraints

v0.76.0 replaces the learner-facing raw path/JSON remediation editor with a bounded Windows/Linux typed-action catalog. Gateway, DNS, firewall, interface, service and Windows network-profile actions are validated for exact parameters, OS/resource compatibility and safe value ranges before compilation to one deterministic Phase-75 Engine operation. New notebooks use schema 0.3.0 with optional immutable typed-action audit metadata; legacy 0.1.0/0.2.0 notebooks remain accepted. No automatic solution recommendation, guest execution, live connector, hidden scoring or AI/ML/LLM is introduced.


## Phase 77 — Guided Troubleshooting Workflow / Remediation UX

v0.77.0 adds a deterministic Runtime process map across evidence collection, learner-visible evidence review, learner hypothesis, typed remediation, matching after-evidence and before/after verification. The workflow boundary is `PROCESS_GUIDANCE_NO_DIAGNOSIS`: it never chooses the learner's target, command, probe, diagnosis, remediation action or remediation value. Exact workflow state is content-addressed and bound to the current Runtime revision and canonical notebook/review identities.

## Phase 78 — Guided Lab / Scenario Curriculum Wave 1

v0.78.0 adds the first built-in offline troubleshooting curriculum: eight deterministic labs split evenly between Windows and Linux, covering wrong default gateway, wrong DNS resolver, blocking host-firewall policy and disabled RDP/SSH service. The learner can start a lab directly in Runtime or open it in Builder. The learner-visible catalog contains only title/platform/focus/summary/sequence plus the four transparent difficulty dimensions; test-only acceptance verifies the full evidence → typed remediation → same-probe recovery loop without exposing solution parameters in the curriculum manifest. See `docs/PHASE78_GUIDED_LAB_CURRICULUM_WAVE1.md`.


## Phase 79: portable troubleshooting session backup and recovery

Runtime can now export one portable `.yadisession` backup containing the exact content-addressed Runtime progress and Evidence Notebook session envelope, and restore it atomically into the exact same scenario hash. Import validates the portable extension, bounded local JSON size, session schema, embedded SaveState schema, embedded notebook schema, notebook identity, session identity and scenario binding before any Runtime/notebook state is changed. Corrupt, tampered, cross-scenario or malformed backups fail closed. Existing `.yadiprogress` and `.yadinotebook` exports remain available and existing IndexedDB combined-session autosave semantics are unchanged. No hidden solution material, live connector, guest execution or network mutation is added. See `docs/PHASE79_PORTABLE_SESSION_HARDENING.md`.

Phase 93 advances Phase E with an Engine-owned DNS chain. Configured resolver order, literal resolver-to-resource mapping, network/gateway reachability, DNS service state, modeled A-like records, selected resolver and resolved address/resource mapping are emitted as one immutable `DnsChainDecisionTrace`. Active Probe consumes the Engine trace instead of running a separate DNS decision loop; Visual Journey validates source/query/order/mapping/network/service/record/answer bindings fail-closed and the browser renders a DNS Chain X-Ray without selecting resolvers or matching records itself. Network blocks stop the chain before service/record inspection. Compiler authoring validation rejects malformed resolver lists and malformed DNS service/record shapes while runtime ambiguity remains Engine-owned `UNKNOWN`. This checkpoint does not implement recursive DNS/CNAME behavior or DHCP DORA. See `docs/PHASE93_DNS_CHAIN_XRAY.md`.


Phase 94 advances Phase E with an Engine-owned modeled DHCP DORA chain over explicit local L2 topology and explicit server offer state. The Engine proves Discover and Offer return reachability using VLAN/STP-aware local L2 truth, then projects server enabled/pool/offer evidence into deterministic DISCOVER → OFFER → REQUEST → ACK stages. Active Probe exposes Windows `ipconfig /renew` and Linux `dhclient -v` as modeled no-guest-execution learning surfaces; Visual Journey validates DORA evidence fail-closed and the browser renders DHCP DORA X-Ray without selecting a server or allocating an address itself. DHCP relay across L3, dynamic pool allocation, lease mutation/aging, T1/T2, renew/rebind, declined-address conflict handling and real guest/network traffic remain deliberately NOT MODELED. See `docs/PHASE94_DHCP_DORA_XRAY.md`.

Phase 95 advances Phase E with Engine-owned listener/service-state semantics. When an explicit Host Stack exists, a complete TCP `LISTEN` / UDP `BOUND` socket snapshot is authoritative listener evidence; service `enabled`/`disabled` remains a separate state and cannot by itself invent a listener. Complete explicit absence proves `NO_LISTENER`, partial snapshots remain `UNKNOWN`, malformed ownership fails closed, and legacy service-only scenarios retain declaration-only compatibility without fabricated socket IDs. Active Probe propagates the immutable decision, Visual Journey validates it against Host Stack evidence, and Listener / Service State X-Ray displays both truths without recalculation. See `docs/PHASE95_LISTENER_SERVICE_STATE.md`.
