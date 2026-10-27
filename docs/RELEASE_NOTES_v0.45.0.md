# Release notes v0.45.0 — sealed dependency snapshot transport

YadiLab Foundation v0.45.0 continues directly from v0.44.0 and preserves Masterprompt v1.2 as the VERIFIED / LOCKED architecture agreement.

## Added

- canonical deterministic `ZIP_STORED` transport for Phase 44 dependency snapshots;
- safe transport extractor with path/type/size/order/hash preflight;
- basename-bound SHA-256 sidecar verification that never executes a sidecar-provided path;
- one-command trusted-online-host producer: `prepare_offline_browser_snapshot.sh`;
- direct sealed-ZIP support in `install_offline_browser_dependencies.sh`;
- focused Phase 45 transport adversarial suite.

## Verified in the current environment

- dependency gate: 31 PASS;
- dependency adversarial: 34 PASS;
- Phase 44 snapshot: 28 PASS;
- Phase 45 transport: 42 PASS.

The genuine npm snapshot, dependency-resolved `ui/dist`, real Chromium workflow and Parrot OS x86-64 acceptance remain external gates. v0.45.0 is therefore a VERIFIED DEVELOPMENT CHECKPOINT, not a VERIFIED PRODUCT RELEASE.
