# Release notes v0.30.0 — Visual Validation

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

v0.30.0 continues from exact-byte verified v0.29.0.

Added:
- deterministic Visual Validation subsystem;
- sibling overlap detection;
- node-outside-zone plus zone-overflow detection;
- root canvas-bound checks;
- deterministic label-readability geometry check;
- excessive coincident-edge detection;
- unreasonable-whitespace detection;
- Visual Validation integrated into auto-layout and Scenario Certification.

Verification highlights:
- layout: 16 functional + 14 adversarial assertions PASS;
- Visual Validation: 3 functional + 9 adversarial assertions PASS;
- Scenario Certification: 11 functional + 8 adversarial assertions PASS;
- complete Foundation regression through Phase 30 PASS before packaging.

External rendered-browser and real Parrot acceptance gates remain fail-closed and are not claimed as verified in this environment.
