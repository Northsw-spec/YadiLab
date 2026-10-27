# Release notes v0.35.0 — Bounded IPv4 SNAT / source-aware policy

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.
This development checkpoint extends the exact-byte-verified v0.34.0 source archive; it does not rebuild Foundation.

New: separate required/optional SNAT policy and ordered declaration on transit resources; proven, forward-path-only IPv4 source rewrite; source CIDR matching at upstream/downstream ACL and firewall checkpoints; composable SNAT + existing DNAT; explainable translated source and matched SNAT rule. Invalid source identity, malformed/unsupported rules, NAT66 and unsupported source-port translation fail closed. Compiler adds SNAT static parameter/selector diagnostics. Engine version advances to 0.8.0 with aligned semantic minimum-version tests.

Verification: entire existing Foundation regression; Engine 110 functional + 60 adversarial; Compiler 61 functional + 51 adversarial; all prior PackageIO/CLI/canvas/layout/browser/persistence/launcher/acceptance-contract tests remain green. This is a VERIFIED DEVELOPMENT CHECKPOINT, **not** a Parrot VERIFIED RELEASE. Dependency-resolved browserbuild and real Parrot x86-64 acceptance remain external gates.
