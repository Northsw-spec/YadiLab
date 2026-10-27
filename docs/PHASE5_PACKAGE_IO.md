# Phase 5 — PackageIO, integrity and distribution safety

Version: 0.5.0

Phase 5 extends the verified v0.4.0 Foundation. It does not replace the compiler, Engine, or canonical regression framework.

## PackageIO boundary

ZIP/container handling is isolated behind a generic `ArchiveBackend` and `SafePackageIO` boundary. Core scenario semantics do not import or depend on zip.js APIs.

The production adapter is `ZipJsArchiveBackend`, which dynamically loads the declared `@zip.js/zip.js` dependency. This keeps the dependency behind PackageIO and avoids coupling Compiler/Engine code to ZIP implementation details.

## Distribution builds

`SafePackageIO.write()` supports:

- `student` distribution;
- `author` distribution.

Both distributions serialize `scenario.json` without an embedded `canonicalSolution`.

Author build:

```text
manifest.json
scenario.json
solution.json   (when a canonical solution exists)
layout.json     (optional)
assets/...      (optional)
docs/...        (optional)
```

Student build omits `solution.json` completely.

The student solution is not hidden, obfuscated, or renamed; it is absent.

## Integrity model

`manifest.json` records for every packaged data file:

- path;
- byte size;
- SHA-256;
- MIME type.

The manifest does not hash itself, avoiding recursive integrity metadata.

When reading a package, PackageIO verifies:

- manifest exists;
- manifest passes the injected authoritative manifest validator;
- archive file set exactly equals `manifest.files` plus `manifest.json`;
- file sizes match;
- SHA-256 hashes match;
- scenario ID/hash/schema/minimum Engine version match the manifest;
- capability/profile locks match exactly;
- student packages contain no `solution.json`;
- `scenario.json` never embeds `canonicalSolution`.

## Archive safety gates

Before normal package contents are exposed, PackageIO rejects:

- absolute paths;
- `..` traversal;
- dot/empty path segments;
- backslashes;
- Windows drive paths;
- encoded traversal/separator forms used for ambiguous decoding;
- control characters;
- unknown top-level roots;
- exact duplicate paths;
- case-colliding paths;
- excessive entry count;
- excessive compressed size;
- excessive decompressed size;
- excessive single-file size;
- excessive compression ratio;
- unlisted archive files;
- declared files missing from the archive;
- hash/size manipulation.

## Safe asset policy

Foundation PackageIO currently allows only a conservative portable set:

- PNG;
- JPEG;
- WebP;
- Markdown/plain-text documentation;
- JSON package documents.

At v0.5.0, scenario-provided SVG was explicitly rejected with `PACKAGE_CUSTOM_SVG_REQUIRES_SANITIZER` until a strict sanitization/rendering layer existed. That historical fail-closed boundary is superseded by Phase 31, which accepts only a strict passive sanitized subset; unsanitized/active SVG remains forbidden.

Built-in application SVG assets remain a separate trusted asset class and are not scenario package uploads.

## Determinism

Package semantic files are encoded with canonical object-key ordering. File entries are sorted by path before manifest creation. The zip.js adapter uses a stable ZIP entry modification date.

The test backend verifies semantic package determinism independently of ZIP byte-level implementation details.

## Current environment boundary

The generic PackageIO logic and zip.js adapter TypeScript surface are strict-typechecked. The sandbox does not have the declared npm package installed, so the real `ZipJsArchiveBackend` read/write methods are not runtime-executed in this checkpoint. All security, manifest, distribution, hashing, and file-set logic is exercised through the backend-independent memory archive test driver.

A later environment with resolved npm dependencies must run a real ZIP smoke/regression test before zip.js runtime integration itself is labelled end-to-end verified.
