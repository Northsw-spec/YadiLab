# Release notes v0.19.0 — Builder Inspector and visual Builder editing

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.19.0 continues directly from exact-byte verified v0.18.0.

Added:

- typed visual Inspector for Mission, Zone, Resource, and Connection objects;
- create Zone/Resource/Connection controls in the browser Builder;
- resource duplicate and selected-object delete controls;
- strict JSON editing for resource properties/interfaces and connection properties;
- explicit zone-parent cycle prevention at Builder command boundary;
- stable read-only semantic IDs in ordinary Inspector editing;
- Browser UI wired to the existing tested Builder API rather than introducing separate state mutation logic.

Verification:

- Builder Inspector functional suite: 37 assertions PASS;
- Builder Inspector adversarial suite: 24 assertions PASS;
- complete Foundation regression through Phase 19: PASS.

This is a VERIFIED DEVELOPMENT CHECKPOINT, not a VERIFIED RELEASE. Dependency-resolved rendered-browser and real Parrot OS x86-64 acceptance remain external gates.
