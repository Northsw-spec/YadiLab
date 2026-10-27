# Release notes v0.11.0 — Loopback distribution preparation

YadiLab Foundation v0.11.0 continues directly from v0.10.0.

## Added

- generic Go loopback static launcher;
- loopback-only binding on `127.0.0.1`;
- stable default local port;
- strict static-root/path/symlink/method controls;
- hardened response headers;
- generated local browser/PWA delivery shell;
- reproducible Linux x86-64 launcher build script;
- precompiled `distribution/linux-x86_64` candidate;
- per-file SHA-256 manifest for the local distribution;
- launcher unit and live curl/security smoke tests;
- explicit Chromium environment probe record.

## Preserved

All Phase 0-10 semantic, compiler, Engine, persistence, and PWA-contract verification remains in `npm run test:foundation`.

## Boundary

The precompiled launcher is verified as a generic Linux x86-64 development checkpoint in this environment. It is not labelled Parrot-verified until the exact distribution is tested on supported Parrot OS. Chromium headless probing is currently blocked by the container runtime and is not counted as PASS.
