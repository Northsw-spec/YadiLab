# Release notes v0.33.0 — Route/VLAN/ACL-aware NetworkEngine

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.33.0 continues directly from exact-byte verified v0.32.0.

Added:
- authoritative declared route-table evaluation;
- resource/zone/default and IPv4/IPv6 CIDR route matching;
- route next-hop/interface/blackhole semantics;
- VLAN-constrained connection reachability with declared endpoint membership;
- ordered ACL allow/deny/default semantics on resources;
- malformed/conflicting route/VLAN/ACL state propagates `UNKNOWN`;
- Engine version 0.6.0 and updated semantic minimum-version gates.

Verification highlights before packaging:
- Engine functional: 94 assertions PASS;
- Engine adversarial: 47 assertions PASS;
- Compiler functional: 61 assertions PASS;
- Compiler adversarial: 40 assertions PASS;
- complete Foundation regression through Phase 33 PASS.

NAT translation is not claimed by this checkpoint.
