# Release notes v0.48.0 — browser-build template binding correction

YadiLab Foundation v0.48.0 continues directly from the exact v0.47.0 ZIP. Masterprompt v1.2 remains VERIFIED / LOCKED.

This is an audit-correction release. It fixes a discrepancy discovered in v0.47.0: the verification text claimed the production full-browser builder loaded `app-shell.js`, but the packaged `build_browser_app.mjs` did not.

Changes:
- production browser index generation moved to a directly tested `browser-index-template.mjs`;
- production builder is explicitly bound to that renderer;
- local `app-shell.js` is emitted before local `assets/app.js`;
- release integrity rejects reversed bootstrap/application ordering;
- synthetic release tests use the same renderer as production;
- persistence regression follows the rendered output instead of a stale source literal;
- Foundation regression expands to 106 deterministic commands.

External dependency-resolved browser and Parrot gates remain fail-closed and unclaimed.
