# Release notes v0.50.0 — snapshot producer coherence and offline replay

YadiLab Foundation v0.50.0 continues directly from the exact v0.49.0 checkpoint under Masterprompt v1.2 VERIFIED / LOCKED.

Phase 50 closes two dependency-handoff gaps. Producer platform metadata is now semantically validated and cross-bound to the snapshot manifest, and the online snapshot producer must prove that its populated npm cache can perform a fresh strict-offline reinstall before sealing the transport.

New dedicated verification covers valid producer metadata, adversarial platform/architecture/Node/npm/kernel mutations, manifest-vs-platform identity forgery, explicit producer identity mismatch, malformed platform JSON, and the required online-populate → cache-verify → destroy-first-install → strict-offline-replay → readiness → executable-toolchain → manifest ordering.

This remains a development checkpoint. No dependency-resolved React browser build, Chromium offline reload or Parrot acceptance is claimed until genuine npm dependency bytes are available and those external gates execute successfully.
