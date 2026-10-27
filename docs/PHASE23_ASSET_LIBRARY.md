# Phase 23 — Asset Library / reusable trusted assets

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 23 continues from exact-byte verified v0.22.0.

Implemented:

- trusted built-in Asset Library with stable ID + exact version + local path + MIME + intrinsic dimensions + appliesTo patterns;
- required generic infrastructure categories from Masterprompt v1.2 plus deterministic `resource.generic` fallback;
- preferred built-in master format SVG; local static SVG files contain no script, event handlers, or remote references;
- optional `resources[].asset {id,version}` requirement in scenario source;
- deterministic automatic asset selection when no explicit override is provided;
- exact normalized `asset` refs on every resource and exact `assetLocks`;
- explicit diagnostics for missing asset, unavailable version, type mismatch, and ambiguous equally-specific auto-match;
- package manifest asset locks and PackageIO manifest↔scenario cross-check;
- Asset Library resolver refuses missing/duplicate/untrusted/unsafe/mime-mismatched locks;
- Canvas projection renders only a successfully resolved trusted lock and uses contain-style presentation;
- Builder Asset Library palette applies/clears explicit asset overrides through existing Builder commands;
- browser and loopback distribution copy trusted assets locally; launcher smoke fetches a built-in SVG over 127.0.0.1.

Security boundary:

- built-in app SVG is trusted source-controlled application content;
- scenario-provided custom SVG remains UNTRUSTED; Phase 31 adds a strict passive sanitizer/allowlist in PackageIO, while active/remote SVG remains fail-closed;
- scenario source never supplies a render path directly; normalized paths come only from the active trusted Asset Library catalog.

Not claimed:

- dependency-resolved rendered browser build in this sandbox;
- custom SVG sanitizer acceptance;
- real Parrot OS x86-64 acceptance.
