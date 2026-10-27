# YadiLab Foundation v0.41.0 — verified PWA precache byte integrity

Incremental development checkpoint built from exact v0.40.0 release.
Generated PWA workers now enforce actual SHA-256 hashes for release assets
both at installation and when serving cached files. Wrong content, redirects,
failed downloads and partial cache writes fail closed without purging the last
working release. No Engine/schema change; user data is never PWA cached.

Phase 41: 23 functional + 43 adversarial assertions PASS. Full Foundation
regression PASS (after independent packaged-byte verification).

Real npm-resolved React/React Flow/ELK/Ajv/zip.js browser bundle and real
Parrot OS acceptance remain EXTERNALLY BLOCKED. This is a VERIFIED
DEVELOPMENT CHECKPOINT, **not** a product VERIFIED RELEASE.
