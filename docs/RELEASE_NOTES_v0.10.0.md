# Release notes v0.10.0 — Offline persistence / PWA foundation

YadiLab Foundation v0.10.0 continues directly from v0.9.0.

## Added

- strict Engine save-state creation/restoration;
- exact scenario/schema/Engine compatibility checks;
- portable Runtime progress import/export;
- centralized `.yadiprogress` extension usage;
- generic `ProgressStore` abstraction;
- deterministic memory persistence implementation;
- IndexedDB browser adapter;
- persistent-storage request helper;
- PWA manifest generation from centralized branding;
- same-origin generic service-worker foundation;
- persistence/PWA functional, adversarial, and schema verification.

## Preserved

All Phase 0-9 verification remains in `npm run test:foundation`.

## Boundary

Real IndexedDB, service-worker lifecycle, installable PWA behavior, actual offline browser execution, and Parrot acceptance remain explicitly pending and are not labelled verified by this checkpoint.
