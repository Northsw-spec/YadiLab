# Foundation v0.71.0

Phase 71 adds **Diagnostic / Observation Engine, Wave 2 — deterministic active modeled probes**.

Highlights:

- observation engine advances to `foundation.observation@0.2.0`;
- four Windows + four Linux active modeled probes: ping, TCP-port test, DNS lookup and path trace;
- active connectivity delegates to the existing deterministic Network Engine rather than creating a second routing model;
- known off-link probes validate modeled default-gateway/on-link semantics when enough address/topology evidence exists;
- host `aclDefaultAction` deny/block is enforced for active probes when no explicit ACL list exists;
- same-subnet/on-link probes remain independent of a wrong default gateway;
- DNS lookup uses only declared resolver addresses, `network.dns_server` resources, service state and modeled records;
- corrupt DNS records can succeed syntactically while returning an address with no declared resource mapping;
- path traces expose deterministic blocking points and never claim later hops were reached after a block;
- Runtime adds a separate Modeled active probes panel;
- Builder, cross-OS probes, invalid ports, malformed DNS names and scenario/state identity drift fail closed;
- active probes are read-only and cannot expose hidden fault/generator ground truth;
- no guest command, packet, socket or DNS request execution is claimed.

The Phase 70 Wave-1 command-shaped configuration observations remain available unchanged in semantics.

Classification remains **VERIFIED DEVELOPMENT CHECKPOINT, NOT VERIFIED PRODUCT RELEASE** until the external dependency/browser/Parrot gates are satisfied.
