# Phase 31 — Strict Custom SVG Sanitizer

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

## Purpose

Phase 31 replaces the historical “reject every scenario SVG” boundary with a strict accept-or-reject sanitizer for untrusted scenario-provided SVG assets.

## Security model

Custom SVG remains UNTRUSTED CONTENT. Passing the sanitizer does not promote it to the trusted built-in Asset Library.

The sanitizer accepts only a small passive subset of SVG elements and attributes. It rejects rather than repairs documents outside the policy. In particular it rejects:

- script and active/unsupported elements;
- event-handler attributes;
- style/CSS;
- href/src/reference-capable attributes and use/image constructs;
- javascript:, data:, http(s):, file:, blob:, protocol-relative and CSS url()/@import references;
- DOCTYPE, ENTITY, comments, processing instructions and CDATA;
- extra namespaces/namespaced attributes;
- malformed tag structure, duplicate attributes and unsupported attribute syntax.

Only the canonical root `xmlns="http://www.w3.org/2000/svg"` URI is allowed as a URI-like exception.

## PackageIO integration

- Writer validates/sanitizes SVG before hashing and archive creation.
- Reader verifies manifest size/SHA-256 first, then applies the same SVG policy before exposing bytes.
- Therefore an attacker-built package with internally correct hashes cannot bypass SVG content safety.
- Safe SVG remains byte-identical; the Foundation sanitizer does not silently rewrite dangerous markup into a guessed safe result.

## Scope

The sanitizer is a package-content safety gate. Browser rendering remains subject to the application rule that scenario-provided SVG is rendered as an image resource under restrictive policy, never injected as arbitrary inline DOM markup.
