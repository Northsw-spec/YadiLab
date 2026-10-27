# Release notes v0.21.0 — Builder Canvas Interactions

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.21.0 continues from exact-byte verified v0.20.0.

Added:
- React Flow multi-select routed through the canonical semantic Builder selection;
- selected node/edge projection is derived from `workspace.selection`, not a parallel React Flow source of truth;
- live manual drag overrides now update both retained layout override data and the current LayoutDocument projection;
- zone resize through `NodeResizer`, with finite/min/max dimensional guards and no ScenarioSource mutation;
- interactive source/target connection gestures mapped to a normal declarative `ScenarioSource.connection`;
- interface handle validation (`out:<iface>` / `in:<iface>`) with generic-handle support;
- deterministic collision-safe interactive connection IDs;
- explicit adversarial guards against ghost selection IDs, React Flow-only edges, invalid handles/interfaces, self-links, and invalid resize values.

Verification:
- 31 Builder Canvas Interactions functional assertions PASS;
- 33 Builder Canvas Interactions adversarial assertions PASS;
- complete Foundation regression through Phase 21 PASS.

External dependency-resolved rendered-browser and real Parrot OS x86-64 acceptance remain unclaimed gates.
