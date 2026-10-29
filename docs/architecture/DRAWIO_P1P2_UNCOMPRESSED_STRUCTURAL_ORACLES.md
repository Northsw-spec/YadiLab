# DRAWIO-P1/P2 — frozen uncompressed structural-preview oracles

**PREP status at first commit: PLANNED / NOT_IMPLEMENTED / NOT_TESTED.**
Canonical code at start `main=df3625b103089b8272694f6ed81cdb756a53a218`, tree `bef69c0b8a3091692a5b68b2ab192453d6ba6e1b`; observe `AGENTS.md`. No historical archive is a source baseline.

## Evidence and deliberately restricted profile
- Official diagrams.net file-format specification: https://github.com/jgraph/drawio/wiki/File-Format
- Official diagrams.net generation and validation reference: https://www.drawio.com/docs/reference/diagram-generation/
- Official export options: https://www.drawio.com/docs/manual/export/export-to-xml/
- Existing canonical `enterprise-import/src/xml-lite.ts`, `graphml-preview.ts`, `ui/src/browser/graphml-import-preview.ts`, and isolated panels are the implementation constraints.
- Accept a local `.drawio` basename, max 2 MiB, containing strict UTF-8 `mxfile` with 1–16 unique `diagram` children each with **exactly one direct, uncompressed** `mxGraphModel` and one `root` of `mxCell` elements; accept bare `mxGraphModel` as a one-page profile. The `mxCell` root must include distinct structural cells `id="0"` (no parent) and `id="1" parent="0"`. Other cells have unique bounded IDs and parent in the supported layer `1`, with `vertex="1"` XOR `edge="1"`. Edges require explicit, distinct or same existing vertex source and target IDs. Shape geometry under `mxCell` may be `mxGeometry`; do not interpret coordinates, styles, labels or embedded HTML. Reject unknown wrappers, nested parent/group hierarchy, extra graph roots, inline library content, dangling edges and unsupported profile variants instead of fabricating partial counts.
- Compressed `diagram` text is **NOT IMPLEMENTED** in this checkpoint (stable `DRAWIO_COMPRESSED_UNSUPPORTED`). No implicit deflate, no new dependencies or remote conversion. Likewise `.xml`, `.drawio.svg`, `.png` and SVG/HTML wrapper files remain unsupported.
- Structure preview is a **metadata-only aggregate**: `status:PREVIEW_ONLY`, `semanticTrack:TOPOLOGY_DECLARED`, `canActivate:false`, `engineVerified:false`, `physicalTopologyVerified:false`, `modelMutated:false`, `sourceSha256`, bounded array of per-page ordinal + vertex and drawn-edge counts, totals. **No page names, node IDs, labels, IP addresses, styles, XML fragments, connection endpoints, geometry or plugin data in returned data, DOM, error messages or exports.** Do not claim that drawn edges represent actual cables or traffic; no Builder, Engine, network operations or topology mutations.

## Positive oracles (frozen before implementation)
- Independently generated valid two-page, uncompressed `mxfile`: page 0 has root cells 0/1, two vertex cells and one edge referencing them; page 1 has one vertex, no edges. Expected pageCount 2, vertexCount 3, drawnEdgeCount 1, per-page [2/1,1/0]. SHA256 must be over **original full bytes**. Malicious HTML and private host values in shape labels/page names must not appear in UI, returned JSON, error strings or logs. A bare `mxGraphModel` with valid root should count one page.
- Real compiled YadiLab Chromium UI: choose local `.drawio`; inspect counts and source hash; invalid and compressed replacements clear previous preview; closing/reopening resets; exported canonical Builder JSON and active scenario unchanged; no external request or error; no activation button. Synthetic files only, no diagrams.net installation required.

## Adversarial fail-closed oracles
- Wrong root (GraphML/Nmap/Nessus), `.xml` spoof, path traversal/invalid filename, zero/oversized and invalid arrayBuffer; DTD/ENTITY/XXE, invalid UTF-8, stylesheet PI, NUL; compressed page, empty page, mixed compressed+uncompressed, duplicate/missing page IDs, >16 pages, duplicate/missing root cells, duplicate ID within page, missing or wrong parent, duplicate/dangling/unknown edge endpoint, conflicting vertex/edge flags, unsupported children/wrappers, >1000 vertices or >2000 edges, unsupported nested groups. No raw attacker-controlled strings in error messages.
- Bound XML parse complexity using existing `parseSafeXml` (DTD/XXE rejection). No change to shared parser and no dependency addition.
- Additive import menu only. Nmap/Nessus/GraphML/DOCX/ODT/Ansible and release-integrity suites stay green at exact PR-head; genuine Chromium check and Linux postmerge release required.

## Truth statement
The original editor's vector drawing is `TOPOLOGY_DECLARED` metadata only. Structural XML validation is neither diagrams.net cross-version compatibility proof nor validation of infrastructure, asset identity, link existence, network state or Engine result. Later compressed support or manual reviewed mapping requires separate checkpoints.
