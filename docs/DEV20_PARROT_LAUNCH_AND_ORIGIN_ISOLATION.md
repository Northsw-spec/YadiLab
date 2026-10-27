# dev20 — Parrot launch/origin isolation

Version: `1.1.0-dev.20`
Baseline: `1.1.0-dev.19`.

This checkpoint keeps the dev19 topology/right-panel UI maintenance and adds a visible build-version marker so a tester can distinguish stale browser content from the current build. The Parrot test kit is responsible for process cleanup, version-specific loopback origin selection, exact-build HTTP verification, and automatic browser launch.

No Engine/protocol/dependency behavior is changed.
