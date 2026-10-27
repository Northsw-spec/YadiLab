# Release notes — Foundation v0.64.0

Phase 64 implements deterministic **Enterprise Baseline → Scenario/Topology Projection**.

Key additions:

- schema-defined enterprise topology projection report;
- optional `enterpriseOrigin` binding in scenario-source and normalized scenario;
- deterministic site/zone/resource projection from the normalized Enterprise Model;
- conservative active-fact projection (`KNOWN` / `INFERRED` only);
- preserved uncertainty/provenance metadata on projected resources and relationships;
- recognized interface/address/MAC, routes, services, firewall/NAT property projection;
- supported enterprise relationship → ordinary scenario connection projection;
- unsupported/unresolved relationships reported and preserved rather than fabricated;
- ordinary scenario Compiler integration;
- ordinary Layout Graph integration;
- Import Helper action to replace the current Builder with the imported topology and run compile + ELK layout;
- focused functional/adversarial projection regression.

The projection intentionally does not infer missing network links, gateways, VLAN membership or other facts from convention. Incomplete enterprise input may therefore produce an incomplete but truthful topology.
