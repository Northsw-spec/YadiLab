# YadiLab Foundation v0.52.0

Phase 52 binds sealed offline dependency snapshots to the exact YadiLab source checkout rather than only to dependency declarations. Snapshot schema 1.1.0 adds a deterministic source-checkout identity over canonical file paths, bytes and Unix modes. The verifier recomputes that identity on the consumer before npm can inspect the transferred cache.

This closes a reproducibility gap where two different application/build checkpoints with unchanged `package.json` and dependency policy could otherwise accept the same snapshot. Generated/local state is deliberately excluded; source symlinks and source drift fail closed.

The phase does not fabricate npm bytes and does not promote the current Debian environment to dependency-resolved or Parrot-verified status.
