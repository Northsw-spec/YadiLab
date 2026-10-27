# Release notes v0.22.0 — Builder Notes

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.22.0 continues from exact-byte verified v0.21.0.

Added:
- optional portable `notes` collection to source and normalized scenario contracts;
- note model: stable id, non-empty text, optional title, optional semantic target;
- compiler normalization/preservation of notes;
- semantic validation for global ID collisions and unknown note targets;
- Builder Notes JSON authoring panel routed through Builder commands;
- backward compatibility: notes remain optional so earlier compiled packages stay schema-valid;
- notes are documentation only and do not participate in Engine rules/completion.

Verification:
- schema suite 19/19 PASS;
- compiler suite 48 assertions PASS;
- Builder Notes 9 functional + 10 adversarial assertions PASS;
- complete Foundation regression through Phase 22 PASS.

External dependency-resolved rendered-browser and real Parrot OS x86-64 acceptance remain unclaimed gates.
