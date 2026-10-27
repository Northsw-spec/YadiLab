# Release notes — v0.57.0 development checkpoint

Phase 57 adds a fail-closed external operator key-material ceremony for future signed dependency snapshots.

- Adds atomic Ed25519 producer-key bundle generation outside the application checkout.
- Enforces `0600` on private key material and `0644` on public ceremony artifacts.
- Verifies private/public pair, SPKI-derived key ID and exact fingerprint file.
- Adds canonical public ceremony metadata bound to the source-checkout identity used to initiate the ceremony.
- Refuses overwrite, source-checkout paths, symlink path escapes, extra bundle files, symlinked bundle members, insecure modes, pair mismatch, fingerprint manipulation, record manipulation and source-identity drift.
- Adds functional, adversarial and CLI-contract regression suites.
- Does not embed or fabricate any production key; release trust store remains intentionally empty.

This remains a VERIFIED DEVELOPMENT CHECKPOINT, not a verified product release. A real operator-controlled trust anchor, genuine signed npm dependency snapshot, dependency-resolved browser build, live Chromium offline reload and Parrot OS x86-64 acceptance remain external gates.
