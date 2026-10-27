# YadiLab Foundation v0.38.0 — package image media boundary

Direct incremental continuation from exact v0.37.0; no changes to Engine 0.8.0, scenario schema, compiler, or PackageIO archive semantics.

Adds a safe browser-only package-image gallery for validated custom SVG/raster assets, strict MIME/path/SVG defense-in-depth, ephemeral Blob URL creation/revocation and rollback, plus explicit package media failure diagnostics. The loopback launcher Content Security Policy now permits local/Blob images but not data/remote/object-based rendering. All image data remains separate from the deterministic model and progress.

The complete pinned npm installation and real React/React Flow/ELK/Ajv/zip.js browser rendering remain BLOCKED in this DNS-restricted Debian environment. The Phase 38 browser integration is source/TypeScript/component-contract tested, not a verified interactive Chromium release. Parrot x86-64 acceptance remains required.

Status: VERIFIED DEVELOPMENT CHECKPOINT only, after successful full and packaged-byte regression.
