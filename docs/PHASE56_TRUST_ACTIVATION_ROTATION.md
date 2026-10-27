# Phase 56 — trust activation and rotation ceremony

Phase 55 made public-key onboarding and revocation deterministic, but a newly onboarded public key became active immediately. A fingerprint check proves that the expected public key was selected; it does **not** prove that the operator currently controls the corresponding private key. Phase 56 closes that gap.

## Trust-store schema 1.2.0

Every trust entry now contains `activationProof` in addition to the key metadata and lifecycle state. Lifecycle states are:

- `pending` — public key and independently confirmed fingerprint are recorded, but the key is not trusted to sign dependency snapshots;
- `active` — the matching private key has produced a valid proof-of-possession signature;
- `revoked` — the key remains recorded but cannot verify or sign new snapshots.

A pending entry must have `activationProof: null`. An active entry must contain a valid Ed25519 activation proof. A revoked entry retains its proof if it was previously active; a never-activated pending key may be revoked with a null proof.

## Staging

```text
node scripts/manage_offline_snapshot_trust.mjs stage PUBLIC_KEY.pem EXPECTED_KEY_ID LABEL
```

`onboard` remains an alias for `stage`, but no longer means "trusted immediately". The public-key input must resolve outside the source checkout and the supplied expected fingerprint must exactly match the SPKI-derived Ed25519 key ID.

## Proof-of-possession activation

```text
node scripts/manage_offline_snapshot_trust.mjs activate KEY_ID PRIVATE_KEY.pem
```

The private key must resolve outside the source checkout and its file mode must be `0400` or `0600`. YadiLab derives the public key from the private key, requires it to match the staged key, signs a canonical activation payload, stores only the resulting public proof, and then re-reads/verifies the canonical trust store before reporting success.

The activation payload binds the key ID, label, canonical SPKI public key and producer role. The private key itself is never written to the checkout or release artifact.

## Fail-closed behavior

The trust reader rejects:

- an `active` entry with no activation proof;
- an activation proof signed by another key;
- tampered proof bytes;
- unknown activation-proof fields or malformed signatures;
- activation with a non-matching private key;
- snapshot signing while a key is only pending;
- activation or staging of a revoked key.

## Rotation

Rotation is intentionally coupled to source-checkout identity because the trust store is source-controlled and identity-covered.

1. Existing producer key A is active.
2. Stage key B and verify its fingerprint out of band.
3. Activate B with B's external private key. A and B are both active in the overlap checkpoint.
4. Generate/verify a dependency snapshot for that overlap checkpoint if needed.
5. In the next reviewed checkpoint, revoke A.
6. Generate a fresh dependency snapshot signed by B for the new source identity.

Snapshots from before a trust-store mutation are expected to fail source-checkout identity verification. This is deliberate: trust-policy changes are part of the source state, not external mutable policy.

## Current checkpoint state

The release trust store remains empty. Phase 56 verifies the staged/active/revoked mechanism and rotation behavior with ephemeral test keys only. No production key or private credential is invented or embedded.
