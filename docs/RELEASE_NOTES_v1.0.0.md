# YadiLab v1.0.0

This product release promotes the verified v1.0.0-rc.1 candidate without adding learner features or changing modeled product behavior.

Release sealing changes:

- generated an operator-owned Ed25519 dependency-snapshot signing key through the existing external key ceremony;
- pinned only its public trust anchor and proof of possession in source;
- kept the private key outside the checkout, distribution and release archive with mode `0600`;
- fixed the snapshot producer's pre-signing verification step so it validates the complete unsigned manifest/cache structure before provenance exists, while final verification still requires a valid signature;
- verified signature acceptance plus payload, signature, wrong-key and missing-key rejection;
- promoted package and release metadata from `1.0.0-rc.1` to `1.0.0`.

The application remains an offline, deterministic modeled lab. It does not execute guest commands, transmit probes, scan networks, infer hidden diagnoses, expose canonical solutions, or require Node/npm for end users.
