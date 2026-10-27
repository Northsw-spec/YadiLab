# Phase 71 — Diagnostic / Observation Engine, Wave 2

Foundation v0.71.0 adds deterministic **active modeled probes** on top of the read-only Wave-1 observation layer.

## Boundary

The observation engine advances to `foundation.observation@0.2.0`.

Active probes are explicitly model-based. Familiar command names are a learning interface only. No guest OS command, packet, socket, DNS request, PowerShell process, shell process or kernel operation is executed.

Every active-probe transcript is marked:

- `modeled: true`;
- boundary `NO_GUEST_COMMAND_EXECUTION`;
- mode `ACTIVE_MODELED_PROBE`;
- exact scenario ID/hash and Runtime `stateRevision`;
- exact source, probe ID and arguments;
- deterministic `TRUE` / `FALSE` / `UNKNOWN` verdict;
- direct modeled evidence and Network Engine explanations.

`UNKNOWN` is used whenever the model cannot safely prove a result. Missing or malformed state is never silently repaired.

## Windows Wave 2

Four active modeled probes are available from modeled Windows Runtime hosts:

1. `ping <destination>` — ICMP reachability;
2. `Test-NetConnection <destination> -Port <port>` — TCP path plus destination listener;
3. `Resolve-DnsName <name>` — modeled DNS resolver selection/service/record lookup;
4. `tracert <destination>` — path and blocking-point evidence.

## Linux Wave 2

Four equivalent probes are available from modeled Linux Runtime hosts:

1. `ping -c 4 <destination>`;
2. `nc -vz <destination> <port>`;
3. `dig <name>`;
4. `tracepath <destination>`.

## Connectivity semantics

Network connectivity is delegated to the already verified deterministic Network Engine `queryReachability` implementation. Wave 2 does not create a parallel packet-routing engine.

For Windows/Linux source hosts, active probes add two explicit host-side checks when the required modeled evidence exists:

- **default-gateway reachability for known off-link destinations** — same-subnet/on-link destinations do not require the default gateway; off-link probes fail when a known modeled gateway is absent, malformed, not on-link, or provably not represented by a next-hop resource on the selected topology path;
- **host ACL default policy** — where no explicit ACL list is declared but a modeled `aclDefaultAction` exists, `deny`/`block` fails unmatched active probes at that resource, while unsupported policy values become `UNKNOWN`.

If topology or address data is insufficient to safely prove gateway identity, the result is `UNKNOWN` rather than guessed.

This creates an explicit pedagogical distinction such as:

`local/on-link works → off-link fails at gateway`.

## DNS semantics

DNS probes use only modeled state:

1. source `properties.dnsServers` supplies resolver addresses in declared order;
2. a resolver address must map unambiguously to a declared `network.dns_server` resource;
3. modeled network reachability to that resolver is checked;
4. `properties.dns.enabled` must be known and enabled;
5. `properties.dns.records` must be a valid modeled record array;
6. the requested canonical DNS name must match one unambiguous record;
7. the returned address is reported exactly as modeled and is mapped back to declared resource IDs only when an exact modeled address match exists.

A corrupt DNS record can therefore return `TRUE` syntactically while mapping to the wrong/no declared resource, which is intentionally different from resolver failure.

DNS input is bounded and validated. Whitespace/path-like input, overlong names and malformed labels fail closed before rendering a command-shaped transcript.

## Path visibility

Path probes expose the deterministic Network Engine path and blocking point. If a path is blocked, the transcript never presents later topology nodes as reached after the blocking point.

## Runtime UI

Runtime now exposes a separate **Modeled active probes** panel alongside Wave-1 observations. The learner chooses:

- source host;
- active probe;
- destination resource when applicable;
- TCP port when applicable;
- DNS name when applicable.

The result shows the command-shaped surface, verdict, Runtime revision, modeled path/evidence and Engine explanation. Builder cannot execute active probes.

## Permanent verified fault visibility

Wave-2 regression proves active effects for representative previously verified faults, including:

- wrong Windows/Linux default gateway;
- removed default gateway;
- APIPA/link-local source addressing with an unreachable old gateway;
- Windows/Linux host ACL default-deny;
- wrong resolver configuration without fabricated DNS success;
- disabled modeled DNS service;
- corrupt DNS record returning a wrong documentation-prefix answer;
- disabled HTTP service causing TCP/80 failure;
- wrong router next hop producing a path blocking point.

It also proves that a wrong default gateway does **not** break a declared on-link/same-subnet probe.

## Non-goals

v0.71.0 does not introduce:

- real ICMP/TCP/DNS packets;
- guest command execution;
- terminal/PTY access;
- automatic diagnosis, ranking or remediation;
- packet capture;
- ARP/ND cache simulation;
- DNS recursion/caching/TTL/CNAME/MX/SRV protocol simulation;
- DHCP lease negotiation;
- latency, packet loss or timing randomness;
- temporal/intermittent fault scheduling;
- AI/ML/LLM inference.

Those require separate explicit model/execution contracts rather than fabricated behavior.
