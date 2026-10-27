# Phase 26 — Headless SVG Renderer / CLI render

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 26 continues from exact-byte verified v0.25.0.

## Implemented

- dependency-free deterministic headless renderer built on the same normalized model and CanvasProjection used by the browser layer;
- explicit `LayoutDocument` is required; unresolved nodes fail instead of being silently stacked or auto-invented;
- parent-relative layout coordinates are resolved deterministically;
- semantic zones, resources and connections are emitted to a standalone SVG preview;
- labels/titles are XML-escaped;
- output contains no script, href/src, CDN or remote-resource references;
- `app render --input <source-or-normalized.json> --layout <layout.json> --output <preview.svg>`;
- source input compiles first; normalized input is schema-version gated before rendering.

## Boundary

This is the Foundation headless preview renderer. It does not claim PNG output or direct `.yadilab` ZIP reading in the CLI. Those require the real package ZIP adapter / dependency-resolved production toolchain and remain separate external work.
