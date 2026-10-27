# Phase 13 — dependency-locked browser build gate

Phase 13 continues directly from the exact v0.12.0 checkpoint. It does not replace or fork the existing compiler, Engine, PackageIO, CLI, canvas, layout, Builder/Runtime, persistence, launcher, or Parrot acceptance layers.

## Goal

Prevent a shell-only or dependency-drifting build from ever being promoted as the finished browser application.

The browser application remains the compatibility baseline. Runtime dependencies are development/build inputs only; the end-user Linux/Parrot distribution serves already-built local static assets and must not require Node/npm.

## Exact direct dependency policy

`dependencies/browser-runtime.policy.json` is the Foundation direct-dependency policy for the browser build. It pins exact versions for:

- React;
- React DOM;
- React Flow (`@xyflow/react`);
- ELK.js;
- Ajv;
- zip.js;
- TypeScript;
- esbuild.

No `^`, `~`, tag, URL, workspace alias, or floating version is accepted in the protected direct set.

This policy is not a substitute for the transitive npm lock. A dependency-resolved browser build is not build-ready until a real `package-lock.json` exists and the installed direct package metadata exactly matches the declared pins.

## Fail-closed readiness

`scripts/check_browser_build_readiness.mjs` returns:

- exit `0` only when the direct policy, package lock, and installed direct package versions match;
- exit `77` when required dependency material is missing or unresolved.

The current sandbox intentionally remains `BLOCKED` because registry DNS/network access is unavailable and no genuine lock/install may be fabricated.

## Real browser entry source

`ui/app/main.mjs` is the first dependency-resolved React/React Flow application entry source. It connects the already verified framework-neutral layers rather than recreating their semantics:

- Builder uses `ScenarioSource`;
- compiler uses the authoritative Ajv adapter;
- auto-layout uses `ElkLayoutBackend`;
- canvas uses the existing model -> React Flow projection;
- Runtime operations pass through the deterministic Engine reducer;
- drag coordinates become separate manual layout overrides;
- scenario import/export uses standard File/Blob behavior.

React Flow remains a view. It does not become canonical scenario state.

## Browser bundle build

`scripts/build_browser_app.mjs` is fail-closed. Once dependencies are genuinely resolved it:

1. verifies dependency readiness;
2. bundles the app locally with pinned esbuild;
3. emits only local static assets;
4. creates the production `index.html` with `data-app-runtime="ready"`;
5. creates a local service worker;
6. writes `browser-build-manifest.json` with exact direct pins and SHA-256/size for output files;
7. rejects remote runtime URL references.

No CDN is permitted at runtime.

## Distribution promotion rule

`build_loopback_distribution.sh` copies `ui/dist/` only when its browser manifest says `status: ready`. Otherwise it deliberately packages the old local shell with:

- `data-app-runtime="shell"`;
- `browser-build-manifest.json` -> `status: shell-only`.

A shell-only package remains useful for launcher/PWA plumbing tests but is not the complete application.

## Parrot acceptance hardening

The Parrot acceptance harness now requires both:

- `browser-build-manifest.json` with `status: ready`;
- `data-app-runtime="ready"` in the served application document.

Therefore a real Parrot machine cannot accidentally promote the shell-only checkpoint to a verified application release.

## Verification boundary

Verified in this checkpoint:

- exact direct dependency policy;
- dependency drift/adversarial guards;
- lock/install readiness logic;
- local-only runtime-reference guard;
- browser entry/build-script syntax;
- shell vs ready distribution distinction;
- hardened Parrot acceptance contract;
- all previous Foundation regression suites.

Not claimed yet:

- successful npm dependency acquisition in this sandbox;
- actual esbuild execution against real installed React/React Flow/ELK/Ajv/zip.js;
- rendered React application acceptance;
- Parrot target PASS.

Those remain explicit gates, not assumed facts.
