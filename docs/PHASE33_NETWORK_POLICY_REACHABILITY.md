# Phase 33 — Route/VLAN/ACL-aware NetworkEngine

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 33 extends the bounded deterministic NetworkEngine. It does not implement packet forwarding, routing protocols, switch ASIC behavior, timing, or NAT translation. Existing scenarios without declared route/VLAN/ACL state preserve the previous topology/firewall/listener behavior.

## Route semantics

A resource may declare `properties.routes` as an ordered data set. Routes may target a resource ID, zone ID, `default`/`any`/`*`, or IPv4/IPv6 CIDR. Route decisions are evaluated only when the resource declares an authoritative route table.

Supported route fields include `id`, `destination`, optional `via`, optional `interface`, optional `enabled`, and optional `action`. Supported forwarding actions are `forward`/`allow`; `blackhole`, `unreachable`, `prohibit`, `deny`, and `block` prove a blocked path. Malformed or equally-specific conflicting route data yields `UNKNOWN`.

## VLAN semantics

Network/management connections may declare `properties.vlan` or `vlanId` in range 1..4094. Resources may declare `properties.vlan` or `properties.vlans`. Declared membership mismatch blocks the segment. Malformed VLAN state yields `UNKNOWN`. A connection without a VLAN constraint remains backward-compatible.

## ACL semantics

Any resource may declare ordered `properties.acls` with source/destination/protocol/port/action matching and optional `aclDefaultAction`. ACL allow/deny is evaluated in addition to firewall rules. Malformed or unsupported ACL policy yields `UNKNOWN`, never implicit allow/deny.

## Version boundary

Engine version is advanced to **0.6.0** because reachability results now incorporate declared route/VLAN/ACL state. Network reachability/segmentation/route-test/port-scan and virtualization management-exposure semantics require Engine 0.6.0 in compiled scenarios.

NAT translation is intentionally excluded from this phase and remains a separate explicit Foundation gap.
