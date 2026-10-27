# Phase 41 — release-scoped PWA byte-integrity and rollback

Base: exact v0.40.0 ZIP, SHA-256 `fddf99d9fbf75b9490492dd1ef371b71b3afd7217b0de1d50c3c03dfda5d5471`.

## Problem and bounded remediation

Previously the service worker derived a cache name from the manifest's SHA-256
values but relied on `cache.addAll` to fetch files without actually checking
the downloaded bytes. A changed origin could fill a release-named cache with
incorrect JavaScript while the hash-named cache appeared valid.

The generated shell AND future production-browser workers now:

- use the manifest's *per-file* SHA-256 values to verify each response's actual
  bytes using `crypto.subtle.digest('SHA-256')` in the secure-context worker;
- require exact same-origin response URLs, HTTP 200, no redirects/opaque
  responses and conservatively limit assets to 32 MiB each;
- prefetch and verify **every** allowlisted response before modifying the new
  cache and remove a partially created new cache after a write failure;
- leave an existing same-name release cache unchanged and verify it rather
  than overwriting it;
- serve cached assets only if their bytes still match; an unexpected/corrupted
  cache hit can be replaced only by an independently verified same-hash
  network response, otherwise it fails closed;
- intercept only known release asset paths with no query strings and never
  cache user scenarios, progress, or arbitrary same-origin requests;
- remove old owned caches only upon successful activation, while preserving
  unrelated caches and preserving the previous release after install failure.

`./` and `./index.html` must carry identical hash values; canonical duplicate
paths are rejected by the generator. No change to scenario schema, Engine or
project architecture was needed.

## Verification boundary

The generated service-worker JS is executed with real Node WebCrypto SHA-256
and native Request/Response objects against simulated CacheStorage and fetch.
Phase 41: **23 functional + 43 adversarial assertions** including tampered
bytes, partial cache writes, failed downloads, bad HTTP status/content length,
opaque/redirect responses, poisoned existing caches and private-resource
bypass. PWA static contract: **17 assertions**. Generated shell-file SHA-256 readback: **29 assertions** across five actual local paths. Live Go loopback launcher
smoke additionally fetches and inspects the generated worker.

This is *not* publisher authenticity: an attacker able to replace both
service-worker code and its trusted release manifest is outside this check.
No signatures or remote trust infrastructure are added. This harness is
not a substitute for real React bundle, browser engine, service-worker or
Parrot OS target acceptance.
