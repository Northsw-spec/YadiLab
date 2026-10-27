# YadiLab Foundation v0.55.0

Phase 55 adds a deterministic trust-anchor lifecycle around the Phase 54 Ed25519 snapshot provenance mechanism. The trust store moves to schema `1.1.0`, requires canonical entries with explicit producer role and `active`/`revoked` status, and rejects non-canonical or ambiguous trust metadata.

A new fail-closed lifecycle CLI onboards only an external Ed25519 public key whose derived key ID exactly matches a separately supplied expected fingerprint. Revocation is persistent, cannot be silently undone by re-onboarding, blocks future signing, and causes verification under the current checkpoint to identify the key as revoked.

No production trust anchor or private key is embedded in this checkpoint. Genuine dependency-snapshot production therefore remains blocked until an operator deliberately provisions a real public trust anchor.
