# Phase 93 — DNS Chain X-Ray (v1.1.0-dev.14 candidate)

Authoritative architecture: YadiLab Masterprompt v1.3 VERIFIED / LOCKED plus Living Topology & Visual Simulation Specification v1.0.
Parent checkpoint: YadiLab v1.1.0-dev.13 / Phase 92.

## Goal

Implement the second listed Phase E deliverable as one Engine-owned DNS decision chain, replacing the former Observation-owned resolver decision loop without changing the modeled DNS data source.

The authoritative chain is:

```text
source dnsServers + modeled resolver resources/state
  -> Engine queryDnsChain / DnsChainDecisionTrace
  -> Active Probe transcript
  -> Visual Journey fail-closed validation
  -> DNS Chain X-Ray
```

No downstream layer performs resolver selection, resource mapping, network reachability, DNS-service evaluation or record matching.

## Engine truth

For a bounded query the Engine records:

- exact source resource and canonical query name;
- resolver configuration state (`KNOWN`, `ABSENT`, `MALFORMED`);
- configured resolver address order;
- exact resolver-address-to-`network.dns_server` mapping;
- per-resolver network truth, path, blocking point and explanation;
- resolver DNS service state;
- modeled records state and matching-record count;
- resolver disposition (`UNMAPPED`, `AMBIGUOUS_MAPPING`, `NETWORK_BLOCKED`, `NETWORK_UNKNOWN`, `SERVICE_DISABLED`, `SERVICE_UNKNOWN`, `RECORDS_UNKNOWN`, `NO_RECORD`, `RECORD_AMBIGUOUS`, `RECORD_MALFORMED`, `RESOLVED`);
- selected resolver, answer address and answer-to-resource mapping when resolution is proven.

Configured resolver order remains authoritative. Missing, malformed or ambiguous state becomes explicit `UNKNOWN` rather than guessed truth.

## Cross-phase network boundary

Resolver reachability reuses Network Engine truth, including the existing modeled source default-gateway/on-link contract. If the resolver path is blocked, the DNS attempt terminates at `NETWORK_BLOCKED` and the Engine does not inspect DNS service or records after the block point. No answer is fabricated.

## Compiler boundary

Phase 93 adds conservative authoring validation:

- `dnsServers`, when present, must be an array of unique literal IPv4 addresses; an empty array remains valid and means explicitly no configured resolver;
- `properties.dns`, when present, must be an object;
- `dns.enabled`, when present, must be boolean;
- `dns.records`, when present, must be an array;
- each authored A-like record must provide a non-empty `name`/`hostname`/`fqdn` and a literal IPv4 `address`.

Duplicate matching record names are not rejected by the compiler because runtime ambiguity is intentionally represented by the Engine as `RECORD_AMBIGUOUS / UNKNOWN`.

## Active Probe boundary

The existing Windows/Linux modeled DNS probes now consume `queryDnsChain`. Learner-facing command-shaped text remains compatible, but all resolver/network/service/record decisions come from the Engine trace. No guest DNS command or real packet is executed.

## Visual Journey / UI boundary

Visual Journey rejects DNS traces whose source/query/truth, resolver order, resource mapping, network truth/path/blocking point, selected resolver or answer binding disagrees with the transcript/scenario. DNS gets its own `dns.resolve` terminal event; a negative DNS result is not mislabeled as a fabricated packet drop.

The browser DNS Chain X-Ray shows configured resolver order, mapping, network truth, service/records state, selected resolver and answer. The UI performs no DNS decision logic.

## Deliberate non-features

This checkpoint does not implement:

- recursive resolver behavior;
- iterative root/TLD/authoritative traversal;
- CNAME chasing, TTL/cache/negative-cache behavior;
- DNSSEC;
- real DNS packets or guest commands;
- DHCP DORA;
- later Phase E listener/service-state, TCP state-machine, UDP/ICMP failure or MTU/PMTUD slices.

## Verification target

Checkpoint acceptance requires version-bumped Engine, Observation/Active Probe, Visual Journey/UI contract, schema/compiler, Canvas, branding, acceptance-contract and package-lock structural gates to pass. Installed-dependency/Foundation/browser/build/Parrot gates are classified separately from their actual execution and are never inferred as PASS.

## Focused verification before final sealing

- Engine: 300 functional + 157 adversarial + 24 regression + 22 regression-adversarial PASS.
- Observation: 88 functional + 11 adversarial PASS.
- Active Probe: 194 functional + 29 adversarial PASS.
- Visual Journey: 36 functional + 89 adversarial + UI contract PASS.
- Compiler: 69 functional + 110 adversarial + 2/2 generated-output schema validations PASS.
- Schema: 55/55 fixtures + 18/18 Draft 2020-12 meta-validations PASS.
- Canvas: 19 functional + 10 adversarial; device visuals 31 functional + 16 adversarial PASS.
- Branding and acceptance-contract PASS.
- `scripts/verify_package_lock.mjs`: PASS, requiredPackageCount 33.

Final environment-dependent gate results are appended after the version-bumped rerun.

## Next authoritative Phase E slice

After this checkpoint is sealed, the next listed Phase E deliverable is **DHCP DORA**.
## Final local verification on version-bumped source

- `npm run test:engine`: PASS — 300 functional, 157 adversarial, 24 regression, 22 regression-adversarial assertions.
- `npm run test:observation`: PASS — Observation 88 functional + 11 adversarial; Active Probe 194 functional + 29 adversarial assertions.
- `npm run test:visual-journey`: PASS — 36 functional + 89 adversarial; UI contract and `ui/app/main.mjs` syntax PASS.
- `npm run test:compiler`: PASS — 69 functional + 110 adversarial assertions + 2/2 generated-output schema validations.
- schema: PASS — 55/55 fixture expectations + 18/18 Draft 2020-12 meta-validations.
- `npm run test:canvas`: PASS — 19 functional + 10 adversarial; device visuals 31 functional + 16 adversarial.
- branding and acceptance-contract: PASS.
- `node scripts/verify_package_lock.mjs`: PASS — `requiredPackageCount: 33`.

Environment-dependent gates actually run on the same frozen source:

- `npm run test:foundation`: RC 2 / **BLOCKED** after Canvas; first stop is Layout TypeScript compilation because `elkjs/lib/elk.bundled.js` is not installed.
- `npm run check:browser-readiness`: RC 77 / **BLOCKED** because the pinned installed dependency tree is absent.
- `npm run build`: RC 2 / **BLOCKED** on missing `elkjs` and `ajv`.
- Parrot OS x86-64 acceptance: **NOT RUN**.
- final real Chromium acceptance: **NOT RUN**.
- final real Firefox acceptance: **NOT RUN**.

This remains a development checkpoint and is **not** a VERIFIED PRODUCT RELEASE.

