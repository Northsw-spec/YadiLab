# dev23 — Synchronized Event X-Ray

Version: `1.1.0-dev.23`
Baseline: sealed `1.1.0-dev.22`

## Purpose

dev23 makes X-Ray an explicit, always-visible view of the **currently selected canonical playback event**. It does not create a second truth model. The X-Ray frame is a deterministic projection of the same Engine-owned event consumed by Packet Journey.

## Contract

Every Journey cursor position has exactly one `VisualJourneyXRayFrame` with:

- schema version `1.0.0`;
- source `ENGINE_EVENT_PROJECTION`;
- exact event ID, sequence and event count;
- event kind and decision family;
- Engine truth and `MODELED` provenance;
- current/source/target resource identity when modeled;
- active connection/projected connections when modeled;
- protocol/port when modeled;
- evidence references and exact event summary;
- terminal outcome only when the canonical event owns that outcome.

The X-Ray cursor is the Packet Journey cursor. `Play`, `Pause`, `Step`, backward step, scrub and `Replay` therefore change Packet Journey and X-Ray together; the UI may not maintain an independent X-Ray cursor.

## Decision families

The synchronized frame classifies the event only by its canonical event kind:

- `FLOW`
- `ROUTING`
- `ARP_ND`
- `MAC_CAM`
- `VLAN`
- `STP_BPDU`
- `NAT_PAT`
- `CONNTRACK`
- `FIREWALL_ACL`
- `HOST_STACK`
- `LISTENER_SERVICE`
- `TCP_STATE`
- `UDP_ICMP`
- `DNS`
- `DHCP`

This is presentation classification, not recomputation of Engine truth.

## Host-side evidence as timeline events

Previously Host Stack, listener/service and TCP microscope data could remain visible as Journey-wide panels even when the current playback event represented another layer. dev23 emits explicit canonical events for those Engine traces:

- `hoststack.decision`
- `listener.service`
- `tcp.state`

Their detailed X-Ray panels are shown only when the matching event is current. DNS, DHCP and UDP/ICMP X-Ray are likewise bound to their current terminal event.

## Fail-closed behavior

The synchronized X-Ray never:

- invents a route, neighbor, MAC, VLAN, STP, firewall, NAT or conntrack decision;
- infers a host process/socket/service state;
- invents return traffic;
- converts overall Journey data into a decision that does not belong to the current event;
- advances independently of Packet Journey.

If the current event is only `flow.segment`, its decision family is `FLOW`; later or earlier decision data is not displayed as if it belonged to that hop.
