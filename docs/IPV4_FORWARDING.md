# One-way IPv4 datagram forwarding — first bounded data-plane step

## Source of truth and limitations

The implementation uses the single validated canonical project (schemas 1.0–1.3), the existing `ConnectedRoutingTable` (CONNECTED and explicitly configured STATIC), the existing `ArpSession` with actual broadcast requests and unicast replies, and its underlying `EthernetFabric` with active cables, ports, switch learning and explicit VLAN configurations. It never synthesizes missing MAC addresses, devices, links, interfaces, gateways, routes or IP destinations.

A datagram uses IPv4 EtherType `0x0800` on a validated Ethernet II frame. `IPv4Datagram` serializes an RFC 791 **20-octet** header (version 4, IHL 5, total length, real one's-complement header checksum, exact source/destination, TTL, no options or fragmentation), uses experimental IP protocol number **253** with an empty payload and checks the encoded header after actual Ethernet serialization. This is **not** an ICMP echo packet, TCP/UDP application data, a complete host IP stack or a ping. ICMP Time Exceeded is also **not emitted** on TTL expiration.

## Operation contract

`IPv4Trace(project).send(source_node, source_port, destination_ipv4, ttl)` runs **one explicitly requested datagram** from a declared, enabled non-switch interface with configured IPv4/CIDR and MAC. The destination must be an explicitly supplied canonical usable IPv4 address and the initial TTL an integer in 1..255. Sending to the source interface's own IP is rejected instead of masquerading as real wire traffic.

1. The source node's *existing routing table* is queried for the original datagram destination, with strict longest-prefix match. Missing routes and equally specific ambiguous routes fail. If the explicitly selected source port differs from the route's outgoing port, the engine returns `SOURCE_INTERFACE_MISMATCH` instead of substituting another source silently.
2. The selected output interface must have configured MAC and IPv4. For a STATIC route, the ARP target is exactly the explicit on-link next-hop; for a CONNECTED route, ARP targets the final IPv4 destination. The existing `ArpSession.resolve` performs real Layer 2 requests/replies and reports failures such as a disabled cable, unmatched VLAN, or missing target MAC. If it is not `RESOLVED`/`CACHE_HIT`, **no IPv4 frame is sent** and the status is `ARP_FAILED`.
3. The engine constructs a validated Ethernet frame containing the actual IPv4 header and sends it with the existing `EthernetFabric.inject_frame`. Only an actual arrival at an endpoint with both the **correct configured destination MAC and next-hop IPv4 on the receiving port** is accepted. No switched topology path alone proves packet arrival or NIC acceptance.
4. If the arriving port's configured IP equals the datagram destination, the result is `DELIVERED` (a narrow model of one-way datagram delivery to that declared interface, **not** delivery to an application). Otherwise, only devices explicitly typed `router` may forward transit IPv4. A router must have TTL >1 before forwarding; it decrements TTL once, recomputes the header checksum and repeats the same routing/ARP/Ethernet process on the chosen output interface. Hosts and firewalls have no modeled transit forwarding.
5. Invalid routes, missing identity, ambiguous routes, failed ARP, inoperative cables/VLAN, transit through non-router devices, TTL expiration, and simulation hop limits return **distinct explicit statuses**. No implicit ICMP error is generated. Local delivery on a router's *different* interface is conservatively unsupported, rather than assumed.

Return fields include `status`, `meaning`, actual source/destination, initial/final TTL, observed receiving interface when successful, per-hop chosen route and next-hop, actual ARP statuses/request/reply wire traces, actual IPv4 wire transmissions, observed VLAN drops and learned switch MAC tables. `icmpSent` is always false in this phase. A result of `DELIVERED` never claims full bidirectional reachability: no return route, reply, service, or host stack has been verified.

## HTTP and Builder

`POST /api/ipv4/trace` requires **exactly**:

```json
{"project": {"schemaVersion":"1.3","name":"...", "zones":[], "nodes":[], "links":[]},
 "sourceNode":"a", "sourcePort":"eth0", "destinationIpv4":"203.0.113.20","ttl":4}
```

The server creates a fresh isolated engine for each request; there is no on-disk mutation, reusable IP session, background simulation or cached prior ARP learning. Invalid shapes, TTL and addresses return HTTP 422. Builder's separate IPv4 panel selects an explicit source port, destination IP and TTL and presents actual hop/ARP/Ethernet traces without pretending to show ping.

The existing `/api/routing/connected`, `/api/diagnostics/arp` and `/api/simulation/*` semantics remain unchanged. An explicit SAVE is still required for any project mutation. This feature adds no schema fields.

## Verification

`tests/test_ipv4_forwarding.py` validates the RFC 791 header/checksum and parsing, negative malformed packets and TTL, one- and two-router forwarding, explicit static next-hop followed by connected-route ARP, VLAN isolation, missing/down cables, missing MAC, missing or ambiguous route, wrong selected source, non-router transit, actual HTTP loopback and persisted project bytes/SHA unchanged.

`tests/browser_smoke.py` drives the real Chromium UI through local HTTP: direct datagram delivery to a declared interface, one missing static next-hop => `ARP_FAILED`, invalid TTL => HTTP 422, and identical saved bytes.
