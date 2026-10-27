# Phase 15 — Builder package export and self-verification

Phase 15 continues directly from v0.14.0 and completes the browser-controller package round trip.

## Export path

```text
Builder ScenarioSource
  -> successful current compile
  -> optional current complete layout
  -> PackageIO.write()
  -> immediate PackageIO.read() self-verification
  -> student/author policy checks
  -> Blob download descriptor (.yadilab)
```

A browser download is never produced merely because archive writing returned a Blob. The Blob must be readable again through the same safe PackageIO contract first.

## Student packages

Student export verifies that read-back contains:

- the requested `student` distribution identity;
- the same scenario ID and source hash;
- no `solution.json` material;
- layout when Builder supplied a layout.

## Author packages

Author export verifies that read-back contains the canonical solution whenever the compiled model contains one. `scenario.json` itself still never embeds canonical solution data.

## Layout freshness guard

A Builder layout is exportable only when its semantic node set exactly covers the current compiled zones + resources. Missing nodes, orphan nodes, duplicate node IDs, or wrong scenario identity block export.

This prevents an old visual layout from being silently attached after semantic edits/recompilation.

## Filename / branding

The generic browser module receives the scenario extension as an input. The React integration supplies the centrally configured `branding.scenarioExtension`; the core package module does not hardcode the current product name.

## Verification

Added:

- 17 package-export functional assertions;
- 16 package-export adversarial assertions;
- student solution leakage self-check;
- author solution loss self-check;
- distribution identity self-check;
- scenario ID/hash read-back check;
- layout completeness/orphan checks;
- safe-extension guard;
- backend write/read failure normalization.

All earlier Foundation suites remain mandatory.
