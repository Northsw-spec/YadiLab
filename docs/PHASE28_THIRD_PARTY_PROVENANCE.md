# Phase 28 — Third-party License Inventory / Release Provenance

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 28 continues from exact-byte verified v0.27.0.

## Implemented

- exact `dependencies/license-inventory.policy.json` matched against the pinned browser runtime/development dependency policy;
- deterministic offline generation of `THIRD_PARTY_NOTICES.md` and `dependencies/third-party-inventory.json`;
- baseline inventory explicitly labels itself `declared-direct-baseline` and cannot claim resolved release completeness;
- dependency-resolved browser builds derive bundled third-party components from actual esbuild metafile inputs and installed package metadata;
- resolved generation fails closed if a bundled package cannot be mapped to name/version/license metadata;
- browser production build embeds resolved notices/inventory and synchronizes release evidence back to the project root;
- loopback distribution ships notices/inventory and includes both in `SHA256SUMS.txt`;
- notice/inventory tests reject version drift, missing license metadata, duplicate policy entries and false empty resolved inventories.

## Boundary

This checkpoint can generate and verify the deterministic direct-dependency baseline offline. A full `bundle-resolved` inventory still requires the dependency-resolved browser build, which is BLOCKED in this sandbox by missing package-lock/node_modules and registry access. VERIFIED RELEASE therefore remains unavailable here.
