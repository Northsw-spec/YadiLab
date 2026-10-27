# Phase 94 — DHCP DORA X-Ray (v1.1.0-dev.15 candidate)

## Scope

Phase 94 adds an Engine-owned modeled DHCP DORA chain for explicitly modeled local-L2 DHCP. It does not execute guest commands or real DHCP packets.

The authoritative chain is `queryDhcpDora(...)`:

1. reads the client `properties.dhcp.enabled` state;
2. enumerates modeled `network.dhcp_server` resources deterministically;
3. proves client→server Discover and server→client Offer paths using local L2 topology only;
4. consumes existing VLAN/STP forwarding truth on those paths;
5. reads explicit server DHCP state (`enabled`, `availableLeases`, `offers`, `gateway`, `dnsServers`, `prefixLength`);
6. requires exactly one explicit client→address Offer to prove a lease;
7. emits immutable DISCOVER / OFFER / REQUEST / ACK stage truth and the selected server/options only when uniquely provable.

## Fail-closed boundaries

- Missing or malformed client DHCP state is `UNKNOWN`.
- Missing/incomplete server offer state is `UNKNOWN`; an address is never synthesized from a subnet or pool.
- Pool exhaustion is a conclusive `FALSE`.
- More than one provable Offer is `UNKNOWN` because client timing/preference is not modeled.
- L3 transit through a router/firewall is not treated as DHCP broadcast reachability. DHCP relay is not modeled in this slice.
- A lower-layer VLAN/STP block terminates the candidate before server enabled/pool/offer state is consumed.
- Visual Journey rejects missing, reordered, endpoint-mismatched, topology-invalid, contradictory or fabricated DORA evidence before UI rendering.

## Presentation

Active Probe adds modeled learning surfaces for Windows `ipconfig /renew` and Linux `dhclient -v`. Both are read-only Engine queries with `NO_GUEST_COMMAND_EXECUTION`.

DHCP DORA X-Ray renders only Engine evidence: client state, four DORA stages, candidate servers, Discover/Offer-return L2 paths, server/pool disposition, explicit Offer, selected lease, gateway, DNS and prefix. The UI performs no DHCP server selection, address allocation or relay inference.

## Deliberate non-features

This checkpoint does not implement DHCP relay, dynamic address allocation, mutable lease tables, lease aging, T1/T2, renew/rebind state machines, decline/conflict detection, Option 82, real sockets/packets or guest command execution.

The next Phase E slice is listener/service-state semantics.

## Verification

Final version-bumped verification: Engine **318 functional + 167 adversarial + 24 regression + 22 regression-adversarial**; Observation **88 + 11**; Active Probe **210 functional + 32 adversarial**; Visual Journey **44 functional + 97 adversarial** plus UI contract; Compiler **69 functional + 126 adversarial + 2/2 output-schema**; schema **55/55 fixtures + 18/18 meta-validations**; Canvas, branding, acceptance-contract and package-lock gate PASS. `test:foundation` reaches and passes Canvas then is **RC 2 / BLOCKED at Layout** because `elkjs/lib/elk.bundled.js` is not installed. Browser readiness is **RC 77 / BLOCKED** on the absent pinned dependency tree. Top-level build is **RC 2 / BLOCKED** on missing `elkjs`/`ajv`. Parrot OS and final real Chromium/Firefox acceptance are **NOT RUN**.
