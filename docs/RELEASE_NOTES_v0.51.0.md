# YadiLab Foundation v0.51.0

Phase 51 adds fail-closed consumer-environment coherence for sealed offline dependency snapshots.

The offline installer now requires the consuming Linux x86-64 machine to use the exact Node and npm versions recorded by the trusted producer in `snapshot-manifest.json`. This check occurs before npm reads the transferred cache or performs `npm ci --offline`.

This remains a development checkpoint. A genuine dependency-resolved browser build, live Chromium Builder→Runtime proof, server-stopped offline reload, and Parrot OS acceptance remain external gates until real npm snapshot bytes are supplied.
