# Release notes v0.37.0 — Dependency supply-chain readiness and offline browser-build handoff

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.
Baseline: exact local v0.36.0 checkpoint (SHA-256 `a5d280bf4fdaa2291392fd589b5befe095f1cc037a698397d106bc0d6990d0f0`). All previous Engine and scenario behavior preserved.

The previous browser readiness check could accept a fabricated root-only package-lock and manually-created direct package metadata. Phase 37 replaces that weak pass criterion with strict v3 npm project lock closure, concrete direct and required transitive dependency entries, SHA-512 SRI, safe registry origins, physical installed metadata, and `node_modules/.package-lock.json` consistency. Adversarial tests include a missing direct lock entry, integrity removal/mismatch, unsafe origin, unresolvable transitive dependency, missing installed lock, undeclared installed package, metadata forgery, and an uninstalled otherwise locked transitive dependency. A complete nested fixture is also accepted to avoid false-positive blocking.

Developer-only scripts `prepare_offline_browser_cache.sh` and `install_offline_browser_dependencies.sh` provide an optional trusted Linux x86-64 npm-cache handoff. The offline install uses `npm ci --offline` and never fetches live registry data. A separate `check:package-lock` preflight blocks incomplete or unsafe locks before npm ci.

**Scope/limits:** these are lock/metadata consistency gates, not publisher authenticity or an independent hash of every installed file. Actual npm tarball SRI checking and real esbuild browser bundling must still occur on a provisioned builder. Online cache preparation, actual offline installation, rendered browser checks and Parrot target acceptance are unexecuted in this DNS-blocked Debian sandbox. Browser and Parrot gates must remain `77/BLOCKED`. Status: VERIFIED DEVELOPMENT CHECKPOINT only, not VERIFIED RELEASE.
