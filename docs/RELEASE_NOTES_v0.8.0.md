# Release notes v0.8.0 — ELK layout Phase 8

YadiLab Foundation v0.8.0 continues directly from v0.7.0.

## Added

- compound semantic -> layout graph projection;
- stable initial node dimensions;
- globally unique interface port IDs;
- generic `LayoutBackend` boundary;
- strict backend output completeness/geometry/hierarchy validation;
- deterministic `LayoutDocument` generation;
- separate post-layout manual overrides;
- `ElkLayoutBackend` source using ELK Layered;
- layout functional and adversarial suites.

## Preserved

All Phase 0-7 verification remains in `npm run test:foundation`.

## Boundary

Real `elkjs` runtime execution is pending a dependency-resolved environment. The layout semantics and backend safety contract are verified independently of the library implementation.
