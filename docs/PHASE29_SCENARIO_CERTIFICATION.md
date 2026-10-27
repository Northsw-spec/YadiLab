# Phase 29 — Scenario Certification Pipeline

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

## Purpose

Phase 29 closes the Scenario Completeness gap between “package can be written/read” and “scenario has been proven ready for verified delivery.”

A Builder package export may report `selfVerified: true` only after the reusable headless certification pipeline passes every applicable Foundation gate.

## Certification gates

1. Canonical/reference solution exists.
2. Initial-state → canonical operations → solved-state regression passes.
3. Layout belongs to the compiled scenario and preserves every semantic node, parent hierarchy, and valid geometry.
4. Current Engine version and exact capability-pack locks can initialize/evaluate the scenario.
5. PackageIO builds the requested student/author distribution.
6. Safe PackageIO readback preserves normalized scenario, layout, distribution, and solution policy exactly.
7. The read-back scenario independently passes Runtime compatibility again.

The certificate records five grouped PASS stages: regression, layout, runtime, package-write, and package-readback.

## Distribution rules

- Student certification rejects any canonical/reference solution leakage.
- Author certification requires and verifies `solution.json`.
- Package readback drift in scenario/layout/distribution/solution is a hard failure.
- Missing or stale layout is a hard failure.
- A broken canonical solution is rejected before PackageIO write.

## Builder contract change

`buildBuilderPackageExport()` now delegates package construction and verification to `certifyCompiledScenario()`. The previous narrow meaning of `selfVerified` (write/readback only) no longer applies.

## Verification scope

The certification semantics are fully regression-tested through the in-memory SafePackageIO backend. Real zip.js byte execution and full dependency-resolved browser rendering remain separate external gates in this sandbox.
