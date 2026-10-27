# Release notes v0.26.0 — Headless SVG Renderer / CLI render

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.26.0 continues from exact-byte verified v0.25.0.

Added:
- deterministic dependency-free SVG preview renderer;
- CanvasProjection-based render path;
- explicit layout/geometry validation;
- safe XML escaping and no remote/executable SVG output;
- `app render` CLI command for source/normalized JSON + layout.

Verification highlights:
- renderer: 12 functional + 6 adversarial assertions PASS;
- CLI: 49 functional + 17 adversarial assertions PASS;
- complete Foundation regression through Phase 26 PASS before packaging.

Direct packaged `.yadilab` CLI rendering and PNG remain outside this verified checkpoint.
