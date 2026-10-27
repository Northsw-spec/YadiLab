# YadiLab Foundation v0.70.0

Phase 70 adds **Diagnostic / Observation Engine, Wave 1**.

Highlights:

- new deterministic `foundation.observation@0.1.0` runtime observation engine;
- 7 modeled Windows command surfaces and 7 modeled Linux command surfaces;
- routing, DNS, DHCP, interface, host firewall and service/listener evidence;
- transcripts bind exact scenario hash, Runtime revision, target and command;
- direct modeled evidence paths accompany command-shaped output;
- missing data is explicit `<not modeled>` and malformed state is fail-safe rather than guessed;
- observations are read-only and never create Runtime history mutations;
- Browser Runtime panel exposes target/command selection and modeled transcript/evidence;
- Builder and cross-OS command misuse fail closed;
- hidden fault/generator ground truth is not available through the observation channel;
- no guest OS, PowerShell, shell or kernel command execution is falsely claimed.

The Phase 65–69 Fault Engine, Fault Packs, mandatory preview flow and deterministic multi-fault generator remain unchanged in semantics.

Classification remains **VERIFIED DEVELOPMENT CHECKPOINT, NOT VERIFIED PRODUCT RELEASE** until external dependency/browser/Parrot gates are satisfied.
