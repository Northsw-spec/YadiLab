# YadiLab Foundation v0.56.0

Phase 56 introduces a proof-of-possession trust activation ceremony and checkpoint-coupled rotation model for signed offline dependency snapshots.

A public producer key is now staged as `pending`, not trusted immediately. Activation requires the matching external Ed25519 private key, restrictive key-file permissions at the CLI boundary, and a cryptographically verifiable activation proof stored in the canonical trust store. The trust reader rejects manual or tampered activation state. Rotation tests cover an old/new active overlap checkpoint, old-key revocation, source-identity invalidation across trust mutations, and fresh new-key snapshot verification after revocation.

No real production trust anchor is embedded. Genuine dependency snapshot production remains blocked until an operator deliberately provisions and activates a real external producer key.
