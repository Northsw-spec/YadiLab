# YadiLab Foundation v0.54.0

Phase 54 adds cryptographically signed provenance to the sealed offline dependency snapshot workflow. Snapshot schema `1.2.0` requires `snapshot-provenance.json` plus an Ed25519 detached signature bound to the exact manifest bytes, source-checkout identity, target and producer tool identity. Verification uses only source-controlled trusted public keys; private keys remain external and are forbidden inside the YadiLab checkout.

The release trust store intentionally contains no automatically trusted producer/test key. A genuine signed dependency snapshot therefore remains an explicit external/provisioning gate rather than being simulated with a repository-embedded secret.

Release hygiene also corrects the source-identity generated-file exclusion to match the Parrot harness's actual `parrot-acceptance-report.txt` output, preventing an acceptance run from changing the source-checkout identity.

This remains a VERIFIED DEVELOPMENT CHECKPOINT, not a product release. Genuine npm dependency bytes, dependency-resolved Chromium execution and Parrot OS x86-64 target acceptance remain external gates.
