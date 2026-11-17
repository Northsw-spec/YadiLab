# Process-local Layer 2 simulation sessions

## Scope and existing behavior

A simulation session is an explicit, temporary **Python server-memory** object holding exactly one existing `ArpSession` and its underlying `EthernetFabric`. Unlike the pre-existing one-shot `POST /api/diagnostics/arp` endpoint (which stays unchanged), a live session retains actually learned switch MAC tables and per-interface ARP caches across multiple requested operations. It never invents a cable, VLAN, MAC, destination, route or packet result.

Builder provides a separate Stepwise Layer 2 panel with Start, Send ARP, Send Ethernet, Reset Tables and Stop actions. Nothing runs automatically. Select a real non-switch source interface with an explicit bound MAC. To resolve ARP, that interface also needs configured IPv4/CIDR. VLANs come exclusively from persisted schema 1.2 switch-port configuration, with the same access/trunk semantics and strict missing-configuration rejection as before.

A real Ethernet send constructs a strictly validated **opaque Ethernet II** frame, with an explicitly configured source MAC, a user-entered destination MAC and EtherType **0x88B5** with empty payload. It uses `EthernetFabric.inject_frame`; broadcast/unknown unicast and known-unicast switching and VLAN drops are observable. A destination port arrival is **not** proof a NIC accepted or decoded the frame. No IPv4 or ping simulation is implied.

## HTTP contract (loopback server only)

All endpoints accept only POST JSON, with exact required keys:

| Endpoint | JSON request | Behavior |
|---|---|---|
| `/api/simulation/start` | `{"project": <canonical project>}` | Validates the entire project and creates a new isolated session; returns opaque `sessionId`, `operationCount: 0`, `macTables: []`, `ephemeral: true` |
| `/api/simulation/run` | `{"sessionId": "...", "project": <same project>, "operation": "arp" or "ethernet", "sourceNode":"...", "sourcePort":"...", "target":"..."}` | ARP uses target IPv4, Ethernet uses target MAC; returns actual `result`, source-port `arpTable`, switch `macTables`, `operationCount` and `ephemeral: true` |
| `/api/simulation/reset` | `{"sessionId":"...", "project": <same project>}` | Recreates the underlying engine from the declared canonical project, clears all ARP/MAC learning and resets count to 0 |
| `/api/simulation/stop` | `{"sessionId":"..."}` | Deletes the process-local session; later use of the token is rejected |

The registry validates and canonically hashes the current project **on each operation/reset**; if any declared source fact changes (including ports, links, VLAN, IP or MAC), operations reject with `INVALID_PROJECT`. It does not quietly create a fresh session or silently continue with stale state. Changing a project in Builder invalidates the UI session and requests release; manual Start is required again. A project load, new/import or position edit likewise invalidates it. UI output is tied to the in-flight project snapshot; stale asynchronous results are not displayed.

Every session uses a server-generated opaque identifier. Sessions are isolated from one another, with serialized state transitions protected by a lock. The registry is bounded to **16 active sessions per server process** and **256 successful operations per session**; capacity or operation exhaustion is explicitly rejected. Stop or Reset is required to free capacity/operation budget. A local server restart loses all sessions, IDs and caches. This is *not* a persistent multiuser/session service or a background emulator.

The prior `/api/diagnostics/arp` remains a separate, one-shot diagnostic route. It never borrows MAC or ARP state from a live session.

## Source-document boundary and truth claims

The source `.yadilab` project schema remains **1.2** and is never extended with learned protocol state, sessions, tokens or diagnostic traces. Start/Run/Reset/Stop call no project file writer. Only explicit Save performs existing atomic writes with SHA-256 conflict control. Ethernet frames do not simulate IPv4, TTL, ICMP or ping. No ARP aging, STP, native VLAN, NIC acceptance, custom payload injection or persistent sessions.

Returned `RESOLVED` is a modeled ARP exchange, `CACHE_HIT` a real previous successful entry with **no new request/reply frames**, `NO_REPLY` a missing ARP response in the modeled broadcast domain, and Ethernet `SIMULATED` only that the frame was forwarded according to declared ports/links and learned entries. No status is a generic proof of IP reachability.

## Verification

`tests/test_simulation_sessions.py` exercises real HTTP, cache continuity, MAC learning across ARP and Ethernet, VLAN isolation/drops, reset, session isolation, project mismatch, malformed request shapes, capacity/operation limits, stop and server restart without session persistence; existing disk bytes and hashes remain unchanged.

`tests/browser_smoke.py` drives the actual Chromium UI over local HTTP: VLAN-blocked ARP in a newly started session, topology change invalidating that session, successful ARP, repeat `CACHE_HIT` without transmissions, Ethernet send, Reset and Stop, with saved project bytes checked for unchanged SHA-256.
