# Phase 36 — Integrated Golden Scenario Acceptance

Architecture: Masterprompt v1.2 VERIFIED / LOCKED.
Base: exact-byte v0.35.0 ZIP (SHA-256 `b78336e45eecaf34bc25b8e06b7512e2ad0f111337d68bce8fdaef259d06348f`). No previous Foundation module is replaced. Engine remains 0.8.0.

The checked-in Golden Scenario at `tests/fixtures/golden/proxmox_rds_opnsense.source.json` combines ten declared resources, four zones and ten declarative tests across network, virtualization management, Windows AD authentication/MFA, logging, alerting and backup restore state. It is a deterministic simulation **not** a real Proxmox/OPNsense/AD deployment.

The acceptance harness exercises the existing production compiler, Engine, Visual Validator, Scenario Certification and SafePackageIO (MemoryArchiveBackend), verifying source-to-package certification, initial misconfiguration, canonical solution, all ten exact initial/solved test expectations, completion transitions, student-solution stripping, author solution retention, source-hash determinism and preservation of both legitimate RDP and Proxmox management. It rejects manipulated canonical remediation, incorrect DNAT, overlapping layout and omitted required backup capability.

An additional isolated derived probe checks v0.35 source NAT is not regressed: combined forward-path DNAT + SNAT reaches the translated CIDR policy with explicit translated source/matched-rule evidence, while wrong or absent SNAT is rejected downstream. The certified base model is never mutated by these SNAT probes. This is bounded IPv4 reachability simulation, not stateful NAT/return-path or real packet emulation.

Verification: `npm run test:golden` (53 assertions plus three independent Draft 2020-12 schema validations) and `npm run test:foundation` (all earlier Foundation suites). Dependencies required to DEVELOP these TS suites are separate from end-user runtime.

External limits: genuine zip.js binary I/O, full React/React Flow/ELK/Ajv browser bundle and actual Parrot x86-64 acceptance remain BLOCKED here because required npm packages are unavailable and this is a Debian host. Do not label v0.36 a full VERIFIED RELEASE.
