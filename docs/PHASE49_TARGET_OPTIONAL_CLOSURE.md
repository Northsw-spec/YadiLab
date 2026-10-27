# Phase 49 — target-native optional dependency closure

YadiLab's browser/toolchain dependency contract is pinned by exact package versions, an npm v3 lockfile, SHA-512 SRI, installed npm metadata, and executable toolchain probes.

Phase 49 closes one earlier gap in the lock/snapshot stage: npm packages can place platform-native artifacts in `optionalDependencies`. For the mandatory Linux x86-64 development/Parrot target, `esbuild@0.28.2` requires the native `@esbuild/linux-x64@0.28.2` package. Before Phase 49 the lock closure traversal followed ordinary `dependencies`, while the later executable esbuild probe was responsible for discovering a missing native optional package.

The dependency policy now carries an explicit target requirement:

- target: `linux-x86_64`;
- source package: `esbuild`;
- required optional package: `@esbuild/linux-x64`;
- exact version: `0.28.2`.

The lock verifier now requires all of the following before a Linux x86-64 dependency closure can be accepted:

1. the source package exists in the npm lock;
2. its `optionalDependencies` table declares the target-native package;
3. the target-native package has a real lock entry;
4. that entry uses the exact policy version plus normal SRI/registry checks;
5. the target-native path is included in the required closure;
6. npm's installed hidden lock contains that same path;
7. physical installed package metadata exists and matches the project lock.

Because `requiredLockPackageCount` is derived from the same target-aware closure, Phase 44/45 offline snapshots now bind the target-native esbuild package as part of the sealed dependency handoff too.

This remains metadata/provenance validation. It does not replace the Phase 46 executable esbuild transform, the dependency-resolved browser build, real Chromium offline reload, or Parrot target acceptance.
