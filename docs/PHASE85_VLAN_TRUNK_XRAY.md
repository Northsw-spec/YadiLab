# Phase 85 — VLAN/Trunk X-Ray (v1.1.0-dev.6 candidate)

This slice extends authoritative Phase C with deterministic VLAN access/trunk evidence. It adds only VLAN classification and tag-state decisions that the Network Engine can prove from explicit modeled switchport state. STP/BPDU forwarding/blocking remains the next separate Phase C slice.

## Truth boundary

Switchport truth is read only from explicit `resource.interfaces[].switchport` state. The UI never decides port mode, access VLAN, allowed VLANs, native VLAN, ingress classification, egress eligibility, tagged/untagged state, or tag rewrite.

The schema supports two explicit switchport forms:

```text
access: mode=access + accessVlan
trunk:  mode=trunk + allowedVlans + optional nativeVlan
```

VLAN IDs are limited to 1–4094. Structural validity is enforced by JSON Schema. Cross-field semantic consistency, including a native VLAN that is absent from `allowedVlans`, is validated by the Engine and fails closed.

The Engine emits a `VlanDecisionTrace` at a modeled switching boundary. It records the authoritative VLAN, ingress and egress interfaces, access/trunk modes, wire tag state, rewrite disposition, truth value, and per-port evidence. Rewrites are `ADD_TAG`, `REMOVE_TAG`, `PRESERVE_TAG`, `PRESERVE_UNTAGGED`, or `UNKNOWN`.

Deterministic rules include:

- untagged ingress on an access port is classified into its explicit access VLAN;
- a trunk accepts only explicitly allowed VLANs;
- a modeled native VLAN is untagged on that trunk;
- non-native trunk traffic is tagged;
- access egress for the matching VLAN is untagged;
- an access-to-trunk transition can add a tag;
- a trunk-to-access transition can remove a tag;
- adjacent modeled switches carry the Engine's VLAN/tag frame state between switching boundaries;
- a known VLAN that is explicitly disallowed on a trunk is `FALSE`, not `UNKNOWN`;
- missing, malformed or ambiguous authoritative state remains `UNKNOWN`;
- explicit link VLAN evidence that contradicts switchport truth fails closed rather than being repaired by the UI.

When explicit switchport state exists, MAC/CAM forwarding and unknown-unicast/broadcast flood eligibility use the same Engine-owned VLAN truth. A port in another VLAN is not inserted into the flood set by presentation code. Legacy scenarios with no switchport model preserve their prior behavior.

## Propagation

The exact immutable trace flows through:

```text
Network Engine
→ ReachabilityDetails.vlanDecisions
→ ActiveProbeTranscript.vlanDecisions
→ VisualJourneyModel
   → vlan.classify
   → vlan.tag / vlan.untag / vlan.forward
→ VLAN/Trunk X-Ray + Engine-projected topology edge
```

Visual Journey validates Engine traces before rendering them. Invalid resource/path relationships, port identities, switchport configuration, rewrite values, truth combinations or unmappable egress connections fail closed. The browser layer never recalculates a VLAN or substitutes another port.

## Presentation

The in-place VLAN/Trunk X-Ray contains two separate evidence tables required by the authoritative visual specification:

1. **VLAN decision table** — VLAN, ingress interface/mode, ingress wire state, egress interface/mode, egress wire state, rewrite and truth.
2. **Trunk / access port table** — every Engine-provided switchport row with mode, access VLAN, allowed VLANs, native VLAN, wire egress state and role/disposition.

The panel also exposes Engine-derived DOM contract attributes for browser acceptance, including `data-vlan-id`, `data-vlan-rewrite`, `data-vlan-ingress-mode`, `data-vlan-egress-mode`, `data-vlan-decision-table` and `data-vlan-port-table`. Missing evidence is shown as `UNKNOWN` or `NOT MODELED`; it is never guessed.

## Verification coverage

Focused local tests currently pass:

- Engine: 170 functional, 89 adversarial, plus 24 functional and 22 adversarial legacy regression assertions;
- Active Probe: 128 functional and 22 adversarial assertions;
- Visual Journey: 10 functional and 26 adversarial cases plus UI contract;
- schema: 55/55 fixture expectations and 18/18 Draft 2020-12 meta-schema checks;
- TypeScript build;
- Canvas/Layout/Browser regression suites;
- package export, certification, browser distribution build, launcher smoke and acceptance contract.

Functional VLAN cases include access/access forwarding, access mismatch, access-to-trunk tag addition, native-VLAN untagged behavior, two-switch tag preservation/removal and VLAN-aware unknown-unicast flooding. Adversarial cases include missing access VLAN, empty allowed-VLAN set, invalid native-VLAN membership, missing connected-port configuration, unsupported mode, trunk ingress without authoritative VLAN context, explicit disallowed VLAN, duplicate port connectivity, link/switchport VLAN contradiction and incomplete VLAN-aware flood evidence.

Real Parrot OS acceptance and final target Chromium/Firefox acceptance remain pending. This is a development checkpoint, not a VERIFIED PRODUCT RELEASE.

## Next authoritative work

Continue Phase C with STP/BPDU forwarding/blocking-state modeling and visualization. Do not start Phase D firewall/NAT/conntrack visualization until the remaining Phase C switching slice is complete and green.
