# Phase 11 — Loopback distribution preparation

Version: 0.11.0

Phase 11 continues directly from the exact v0.10.0 checkpoint.

## Goal

Provide the Masterprompt v1.2 local Parrot/Linux delivery mechanism without changing the browser/PWA semantic baseline:

```text
bundled local web assets
        +
precompiled generic Linux x86-64 launcher
        ↓
127.0.0.1:<stable-port>
        ↓
user browser
```

The launcher is only a delivery mechanism. It does not own scenario semantics, Engine logic, Compiler logic, package formats, or persistence.

## Generic Go launcher

A small standard-library-only Go HTTP launcher now exists under `launcher/`.

Properties:

- binds IPv4 loopback only (`127.0.0.1`);
- default port is stable (`17931`);
- supports explicit local port override for testing;
- serves only regular files below the configured static root;
- rejects encoded traversal patterns;
- rejects symlink escape outside the static root;
- accepts only GET/HEAD;
- provides CSP, COOP, no-sniff, frame, referrer, permissions, and cache-control headers;
- does not expose an option to bind `0.0.0.0` or arbitrary host interfaces.

## Precompiled candidate

`scripts/build_loopback_distribution.sh` builds:

```text
distribution/linux-x86_64/
  app-launcher
  SHA256SUMS.txt
  web/
    index.html
    app-shell.js
    manifest.webmanifest
    sw.js
```

The launcher build uses:

```text
CGO_ENABLED=0
GOOS=linux
GOARCH=amd64
-trimpath
-s -w -buildid=
```

The resulting binary is a standalone Linux x86-64 ELF with no dynamic-library requirement in the current environment.

The runtime smoke starts that binary with a deliberately unusable PATH (`PATH=/nonexistent`) and still serves the distribution. This verifies that Node/npm/TypeScript/Go are not runtime requirements for the built launcher package.

## Web delivery shell

The generated HTML/PWA shell is produced from centralized branding. Static assets are same-origin/local only. The service worker registers locally and precaches the generated shell resources.

This is a delivery shell, not yet the complete rendered React Builder/Runtime application bundle.

## Verification

Automated launcher checks cover:

- Go unit tests;
- normal static serving;
- path traversal rejection;
- symlink escape rejection;
- method restrictions;
- security headers;
- explicit `.webmanifest` MIME type;
- loopback-only listener verification with `ss`;
- no Node/runtime tooling requirement;
- standalone x86-64 ELF inspection;
- distribution SHA-256 validation;
- local app-shell/service-worker asset serving.

## Chromium/Parrot boundary

The installed Chromium process in this sandbox hangs in headless mode because of the container environment/DBus and is terminated by timeout. This is recorded as `BLOCKED`, not PASS and not an application failure.

Therefore v0.11.0 does NOT claim:

- Chromium browser acceptance;
- Firefox browser acceptance;
- service-worker lifecycle acceptance in a real browser;
- installable PWA acceptance;
- actual Parrot OS x86-64 acceptance.

Those remain external runtime acceptance gates.
