# Phase 81 — Real Device Visuals (v1.1.0-dev.2)

Status: DEVELOPMENT CHECKPOINT CANDIDATE — not a verified product release.

This checkpoint implements Phase B of the authoritative Living Topology & Visual Simulation Specification.

Implemented vertical slice:

- deterministic presentation descriptors map declared resource types to router, switch, firewall, server, client, hypervisor, actor or explicit generic families;
- CSS-native chassis silhouettes replace letter-only cards for recognized device families without modifying the locked v1.0.0 built-in asset bytes;
- declared interfaces render as visible port anchors and compact port rows with addresses when present;
- missing interface modeling is shown explicitly as `PORTS NOT MODELED`;
- device LEDs, interface LEDs and link LEDs activate only from the current deterministic Visual Journey frame;
- semantic links have distinct network, management, trust, authentication, dependency and data-flow styles;
- VLAN and direction labels appear only when explicitly declared in connection properties;
- an explicit `enabled: false` renders a disabled link; missing or non-boolean values do not fabricate link-down truth;
- zone headers reserve their visual band and use stable type accents;
- reduced-motion keeps all Phase B state visible without pulsing animation.

Truth boundary:

The Phase B layer classifies presentation from schema-defined resource and connection types. It does not decide reachability, path, route, firewall, NAT, port operational state or device activity. Activity comes only from the existing Engine-backed Visual Journey model. Interfaces without operational state remain `DECLARED`; the UI does not label them up or down.

Local checkpoint verification must include:

- canvas TypeScript compile;
- Phase B functional and adversarial suites;
- existing canvas and Phase A Visual Journey regression;
- full Foundation regression where the local dependency/toolchain boundary permits it;
- JavaScript syntax check.

Still required before any verified v1.1.0 product claim:

- dependency-resolved browser build from the signed offline snapshot;
- real Chromium and Firefox DOM/screenshot acceptance;
- Parrot OS x86-64 acceptance;
- complete release signing and reproducibility gates.
