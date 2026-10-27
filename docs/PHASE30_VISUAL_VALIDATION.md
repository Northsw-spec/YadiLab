# Phase 30 — Visual Validation

Authoritative architecture: YadiLab Masterprompt v1.2 VERIFIED / LOCKED.

## Purpose

Phase 30 implements the visual-validation requirements that were not covered by structural Layout validation. The validator is deterministic and works from normalized scenario semantics plus `LayoutDocument`; it does not inspect screenshots or use AI/ML.

## Detected conditions

- sibling node overlap in the same parent coordinate space;
- child/resource geometry outside its parent zone;
- zone overflow caused by child geometry;
- root nodes outside the non-negative canvas origin or explicit canvas bounds;
- label geometry too small for deterministic readability policy;
- excessive coincident semantic edges;
- unreasonable whitespace in sibling groups;
- scenario/layout identity mismatch.

## Pipeline integration

`runAutoLayout()` runs Visual Validation after manual overrides are applied and fails closed on visual errors.

`certifyCompiledScenario()` runs the same validator before package creation. Therefore Builder package export cannot receive `selfVerified: true` when the layout is structurally correct but visually invalid.

## Coordinate rule

Layout coordinates remain parent-relative for nested nodes. Overlap is compared only among siblings in the same coordinate system; absolute geometry is calculated only where required for edge-route checks.

## Scope boundary

This is deterministic geometry/text-capacity validation, not screenshot-based browser QA. Actual React/React Flow rendering and real Parrot browser acceptance remain external gates until dependencies/target environment are available.
