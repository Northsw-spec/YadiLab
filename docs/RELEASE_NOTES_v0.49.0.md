# Release notes v0.49.0 — target-native optional dependency closure

YadiLab Foundation v0.49.0 continues directly from the exact v0.48.0 checkpoint under Masterprompt v1.2 VERIFIED / LOCKED.

Phase 49 hardens dependency provenance for the mandatory Linux x86-64 target. The lock closure previously followed ordinary transitive dependencies but did not make the target-native optional esbuild binary an explicit closure requirement. The later executable toolchain probe would still fail, but an incomplete lock/snapshot could pass too far into the handoff pipeline before that failure.

Changes:
- dependency policy explicitly binds `esbuild@0.28.2` to `@esbuild/linux-x64@0.28.2` for `linux-x86_64`;
- lock closure requires the parent optional-dependency declaration and exact native package entry;
- target-native paths are included in required installed-lock parity checks;
- offline snapshot lock-package counts automatically include the target-native path;
- dedicated functional/adversarial target-optional regression suites added;
- full-regression branding guard exposed three old test-only hardcoded display-brand fixture titles; those fixtures now use neutral names so protected-source branding remains configuration-driven;
- the later native esbuild executable transform remains mandatory and is not replaced by metadata checks.

The current sandbox still has no genuine npm-generated lock/cache/node_modules closure, so dependency readiness, real browser build, Chromium offline acceptance, and Parrot target acceptance remain fail-closed rather than inferred.
