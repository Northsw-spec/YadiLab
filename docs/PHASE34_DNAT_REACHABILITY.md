# Phase 34 — DNAT / Port-forward-aware NetworkEngine

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 34 adds bounded destination-NAT semantics to deterministic reachability without becoming a packet/NAT appliance emulator.

A transit resource may declare `properties.natRules` and optional `natPolicy` (`optional` or `required`). Supported DNAT fields include `id`, `type: dnat`, source/destination selectors, protocol, `externalPort`/`port`, `translatedDestination`, `translatedPort`, enabled, and action. Matching DNAT may translate the effective destination listener port.

`natPolicy: required` proves a block when no matching DNAT rule exists. Invalid translated ports, unsupported NAT policy/actions, and malformed rule data yield `UNKNOWN`. Explicit deny/block actions yield `FALSE`.

Reachability details expose `translatedPort` when destination-port translation occurred. Firewall/ACL policy continues to evaluate the original semantic flow; listener evaluation uses the translated destination port.

Engine version advances to **0.7.0**. Network reachability/segmentation/route-test/port-scan and virtualization management-exposure semantics require 0.7.0.

SNAT/source-address rewriting is not claimed by this phase because Foundation queries identify semantic resources rather than packet source addresses.
