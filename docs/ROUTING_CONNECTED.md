# Connected IPv4 route lookup — Phase 3, first bounded step

## What is implemented

The model has supported an explicit `ipv4` address/prefix on each declared port since schema 1.0. PR #15 added **read-only connected IPv4 routing tables**; PR #16 extended the same lookup engine with explicitly persisted static routes in **schema 1.3**. Schemas 1.0, 1.1 and 1.2 remain compatible without silent migration. The sole authority is the same validated canonical project. See [STATIC_ROUTES.md](STATIC_ROUTES.md).

`ConnectedRoutingTable(project, node_id)` selects one declared host, router or firewall. For each **administratively enabled** port with an explicit IPv4/CIDR, it computes a connected network with Python `ipaddress.IPv4Interface`. Unconfigured or disabled ports contribute no route. The resulting table includes the declared source IPv4, output node/port ID, computed prefix and `nextHop: null` (on-link). No default route, gateway or metric is added by guessing. Static routes and default routes appear only when the user declares them explicitly in schema 1.3.

The lookup query `lookup(destination_ipv4)` accepts **one IPv4 address**, not CIDR, IPv6 or ambiguous shorthand. It performs true mathematical *longest-prefix match* across the selected node's active interface networks. It reports:

- `MATCH`: exactly one route at maximum matching prefix length, with `selectedRoute`.
- `NO_ROUTE`: no configured connected prefix on the selected node matches.
- `AMBIGUOUS`: two or more equally specific matching routes on different interfaces. The implementation returns all equal-best `candidates` and refuses to invent a metric or selection based on list order or physical topology.

`routes` always lists the whole table, sorted by decreasing prefix length, network-address value and port identity. Returned records are detached copies, and no learning occurs. A Layer-2 switch is explicitly rejected as a route-table owner; selecting a `router` as an owner is not permission to forward transit traffic.

## Physical links are a different question

Connected-route table creation models **configured local IPv4 interfaces**, not successful Layer-1 or Layer-2 network communication. An interface may have a connected network in its route table despite having **no cable** or a disabled cable. Conversely, disabling the interface itself removes that route. An address match **never** claims that a host, network, router, or next-hop is reachable. No ARP, Ethernet frame, IP packet, ping or physical path traversal occurs on lookup.

The current implementation supports explicit static next-hop **configuration** but not route metrics, next-hop resolution, local/remote packet delivery, IPv4 forwarding, TTL or ICMP. A deliberately configured interface with a `/0` prefix is treated as a mathematical on-link route, not as an inferred default gateway. The application cannot claim functional IP connectivity from this model alone.

## HTTP and Builder contract

`POST /api/routing/connected` accepts exactly:

```json
{"project": { "...": "canonical project" }, "nodeId": "r1", "destinationIpv4": "192.0.2.25"}
```

The response contains `status`, `sourceNode`, `destinationIpv4`, `routes`, `selectedRoute` (or null), `candidates` and `meaning`. Input failures are HTTP 422 `INVALID_PROJECT`. There is no server session or storage side effect.

Builder provides a separate *Layer 3 / Route Lookup* inspector with a node selector (excludes switches), IPv4 destination input and explicit Run action. Routes of both types are returned by the same endpoint. Switches cannot own Layer 3 routes. It displays the configured table and the longest-prefix result, clearly indicating that routing-table selection is **not** packet delivery. Changing project facts invalidates the displayed result; stale in-flight HTTP replies are discarded. Queries never call Save or mutate `.yadilab`.

## Verification

`tests/test_connected_routing.py` independently exercises /8-/16-/24 overlaps, exact /32 and /31, deliberate /0, no match, equal-prefix ambiguity, disabled interfaces, unplugged/disconnected cables, per-device isolation, invalid IP and switch/unknown-node rejection, detached record copies, legacy schemas, 100 configured ports, actual loopback HTTP 200/422 and saved file SHA-256 nonmutation.

`tests/browser_smoke.py` verifies real Chromium input over direct local HTTP: matching /24 route, absent route, IPv6 rejection, a disabled interface removing its route, and unchanged saved project bytes. Full Python/JavaScript/Chromium CI is required before PR merge.
