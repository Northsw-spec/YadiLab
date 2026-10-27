# Phase 39 — bounded raster header/container validation

Architecture: Masterprompt v1.2 VERIFIED / LOCKED. Exact base: v0.38.0.

Custom raster `assets/` files now have an explicit fail-closed preflight in the existing safe PackageIO path and, defensively, again before browser Blob URL allocation. Trust level remains untrusted. This does not change Engine logic, scenario schema, canonical solution, model-derived asset locks, or the launcher CSP.

## Deterministic checks

- PNG: exact signature; first IHDR; validated dimensions/bit depth; bounded chunk structure; CRC32 for each chunk; image data + terminal IEND with no trailing bytes; animated PNG and unknown critical chunks rejected.
- JPEG: SOI/EOI framing, supported baseline/extended/progressive SOF with nonzero bounded dimensions, ordered frame-before-scan headers, bounded segment lengths. Entropy stream validity is delegated to the browser decoder.
- WebP: exact RIFF/WEBP framing/length, VP8/VP8L/VP8X header validation, bounded dimensions, one image payload, and rejection of animation. Entropy stream validity is delegated to the browser decoder.
- Image size bounds: max 8192 px per side, max 16,777,216 declared pixels. Existing PackageIO compressed/decompressed byte limits remain in force.

**Not a full decoder or guarantee of pixel-level validity**: this cannot guarantee a raster is visually renderable. The browser performs native image decoding. The preflight prevents common forged formats, oversized header dimensions, corrupt containers, and misuse of the declared image MIME without importing a new third-party decoder or making runtime internet calls.

## Security invariant

All raster asset bytes must pass the same preflight **both before package hash/write and after hash/read**, including attacker-built packages with otherwise correct manifest hashes. Browser media repeats the check before ephemeral Blob allocation; partial allocations revoke all earlier URLs on any failure. Browser uses native `<img>` only; no inline untrusted SVG/HTML. No file-path changes are inferred from media headers.

Fixtures are real tiny locally generated PNG/JPEG/WebP binaries committed to the project. Tests include valid multi-format roundtrips, MIME-content spoofing, CRC tampering, truncation, oversize dimensions, RIFF mismatch, and a malicious correctly-hashed ZIP read path.

The actual npm dependency-resolved browser bundle and real Parrot x86-64 acceptance remain separately BLOCKED. No new production dependency is introduced.
