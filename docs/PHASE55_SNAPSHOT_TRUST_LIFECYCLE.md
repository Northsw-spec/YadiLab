# Phase 55 — dependency-snapshot trust-anchor lifecycle

Phase 55 closes the operational gap left after Phase 54 introduced Ed25519 snapshot provenance. The cryptography was present, but adding a real producer trust anchor still required manual JSON editing and there was no explicit revocation lifecycle.

## Canonical trust store

`dependencies/offline-snapshot-trust.json` now uses schema `1.1.0`. Each entry has exactly:

- `keyId` — derived as `ed25519-sha256:<SHA-256(SPKI DER)>`;
- `label` — operator-readable identifier;
- `publicKeySpkiBase64` — canonical Ed25519 SPKI public-key bytes;
- `role` — exactly `dependency-snapshot-producer`;
- `status` — `active` or `revoked`.

The file itself must be in one canonical JSON representation. Unknown fields, duplicate fingerprints, mismatched declared/derived key IDs, malformed Ed25519 keys and non-canonical bytes fail closed.

## Onboarding ceremony

The lifecycle CLI is:

`node scripts/manage_offline_snapshot_trust.mjs onboard PUBLIC_KEY.pem EXPECTED_KEY_ID LABEL`

The public-key input must resolve outside the application checkout. The operator must provide the expected fingerprint separately; YadiLab derives the fingerprint from the actual Ed25519 public key and refuses the change unless both values match exactly. Private-key material is rejected by the onboarding library.

This prevents a trust anchor from being accepted merely because a file was copied into place. The expected fingerprint is intended to be verified through a separate/out-of-band operator channel before the reviewed source change is committed.

## Revocation

`node scripts/manage_offline_snapshot_trust.mjs revoke KEY_ID`

Revocation is retained in the trust store rather than deleting history. A revoked key:

- is absent from the active verification map;
- cannot sign new dependency snapshot provenance;
- causes previously signed material checked against the current checkpoint to fail explicitly with `SNAPSHOT_PROVENANCE_REVOKED_KEY`;
- cannot be silently reactivated through the onboarding path.

Multiple active keys are allowed so a reviewed overlap window can be used for future rotation.

## Current checkpoint state

The v0.55.0 release trust store intentionally still contains **zero** production keys. Phase 55 verifies the onboarding/revocation mechanism without inventing an operator identity or embedding a private/test credential. A genuine signed dependency snapshot therefore remains blocked until a real operator-controlled public key and separately verified fingerprint are deliberately provisioned.

## Trust boundary

This ceremony reduces accidental or unauthorized trust-store changes but does not create an external root of trust by itself. The expected fingerprint must come from a channel the operator independently trusts. Source checkout integrity, release archive integrity, npm lock/SRI integrity, executable toolchain attestation and Parrot/browser acceptance remain separate gates.
