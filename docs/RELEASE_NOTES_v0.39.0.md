# YadiLab Foundation v0.39.0 — raster package/media preflight

Incrementally based on **exact v0.38.0 ZIP**, SHA-256 `1952b029f89df91c87f2577878d68b2fd244e31554f170ea405cedc95a5e0e1a`. No reimplementation of prior phases.

- Added bounded, dependency-free PNG/JPEG/WebP structural/header validation on PackageIO read and write and browser media allocation.
- Rejects forged MIME, corrupt PNG CRCs, impossible/oversized image dimensions, malformed/truncated binary containers, WebP/PNG animation and certain unsupported subformats. This preflight **does not claim full image decoding**.
- Replaced synthetic four-byte PNG test fixtures with real small raster files; added targeted functional/adversarial validation including a correctly-hashed hostile package payload.
- Remains fail-closed for missing npm dependency tree and non-Parrot target.

Release status: **VERIFIED DEVELOPMENT CHECKPOINT only**, conditional on final ZIP byte-readback and documented checks. The actual React/React Flow/Ajv/ELK/zip.js browser bundle and Parrot acceptance are not verified.
