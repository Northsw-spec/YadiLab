# Explicit VLAN access/trunk forwarding — narrow Python simulation

## Scope

`EthernetFabric(project, vlan_ports=...)` creates one VLAN-aware session using the same declared project topology and switch-forwarding queue as the original Ethernet model. Sessions without a `vlan_ports` argument retain their legacy unsegmented behavior. VLANs are never inferred from IP, MAC, port names, physical position or device type. Since schema 1.2, explicitly saved switch-port VLANs also enable the same forwarding engine; incomplete active-port configurations fail closed.

Each **active, wired switch port** requires an explicit entry:
- Access: `("sw", "p1"): {"mode": "access", "vlan": 10}`.
- Trunk: `("sw", "uplink"): {"mode": "trunk", "allowedVlans": [10, 20]}`.

Supported VLAN IDs are exact integers 1..4094. Empty, duplicated, missing, malformed and unknown port configurations are rejected. Endpoints are untagged; switch-to-endpoint connections require access mode. Switch-to-switch links require matching port modes, with identical VLAN IDs for access-to-access links. Native VLAN, tagged endpoints and VLAN translation are explicitly unsupported. A switch-to-switch active loop is still rejected (no STP).

## Forwarding contract

An untagged frame arriving on access port joins its declared VLAN. A tagged frame arriving on a trunk must have a VLAN allowed by that ingress; otherwise it is recorded as `vlanDrops: [{reason:"TRUNK_NOT_ALLOWED", ...}]` and never learned. MAC tables are keyed by (VLAN ID, source MAC), so learned addresses in VLAN 10 cannot direct traffic in VLAN 20. Broadcast and unknown unicast flood only to active egress ports admitted to the current VLAN. Access egress sends untagged; trunk egress is tagged. `transmissions` records each real declared wire, `vlanId` and `tagged` flags. `mac_table("sw", 10)` returns an independent copy of VLAN 10's learned entries.

These traces are **abstract per-link VLAN metadata**, not a byte-for-byte capture of a payload on each link. They do not prove NIC acceptance, ARP, IP connectivity or ping. No physical link or address is manufactured.

## Ethernet II 802.1Q codec

`EthernetFrame(..., vlan_id=10)` serializes a single C-tag: destination (6), source (6), TPID 0x8100 (2), TCI (2, PCP=0, DEI=0, VID=10), inner EtherType (2), opaque payload. Untagged size is 60..1514 bytes; tagged size is 60..1518 bytes, both excluding FCS. Payload is capped at 1500 bytes. Minimum tagged payload is padded to 42 bytes. `parse()` preserves padding as opaque bytes. The codec rejects malformed tags, invalid VID, nonzero PCP/DEI, QinQ, unsupported tag types and excess lengths.

Only untagged terminal NIC injection is accepted by `EthernetFabric.inject_frame`; trunk tagging is handled by forwarding metadata. The separate ARP endpoint parser also rejects tagged frames. No 802.1Q protocol stack or raw per-hop bytes are claimed.

## Non-persistence and limitations

`.yadilab` remains schema 1.1. **Explicit VLAN port configuration is persisted in schema 1.2** when entered in Builder and saved deliberately. The original `vlan_ports` session argument remains available and can fill missing configurations; contradictory session values for saved switchports are rejected. See [VLAN_PERSISTENCE.md](VLAN_PERSISTENCE.md). `ArpSession(project, vlan_ports=...)` now reuses this same VLAN-aware fabric for its ARP request and reply, using only untagged terminal frames; the trunk tagging is still represented as wire metadata, not separately serialized ARP bytes per hop. Omitting `vlan_ports` retains legacy unsegmented ARP. `requestVlanDrops` and `replyVlanDrops` report observed trunk admission failures when configured. ARP cache only updates after the reply actually reaches the requester. There is no IP routing, ICMP/ping, DHCP, DNS, STP, multicast, native VLAN, QinQ, per-hop raw frame serialization, FCS or realistic timing. Learned MAC tables do not persist.

`tests/test_vlan_arp.py` covers VLAN-isolated ARP requests/replies and negative failure cases. `tests/test_vlan.py` checks exact wire headers, access VLAN isolation, learned unicast, trunk tagging, blocked VLANs, invalid settings, failure cases and legacy regression. CI must validate these plus the existing Chromium and durable Save/Open tests.
