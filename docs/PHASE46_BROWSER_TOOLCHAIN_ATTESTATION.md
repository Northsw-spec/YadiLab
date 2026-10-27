# Phase 46 — Executable Browser Toolchain Attestation

Phase 46 continues directly from the exact verified v0.45.0 checkpoint.

## Problem closed

Phase 37/44/45 verify exact dependency policy, lock closure, transferred cache bytes,
installed lock metadata and package versions. Those checks are necessary but do not
prove that the installed JavaScript/native toolchain can actually execute on the
build host.

A copied or ABI-incompatible installation could otherwise look metadata-correct
while native esbuild, ELK or another required module fails only after promotion.

## New fail-closed gate

`scripts/check_browser_toolchain_execution.mjs` first reuses the existing dependency
readiness gate. If dependencies are absent or not reproducibly installed, it exits
77/BLOCKED.

Once metadata readiness is PASS, the executable attestation must then pass all of:

- React element creation;
- ReactDOM server rendering;
- `@xyflow/react` required exports;
- Ajv strict schema compilation and validation;
- ELK bundled module load plus an actual deterministic graph layout;
- zip.js required reader/writer constructor exports;
- exact pinned TypeScript version plus `transpileModule` execution;
- exact pinned esbuild version plus a real TypeScript `transform()` call, forcing
  the native esbuild service/binary path to execute.

If an installed toolchain fails any executable probe, the result is a real FAIL
(exit 1), not BLOCKED.

## Integration

The gate is enforced in both paths:

1. `install_offline_browser_dependencies.sh` after `npm ci --offline` and before
   browser bundling;
2. `build_browser_app.mjs` itself, so direct build invocation cannot bypass it.

## Current sandbox

The sandbox has no genuine npm-generated project lock/cache/node_modules closure.
Therefore the real Phase 46 toolchain gate correctly returns 77/BLOCKED here and
no executable dependency-resolved browser build is claimed.
