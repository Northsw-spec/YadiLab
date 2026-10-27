# Phase 54 — signed dependency-snapshot provenance

Phase 54 closes the authenticity gap left deliberately open by the earlier SHA-256 transport integrity work.

A transport SHA-256 sidecar can detect accidental or uncoordinated byte changes, but it cannot identify who produced the snapshot: an attacker able to replace the ZIP can also replace its SHA-256 sidecar. Phase 54 therefore adds a separate Ed25519 provenance gate.

## Trust model

YadiLab contains only a source-controlled public-key trust store:

- `dependencies/offline-snapshot-trust.json`

Private signing keys are external operator material and must never be stored inside the YadiLab checkout or dependency transport. The producer and signing CLI refuse a private-key path inside the source checkout. Key files must be mode `0400` or `0600`.

The v0.54.0 development checkpoint intentionally ships with an empty trusted-key list. This proves the mechanism without embedding a test credential or silently inventing a production identity. Genuine snapshot production remains BLOCKED until an operator-controlled Ed25519 public key is deliberately added to the source-controlled trust store in a later reviewed checkpoint.

## Signed evidence

After `snapshot-manifest.json` has been produced, the trusted online producer writes:

- `snapshot-provenance.json`
- `snapshot-provenance.sig`

The provenance document binds:

- exact SHA-256 of the raw `snapshot-manifest.json` bytes;
- the source-checkout identity already sealed in the manifest;
- Linux x86-64 target identity;
- exact producer Node and npm versions;
- a public-key-derived key ID of the form `ed25519-sha256:<SPKI-SHA256>`.

The detached signature is Ed25519 over the exact provenance JSON bytes. The verifier derives the trusted key ID from the pinned SPKI public key; a trust-store entry cannot declare an unrelated key ID.

## Fail-closed ordering

For a sealed transport, import now requires all three control files:

1. `snapshot-manifest.json`
2. `snapshot-provenance.json`
3. `snapshot-provenance.sig`

Safe ZIP structure and the adjacent transport SHA-256 sidecar are checked first. After extraction, source/snapshot integrity and Ed25519 provenance are verified before consumer-environment checks, npm cache verification, or `npm ci --offline`.

A canonical ZIP that has been modified and given a freshly recomputed SHA-256 sidecar still fails if its provenance/signature does not verify against the source-controlled trust store.

## Snapshot schema

Phase 54 bumps the offline dependency snapshot schema from `1.1.0` to `1.2.0`. Signed provenance is mandatory for production verification under this schema.

Tests may call the library with provenance disabled only to preserve narrow unit coverage of older metadata/closure functions. Production CLI, sealing, import and install paths use mandatory provenance verification.

## Scope

This is provenance/authenticity of the YadiLab dependency snapshot producer key. It does not by itself prove npm publisher identity, package author intent, or compromise-free upstream registries. Existing npm lock integrity, exact dependency policy, native esbuild closure, executable toolchain attestation, source identity, producer/consumer coherence and transactional install gates remain independently mandatory.
