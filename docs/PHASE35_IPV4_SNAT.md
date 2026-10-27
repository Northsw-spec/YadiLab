# Phase 35 — Bounded IPv4 SNAT in the deterministic NetworkEngine

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.
Parent checkpoint: exact-byte-verified Foundation v0.34.0.

This phase extends the existing DNAT/route/VLAN/ACL engine rather than replacing it. A transit resource can declare `properties.snatPolicy` (`optional` or `required`) and `properties.natRules` entries with `type: "snat"`, source/destination selector, protocol, optional listener port, literal `translatedSource` IPv4, and optional explicit allow/translate/deny/block action. Rule ordering is deterministic; all enabled SNAT records are preflight-validated, so an early valid rule cannot hide a malformed later rule. Required SNAT with no matching rule is FALSE; malformed or insufficient identity evidence is UNKNOWN.

An eligible forward-path SNAT rule requires an unambiguous, declared original IPv4 address on the source resource. Only explicit IP/CIDR source selectors see the rewritten address downstream of the translating node. Ordinary resource-ID/zone selectors retain logical identity; the translating node's own policy sees the pre-SNAT address. Existing DNAT can compose with SNAT on the same declared path. Results expose `translatedSource` and `matchedSnatRule` for explainability; both translated source and translated destination-port data are retained when they coexist.

Scope boundaries: this is **declared forward-path security-reachability simulation only**, not a packet stack, conntrack implementation, source-port/PAT allocator, dynamic address pool, stateful return path, NAT66, hairpin NAT, protocol ALG, or production firewall emulator. The compiler statically rejects malformed author-supplied SNAT and the Engine also fails closed on malformed mutated runtime state. Old packages with lower minimum Engine versions retain the existing declared compatibility gate; mutable save-state files remain exact Engine-version bound and require explicit compatible migration rather than silent reinterpretation.

Engine version: 0.8.0. Newly compiled network reachability/segmentation/route-test/port-scan and virtualization management-exposure scenarios require Engine 0.8.0.
