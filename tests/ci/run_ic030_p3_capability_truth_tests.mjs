import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = file => readFileSync(file, "utf8");
const audit = JSON.parse(read("docs/architecture/import-capability-matrix.v1.json"));
assert.equal(audit.formatId, "yadilab.import.capability-audit");
assert.equal(audit.schemaVersion, "1.0.0");
assert.equal(audit.status, "SOURCE_AUDIT_NOT_FUNCTIONAL_CERTIFICATION");
assert.equal(audit.profiles.length, 27, "Changing format inventory requires a separate profile audit");
assert.equal(new Set(audit.profiles.map(p => p.id)).size, 27, "Duplicate profile ID");
const byId = new Map(audit.profiles.map(p => [p.id, p]));
const graphml = byId.get("graphml.structural.v1");
const drawio = byId.get("diagrams.drawio.v1");
assert.ok(graphml && drawio, "Both specialized GraphML/diagrams.net profiles must be present");
assert.equal(graphml.registry, "PLANNED_HINT",
  "Specialized GraphML preview/Builder is NOT an active generic enterprise adapter");
assert.equal(drawio.registry, "PLANNED_HINT",
  "Specialized diagrams.net preview/Builder is NOT an active generic enterprise adapter");
const graphStages = {
  detect: "SPECIALIZED_GRAPHML_FILE_ENTRY",
  parse: "BOUNDED_GRAPHML_ORIGINAL_XML_SHA",
  review: "MANUAL_NODE_ROLES_FIRST_80_AND_UNDIRECTED_EDGES_ACK",
  projection: "EXPLICIT_REVIEWED_GRAPHML_WORKBOOK_CANDIDATE",
  builder: "REAL_COMPILER_ELK_ORIGINAL_REREAD_WORKSPACE_GATE",
  modeledProbe: "NOT_ATTESTED_NO_AUTOMATIC_RUNTIME"
};
const drawStages = {
  detect: "SPECIALIZED_DRAWIO_P1P6_XML_READ_ONLY_AND_P2B_DRAWIO_ONLY",
  parse: "BOUNDED_2MIB_16P_1000V_2000E_RAW_DEFLATE_SHA",
  review: "P1P6_REFERENCE_ONLY_OR_P2B_1_TO_20_EXPLICIT_NODES_EDGES_ACK",
  projection: "P2B_EXPLICIT_REVIEWED_DRAWIO_GRAPH_CANDIDATE_ONLY",
  builder: "P2B_REAL_COMPILER_ELK_LAST_ORIGINAL_REREAD_WORKSPACE_GATE",
  modeledProbe: "NOT_ATTESTED_NO_AUTOMATIC_RUNTIME",
  replay: "P1P6_REFERENCE_REPORT_ONLY_P2B_CANDIDATE_NOT_REPLAYED"
};
for (const [field, value] of Object.entries(graphStages))
  assert.equal(graphml.stage[field], value, "GraphML capability over/under-claim: " + field);
for (const [field, value] of Object.entries(drawStages))
  assert.equal(drawio.stage[field], value, "Drawio capability over/under-claim: " + field);
assert.ok(graphml.ciCoverage.startsWith("REQUIRED_AND_POSTMERGE_"),
  "GraphML is not dedicated-CI-only after IC-030 P1");
assert.ok(drawio.ciCoverage.startsWith("REQUIRED_AND_POSTMERGE_"),
  "P2b actual Chromium evidence must be reflected, not marked reference-only");
for (const p of [graphml, drawio]) {
  assert.equal(p.nextCheckpoint, "IC-030_P3_SCOPED_EXIT_GATE");
  assert.match(p.risk, /NOT_ATTESTED|not attested/i,
    "Unverified modeled probes/physical truth must be explained");
  for (const file of [...p.sources, ...p.tests]) assert.doesNotThrow(
    () => read(file), "Matrix cites a missing actual source/test: " + file);
}
const active = audit.profiles.filter(p => p.registry === "ACTIVE_ADAPTER");
assert.equal(active.length, 5, "The baseline generic enterprise adapters must remain five");
const graphSource = read("enterprise-import/src/graphml-review-mapping.ts");
const graphUI = read("ui/app/graphml-preview-panel.mjs");
const graphFile = read("ui/src/browser/graphml-import-preview.ts");
const drawSource = read("enterprise-import/src/drawio-reviewed-candidate.ts");
const drawFile = read("ui/src/browser/drawio-reviewed-candidate-file.ts");
const drawUI = read("ui/app/drawio-reviewed-builder-panel.mjs");
const mainUI = read("ui/app/main.mjs");
assert.ok(graphSource.includes("graphml_manual_verification"),
  "Reviewed GraphML source must not be automatically marked verified");
assert.ok(graphSource.includes("GRAPHML_DIRECTIONAL_EDGE_UNSUPPORTED"),
  "Directed graph edges must not be mapped to undirected physical links");
assert.ok(graphUI.includes("MAX_VISIBLE_ROWS = 80"),
  "GraphML manual review scope must be bounded and the matrix must not claim full node selection");
assert.ok(graphUI.includes("acknowledgeModeledConnections"),
  "GraphML connections require explicit acknowledgment");
assert.ok(graphFile.includes("verifyGraphmlOriginalForReviewedActivation"),
  "GraphML original must be reread for manual Builder activation");
assert.ok(drawSource.includes("DRAWIO_GRAPH_MAX_SELECTED = 20"),
  "P2b user-selected positions must remain bounded");
assert.ok(drawSource.includes("drawio_manual_verification"),
  "A reviewed drawn link must not invent Engine PASS");
assert.ok(drawSource.includes("DRAWIO_CONNECTION_ACK_REQUIRED"),
  "Drawio modeled connections must need an explicit acknowledgement");
assert.ok(drawFile.includes("verifyDrawioOriginalForReviewedActivation"),
  "Drawio original must be checked immediately before UI commit");
assert.ok(drawFile.includes('.drawio$'), "P2b accepts .drawio originals only, not arbitrary XML");
assert.ok(drawUI.includes("PAGE_SIZE=20"), "P2b UI pagination is bounded");
assert.ok(drawUI.includes("data-drawio-candidate-confirm"), "P2b Builder action requires explicit user confirmation");
for (const marker of [
  "verifyGraphmlOriginalForReviewedActivation",
  "verifyDrawioOriginalForReviewedActivation",
  "IC030_P1_WORKSPACE_CHANGED", "IC030_P2B_WORKSPACE_CHANGED",
  "GraphmlReadOnlyPanel", "DrawioReviewedBuilderPanel"
]) assert.ok(mainUI.includes(marker), "Actual app missing source/workspace gate: " + marker);
const required = read(".github/workflows/required-ci.yml");
const release = read(".github/workflows/release-identity.yml");
for (const [name, content] of [["required", required], ["release", release]]) {
  for (const marker of [
    "node tests/ci/run_ic030_p3_capability_truth_tests.mjs",
    "npm run test:ic030-p1-graphml-freshness",
    "npm run test:ic030-p2a-drawio-candidate",
    "npm run test:ic030-p2b-drawio-ui",
    "run_ic030_p1_graphml_real_browser.py",
    "run_ic030_p2b_drawio_real_browser.py",
    "node tests/ci/run_ubuntu_browser_mirror_contract_tests.mjs",
    "node tests/ci/run_pr_concurrency_contract_tests.mjs"
  ]) assert.ok(content.includes(marker), name + " CI/release lost independent gate " + marker);
}
assert.ok(required.includes("yadilab-required-ci:"), "Protected required job name must remain");
assert.ok(release.includes("linux-attested:"), "Independent Linux release must remain");
assert.ok(!release.includes("cancel-in-progress:"),
  "Main release must not gain automatic PR cancellation");
console.log("PASS IC-030 P3 source-truth: 27 profiles intact; GraphML and diagrams.net reviewed Builder accurately scoped, no invented Runtime/probe truth; required CI and independent Chromium release retained");
