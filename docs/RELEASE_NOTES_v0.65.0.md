# YadiLab Foundation v0.65.0

Phase 65 adds the deterministic Fault Injection Engine Core required by Masterprompt v1.3.

Highlights:

- new Fault Pack and Fault Overlay Draft 2020-12 schemas;
- content-addressed/versioned fault packs;
- deterministic named target bindings;
- preconditions, incompatibilities, mutations, expected effects and negative controls;
- seeded deterministic choice values;
- actual blast-radius verification;
- captured/tested inverse operations;
- overlay and per-application SHA-256 integrity;
- safe latest-fault rollback gate;
- persistent `SCENARIO_VARIANT` materialization;
- compiler-preserved `faultOrigin`;
- built-in starter network fault pack;
- baseline/source remains non-destructively reusable.

Classification remains **VERIFIED DEVELOPMENT CHECKPOINT, NOT VERIFIED PRODUCT RELEASE** until the external dependency/browser/Parrot gates are satisfied.
