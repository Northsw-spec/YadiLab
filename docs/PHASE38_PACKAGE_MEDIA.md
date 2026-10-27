# Phase 38 — Browser package media boundary

Baseline: exact v0.37.0 development checkpoint; Masterprompt v1.2 remains LOCKED.

- SafePackageIO continues to validate archive metadata, file limits, MIME, hashes and strict passive custom SVG. The browser image adapter performs MIME/path and SVG sanitization again as defense in depth.
- Only image/png, image/jpeg, image/webp and passive image/svg+xml become ephemeral Blob URLs, exclusively for native `<img src>` consumption. There is no inline SVG injection, HTML insertion, object/embed, remote file loading or document media rendering.
- The optional image URL host is injected only after schema, version, capability and layout checks. Headless `openRuntimePackage` retains its old behavior without a URL host. Media failure returns an explicit diagnostic and cannot return a partially initialized playable Runtime.
- Created URLs are released on package replacement, mode switch and React unmount. Partial URL creation errors revoke prior allocations. Media URLs remain separate from Engine state, scenario source, progress and packages.
- Loopback CSP permits `img-src 'self' blob:` only and keeps script loading same-origin-only. `script-src` also permits `unsafe-eval` because the pinned Ajv browser runtime compiles the shipped/imported JSON Schemas with `new Function`; remote script sources remain forbidden. `object-src 'none'` and the other policies remain restrictive. Neither `data:` nor remote images are necessary.
- Scope boundary: this adds a safe **package image gallery**, not custom-image selection as a semantic resource icon. That feature needs explicit asset references in the scenario contract. Do not claim rendered full browser or real Parrot acceptance until the genuine dependency-resolved bundle and target checks pass.

Tests: package media functional/adversarial, existing browser/package IO suites, Go CSP unit test, live launcher smoke headers, full Foundation regression and exact-byte package verification.
