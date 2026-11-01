import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const workflowDir = ".github/workflows";
const workflows = readdirSync(workflowDir).filter(name => /\.ya?ml$/.test(name)).sort();
assert.equal(workflows.length, 43, "Review each newly added or deleted workflow before changing this frozen contract");
const expectedHeader = [
  "concurrency:",
  "  group: __DOLLAR__{{ github.workflow_ref }}-__DOLLAR__{{ github.event.pull_request.number || github.run_id }}",
  "  cancel-in-progress: __DOLLAR__{{ github.event_name == 'pull_request' }}",
  "",
  ""
].join("\n").replaceAll("__DOLLAR__", "$");
let prCount = 0, chromiumCount = 0;
for (const workflow of workflows) {
  const text = readFileSync(workflowDir + "/" + workflow, "utf8");
  assert.match(text, /^on:\s*$/m, "Must retain event entry point: " + workflow);
  const isPR = /^  pull_request:\s*$/m.test(text);
  const hasTopConcurrency = /^concurrency:\s*$/gm.test(text);
  if (isPR) {
    prCount++;
    assert.equal(text.split(expectedHeader).length - 1, 1,
      "PR workflow must have exact once scoped cancellation guard: " + workflow);
    assert.ok(text.indexOf(expectedHeader) < text.indexOf("\non:") + 1,
      "Concurrency must be at workflow top-level before event triggers: " + workflow);
    assert.equal(text.split(/^concurrency:\s*$/m).length - 1, 1,
      "No duplicate concurrency declarations: " + workflow);
    assert.equal(text.split("cancel-in-progress:").length - 1, 1,
      "No job-level or duplicate cancellation rules: " + workflow);
    assert.match(text, /^  workflow_dispatch:\s*$/m,
      "Existing independent manual evidence trigger retained: " + workflow);
  } else {
    assert.equal(workflow, "release-identity.yml", "Non-PR workflows must be audited explicitly");
    assert.equal(hasTopConcurrency, false, "Independent main release must not gain PR cancellation");
    assert.equal(text.includes("cancel-in-progress:"), false, "Release must not be automatically cancelled");
    assert.match(text, /^  push:\s*$/m, "Independent release still triggered by main push");
    assert.match(text, /^    branches: \[main\]\s*$/m, "Main release branch selector unchanged");
  }
  if (text.includes("playwright install --with-deps chromium")) chromiumCount++;
}
assert.equal(prCount, 42, "All current PR workflows must be covered");
assert.ok(chromiumCount >= 30, "Full real Chromium system dependency acceptance retained");
for (const critical of ["required-ci.yml", "release-identity.yml"]) {
  const content = readFileSync(workflowDir + "/" + critical, "utf8");
  assert.ok(content.includes("node tests/ci/run_pr_concurrency_contract_tests.mjs"),
    "New contract must execute in both premerge and independent postmerge workflows");
}
const required = readFileSync(workflowDir + "/required-ci.yml", "utf8");
assert.ok(required.includes("npm run test:ic030-p2b-drawio-ui"), "P2b source test cannot be removed");
assert.ok(required.includes("run_ic030_p2b_drawio_real_browser.py"), "P2b real Chromium cannot be removed");
assert.ok(required.includes("node tests/ci/run_ubuntu_browser_mirror_contract_tests.mjs"), "Ubuntu mirror safety contract retained");
assert.ok(required.includes("yadilab-required-ci:"), "Branch-protection status name must remain");
const release = readFileSync(workflowDir + "/release-identity.yml", "utf8");
assert.ok(release.includes("run_ic030_p2b_drawio_real_browser.py"), "Postmerge P2b browser gate retained");
assert.ok(release.includes("node tests/ci/run_ubuntu_browser_mirror_contract_tests.mjs"), "Postmerge mirror safety gate retained");
const group = (workflowRef, pr, runId) => workflowRef + "-" + (pr || runId);
assert.equal(group("repo/.github/workflows/a.yml@refs/pull/1/merge",1,100),
  group("repo/.github/workflows/a.yml@refs/pull/1/merge",1,101),
  "New commits in the same PR+workflow must share a group");
assert.notEqual(group("repo/.github/workflows/a.yml@refs/pull/1/merge",1,100),
  group("repo/.github/workflows/a.yml@refs/pull/2/merge",2,101),
  "Different PRs may not cancel each other");
assert.notEqual(group("repo/.github/workflows/a.yml@refs/pull/1/merge",1,100),
  group("repo/.github/workflows/b.yml@refs/pull/1/merge",1,100),
  "Different workflow files may not cancel each other");
assert.notEqual(group("repo/.github/workflows/a.yml@refs/heads/main",null,100),
  group("repo/.github/workflows/a.yml@refs/heads/main",null,101),
  "Non-PR fallback must be unique per run");
const mayCancel = eventName => eventName === "pull_request";
assert.equal(mayCancel("pull_request"), true);
for (const event of ["push","workflow_dispatch","release","workflow_run"])
  assert.equal(mayCancel(event), false, "Protected/non-PR evidence must never auto-cancel");
console.log("PASS YADILAB-CI-CONCURRENCY-001: " + prCount +
  " PR workflows isolated; non-PR release protected; " +
  chromiumCount + " real Chromium --with-deps gates retained");
