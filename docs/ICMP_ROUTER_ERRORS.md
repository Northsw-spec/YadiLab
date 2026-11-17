# ICMP router-originated errors — bounded RFC 792 model (PR #19)

## Exact implemented messages

**Only** these two router-originated ICMPv4 errors are supported:

- Time Exceeded, **Type 11 / Code 0**, when a datagram reaches a transit router with TTL=1 and cannot be forwarded.
- Destination Unreachable / Network Unreachable, **Type 3 / Code 0**, when a datagram has actually reached a transit router and its active configured IPv4 table reports `NO_ROUTE`.

This explicitly excludes ICMP Echo Reply, Destination Unreachable host/port/network other codes, Fragmentation Needed, and Time Exceeded reassembly timeout. It does not automatically classify ARP_FAILED, VLAN drops, unknown/ambiguous routes, source-host NO_ROUTE or an unsuccessful Echo Reply as delivered network errors.

## RFC 792 wire contract

`network_core/icmp_errors.py` accepts only Type 11/Code 0 or Type 3/Code 0 and emits **36 exact bytes**: type (8 bits), code (8 bits), one's-complement checksum (16 bits), four zero/unused bytes, and **exactly the original as-received IPv4 20-byte header + first eight datagram data bytes**. The original IPv4 quoted header, fragment fields, protocol and checksum are checked before use, as is the ICMP error's checksum; unsupported messages and modified wire bytes fail closed. For an ICMP Echo request, the first eight quoted data bytes are its actual ICMP type/code/checksum/identifier/sequence. There is no forged address or arbitrary quote.

The `IPv4Trace` engine records a **`routerErrorCandidate`** only for router-observed TTL expiry or transit `NO_ROUTE`. It quotes the header from **router ingress, before TTL decrement**. This context is evidence, not proof that an ICMP error has been sent. A bare one-way `/api/ipv4/trace` query does **not** transmit an ICMP error as a side effect.

## Echo failure and actual return path

`EchoExchange` only attempts one of these errors for an actually failed **ICMP Echo Request** with router provenance. It serializes and parses the error, verifies the original IPv4 source/destination, then uses **the same existing `IPv4Trace` instance**, `ArpSession` and `EthernetFabric` to send the error datagram with IPv4 protocol 1. Its source is the **explicit IPv4 on the observed ingress router port** (never an inferred interface). This bounded choice requires the return route to use that same ingress port. If a more-specific reverse route selects another interface, `SOURCE_INTERFACE_MISMATCH` leads to `NOT_DELIVERED` rather than a fabricated packet.

Successful receipt requires real ARP resolution and Ethernet delivery over the declared links/VLANs; the IP destination and receiving port must exactly equal the original sender, and the received error must parse with a valid checksum, error type/code, and **identical original quoted 28 bytes**. The response `icmpError` object includes `status` (`RECEIVED`, `NOT_DELIVERED`, or `MISMATCH`), `type`, `code`, source router/port, original IP identity, and full `trace` with real route/ARP/Ethernet transmissions. `icmpError` is **null** unless a router actually triggered one of the two supported errors. A failed Echo Request retains the historical top-level `REQUEST_FAILED` status even when its router-error datagram is received; an ICMP error is not an Echo Reply or ping success. No RTT is invented.

The error response itself is *never* used to generate another ICMP router-error response; the codec rejects quoting ICMP error messages. This bounds automatic generation and avoids recursive error storms. ICMP Time Exceeded messages during a reply attempt (or a router-error return itself) are not generated in this scope.

## API, UI, no hidden persistence

The existing `POST /api/icmp/echo` contract remains unchanged: exact `project, sourceNode, sourcePort, destinationIpv4, ttl, identifier, sequence`. Responses now add `icmpError` and the underlying request trace adds `routerErrorCandidate` (or null). The Builder's Ping panel displays the distinct error kind, numeric type/code, router interface, quoted original destination, return IPv4/ARP/Ethernet trace and whether receipt was verified. No new schema (still 1.3), disk mutation, cache inheritance across independent requests or external packet transmission. These are modeled deterministic network packets, not real internet ICMP.

Tested separately: exact RFC 792 bytes/checksum, original-quote integrity, malformed messages, type 11 and type 3 returned over real simulated cables/VLAN, wrong reverse interface, source-only NO_ROUTE, ARP/VLAN failure with no error packet, real loopback HTTP, real Chromium selection of explicit router/next-hop and repeated SHA-256 byte integrity. The established Save/Open browser regression stays active.
