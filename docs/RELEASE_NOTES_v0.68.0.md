# YadiLab Foundation v0.68.0

Phase 68 adds dedicated Windows and Linux Fault Packs on top of the verified Fault Engine/UI.

Highlights:

- new `foundation.os.windows@0.1.0` with 10 deterministic Windows faults;
- new `foundation.os.linux@0.1.0` with 10 deterministic Linux faults;
- explicit built-in Fault Pack selector in the Fault Injection UI;
- exact OS target-type filtering in the UI and Engine;
- pack-independent active-overlay target/path conflict detection;
- independent faults from multiple packs can coexist with multiple exact pack locks;
- Windows RDP/SMB/WinRM and Linux SSH/HTTP service/listener faults are checked against existing Engine service semantics;
- all OS faults remain reversible with canonical restore-pre-injection recovery;
- no arbitrary difficulty score, AI logic or probabilistic mutation added;
- `foundation.network.core@0.2.0` remains unchanged from v0.67.0.

The Diagnostic / Observation Engine is still future work; this checkpoint does not claim real Windows/Linux command execution.

Classification remains **VERIFIED DEVELOPMENT CHECKPOINT, NOT VERIFIED PRODUCT RELEASE** until external dependency/browser/Parrot gates are satisfied.
