# ICMP Echo Request/Reply (first bounded bidirectional ping model)

## Wire format and independent validation

`ICMPEcho` implements RFC 792's two **specific** message types: request (type 8/code 0) and reply (type 0/code 0). Each message has a real 8-byte ICMP header with one’s-complement checksum (padded to even length when needed), exact 16-bit identifier, 16-bit sequence and opaque data up to 1472 bytes. Parsing rejects unknown types/codes, truncated/oversized messages, altered checksums and wrong types. Reply preserves exactly the received request's identifier, sequence and payload; no canned success or invented Echo reply.

`IPv4Datagram` now permits protocol **1** in addition to the preexisting experimental protocol **253**, retaining an actual RFC 791 header checksum and encoded TTL. The existing `IPv4Trace` accepts protocol-1 data only after independent ICMP validation, serializes IPv4 bytes inside Ethernet II 0x0800, verifies decoded Ethernet/IP, checks the actual ARP-resolved destination MAC and receiving interface address, and discloses `deliveredDatagram` only after a real modeled arrival. Protocol-253 behavior remains backward-compatible; no `ICMP` response is inferred from its `DELIVERED` status.

## Ping truth contract

`EchoExchange(project).ping(source_node, source_port, destination_ipv4, ttl, identifier, sequence)` creates **one** `IPv4Trace`, sharing the same actual `ArpSession` and `EthernetFabric` over both directions. It builds a concrete request type 8/code 0 with the user-supplied identity and the documented payload `echo-check`. The request is routed, ARP-resolved, serialized, forwarded and accepted by a configured matching destination IP/MAC on an actually reached port. If that fails, **no reply is generated**, and the result is `REQUEST_FAILED` with the underlying precise failure (e.g. `ARP_FAILED`, `NO_ROUTE`, `TTL_EXPIRED`).

If and only if the request was delivered and the returned packet bytes decode to the exact request message, a declared **host** or **router** interface models an ICMP Echo responder. A firewall does not automatically respond, since firewall policies are not modeled: `RESPONDER_UNSUPPORTED` is returned. The responder creates the real type-0 reply preserving the original identifier, sequence and data. A **second** `IPv4Trace.send` sends from the **actual receiving port**, through that device's explicitly configured reverse route, ARP, Ethernet and VLAN. The same explicitly entered TTL applies independently to each direction. There is no route or MAC guessed from forward success.

Only a reply that **actually reaches the exact initial source port**, has matching reversed source/destination IPv4 addresses and decodes with correct ICMP type, code, checksum, identifier, sequence and payload yields `REPLIED`. Failure of the return route, next-hop ARP, Ethernet/VLAN/port state or TTL results in `REPLY_FAILED`; the response includes the exact failure status and per-hop evidence. A mismatch gives `REPLY_MISMATCH`. A mere topology path, `MATCH` routing lookup, one-way `DELIVERED` or ARP success alone **never** produces a successful ping.

Each response contains `request` (full IPv4 trace), `reply` (trace or null), `icmpError` (null, or an independently traced router-error attempt), `status`, `replyMatched`, `identifier`, `sequence`, ephemeral learned MAC tables and `rttMs: null`. **No wall-clock network delay or latency is modeled**, so the interface must not display a fabricated RTT. For router-originating TTL expiry or a missing transit route, the bounded [ICMP router error](ICMP_ROUTER_ERRORS.md) implementation now *attempts* a real type-11/code-0 or type-3/code-0 response. Such an error is reported as `icmpError.status=RECEIVED` only if its datagram actually reaches the original source port and matches the quoted request. No other failures are automatically reclassified as received ICMP messages.

## HTTP / Builder

`POST /api/icmp/echo` accepts **exactly**:

```json
{
  "project": {"schemaVersion":"1.3","name":"...", "zones":[], "nodes":[], "links":[]},
  "sourceNode":"client-a", "sourcePort":"eth0", "destinationIpv4":"203.0.113.20",
  "ttl":4, "identifier":100, "sequence":1
}
```

Invalid shape, IP, ID, sequence, TTL or any undeclared source produces HTTP 422, never success. Each request creates an isolated temporary engine; it never writes a project or reuses MAC/ARP caches from a prior HTTP request. The Builder provides a dedicated ICMP Echo panel with explicit source, destination, TTL, identifier and sequence; shows request AND reply traces and the exact failure. Existing one-way IPv4, Layer 2, ARP and routing-table endpoints remain unchanged.

## What is not modeled

External/live ping traffic, real RTT, packet loss timing, ICMP errors, IPv4 options or fragmentation, dynamic routing, NAT, firewall ACL, QoS or transport/application handling. An ICMP Echo responder is modeled only on configured host/router interfaces. A reply to a router IP on a **different** interface remains conservatively unsupported under the existing strict IPv4 source-port model; no weak-host acceptance is assumed. No automatic forwarding by firewalls.

## Verification

`tests/test_icmp_echo.py` verifies known independent checksum bytes (RFC 792-style message header), odd-length payload checksums, strict negative codecs, IPv4 protocol-1/TTL/checksum roundtrip, real one- and two-router Echo Request/Reply with reverse-route tables, direct VLAN Echo with TTL 1, missing reverse route, missing reverse ARP next-hop, VLAN isolation, cable down, missing MAC, TTL expiry, nonresponding firewall, invalid input, actual loopback HTTP and unchanged disk bytes/SHA-256.

`tests/browser_smoke.py` verifies real Chromium input and actual HTTP for full two-way ICMP Echo, failed next-hop with no fabricated reply, invalid IPv4 rejection and no hidden Save.
