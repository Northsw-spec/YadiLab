# Phase 19 — Builder Inspector and visual editing

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

Phase 19 continues directly from exact-byte verified v0.18.0. It does not replace the compiler, Builder API, or canonical ScenarioSource model.

Implemented:

- typed Builder Inspector presenter for mission metadata, zones, resources, and connections;
- stable object IDs remain read-only during ordinary Inspector edits;
- mission title/language/briefing/description editing;
- zone label/kind/parent editing with immediate missing-parent, self-parent, and cycle rejection;
- resource label/type/zone/profile/vendor/product editing;
- resource properties edited as a validated JSON object;
- resource interfaces edited as a validated JSON array with mandatory interface IDs;
- connection kind/endpoints/interface-port references/properties editing;
- visual create controls for zones, resources, and connections;
- visual resource duplication;
- selected-object deletion with explicit cascade requirement where semantic references exist;
- every semantic Inspector mutation invalidates stale compile state and increments source revision;
- layout drag overrides remain separate from semantic ScenarioSource state.

Architecture boundary:

- Inspector UI calls existing Builder commands; it does not mutate ScenarioSource objects directly;
- ScenarioSource remains the Builder source of truth;
- IDs are not silently renamed because references depend on stable IDs;
- arbitrary HTML/script execution is not supported;
- malformed JSON/property/interface edits fail atomically with explicit diagnostics;
- compilation/validation remains authoritative before Runtime preview or package export.

Verification:

- Builder Inspector functional suite: 37 assertions PASS;
- Builder Inspector adversarial suite: 24 assertions PASS;
- complete Foundation regression through Phase 19: PASS.

External dependency-resolved rendered-browser execution and real Parrot OS x86-64 acceptance remain explicit unclaimed gates.
