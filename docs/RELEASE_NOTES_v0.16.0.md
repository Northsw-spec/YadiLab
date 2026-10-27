# Release notes v0.16.0 — browser Runtime progress lifecycle

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.16.0 continues directly from v0.15.0.

Added:

- portable `.yadiprogress` Runtime export/import controller;
- authoritative save-schema validation before browser restore;
- IndexedDB-backed autosave/restore/clear session controls;
- exact scenario-hash autosave lookup;
- normalized progress file/store diagnostics;
- browser Runtime controls wired to the existing Engine save/restore contract.

Verification:

- progress-session: 36 assertions PASS;
- progress-session adversarial: 28 assertions PASS;
- full Foundation regression: PASS.

No new save semantics were created in UI. Engine `SaveState` compatibility checks remain authoritative.

Dependency-resolved rendered-browser execution and real Parrot OS x86-64 acceptance remain explicit external gates.
