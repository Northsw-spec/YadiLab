# Phase 76 — Typed Remediation Actions / Safety Constraints

Foundation v0.76.0 replaces the Runtime learner-facing raw remediation path/JSON editor with a bounded catalog of typed Windows/Linux remediation actions. The underlying Engine still receives the same deterministic one-step operations introduced in Phase 75.

## Boundary

Typed remediation is still modeled Runtime state editing. It does not execute PowerShell, shell commands, APIs, guest agents or live-network actions. It does not read `canonicalSolution`, `faultOrigin`, hidden fault truth, generator ground truth or instructor solution material.

The typed action boundary is `LEARNER_ACTION_NO_SOLUTION`.

## Typed action catalog

`foundation.typed_remediation@0.1.0` exposes only actions valid for the selected modeled Windows/Linux resource:

- Change default gateway
- Change DNS servers
- Change firewall default policy
- Set interface addresses
- Enable or disable a modeled service
- Change a modeled service listener port
- Change Windows network profile (Windows only)

Non-Windows/Linux resources expose no Phase-76 typed action catalog.

## Safety constraints

The resolver validates exact parameter names and values before producing an Engine operation:

- gateway: valid IPv4 address;
- DNS: 1–4 unique IPv4 addresses;
- firewall default action: `allow` or `deny`;
- interface: existing interface index plus 1–8 unique IPv4 CIDR addresses;
- service state: supported service already modeled on the selected OS resource plus boolean state;
- service port: supported service with an already modeled port and integer 1–65535;
- Windows network profile: `public`, `private` or `domain` and Windows target only.

Extra parameters fail closed. Unsupported cross-OS services/actions fail closed. A typed action cannot introduce arbitrary resource paths or identity mutations.

## Exact operation mapping

Every accepted typed request resolves to one explicit existing Engine operation such as:

- `change_default_gateway` -> `set properties.defaultGateway`
- `change_dns_servers` -> `set properties.dnsServers`
- `set_firewall_default_action` -> `set properties.aclDefaultAction`
- `set_interface_addresses` -> `set interfaces.<index>.addresses`
- service actions -> the exact modeled `properties.<service>.enabled|port`
- Windows profile -> `set properties.networkProfile`

The Phase-75 raw remediation validator remains an internal compatibility/safety layer. Runtime UI no longer offers a free path/JSON editor.

## Preview / commit binding

Typed preview first resolves the request to its exact Engine operation, then uses the Phase-75 non-destructive preview. A second typed preview token binds the base preview token plus exact typed action audit metadata. Changing target, action, parameters, Runtime revision or notebook identity invalidates commit.

Commit remains exactly one normal undoable Runtime history operation.

## Notebook contract

New troubleshooting notebooks use schema 0.3.0. Legacy 0.1.0 and 0.2.0 notebooks remain accepted.

A typed remediation entry may include immutable `typedAction` audit metadata:

- typed engine ID/version/boundary;
- action ID and learner-facing label;
- target resource ID;
- exact typed parameters.

Notebook verification rejects typed metadata that does not semantically match the recorded Engine operation. Notebook identity covers the typed action metadata.

## Explicit non-goals

v0.76.0 does not add automatic remediation recommendations, canonical-solution lookup/execution, guest command execution, live connectors, real endpoint/network mutation, hidden grading/scoring or AI/ML/LLM assessment.
