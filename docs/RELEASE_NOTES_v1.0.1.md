# YadiLab v1.0.1

Patch candidate for a post-release topology rendering defect found after the locked v1.0.0 VERIFIED PRODUCT RELEASE.

Fix scope:

- reserve a deterministic 64 px header band inside every compound zone before ELK may place child nodes;
- retain the existing 32 px root-graph padding separately from compound-zone content padding;
- fail visual validation with `LAYOUT_ZONE_HEADER_OVERLAP` if any child geometry intrudes into a zone header, including imported/manual layouts;
- clamp Builder drag-stop geometry for parented nodes below the same reserved header band;
- add an actual ELK regression asserting compound children remain below the reserved header;
- add a real Chromium/Playwright release-gate check that compares rendered zone-header and resource-card DOM rectangles and fails on visual overlap.

No Engine, network, identity, fault, PackageIO, observation, remediation, or scenario semantics are changed. Dependency versions are unchanged.

The locked v1.0.0 release remains authoritative until v1.0.1 passes the complete Foundation and real Parrot Chromium/Firefox acceptance/release gates.
