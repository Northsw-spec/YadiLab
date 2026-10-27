# Release notes v0.23.0 — Asset Library

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.23.0 continues from exact-byte verified v0.22.0.

Added:
- trusted reusable built-in SVG Asset Library with Masterprompt infrastructure categories;
- exact asset version resolution and normalized asset locks;
- deterministic automatic resource→asset mapping plus explicit override requirements;
- compiler diagnostics for missing/unavailable/mismatched/ambiguous assets;
- Asset Library safety resolver and contain-style Canvas projection;
- Builder Asset Library palette with compatible-asset application and automatic-selection reset;
- package manifest asset-lock integrity cross-check;
- browser/loopback distribution copying of built-in assets;
- live loopback smoke request for a built-in SVG.

Verification highlights:
- schema suite 19/19 PASS;
- compiler suite 61 assertions + 30 adversarial PASS;
- Asset Library 112 functional + 12 adversarial PASS;
- Builder Asset Library 11 functional + 9 adversarial PASS;
- complete Foundation regression through Phase 23 PASS before packaging.

Custom scenario SVG remains fail-closed/untrusted. Dependency-resolved rendered-browser and real Parrot OS x86-64 acceptance remain external gates.
