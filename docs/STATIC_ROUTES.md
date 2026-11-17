# Static IPv4 routes — schema 1.3 (PR #16)

## Canonical project format and preservation

Schema **1.3** adds an **optional** `staticRoutes` array to **host, router and firewall** nodes, not to Layer 2 switches. Every entry has exactly four required fields:

```json
{
  "id": "route-1",
  "destination": "203.0.113.0/24",
  "nextHop": "192.0.2.1",
  "outPort": "eth0"
}
```

IDs are explicit, unique within their owning device and preserved across Save/Open. The route owner is the canonical node containing the entry; `outPort` must identify one of that **same node's** declared ports. Destination must be a canonical IPv4 network/prefix with no host bits. `0.0.0.0/0` is an explicitly declared static default route, never inferred. Next-hop must be an explicit canonical unicast IPv4 address **within the output port's configured IPv4/CIDR subnet**, but not the port's own address or (where applicable) its network/broadcast address. Invalid/unknown fields, nonexistent ports, duplicate IDs, duplicate identical route facts, impossible next-hops, unconfigured output port IPv4, wrong node kinds, and static route data in schema 1.0–1.2 fail closed with a validation error.

Older 1.0, 1.1 and 1.2 files remain valid, and Open does not migrate them. The canonical `blank_project` and new Builder projects use 1.3; a deliberate Builder port/VLAN/route edit migrates the **in-memory** document to 1.3. The file is written only on explicit Save. Other existing port, VLAN, MAC, link, node and identity facts are preserved exactly under the established schema rules.

## Routing table and priority

The existing **one** `ConnectedRoutingTable` engine now considers two route sources on the selected host, router or firewall:

- `CONNECTED` from each enabled IPv4/CIDR interface, with `nextHop: null`.
- `STATIC` from each explicit schema 1.3 declaration whose output port is enabled and has a configured IP, with `routeId`, `nextHop`, `outInterface` and `sourceIpv4`.

Disabling the output port **does not delete** a static route from its source documentation, but it suppresses the route from the active RIB. Re-enabling the port reinstalls it. If a port's IPv4/prefix changes so that the configured next-hop is no longer on-link, validation rejects the new project rather than silently rerouting.

Longest-prefix match applies to both route types. Only the longest matching prefix qualifies. When more than one equally specific route matches, including one connected and one static route, the result is `AMBIGUOUS`: no administrative distance, metric, ECMP, route ordering or default gateway is invented. A disconnected cable does **not** remove a configured route from this RIB: the table is a configured-software view, **not** a physical connectivity check.

## Builder and API

The existing `POST /api/routing/connected` endpoint retains its name for backward compatibility and returns **both** connected and explicit static routes through the **same** engine. This is one read-only lookup, not a second forwarding implementation. Its payload and response shape are unchanged. A `MATCH` is merely a configured route selection, never a claim that the next-hop or destination is reachable.

Builder provides route creation, per-field editing and deletion in each non-switch node's inspector. Creation requires **three explicit inputs**: canonical destination prefix, next-hop IPv4 and selected output port. The client submits the entire draft to the real Python `/api/validate` endpoint before replacing its in-memory project. Invalid data leave existing documentation intact. Deleting a port referenced by static routes is explicitly blocked until its routes are removed, and converting a node with routes to a switch is rejected. Queries and edits never autosave.

**Unimplemented:** ARP resolution of next-hop for static routes, L3 packet forwarding, IP fragmentation, TTL, ICMP, route metrics and dynamic routing. Static configuration describes intended routes, not verified packet delivery. No ping result is derived from this table.

## Verification

`tests/test_static_routing.py` verifies explicit identity and canonical schema preservation, legacy versions' lossless rejection, on-link validation including /31 and /32, invalid and duplicate routes, LPM across connected/static routes, ambiguous equal prefixes, disabled ports, unplugged cables, actual HTTP and actual disk Save/Open across a full server restart with SHA-256. `tests/browser_smoke.py` checks rejection of an off-subnet next-hop, real Builder route creation/editing, read-only route lookup, disabled-port suppression and actual Save/Open across a full Chromium + server restart.
