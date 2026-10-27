# YadiLab - Masterprompt v1.3

**Status:** VERIFIED ARCHITECTURE AGREEMENT / LOCKED  
**Supersedes:** Masterprompt v1.2  
**Implementation status:** NOT IMPLIED BY THIS DOCUMENT  
**Current display name:** YadiLab  
**Internal product identity:** GENERIC / REBRANDABLE  
**Primary Daniel-facing language:** Swedish unless otherwise requested

### v1.3 precedence and ratification

Masterprompt v1.3 is the authoritative architecture agreement for future YadiLab work. It preserves the validated v1.2 foundation and adds first-release enterprise environment import, normalized enterprise modeling, deterministic fault injection, diagnostics/observation, causal/packet-journey visualization, re-import/diff/merge, customer-data protection, deterministic scenario generation, and explicit benchmarking rules.

Where v1.3 wording conflicts with older v1.2 wording, **v1.3 takes precedence**. In particular, AI/ChatGPT-assisted scenario generation remains supported but is no longer the only primary creation path: structured enterprise import must work fully offline without AI.

---

## 0. Master Goal

Build a scalable, deterministic, visual **enterprise infrastructure, networking, troubleshooting, and cybersecurity lab platform**.

The platform has TWO equally first-class creation paths.

### Path A - Standalone Enterprise Environment Import

A user must be able to import a sufficiently structured enterprise environment WITHOUT opening ChatGPT or depending on any AI service.

Primary standalone flow:

```text
XLSX / ODS / CSV / TSV / JSON / YAML / GraphML / supported structured source
    ↓
Import Adapter
    ↓
Deterministic column/field mapping
    ↓
Provenance + conflict capture
    ↓
Normalized Enterprise Model
    ↓
Validation / review / UNKNOWN handling
    ↓
Topology + configuration baseline
    ↓
Optional fault injection / scenario generation
    ↓
Compiler + tests + layout
    ↓
.yadilab package
```

A good customer workbook or structured dataset must therefore be sufficient to create and operate a useful YadiLab project without AI.

### Path B - Prompt / Assistant Generated Scenario

Daniel may also describe an advanced scenario in ordinary language and ChatGPT or another external assistant may generate ONE complete scenario source/package.

```text
Daniel gives a prompt
    ↓
Assistant creates scenario source
    ↓
Compiler validates and normalizes it
    ↓
Required profiles/assets/capabilities are resolved
    ↓
Automatic topology layout is generated
    ↓
Initial vulnerable/broken state is tested
    ↓
Canonical/reference solution is applied automatically
    ↓
Solved state is regression-tested
    ↓
Visual/package validation is performed
    ↓
Scenario is packaged
    ↓
Daniel receives ONE scenario file
    ↓
Daniel opens it
    ↓
THE COMPLETE LAB WORKS DIRECTLY
```

Both paths converge on the SAME normalized semantic model, Compiler, Validator, Engine, Fault Engine, Diagnostics Engine, Layout Engine, test framework, and package format.

Daniel must normally NOT need to:

- edit JSON,
- move misplaced nodes,
- repair references,
- copy assets,
- install scenario-specific scripts,
- fix missing dependencies,
- correct object names,
- repair rule logic,
- rebuild the topology manually,
- manually redraw a structured customer environment that can be imported deterministically.

The first file DELIVERED to Daniel should already have passed the available automated checks.

Internal generation/import normalization may iterate as much as necessary before delivery.

A core v1.3 principle is:

> One validated enterprise baseline must be reusable as the source for runtime fault injection, persistent faulted variants, multi-fault training, causal explanations, diagnostic exercises, instructor/student workflows, and deterministic scenario generation without manually rebuilding or duplicating the underlying topology.

## 1. What the Product Is

The app is a:

**VISUAL ENTERPRISE INFRASTRUCTURE + TROUBLESHOOTING + CYBERSECURITY LAB PLATFORM**

It is NOT primarily:

- an infographic viewer,
- a hotspot application,
- a slide presentation system,
- a quiz application,
- a 3D editor,
- a static network diagrammer,
- a Cisco-only device emulator,
- an AI chat front end.

The semantic model may consist of:

```text
normalized enterprise baseline
    +
infrastructure resources
    +
topology
    +
networks/zones/sites
    +
identity relationships
    +
configuration state
    +
intended/documented state
    +
observed evidence
    +
simulated ground truth
    +
fault/remediation overlays
    +
deterministic rules
    +
diagnostic observations
    +
tests/attacks
    +
defensive configuration
    +
findings/evidence
    +
causal/dependency relationships
    +
objectives
    +
completion logic
```

The topology itself is the primary visual environment, but topology is only one projection of the semantic model.

The application must distinguish **what is actually true in the simulation** from **what was documented/imported**, **what was observed**, and **what the student is currently allowed to know**. This distinction is mandatory for realistic troubleshooting.

## 2. No Static Infographic as the Main Lab World

Do NOT build normal scenarios around one large infographic with invisible hotspots.

Instead use reusable interactive components such as:

- clients,
- servers,
- routers,
- switches,
- firewalls,
- hypervisors,
- VMs,
- containers,
- gateways,
- identity systems,
- SIEM systems,
- EDR systems,
- backup systems,
- storage,
- cloud systems,
- attackers,
- users,
- network zones,
- connections.

Each visual component corresponds to a real model object.

Infographics may still exist under Learning, Reference, Help, and Explanation, but are not the simulation state itself.

## 3. Permanent App-Name / Rebranding Rule

THIS RULE APPLIES TO THIS APP AND EVERY APP IN EVERY DAN PROJECT.

**THE PRODUCT NAME MUST NOT BE HARDCODED THROUGHOUT SOURCE CODE.**

Internally use generic names:

```text
App
AppConfig
Builder
Runtime
Engine
Scenario
ScenarioCompiler
ScenarioValidator
AssetLibrary
NetworkEngine
IdentityEngine
RuleEngine
TestEngine
LayoutEngine
```

Avoid unnecessary internal identifiers such as:

```text
YadiLabEngine
YadiLabParser
YadiLabBuilder
YadiLabScenarioManager
```

The current visible name must come from one centralized configuration.

Conceptual example:

```text
APP_CONFIG.displayName = "YadiLab"
```

The same centralized branding configuration should control, where practical:

```text
displayName
shortName
tagline
website
aboutText
applicationIcon
theme branding
scenarioExtension
progressExtension
exported report branding
```

Example:

```text
APP_CONFIG.displayName = "YadiLab"
APP_CONFIG.scenarioExtension = ".yadilab"
```

Changing the app name later must NOT require source-wide cleanup.

Do not unnecessarily embed current branding into:

- class names,
- module names,
- engine names,
- internal schema IDs,
- APIs,
- object types,
- event names,
- database keys,
- internal protocols,
- internal package directories,
- persistent engine identifiers.

Internal persistent identifiers should remain neutral.

## 4. Vendors and Product Names Are Allowed

The rebranding rule applies to OUR APP NAME.

It does NOT prohibit real vendors, products, standards, operating systems, or technologies.

Scenarios may explicitly model:

- Cisco,
- Microsoft,
- Windows Server,
- Active Directory,
- Entra ID,
- Defender,
- Sentinel,
- Proxmox,
- VMware,
- Fortinet,
- Palo Alto,
- OPNsense,
- pfSense,
- Linux,
- Wazuh,
- Suricata,
- Zeek,
- AWS,
- Azure,
- GCP,
- and other real technologies.

Prefer:

```text
generic core type
    +
optional vendor/product profile
```

Example:

```text
type: network.switch
vendor: Cisco
product: Catalyst 9300
```

Conceptual profile:

```text
vendor.cisco.catalyst_9300
```

Core engine logic should remain generic when possible.

Vendor-specific semantics should be data-driven through profiles/packs.

## 5. First-Class Platform Target: Parrot OS

Parrot OS is a MANDATORY first-class target platform.

The finished application must support current supported Parrot OS on:

```text
x86-64
```

unless Daniel explicitly expands the platform matrix later.

Required Parrot OS functionality:

```text
Builder
Runtime
Scenario opening
Scenario import/export
Save/load progress
Compiler/Validator
Headless CLI
Scenario tests
Preview/render workflow
Offline operation
```

A scenario feature must NOT require:

- Windows-only runtime APIs,
- macOS-only runtime APIs,
- PowerShell on the host,
- proprietary platform components,
- Blender,
- Godot,
- external web services.

Windows and Linux may of course be SIMULATED inside scenarios.

Host operating system and simulated operating systems are separate.

## 6. Browser/PWA Compatibility Baseline

The browser application is the primary compatibility baseline.

It should work using a modern browser available on Parrot OS.

Target browsers should include at least:

```text
Firefox
A Chromium-based browser
```

when available in the supported Parrot environment.

The production application must NOT require Node.js, npm, TypeScript, Vite, or other development tooling simply to RUN the finished app.

Development dependencies are acceptable for developers.

End users receive built assets.

The mandatory browser file-handling baseline is the standard File API:

- file input,
- drag-and-drop,
- File/Blob reading,
- Blob-based download/export.

The File System Access API may be used only as progressive enhancement. Core scenario opening, saving/exporting, and portability must not depend on it.

Autosave/progress storage should use IndexedDB. Where supported, the app may request persistent storage using `navigator.storage.persist()`, but browser storage is NOT a backup. Important work must always be explicitly exportable to a portable file.

## 7. Offline-First Contract

Normal use must work completely offline.

Production builds must bundle required runtime resources locally.

DO NOT require CDN access for:

- React,
- topology libraries,
- layout engines,
- fonts,
- icons,
- schemas,
- runtime libraries,
- application assets.

Do not depend on unpkg, jsdelivr, Google Fonts, remote icon services, or cloud APIs for basic operation.

Internet access may later be an explicit optional feature.

OFFLINE is the default.

For Parrot OS local distribution, the preferred production baseline is a small precompiled GENERIC loopback launcher that serves only the bundled static application assets on a stable `127.0.0.1`/localhost origin. The launcher must not require Node/npm at runtime and must not expose the application on external interfaces by default. The browser/PWA architecture remains the application baseline; the launcher is a local delivery mechanism, not the semantic core.

## 8. Optional Desktop Packaging

A desktop wrapper may later be provided.

Current preferred direction:

```text
Tauri
```

However, browser/PWA compatibility remains the baseline.

A desktop wrapper must NOT become required for the scenario format, Engine, Compiler, Validator, or tests.

If a Parrot OS desktop package is released, it must be tested on Parrot before being labelled verified.

## 9. High-Level Architecture

The platform consists conceptually of:

1. Builder
2. Runtime
3. Engine
4. Compiler
5. Validator
6. Asset Library
7. Domain/Capability Packs
8. Headless CLI
9. Automated Test Framework
10. Layout Engine
11. Enterprise Import Engine
12. Import Adapter Layer
13. Normalized Enterprise Model
14. Fault Injection Engine
15. Diagnostic / Observation Engine
16. Packet/Evidence Journey Engine
17. Causal/Dependency Graph Model
18. Baseline / Overlay / Variant Manager
19. Provenance / Data-Lineage Model
20. Privacy / Sanitization / Anonymization subsystem

These are architectural responsibilities and do not necessarily require separate executables.

All user-facing creation paths must converge on the same normalized semantic model. Source-format-specific logic must remain inside import adapters; fault-specific behavior must remain in reusable declarative fault packs; UI state must not become semantic truth.

## 10. Builder

Builder is the visual authoring environment.

Required capabilities include the original v1.2 authoring functions plus first-release enterprise import and fault authoring:

- create resource,
- delete resource,
- duplicate resource,
- drag/move resource,
- multi-select,
- create connection,
- edit connection,
- create zone/site/group,
- resize zones,
- Inspector editing,
- typed properties,
- labels,
- notes,
- mission briefing,
- objectives,
- tests,
- findings,
- hints,
- canonical/reference solution,
- validation,
- preview Runtime,
- import,
- export,
- auto-layout,
- manual layout override,
- Enterprise Environment Import Wizard,
- sheet/file detection,
- deterministic column/field mapping,
- mapping profile save/load,
- import dry-run and preview,
- conflict/UNKNOWN review,
- import provenance inspection,
- baseline creation,
- re-import / diff / merge,
- fault injection panel,
- fault preview / blast-radius preview,
- runtime fault injection,
- persistent faulted scenario variant creation,
- multi-fault scenario generation,
- seed-controlled variant generation,
- healthy-vs-faulted comparison,
- anonymized training-clone export,
- instructor/student package preview.

IMPORTANT:

ChatGPT must NOT depend on GUI automation to create scenarios.

ChatGPT should primarily generate scenario source programmatically.

Equally important: normal structured enterprise import must NOT depend on ChatGPT. A user must be able to import, validate, normalize, visualize, fault-inject, and package a structured environment entirely inside YadiLab while offline.

## 11. Runtime

Runtime is student/player mode.

Editing controls are hidden unless specifically enabled.

Runtime should expose concepts such as:

```text
Mission
Topology
Inspector
Configuration
Diagnostics
Packet / Evidence Journey
Tests
Findings
Evidence
Progress
Hints
Learning
```

The Runtime must derive outcomes from Engine state.

Runtime diagnostics must expose only information that the scenario visibility policy permits. The student must not automatically see hidden fault definitions, causal ground truth, canonical solutions, instructor notes, or imported secrets.

Where supported by the scenario, Runtime should permit realistic deterministic diagnostic actions such as ping/traceroute/name resolution/route inspection/service inspection/firewall inspection/log inspection without executing arbitrary host commands.

## 12. Engine

The Engine is the semantic source of truth.

The canvas is NOT the source of truth.

Engine responsibilities include:

- normalized enterprise baseline,
- scenario state,
- topology state,
- configuration,
- networks,
- sites/zones,
- reachability,
- identities,
- relationships,
- rules,
- tests,
- findings,
- evidence,
- objectives,
- completion,
- reset,
- checkpoints,
- progress,
- deterministic simulation,
- truth/observation separation,
- fault overlays,
- remediation overlays,
- runtime mutations,
- virtual time where needed,
- deterministic temporal/intermittent faults,
- diagnostic observations,
- packet/evidence decision traces,
- causal/dependency explanation data.

The imported baseline, fault definition, runtime state, and remediation state must be separable. Injecting a training fault must not destructively mutate the reusable enterprise baseline.

## 13. Compiler

The Compiler transforms author/LLM-friendly source into normalized, validated scenario data.

Conceptual pipeline:

```text
Source
  ↓
Schema validation
  ↓
Type validation
  ↓
Reference resolution
  ↓
Defaults
  ↓
Profile resolution
  ↓
Capability resolution
  ↓
Asset resolution
  ↓
Topology validation
  ↓
Network validation
  ↓
Identity validation
  ↓
Rule validation
  ↓
Objective validation
  ↓
Canonical solution validation
  ↓
Auto-layout
  ↓
Visual validation
  ↓
Initial-state tests
  ↓
Canonical solution application
  ↓
Solved-state tests
  ↓
Package creation
```

Compilation failure means:

```text
DO NOT LABEL THE SCENARIO VERIFIED.
```

## 14. Validator

Validator must catch errors BEFORE Runtime.

Examples:

- unknown property,
- invalid enum,
- invalid CIDR,
- invalid port,
- duplicate ID,
- missing reference,
- impossible connection,
- missing required capability,
- missing asset,
- contradictory objective,
- unreachable reference solution,
- unsatisfiable condition,
- malformed firewall rule,
- invalid route,
- invalid zone membership.

Unknown fields should normally be rejected.

Example:

```text
mfa_enabeld
```

should fail and ideally suggest:

```text
mfa_enabled
```

Do NOT silently ignore invalid scenario data.

## 15. Scenario-Format-First Design

The scenario specification is more important than manual GUI authoring.

The complete lab must be reconstructable from the scenario package.

The scenario file describes MODEL STATE.

It must not depend on arbitrary editor history.

## 16. Source Format vs Distribution Package

### 16.1 Canonical Authoring / Normalized Sources

JSON remains the preferred canonical machine-readable source format.

Conceptual source artifacts may include:

```text
enterprise-baseline.json
scenario-source.json
fault-overlay.json
mapping-profile.json
import-provenance.json
```

These are conceptual responsibilities; one physical source file may embed several of them where practical.

A normalized enterprise baseline is NOT the same thing as an imported spreadsheet. Imported files are evidence/sources; the normalized model is the canonical format-independent representation produced by deterministic adapters and validation.

Optional alternative authoring/import syntaxes are supported through adapters, but the authoritative semantic contract is normalized and schema-defined.

Source should be compact where practical. Compiler/import normalization may apply explicit defaults, but must not fabricate missing enterprise facts.

### 16.2 Compiled Scenario Package

Current user-facing extension may be configured as:

```text
.yadilab
```

but this is branding configuration.

Internal format identity remains generic.

The scenario package should be a normal documented archive/container, preferably ZIP-compatible.

Conceptual contents:

```text
manifest.json
scenario.json
layout.json
tests.json
assets/
docs/
```

Author/instructor builds may additionally contain:

```text
solution.json
author metadata
fault authoring metadata
import/provenance summaries where safe
```

Student distribution builds MUST omit the canonical/reference solution and other instructor-only hidden truth after successful compilation/testing.

Raw customer source files, secrets, unredacted customer notes, mapping keys for reversible anonymization, and private imported material must NOT be copied into a student package merely because they were used to create the normalized model.

Do not rely on "hidden files" as security.

## 17. Package and Import Safety

Scenario packages and enterprise import files are DATA, not arbitrary applications.

Do NOT execute:

- embedded JavaScript,
- embedded Python,
- shell scripts,
- Office macros,
- workbook VBA,
- arbitrary plugins,
- imported binaries

from normal scenario/import packages.

When opening ZIP-based packages or workbook containers:

- reject path traversal,
- reject absolute archive paths,
- reject unsafe symlinks where relevant,
- limit file count,
- limit decompressed size,
- defend against ZIP bombs,
- validate checksums where present,
- validate manifest before loading assets,
- sanitize SVG,
- reject executable SVG scripting,
- reject unsafe external SVG references,
- avoid automatic remote resource loading.

Spreadsheet import rules:

- macros are never executed,
- external workbook links are never fetched automatically,
- formula code is not treated as trusted executable logic,
- cached formula values may be imported only with provenance/warning when the formula cannot be deterministically evaluated,
- macro-enabled workbooks may only be treated as data containers if the parser can guarantee no macro execution,
- embedded executables/objects are ignored or rejected unless explicitly supported as safe data.

XML import rules:

- disable DTD/external entity resolution,
- disable XXE-capable behavior,
- do not resolve remote schemas/resources automatically.

YAML import rules:

- use a safe data-only loader,
- reject executable/custom object tags.

Scenario packages should be safe to inspect/open offline.

ZIP read/write must be hidden behind an internal generic `PackageIO` abstraction. The initial implementation should use `zip.js`, but scenario semantics must not depend directly on that library.

Built-in SVG assets are trusted application assets. Custom SVG supplied by scenarios is UNTRUSTED CONTENT and must be sanitized under a strict policy before rendering. Do not inject arbitrary scenario SVG directly into the DOM, and reject script-capable or remote-referencing SVG constructs that violate the asset policy.

## 18. Stable Internal IDs

Internal object IDs should be predictable and machine-friendly.

Prefer ASCII-safe identifiers:

```text
firewall01
rdg01
rds01
ad01
mgmt_vlan
```

Display labels may freely use Unicode/Swedish:

```text
"Primär brandvägg"
"Återställningsserver"
```

Do not depend on display labels as stable references.

## 19. Asset Library

Visual assets should be reusable.

Preferred master format:

```text
SVG
```

Optional derived formats:

```text
PNG
```

Never distort source aspect ratio.

Use contain-style rendering.

Built-in assets should include generic infrastructure categories such as:

```text
network.firewall
network.router
network.switch
endpoint.windows
endpoint.linux
endpoint.macos
server.generic
windows.domain_controller
windows.rd_gateway
windows.rds_host
virtualization.hypervisor
virtualization.proxmox
security.siem
security.edr
security.backup
actor.user
actor.admin
actor.attacker
```

Prefer built-in assets for automatically generated scenarios.

## 20. Component-Based Topology

Each visual node corresponds to a model resource.

Example:

```text
Internet
   ↓
Firewall
   ↓
RD Gateway
   ↓
RDS01
   ↓
AD01
```

Other resources may include:

```text
Proxmox
SIEM
Backup
Admin workstation
File server
DNS
DHCP
VPN
Database
Cloud service
```

A node is NOT an invisible hotspot.

The node itself is interactive.

## 21. Connections Are Semantic

Connections must not be only decorative lines.

A connection may represent:

- network adjacency,
- interface attachment,
- VLAN membership,
- logical service dependency,
- route relationship,
- trust,
- authentication path,
- management path,
- permitted traffic,
- blocked traffic,
- data flow.

Connection type must be explicit.

## 22. Network Zones

Support visual/logical containers:

```text
Internet
WAN
DMZ
LAN
RDS VLAN
Server VLAN
Management VLAN
Security zone
Backup zone
Guest network
```

Zone membership should affect simulation where relevant.

## 23. Automatic Layout

ChatGPT should normally NOT supply raw pixel-perfect positions.

Scenario source should primarily specify topology.

Optional layout hints:

```text
zone
group
rank
order
preferredSide
parent
```

The Layout Engine generates deterministic coordinates from a pure topology/layout projection. React Flow node/edge UI state must NEVER become the canonical scenario state. React Flow is a view/projection of the model.

The first layout implementation is ELK Layered (via ELK.js) because the Foundation must support compound zones and explicit ports/interfaces. Nodes must have defined initial layout dimensions so identical model input produces stable initial layout. Manual user overrides are stored separately from generated layout hints/state.

Visual validation must detect:

- overlapping nodes,
- nodes outside zone,
- nodes outside canvas,
- unreadable labels,
- invalid dimensions,
- excessive edge overlap,
- zone overflow,
- unreasonable whitespace.

Manual Builder changes may override auto-layout.

## 24. Property Type System

Do NOT reduce the platform to boolean checkboxes.

Core types should include:

```text
boolean
integer
number
string
enum
IPv4
IPv6
CIDR
MAC
port
protocol
version
duration
reference
list
map
```

Domain types should include:

```text
network_interface
route
firewall_rule
acl_rule
nat_rule
service
credential_policy
authentication_policy
authorization_policy
user
group
role
permission
```

All state must be schema-defined.

## 25. Network Engine

The Network Engine should understand, where the active capability set supports them:

- interfaces,
- addresses,
- subnets,
- gateways,
- routes,
- route selection/metrics,
- VLANs,
- sites/zones,
- VRF/logical routing domains where modeled,
- links,
- tunnels/VPN relationships,
- NAT,
- ACLs,
- firewall rules,
- services,
- listening ports,
- TCP,
- UDP,
- DNS relationships,
- DHCP relationships,
- management networks,
- reachability,
- MTU/PMTUD semantics where declared,
- deterministic latency/loss/link-state semantics where declared,
- neighbor/ARP-style reachability decisions at an abstract semantic level.

It should answer queries such as:

```text
Can Internet reach RDS01 TCP/3389?
Can RDS01 reach Proxmox TCP/8006?
Which path is used?
Which route was selected?
Which firewall rule allowed or blocked the flow?
Where is traffic blocked?
Is a management bypass path present?
Which DNS answer/path is used?
Would an MTU constraint prevent the modeled flow?
```

The answer must derive from state.

The Network Engine must be able to produce a deterministic **semantic packet/evidence journey** showing the relevant decisions made at each modeled step.

FOUNDATION SCOPE BOUNDARY: NetworkEngine v1 is a security reachability/configuration/troubleshooting simulator. It is NOT required to be a timing-accurate packet emulator, TCP stack, switch ASIC emulator, or routing-protocol implementation. Semantic packet journeys are decision traces over declared state. Deeper packet/protocol simulation may later be added through compatible capabilities without breaking existing scenarios.

## 26. Identity Engine

The Identity Engine should model:

- users,
- groups,
- roles,
- privileges,
- passwords,
- MFA,
- authentication methods,
- authorization,
- service accounts,
- local administrators,
- memberships,
- delegation,
- trust,
- sessions.

Queries may include:

```text
Can user X authenticate to system Y?
Which membership grants access?
Does a privilege path exist?
Is MFA required?
What effective permission results?
```

FOUNDATION SCOPE BOUNDARY: IdentityEngine v1 models authentication/authorization relationships, memberships, effective permissions, MFA requirements, and privilege paths. It is NOT a full Active Directory, Kerberos, NTLM, LDAP, token, or protocol emulator. Vendor profiles may enrich semantics without changing this Foundation boundary.

## 27. Security / Hardening Model

Resources may expose hardening state such as:

- patch level,
- insecure service,
- weak protocol,
- unnecessary port,
- local administrator exposure,
- logging disabled,
- EDR absent,
- NLA disabled,
- MFA disabled,
- restore untested,
- management interface exposed.

State should be domain-defined, not arbitrary free text.

## 28. Declarative Security Tests

Scenario tests must be declarative.

Examples:

```text
network.port_scan
network.reachability
network.segmentation
network.route_test

identity.password_audit
identity.authentication_test
identity.privilege_path

windows.hardening_check
linux.hardening_check

virtualization.management_exposure

logging.visibility_test
logging.alert_test

backup.restore_test
```

Example:

```text
type: network.reachability
from: attacker
to: rds01
protocol: tcp
port: 3389
```

The Engine computes the result.

## 29. No Arbitrary Scenario Code

Normal scenario definitions must NOT contain:

```text
eval()
arbitrary JavaScript
arbitrary Python
shell commands executed on the host
arbitrary plugins
```

Simulation behavior belongs in trusted Engine capabilities.

## 30. Explainable Results

Tests must produce explanations.

Bad:

```text
FAIL
```

Good:

```text
Direct RDP exposure detected

Path:
    Internet
      ↓
    Firewall01
      ↓ TCP/3389 ALLOW
    RDS01

Reason:
    Firewall rule WAN-RDP permits TCP 3389.
```

After remediation:

```text
Direct RDP blocked

Blocking point:
    Firewall01

Rule:
    WAN → RDS TCP/3389 DENY
```

## 31. Rule Engine

Use a constrained declarative rule model.

Supported concepts may include:

```text
all
any
not
equals
compare
exists
reachable
member_of
has_permission
service_enabled
rule_matches
test_result
```

Rules must be statically validatable.

Engine queries and rule predicates must support three-valued logic: `TRUE`, `FALSE`, and `UNKNOWN`. Missing or insufficient evidence must not be silently coerced to false. Composite operators must define deterministic three-valued semantics so uncertainty propagates predictably and can be surfaced in explanations.

## 32. Objectives

Objectives should usually express desired outcomes.

Example:

```text
Internet must not reach RDS01 on TCP/3389.
```

Separate SECURITY OUTCOME from REQUIRED LEARNING ACTION.

Example:

Outcome:

```text
TCP/3389 must not be reachable from WAN.
```

Learning requirement:

```text
Student must correct the perimeter firewall configuration.
```

This distinction permits alternative valid solutions when appropriate.

## 33. Alternative Valid Solutions

Do not unnecessarily require a single exact click path.

If the learning objective permits multiple technically valid solutions, the Engine should accept them.

Example goal:

```text
Internet cannot reach RDS01:3389.
```

Possible valid solutions may include:

- perimeter firewall deny,
- host firewall block,
- disabling RDP,

if the scenario author permits them.

If the lesson specifically teaches perimeter firewall rules, encode that as an additional requirement.

## 34. Canonical / Reference Solution

Advanced scenarios should include a canonical/reference solution during authoring/testing.

Purpose:

- prove solvability,
- test objectives,
- detect contradictions,
- regression-test Engine behavior,
- provide instructor material.

The canonical solution is NOT necessarily the only valid solution.

A student distribution package may omit the reference solution after successful compilation/testing.

## 35. Initial-State Regression Test

The compiler/test pipeline must verify that intended faults actually exist.

Example:

```text
Direct RDP reachable      PASS
Proxmox exposed           PASS
MFA missing               PASS
segmentation weakness     PASS
logging incomplete        PASS
```

If intended faults are absent, scenario generation has failed.

## 36. Solved-State Regression Test

The system automatically applies the canonical solution.

Then verify:

- vulnerabilities intended to be fixed are fixed,
- required legitimate traffic still works,
- management paths behave correctly,
- objectives are satisfied,
- tests return expected outcomes,
- completion condition triggers,
- unrelated systems are not accidentally broken.

Scenario packaging fails if solved-state regression fails.

## 37. Determinism

The same relevant inputs must produce the same relevant results.

For Runtime simulation this includes:

```text
scenario/baseline identity
engine version
capability/profile/fault-pack versions
starting state
seed where applicable
user actions
virtual time inputs where applicable
```

For enterprise import this additionally includes:

```text
source file bytes/hashes
adapter version
mapping profile
explicit import options
user-confirmed conflict resolutions
```

The same structured input + same adapter/mapping versions/options must produce the same normalized baseline identity.

Generative AI must NOT determine Runtime simulation outcomes, import truth, fault consequences, grading, or causal results.

ChatGPT may GENERATE or suggest scenario content/mappings outside the deterministic core.

The app Engine determines outcomes deterministically.

If controlled randomness is used for scenario/fault generation:

- it must use an explicit seed,
- seed must be stored,
- generator/fault-pack versions must be locked,
- result must be replayable.

## 38. Evidence / Event Log

Tests should generate evidence.

Example:

```text
14:23:51
External port scan

Source:
    Internet

Target:
    RDS01

Result:
    TCP/3389 OPEN

Finding:
    Direct RDP exposure
```

After remediation:

```text
TCP/3389 FILTERED
Finding resolved
```

Prefer a scenario virtual clock for deterministic timestamps when necessary.

## 39. Findings

Findings must derive from Engine state/tests.

Example:

```text
RDS01
⚠ Direct RDP exposure
⚠ NLA disabled
⚠ Missing patch
```

After correction:

```text
RDS01
✓ No critical findings
```

Do not maintain dozens of separate icon files for every state.

Use visual status overlays.

## 40. Progress

Prefer objective-based progress.

Example:

```text
Perimeter        2 / 4
Identity         1 / 3
Segmentation     0 / 3
Hardening        4 / 5
Logging          2 / 2
Recovery         0 / 2
```

Avoid arbitrary scores unless a scenario explicitly requests gamification.

## 41. Hints

Support progressive hints.

Example:

```text
Hint 1:
Investigate which services are reachable from the Internet.

Hint 2:
Compare direct RDP with RD Gateway.

Hint 3:
Inspect WAN rules on firewall01.
```

Hints belong to scenario data.

## 42. Learning Material

Optional educational material may include:

- infographics,
- diagrams,
- explanatory text,
- checklists,
- command examples,
- reference documents.

These are secondary resources.

They must not be required to reconstruct simulation state.

## 43. State Management

Runtime must support:

```text
Reset scenario
Undo
Redo
Save progress
Load progress
Checkpoint
Compare before/after where applicable
```

Architecture must support deterministic replay.

The following must remain conceptually separated:

```text
Imported/normalized enterprise baseline
Fault overlay(s)
Scenario definition
Mutable Runtime state
Remediation state
Student progress
Instructor-only truth
```

A runtime fault injection must never silently overwrite the reusable baseline.

Persistent faulted variants should reference a baseline identity plus deterministic mutations where practical, and may be materialized to a self-contained scenario package when exported.

## 44. Save/Progress Format

Progress files should use a generic internal format.

Any user-facing extension must come from centralized branding/config.

Progress data should record:

- scenario identity/hash,
- scenario schema version,
- relevant Engine version,
- mutable state,
- completed objectives,
- evidence/event history if applicable.

Do not silently load incompatible saves.

## 45. Capability / Domain / Adapter / Fault Packs

Design domain functionality as reusable capabilities.

Examples:

```text
core.network
core.identity
core.windows
core.linux
core.virtualization
core.security
core.logging
core.backup
core.diagnostics
core.enterprise_import
```

Possible vendor/domain packs:

```text
cloud.azure
cloud.aws
cloud.gcp

vendor.cisco
vendor.microsoft
vendor.proxmox
vendor.fortinet
vendor.opnsense
```

Import adapters are trusted, versioned application capabilities. Scenario/import data must not supply arbitrary executable adapter code.

Fault Packs are trusted, versioned declarative definitions containing preconditions, mutations, expected effects, observations, recovery conditions, and compatibility constraints.

Core scenario semantics must remain stable.

Compiled packages must lock the EXACT capability/profile/fault-pack versions used to compile/verify the scenario. Version ranges may be accepted in authoring source, but the compiled package records resolved exact versions for reproducibility.

## 46. Profile Resolution

Source scenarios may reference vendor/product profiles.

Compiler resolves these into normalized semantics.

Compiled packages must record the exact resolved profile versions used during compilation. Where practical, they should contain enough normalized data or immutable profile snapshot metadata that Runtime is not dependent on an external mutable profile definition.

A scenario requiring unavailable executable capability code must fail clearly before play.

Do not partially open a scenario and silently remove unsupported behavior.

## 47. Versioning

Version from day one.

Conceptual metadata may include:

```text
formatId
schemaVersion
minimumEngineVersion
normalizedModelVersion
importAdapterVersions
mappingProfileVersion
faultPackVersions
generatorVersion
```

The internal format ID should remain generic and stable.

Do not use the current brand name as a required internal format identity unless there is a compelling compatibility reason.

Support explicit migrations.

Never silently reinterpret incompatible schema.

Re-import/replay must record adapter/mapping versions so a future parser update does not silently change an old baseline without an explicit migration/re-import decision.

## 48. Package Integrity

Compiled packages should support integrity metadata.

Prefer:

```text
manifest
file list
sizes
SHA-256 checksums
```

This helps detect corruption and incomplete generated packages.

Integrity is not the same as cryptographic publisher authenticity.

Signing may be added later if needed.

## 49. Headless CLI - Mandatory

The application/toolchain must support automated use without GUI.

Conceptual commands:

```text
app validate source.json
app compile source.json
app test scenario.package
app inspect scenario.package
app render scenario.package preview.png
app unpack scenario.package
app migrate scenario.package

app import enterprise.xlsx --mapping mapping.json
app normalize import-bundle.zip
app import-report enterprise.xlsx
app diff-baseline old.json new.json
app merge-baseline current.json reimport.json
app anonymize enterprise-baseline.json
app inject-fault baseline.json fault-id --seed 123
app generate-variant baseline.json --fault-pack routing --seed 123
app diagnose scenario.package diagnostic-spec.json
```

CLI naming should remain generic internally.

A branded launcher may map to the generic CLI.

This is critical for both ChatGPT-generated scenarios and deterministic enterprise-import/testing workflows.

## 50. Parrot OS CLI Contract

Compiler, Validator, test runner, inspector, and renderer must work on Parrot OS.

The final user should not need a JavaScript development environment merely to run a compiled scenario.

Developer tooling may require:

```text
Node
package manager
TypeScript toolchain
```

but production Runtime should not.

## 51. Parrot OS Acceptance Test

Before a production release is called Parrot-compatible, perform the following on supported Parrot OS:

```text
Launch app
    ↓
Open scenario package
    ↓
Render topology
    ↓
Inspect node
    ↓
Change configuration
    ↓
Run test
    ↓
Generate finding/evidence
    ↓
Solve objective
    ↓
Trigger completion
    ↓
Save progress
    ↓
Reload progress
    ↓
Reset
    ↓
Builder import
    ↓
Builder export
    ↓
CLI validate
    ↓
CLI test
    ↓
CLI render
    ↓
PASS
```

A feature not tested in this matrix must not be described as verified on Parrot.

## 52. Scenario / Baseline Completeness Contract

An advanced scenario may be exported as VERIFIED only when applicable requirements pass:

- valid metadata,
- valid schema,
- valid IDs,
- valid references,
- valid resource types,
- valid profiles,
- valid topology,
- valid connections,
- valid zones/sites,
- valid initial state,
- valid interactions,
- valid rules,
- valid tests,
- valid findings,
- valid objectives,
- valid completion conditions,
- canonical solution exists where required,
- initial-state regression passes,
- canonical solution can be applied,
- solved-state regression passes,
- assets resolve,
- layout validates,
- package integrity validates,
- package opens successfully in supported Runtime where test tooling permits.

When the scenario derives from enterprise import, applicable additional requirements include:

- import adapter/version recorded,
- source hashes recorded,
- mapping decisions recorded,
- unresolved required mappings rejected or explicitly marked UNKNOWN,
- duplicate/conflicting entities reported,
- no silent fuzzy merge,
- normalized baseline validates,
- provenance references are internally consistent,
- secret/private-key policy passes,
- fault overlays do not mutate baseline,
- injected faults produce intended initial effects,
- negative-control traffic/behavior remains correct where specified,
- recovery/solution regression passes,
- instructor-only truth does not leak into student package.

## 53. Scenario Creation Contracts

### 53.1 Structured Enterprise Import Contract

When a user supplies structured environment data, the preferred workflow is:

1. Detect safe supported source format(s).
2. Compute source hashes/provenance.
3. Select a versioned deterministic import adapter.
4. Detect sheets/tables/records.
5. Apply exact/alias/mapping-profile rules.
6. Surface unmapped/ambiguous/conflicting fields.
7. Preserve UNKNOWN rather than fabricate.
8. Normalize to the Enterprise Model.
9. Validate references/entities/network semantics.
10. Present import report/dry-run.
11. Accept explicit user corrections where necessary.
12. Create baseline identity.
13. Auto-layout topology projections.
14. Optionally create/inject deterministic faults or variants.
15. Compile/test/package.

A sufficiently structured customer dataset must not require an AI conversation.

### 53.2 ChatGPT / External Assistant Scenario Generation Contract

When Daniel asks ChatGPT to create a scenario:

**PRIMARY DELIVERABLE: ONE COMPLETE PLAYABLE SCENARIO FILE**

Normal workflow:

1. Parse learning goal.
2. Identify required domains.
3. Select resource types.
4. Select vendor/product profiles where relevant.
5. Define topology or derive it from supplied enterprise data.
6. Define zones/sites.
7. Define connections.
8. Define initial configuration.
9. Define realistic failures/misconfigurations.
10. Define tests/diagnostics.
11. Define expected findings/evidence.
12. Define objectives.
13. Define completion logic.
14. Define progressive hints if appropriate.
15. Define canonical solution.
16. Validate schema.
17. Resolve profiles/capabilities/fault packs.
18. Resolve assets.
19. Validate topology.
20. Validate network/identity/rules.
21. Auto-layout.
22. Validate visual layout.
23. Run initial-state regression.
24. Apply canonical solution.
25. Run solved-state regression.
26. Compile/package.
27. Validate package integrity.
28. Render/inspect preview where tooling permits.
29. Deliver file.

Assistant-produced mappings/inferences are UNTRUSTED suggestions until the same deterministic schema/provenance/validation rules accept them.

Do not knowingly deliver broken intermediate source as the finished result.

## 54. First-Delivered-File Reliability

Do NOT promise mathematically impossible universal perfection.

Instead define the operational goal:

> Daniel should normally receive the first DELIVERED file already validated and working.

ChatGPT may internally:

- regenerate,
- repair,
- compile,
- rerun tests,
- adjust topology,
- fix references

before presenting the result.

This is the meaning of FIRST ATTEMPT for the user experience.

## 55. Built-In Domain Targets

### Networking

- Ethernet concepts
- switching
- VLAN
- IPv4
- IPv6
- routing
- DNS
- DHCP
- TCP
- UDP
- NAT
- firewalling
- ACL
- VPN
- segmentation
- troubleshooting

### Windows

- Windows clients
- Windows Server
- Windows Firewall
- services
- NTFS/ACL
- SMB
- RDP
- RDS
- Group Policy
- PowerShell concepts
- Scheduled Tasks

### Identity

- Active Directory
- Entra-style identity
- users
- groups
- roles
- permissions
- MFA
- authentication
- authorization

### Linux

- Linux host
- permissions
- services
- SSH
- firewall
- systemd
- logs

### Virtualization

- hypervisor
- VM
- container
- virtual switch/bridge
- VLAN
- management plane
- snapshots
- backup
- Proxmox profiles

### Security

- pentest-oriented tests
- hardening
- vulnerability findings
- attack paths
- lateral movement concepts
- logging
- SIEM
- EDR/XDR concepts
- incident-response concepts
- backup/recovery

### Cloud

Expandable later through capability packs.

## 56. Safe Cyber Range Principle

The normal Engine is a deterministic simulator.

Scenario packages should not become containers for uncontrolled exploit code.

The app may model scan, reachability, authentication, privilege path, segmentation, firewall behavior, attack consequence, detection, and hardening through controlled simulation.

If real infrastructure integration is ever added later, it must be a separate explicit subsystem with its own security model.

## 57. Recommended Implementation Stack

Current preferred direction:

```text
Language: TypeScript
UI: React
Topology: React Flow / xyflow or equivalent
Auto-layout: ELK.js or equivalent
Application state: Zustand or equivalent lightweight typed state layer
Schema contract: JSON Schema Draft 2020-12 + Ajv strict (authoritative external contract)
TypeScript types: generated from the authoritative JSON Schemas
Zod: optional for local UI ergonomics only; never a parallel schema source of truth
Tests: Vitest
UI / acceptance tests: Playwright
Scenario package: ZIP-compatible archive
Primary runtime: local browser / PWA-compatible build
Optional later desktop: Tauri
```

Do not introduce a server/backend/database unless a real requirement justifies it.

## 58. Production Build Requirements

Production artifacts must:

- bundle JavaScript locally,
- bundle CSS locally,
- bundle required fonts locally,
- bundle required icons locally,
- bundle schemas locally,
- bundle built-in asset definitions locally,
- use relative/local asset references,
- work without internet.

Development CDN shortcuts must never leak into release builds.

The build/release pipeline must produce and ship a `THIRD_PARTY_NOTICES` or equivalent dependency/license inventory for distributed third-party components.

## 59. Code Quality

Require:

- strict TypeScript,
- typed interfaces,
- explicit schemas,
- deterministic pure logic where possible,
- clean separation between model and UI,
- small modules,
- unit tests,
- regression tests,
- centralized defaults,
- centralized branding,
- generic engine naming,
- documented public schemas.

Avoid:

- hardcoded brand names,
- giant monolithic components,
- uncontrolled global state,
- magic strings,
- eval,
- arbitrary scenario code,
- scenario-specific hacks inside Engine core,
- vendor-specific if/else sprawl,
- silently ignored invalid data.

## 60. No Scenario-Specific Core Hacks

Do NOT solve a specific lab by adding code such as:

```text
if scenarioId == "proxmox-rds-01":
    ...
```

Scenario-specific behavior belongs in:

- scenario data,
- generic rules,
- reusable profiles,
- reusable capability packs.

The Engine must remain reusable.

## 61. UI Structure

Builder conceptual UI:

```text
┌ Asset/Import ┬────────── Canvas ──────────┬ Inspector ┐
│              │                           │           │
│ assets       │                           │ selected  │
│ imports      │         topology          │ object    │
│ faults       │                           │ state     │
│ variants     │                           │           │
└──────────────┴───────────────────────────┴───────────┘
```

Primary Builder surfaces should include:

```text
Enterprise Import
Mapping Review
Baseline
Fault Injection
Scenario Variants
Topology
Inspector
Validation
```

Bottom/auxiliary panels:

```text
Tests
Diagnostics
Findings
Events
Validation
Import Report
Diff / Conflicts
Fault / Causal Preview
```

Runtime conceptual UI:

```text
Mission
Topology
Inspector
Configuration
Diagnostics
Packet / Evidence Journey
Tests
Findings
Evidence
Progress
Hints
Learning
```

Instructor mode may additionally expose hidden fault truth, causal graph, canonical solution, variant metadata, and grading/assessment details. Student mode must not receive those hidden structures unless explicitly revealed by lesson design.

## 62. Foundation Acceptance Scenario

The first serious end-to-end acceptance case must NOT be a toy and must now exercise the enterprise-import path as well as normal scenario compilation.

The acceptance fixture should include a realistic structured enterprise workbook/bundle representing approximately:

- one or more sites,
- Internet/WAN,
- external client(s),
- perimeter firewall,
- switches/VLANs,
- Windows client(s),
- Linux host(s),
- RD Gateway,
- RDS Session Host(s),
- Active Directory / DNS,
- DHCP,
- File/Profile server,
- Proxmox management,
- management network,
- segmentation,
- routing/access policy,
- SIEM/logging,
- backup/recovery,
- patching/vulnerability state,
- selected UNKNOWN/missing customer facts,
- at least one deliberate conflict that must be surfaced rather than guessed.

Required acceptance flow:

```text
Structured enterprise source
    ↓
Import + mapping
    ↓
Normalized baseline
    ↓
Validation + provenance review
    ↓
Topology generation
    ↓
Healthy baseline verification
    ↓
Inject deterministic fault(s)
    ↓
Create persistent faulted variant
    ↓
Student Runtime diagnostics
    ↓
Packet/evidence journey
    ↓
Finding / causal evidence
    ↓
Remediation
    ↓
Solved-state regression
```

The scenario should include examples of:

- pentest-style discovery,
- firewall correction,
- access correction,
- segmentation,
- identity hardening,
- RDS hardening,
- management-plane hardening,
- logging,
- backup validation,
- at least one cross-layer troubleshooting fault,
- at least one multi-fault variant,
- at least one deterministic diagnostic workflow.

## 63. Foundation / First-Release Definition of Done

The first release is not complete until BOTH major creation paths work.

### Scenario path

```text
scenario source
    ↓
compiled
    ↓
validated
    ↓
automatically laid out
    ↓
packaged
    ↓
opened on Parrot OS
    ↓
played/tested/solved
    ↓
saved/reloaded/reset
```

### Enterprise import path

```text
supported structured enterprise source
    ↓
imported offline
    ↓
mapped/validated with provenance
    ↓
normalized baseline created
    ↓
topology rendered
    ↓
re-import/diff works
    ↓
fault injected
    ↓
faulted variant created
    ↓
student diagnostics executed
    ↓
packet/evidence journey rendered
    ↓
causal explanation available to instructor
    ↓
remediation verified
    ↓
scenario/package exported
```

AND applicable tests pass:

```text
initial-state regression
solved-state regression
package validation
import round-trip/canonicalization
fault regression
negative controls
student/instructor leakage checks
anonymization/secrets policy
Parrot OS acceptance
```

At least these standalone import classes must be operational in the first release unless a ratified technical conflict explicitly changes the matrix:

```text
XLSX
ODS
CSV
TSV
JSON
YAML
GraphML
Nmap XML
native multi-file import bundle
```

A diagrams.net/draw.io XML topology adapter should also be included for topology structure where the source contains usable deterministic graph information; unsupported semantics remain UNKNOWN rather than guessed.

## 64. Development Priority Order

v1.3 changes priority because Enterprise Environment Import and Fault Injection are first-release core capabilities.

Priority:

1. authoritative schemas + normalized Enterprise Model
2. provenance / knowledge-state / baseline identity model
3. deterministic Import Adapter framework
4. XLSX/ODS/CSV/TSV/JSON/YAML core import adapters
5. GraphML/Nmap XML/native bundle adapters
6. import mapping + validation + conflict review
7. Compiler
8. Validator
9. deterministic Engine
10. Network/Identity semantics required for troubleshooting
11. Fault Injection Engine + fault-pack schema
12. Diagnostic / Observation Engine
13. packet/evidence journey + causal model
14. scenario/fault regression framework
15. baseline/overlay/variant manager
16. re-import / diff / merge
17. package format + PackageIO
18. privacy/secrets/anonymization
19. headless CLI
20. topology rendering
21. auto-layout
22. Builder Inspector + Import/Fault UI
23. Runtime troubleshooting UX
24. instructor/student separation and assessment
25. Parrot OS acceptance
26. domain/vendor/import/fault pack expansion
27. performance/scalability hardening
28. benchmark suite
29. visual polish

Do not prioritize appearance ahead of correctness, provenance, determinism, import safety, or scenario solvability.

## 65. Architecture Change Rule

This Masterprompt is a **LOCKED VERIFIED ARCHITECTURE AGREEMENT**.

Do not silently change it during implementation.

If a genuine technical conflict appears:

1. identify the conflict,
2. provide evidence,
3. explain its impact,
4. propose the smallest compatible change,
5. preserve the primary goals:
   - scalability,
   - rebrandability,
   - deterministic behavior,
   - offline operation,
   - Parrot OS compatibility,
   - portable scenarios,
   - safe scenario packages,
   - first-delivered-file reliability.

Daniel must explicitly approve substantial architecture changes.

## 66. Final Product Principle

The product should be engineered so that creating a complex scenario is primarily a **DATA AUTHORING / DATA IMPORT / DETERMINISTIC TRANSFORMATION** task, not a GUI automation task.

The scenario language and import model should deliberately make both humans and external assistants successful.

Prefer:

```text
known resource types
known schemas
normalized enterprise facts
explicit provenance
explicit UNKNOWN/conflict state
reusable templates
reusable import mappings
reusable vendor profiles
reusable fault packs
reusable tests/diagnostics
declarative rules
deterministic auto-layout
deterministic inference
compiler defaults
strong validation
```

over:

```text
arbitrary scripts
manual coordinates
binary file patching
editor automation
embedded executable code
one-off scenario hacks
silent fuzzy entity merge
AI-only interpretation
fabricated missing infrastructure facts
```

The long-term target now has two equally valid starting points:

```text
A) Daniel writes one prompt.
    ↓
Assistant generates one complete scenario package.
    ↓
Automated tooling validates it.
    ↓
Daniel opens it on Parrot OS.
    ↓
The advanced lab works immediately.
```

or:

```text
B) Daniel/customer supplies structured enterprise data.
    ↓
YadiLab imports it fully offline without AI.
    ↓
Normalized enterprise baseline is validated and visualized.
    ↓
Faults/variants/training scenarios are created deterministically.
    ↓
Daniel opens/runs the lab.
    ↓
The advanced lab works immediately.
```

ChatGPT is an optional accelerator, NOT a runtime dependency and NOT a requirement for normal structured enterprise import, fault injection, diagnostics, grading, or simulation.

## 67. Ratified Architecture Validation Precisions - P1 to P24

The following findings from Architecture Validation Research v1.0 are RATIFIED and normative. They clarify the preceding architecture and take precedence if older wording is ambiguous.

### P1. One authoritative schema technology

JSON Schema Draft 2020-12 validated with Ajv strict is the authoritative external scenario contract. TypeScript types are generated from the schemas. Zod must not become a second manually maintained source of truth.

### P2. React Flow is view/projection only

React Flow nodes, edges, selection state, and visual editor state are projections of the canonical model. They must not become canonical scenario state.

### P3. ELK owns Foundation auto-layout

ELK Layered is the first Foundation layout engine for compound zones and explicit ports. Initial node dimensions are defined, deterministic, and separate from manual user overrides.

### P4. Standard File API is the browser baseline

File input + drag/drop + File/Blob reading + Blob download/export must work. File System Access API is optional progressive enhancement only.

### P5. IndexedDB plus explicit portable export

Autosave/progress uses IndexedDB. Persistent storage may be requested where available, but browser storage is not treated as permanent backup. Users can explicitly export important state.

### P6. Stable loopback origin for local Parrot distribution

The offline Parrot package should include a small precompiled generic launcher that serves bundled assets only on loopback, giving the browser app a stable local origin without requiring Node/npm.

### P7. zip.js behind PackageIO

ZIP implementation is abstracted behind generic `PackageIO`. Initial implementation is zip.js; core model and Engine code must not depend directly on zip.js APIs.

### P8. Canonical solution is stripped from student packages

The compiler/test pipeline uses the canonical solution to prove solvability, but ordinary student distribution packages do not contain it. Author/instructor builds may contain it explicitly.

### P9. Custom SVG is untrusted content

Built-in SVG assets are trusted app resources. Scenario-provided SVG is untrusted and must be sanitized and rendered under a restrictive policy without arbitrary script or remote-reference execution.

### P10. Three-valued logic

Engine queries and predicates support `TRUE`, `FALSE`, and `UNKNOWN`. Unknown/insufficient evidence is never silently converted to false.

### P11. Exact capability/profile locks

Compiled packages record exact resolved capability and profile versions. This exact lock is part of reproducibility and verification.

### P12. Foundation engine scope is intentionally bounded

NetworkEngine v1 is security reachability/configuration simulation, not packet emulation. IdentityEngine v1 is authentication/authorization/permission relationship simulation, not full AD/Kerberos/NTLM/LDAP protocol emulation. Deep simulation can be added later through compatible capabilities without breaking Foundation scenarios.


### P13. Enterprise Environment Import is a first-release core capability

Structured enterprise environments must be importable offline without AI. Import is not a later optional feature.

### P14. One normalized Enterprise Model

All supported input formats normalize into one canonical, source-format-independent semantic model before visualization, validation, fault injection, diagnostics, or compilation.

### P15. Missing facts are explicit, never fabricated

Missing/ambiguous customer facts remain UNKNOWN/CONFLICTING/INVALID as appropriate. Common guesses such as assuming `.1` is a gateway are prohibited unless a deterministic rule can actually prove the value.

### P16. Per-fact provenance is normative

Imported and deterministically inferred facts carry lineage sufficient to explain where they came from and which adapter/mapping/inference rule produced them.

### P17. Baseline and faults are separate layers

Imported baseline, fault overlays, runtime state, remediation, and student progress must remain separable. Fault injection does not destructively alter the reusable baseline.

### P18. Fault Injection Engine is first-release core

Runtime faults, persistent variants, seeded generation, multi-fault scenarios, preview, undo/reset, recovery checks, and reusable versioned fault packs are core architecture.

### P19. Diagnostic / Observation Engine is first-release core

Troubleshooting actions return deterministic observations derived from simulation truth and visibility policy. Arbitrary host shell execution is not required or permitted by normal scenarios.

### P20. Packet Journey means semantic decision trace by default

YadiLab must visualize relevant routing/firewall/NAT/DNS/interface/service/MTU decisions without falsely claiming timing-accurate packet/protocol emulation where none exists.

### P21. Customer-data protection is local-first

Enterprise import is local/offline by default, macros/external links are not executed, secrets/private keys are not propagated into student packages, and deterministic anonymized training clones must be supported.

### P22. Re-import/diff/merge is first-class

An updated customer dataset must be re-importable against an existing baseline with deterministic diff/conflict handling. Manual enrichments and fault variants must not be silently overwritten.

### P23. AI is optional and untrusted at the model boundary

AI may propose mappings/scenarios/explanations externally, but deterministic validation is authoritative. Normal structured import and Runtime operation must not depend on an AI service.

### P24. Comparative superiority claims require evidence

YadiLab may target best-in-class enterprise troubleshooting training, but claims such as “world's best” or “greatly outperforms Packet Tracer” must be supported by explicit reproducible benchmark evidence rather than architecture intent alone.

---

## 68. Enterprise Environment Import - First-Release Core

Enterprise Environment Import is mandatory in the first release.

YadiLab must independently import sufficiently structured enterprise infrastructure data without requiring ChatGPT, cloud AI, a backend service, or internet access.

Mandatory first-release input classes:

```text
XLSX
ODS
CSV
TSV
JSON
YAML
GraphML
Nmap XML
native multi-file import bundle
```

A diagrams.net/draw.io XML adapter should support recoverable graph/topology structure where deterministic interpretation is possible. Shapes/labels without known semantics remain generic/UNKNOWN rather than being guessed.

Legacy `.xls`, vendor configuration text, CMDB/IPAM exports, cloud inventories, PCAP, EVTX, log bundles, and direct APIs may be added through versioned adapters. Direct API connectors are optional enhancements and may never become required for normal offline use.

YadiLab should ship an official **Enterprise Import Workbook Template** with recommended sheets such as:

```text
Sites
Devices
Interfaces
Links
VLANs
Networks
Routes
DHCP
DNS
Firewall
NAT
Services
Identity
Virtualization
Observations
Issues
```

Users are not required to use the official template, but it provides the highest-determinism path.

## 69. Import Adapter Architecture

Every import format is handled by a trusted, versioned Import Adapter.

Adapter responsibilities:

1. parse safe data,
2. preserve raw source provenance references,
3. emit typed candidate facts,
4. perform deterministic exact/alias mapping,
5. report unsupported/unmapped data,
6. never fabricate missing enterprise facts,
7. never execute source-provided code,
8. output the shared Normalized Enterprise Model.

Adapters must not directly mutate Runtime state.

An import adapter is trusted application/capability code and must not be supplied as executable code inside a customer file or `.yadilab` package.

## 70. Import Mapping Semantics

Mapping must prioritize deterministic explainability over opaque “smartness”.

Mapping classes should include:

```text
EXACT
ALIAS
USER_MAPPED
DETERMINISTIC_INFERENCE
UNMAPPED
CONFLICTING
INVALID
```

Examples of deterministic aliases:

```text
Hostname / Device Name / Computer → device.name
IP / IP Address / IPv4           → interface.ipv4
Gateway / Default GW             → routing.defaultGateway
```

Alias dictionaries may be language-aware, including Swedish/English terms, but must be versioned data.

Do not present arbitrary AI-like confidence percentages as truth. If a percentage is shown for UX, its exact mathematical meaning must be documented and derived from transparent mapping states.

## 71. Normalized Enterprise Model

The Normalized Enterprise Model is source-format-independent and schema-defined.

It should be able to represent, as capabilities require:

- organizations/tenants where relevant,
- sites/locations,
- zones,
- devices,
- operating systems,
- hypervisors,
- VMs/containers,
- interfaces,
- physical/logical links,
- switches/bridges,
- VLANs,
- subnets,
- IP addresses,
- gateways,
- routes,
- VRFs/logical routing domains,
- tunnels/VPN relationships,
- wireless AP/SSID relationships,
- DHCP,
- DNS,
- firewall/ACL/NAT policy,
- services/listeners,
- identity relationships,
- management paths,
- storage/backup,
- logging/security tooling,
- intended/documented state,
- observed evidence,
- unresolved/unknown facts.

The normalized model is the canonical baseline semantic state. Imported workbook/XML/CSV layout is not.

## 72. Knowledge State Model

Enterprise facts must support explicit knowledge/evidence state.

At minimum:

```text
KNOWN
UNKNOWN
NOT_APPLICABLE
CONFLICTING
INVALID
INFERRED
```

`INFERRED` is permitted only for deterministic derivations whose rule can be named and replayed.

Example permitted inference:

```text
10.20.30.44/24 → network 10.20.30.0/24
```

Example prohibited guess:

```text
missing gateway → assume 10.20.30.1
```

Unknown information must propagate into Engine explanations/rules via three-valued semantics rather than being silently treated as false or filled with defaults.

## 73. Per-Fact Provenance and Data Lineage

Each important imported fact should be traceable, where available, to provenance such as:

```text
source file hash
file name / import source ID
sheet/table
row / column
JSON/YAML pointer
XML path/node
adapter ID/version
mapping rule/profile version
user override
inference rule ID/version
```

Example explanation:

```text
Default gateway = 10.20.30.1
Source: customer.xlsx
Sheet: Interfaces
Row: 44
Column: Gateway
Mapping: alias.default_gateway.v2
```

Provenance enables audit, re-import, conflict resolution, and instructor explanation.

## 74. Intended, Observed, Simulated, and Visible State

YadiLab must not flatten all information into one truth layer.

Distinguish conceptually:

```text
DOCUMENTED / INTENDED STATE
OBSERVED / DISCOVERED EVIDENCE
SIMULATED GROUND TRUTH
STUDENT-VISIBLE KNOWLEDGE
```

A customer's spreadsheet may describe intended architecture while observed diagnostic data shows a different actual state. Both must be preservable.

A scenario may intentionally hide true state until the student performs diagnostic actions.

Conflicting evidence must remain explicit until a deterministic rule or user decision resolves it.

## 75. Deterministic Entity Resolution

Entity resolution must be conservative.

Prefer stable explicit keys:

```text
asset ID
hostname + scoped domain where safe
interface ID
serial/UUID where appropriate
explicit source relation
user-confirmed mapping
```

Do NOT silently merge entities merely because labels are similar.

Fuzzy matching, if ever offered, is only a review suggestion and must never silently become canonical truth.

Duplicate IPs, duplicate MACs, overlapping identifiers, hostname collisions, and conflicting relationships must be surfaced.

## 76. Import Wizard and Review UX

The Import Wizard must support:

```text
source selection
sheet/table detection
adapter detection/selection
column/field mapping
mapping-profile reuse
preview/dry-run
unmapped field review
UNKNOWN/conflict review
provenance inspection
validation
baseline creation
import report export
```

The user must be able to continue with explicitly UNKNOWN optional data while required structural ambiguities block verification.

## 77. Re-Import, Diff, and Merge

Enterprise environments change. Re-import is therefore first-class.

When new source data is supplied, YadiLab must support deterministic comparison between:

```text
current normalized baseline
new normalized import candidate
manual validated enrichments
existing scenario/fault overlays
```

Required behavior:

- show added/removed/changed entities and facts,
- preserve provenance,
- never silently overwrite validated manual corrections,
- surface merge conflicts,
- store explicit conflict resolutions,
- revalidate dependent faults/variants,
- warn when removed/changed infrastructure invalidates scenarios,
- allow rollback/cancel before baseline replacement.

A re-import must not destructively rewrite existing fault variants without explicit migration/revalidation.

## 78. Customer Data Privacy, Secrets, and Anonymization

Enterprise import is local/offline by default.

No customer environment data may be uploaded to a cloud/AI service merely to make normal import work.

YadiLab should detect or allow policies for likely sensitive values such as:

- passwords,
- API tokens,
- private keys,
- SNMP communities,
- access keys,
- connection secrets,
- sensitive user identifiers.

Secrets must not be silently copied into scenario/student packages.

Where practical, YadiLab must support deterministic pseudonymized training clones that can transform:

```text
customer/company names
hostnames
usernames
site names
selected addresses/identifiers
```

while preserving training-relevant relationships, subnet structure, routing relationships, topology, and causal behavior.

Reversible anonymization mappings, if produced, are sensitive instructor/operator data and must be stored/exported separately from student packages.

Logs/reports should avoid unnecessary secret echoing.

## 79. Baseline / Overlay / Variant Model

The imported normalized enterprise baseline is reusable infrastructure truth, not a disposable training scenario.

Conceptual layers:

```text
BASELINE
  + scenario overlay
  + fault overlay(s)
  + runtime/student actions
  + remediation overlay/state
```

A persistent scenario variant should ideally be representable as:

```text
baselineIdentity
scenario metadata
ordered deterministic mutations
locked capability/profile/fault-pack versions
seed where applicable
```

Variants may be materialized into self-contained `.yadilab` packages for portability.

Healthy/faulted/remediated states should be diffable.

## 80. Fault Injection Engine

Fault Injection is a first-release core feature.

Required user operations:

```text
Preview Fault
Inject Fault
Undo
Redo
Reset
Compare Before/After
Reveal Cause (instructor policy)
Save as New Faulted Project/Variant
Create Student Exercise
```

Fault injection may operate against:

- one device,
- one interface,
- one policy/rule,
- one service,
- one route,
- one identity relation,
- a topology relationship,
- multiple coordinated targets.

Faults must be declarative, validated, deterministic, and reversible where the lesson permits.

## 81. Fault Pack Contract

Reusable faults belong in versioned Fault Packs.

A fault definition should be able to declare:

```text
id
version
domain
target types
preconditions
incompatibilities
mutation(s)
expected effects
negative controls / unaffected behavior
observable symptoms
hidden truth
recovery/remediation condition
blast-radius expectations
visibility policy
difficulty dimensions
tags / learning objectives
```

Example conceptual fault:

```text
routing.wrong_default_gateway
```

with preconditions ensuring the target actually has an address/gateway model and expected effects such as local-subnet reachability remaining while external reachability fails.

Fault consequences must be Engine-derived, not merely hardcoded explanatory text.

## 82. Multi-Fault, Chained, and Temporal Faults

Advanced scenarios must support more than one independent fault.

Supported patterns should include:

- simultaneous faults,
- causal/dependency chains,
- one repaired fault revealing another,
- intermittent faults,
- scheduled link/service flapping,
- time-dependent route/service state,
- deterministic packet loss/latency conditions where the capability supports them.

Temporal behavior uses the scenario virtual clock and explicit seeds/schedules.

A compatibility/validation layer must reject or flag fault combinations that make the lesson contradictory, impossible, or semantically meaningless.

## 83. Fault Verification and Solvability

Each injected/generated fault scenario must be testable.

Applicable verification includes:

```text
preconditions satisfied
mutation applied
intended symptom exists
intended diagnostic evidence exists
negative controls remain correct
blast radius matches expectation
canonical/reference remediation can solve it
post-remediation healthy behavior is restored
unrelated required traffic/services remain functional
completion logic triggers correctly
```

Multi-fault scenarios require regression at relevant intermediate and final states.

Do not ship a training fault merely because a UI icon says the device is broken.

## 84. Diagnostic / Observation Engine

YadiLab must include a deterministic Diagnostic / Observation Engine for realistic troubleshooting.

It should support common diagnostics through generic capabilities and vendor/OS profiles, for example:

### Windows-style

```text
ipconfig /all
route print
arp -a
ping
tracert
nslookup
Test-NetConnection
netstat-style service/listener inspection
Windows Firewall state/rule inspection
service status
event/log observations where modeled
```

### Linux-style

```text
ip addr
ip route
ip neigh
ping
traceroute/tracepath
dig/nslookup
ss/netstat-style listener inspection
nftables/iptables-style policy inspection
systemctl/service status
journal/log observations where modeled
```

### Network/vendor profiles

May expose deterministic modeled equivalents of selected `show`/inspection commands.

These commands are SIMULATED OBSERVATIONS over Engine state. Normal scenarios must not execute arbitrary shell commands on the host.

Diagnostic output must respect student visibility and uncertainty. UNKNOWN modeled state may yield incomplete/unknown results rather than fabricated certainty.

## 85. Packet / Evidence Journey

YadiLab should provide a visual deterministic journey for a modeled communication attempt.

A journey may include decisions such as:

```text
name resolution
source address/interface selection
local-vs-remote subnet decision
neighbor/ARP decision
route lookup / metric selection
VLAN / logical segment transition
firewall / ACL decision
NAT transformation
tunnel/VPN transition
MTU/PMTUD constraint
next hop
service listener
application dependency
result / block point
```

The journey should show WHERE communication fails and WHY according to modeled state.

Before/after remediation comparison should be supported.

This is a semantic decision trace unless a deeper packet-emulation capability explicitly states otherwise.

## 86. Causal / Dependency Model

Troubleshooting explanations require typed relationships.

Do not turn temporal ordering or correlation into unqualified causality.

Useful relationship types may include:

```text
causes
depends_on
blocks
permits
contributes_to
observed_as
conflicts_with
correlated_with
```

`causes` should only be used where the model has enough explicit semantic evidence.

Instructor causal chains may remain hidden from students until revealed by lesson policy.

## 87. Instructor / Student Separation

Instructor and student views are separate security/learning surfaces.

Instructor data may include:

- injected fault definitions,
- hidden ground truth,
- causal graph,
- canonical solution,
- expected diagnostic path,
- grading criteria,
- mapping/import provenance,
- variant seed/version metadata.

Student distributions must not contain instructor-only secrets/solutions merely hidden by CSS/UI.

Assessment should primarily validate outcomes, required actions where explicitly pedagogical, and evidence—not brittle exact click paths.

## 88. Deterministic Scenario / Variant Generator

YadiLab should generate training variants from a reusable baseline.

Generation input may include:

```text
baseline identity
fault domains
number of faults
allowed target types
difficulty dimensions
visibility/evidence policy
seed
fault-pack versions
constraints
```

Same normalized inputs + seed + versions must generate the same variant.

Difficulty must not be a mysterious AI score. Prefer explicit dimensions such as:

- number of simultaneous faults,
- number of layers involved,
- dependency depth,
- evidence visibility,
- ambiguity/decoys,
- temporal/intermittent behavior,
- remediation constraints,
- blast radius.

## 89. Enterprise Training Factory

A validated enterprise baseline should be reusable as a training factory:

```text
Baseline
  ├─ Junior variant(s)
  ├─ YH/intermediate variant(s)
  ├─ Advanced variant(s)
  ├─ Senior troubleshooting variant(s)
  ├─ Security/pentest variant(s)
  └─ Custom customer-incident reconstruction
```

A class may receive different seeded variants of comparable explicit difficulty dimensions while remaining reproducible.

The original baseline must not need to be manually redrawn for each exercise.

## 90. Import Health / Completeness Reporting

YadiLab should report data completeness transparently.

Example:

```text
Interfaces: 143 total / 139 with IP / 4 UNKNOWN
Routes: 41 total / 29 complete / 12 incomplete
Links: 84 verified / 10 inferred / 7 unresolved
```

Do not present an opaque “AI confidence score” as if it were factual certainty.

If an overall percentage is shown, it must be calculable from displayed counts and documented rules.

## 91. Large Environment and Visualization Scalability

The semantic model may be larger than what should be rendered simultaneously.

Large-topology UX should support:

- filtering,
- sites/zones/layers,
- search,
- grouping/clustering,
- collapse/expand,
- level-of-detail views,
- lazy/virtualized rendering where appropriate,
- focused packet/evidence journeys,
- subgraph views.

UI optimization must never silently drop semantic model objects.

Release benchmarking should include deterministic small/medium/large synthetic enterprise models and measure import, validation, layout, rendering, diagnostics, fault generation, and package operations.

## 92. Adapter Extensibility and Future Data Sources

Future trusted adapters may include:

```text
NetBox-style exports
CMDB exports
IPAM exports
Nmap/other discovery formats
vendor configuration snapshots
cloud inventory exports
LLDP/CDP-derived topology datasets
firewall policy exports
log/evidence bundles
PCAP-derived evidence summaries
EVTX/log exports
```

Core architecture remains file/offline-first.

Direct live connectors/APIs, if later added, are explicit opt-in integrations with separate credentials/security handling. They must not be required for normal use.

## 93. Canonicalization, Round-Trip, and Baseline Identity

Normalized enterprise data must have deterministic canonical serialization rules sufficient to compute a baseline identity/hash.

Where semantically applicable:

```text
same source bytes
+ same adapter version
+ same mapping profile
+ same import options
+ same user conflict resolutions
= same normalized baseline identity
```

Native normalized export → re-import should preserve equivalent semantics and identity under the same canonicalization/version contract.

## 94. AI Boundary

YadiLab core logic should remain as independent of AI as practical.

NO AI/LLM is required for:

- structured enterprise import,
- normalization,
- validation,
- entity resolution authority,
- fault injection,
- scenario generation from deterministic fault packs,
- Runtime simulation,
- diagnostic outputs,
- causal results,
- grading,
- package creation.

An external assistant may help with messy unstructured customer material, propose mappings, create scenario source, or explain results.

Such output must pass the same deterministic validation as human-authored data.

The application must never silently send customer data to an AI service.

## 95. Benchmarking and Product Claims

The architectural TARGET may be to become best-in-class for visual enterprise troubleshooting training, deterministic fault injection, and causal/packet-journey explanation.

Do NOT encode unverified marketing claims as technical fact.

Claims such as:

```text
world's best
greatly outperforms Cisco Packet Tracer
best troubleshooting simulator
```

require reproducible evidence.

Benchmark against relevant products such as:

```text
Cisco Packet Tracer
GNS3
EVE-NG
other relevant lab/training platforms
```

Compare specific capabilities rather than one vague overall score, for example:

- enterprise dataset import,
- time to create a realistic training topology,
- deterministic fault injection,
- multi-layer/multi-fault scenarios,
- diagnostic realism at the declared abstraction level,
- causal explainability,
- instructor/student separation,
- reproducibility,
- offline portability,
- safe package model,
- automation/CLI,
- re-import/change management.

Document both strengths and limitations.

## 96. v1.3 First-Release Non-Negotiable Summary

The first release is NOT considered architecturally complete without:

1. offline Parrot-compatible Builder/Runtime baseline,
2. deterministic Engine/Compiler/Validator,
3. scenario source + `.yadilab` package workflow,
4. Enterprise Environment Import as a core UI/CLI feature,
5. XLSX + ODS + CSV/TSV + JSON/YAML + GraphML + Nmap XML + native bundle import,
6. normalized Enterprise Model,
7. explicit UNKNOWN/CONFLICTING/provenance model,
8. import preview/validation/report,
9. re-import/diff/merge,
10. baseline/overlay/variant separation,
11. deterministic Fault Injection Engine,
12. versioned Fault Packs,
13. runtime and persistent fault variants,
14. multi-fault/seeded scenario generation,
15. Diagnostic / Observation Engine,
16. visual packet/evidence journey,
17. instructor/student separation,
18. secrets/privacy safeguards,
19. deterministic anonymized training clone support,
20. headless CLI automation,
21. first-release enterprise-import acceptance scenario,
22. real Parrot OS acceptance before claiming Parrot verification.

---

## End - Masterprompt v1.3

**Status:** VERIFIED ARCHITECTURE AGREEMENT / LOCKED  
**Supersedes:** Masterprompt v1.2  
**Substantial architecture changes require Daniel's explicit approval.**
