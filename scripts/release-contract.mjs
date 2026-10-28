/** One source of truth: package.json version + yadilabRelease fields.
 * Lockfile and Git identity are independent fail-closed cross-checks.
 */
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const VERSION = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const CHECKPOINT = /^[A-Z]+-[0-9]{3,}$/;
const SHA = /^[0-9a-f]{40}$/;
function json(filename) { return JSON.parse(fs.readFileSync(filename, "utf8")); }
function git(root, ...args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
}
export function readReleaseContract(root, { requireGit = true } = {}) {
  const pkg = json(path.join(root, "package.json"));
  const lock = json(path.join(root, "package-lock.json"));
  const version = pkg.version;
  const checkpoint = pkg.yadilabRelease?.checkpoint;
  const description = pkg.yadilabRelease?.description;
  if (typeof version !== "string" || !VERSION.test(version) || typeof checkpoint !== "string" || !CHECKPOINT.test(checkpoint) || typeof description !== "string" || !description.trim()) {
    throw new Error("RELEASE_CONTRACT_INVALID: package.json is the authoritative version/checkpoint/description declaration");
  }
  if (lock.version !== version || lock.packages?.[""]?.version !== version || lock.name !== pkg.name || lock.packages?.[""]?.name !== pkg.name) {
    throw new Error("RELEASE_LOCK_MISMATCH: package-lock.json differs from authoritative package.json");
  }
  const contract = { version, checkpoint, description };
  if (!requireGit) return contract;
  let commit, tree, status;
  try {
    commit = git(root, "rev-parse", "--verify", "HEAD^{commit}");
    tree = git(root, "rev-parse", "HEAD^{tree}");
    status = git(root, "status", "--porcelain", "--untracked-files=no");
    if (git(root, "rev-parse", "--show-toplevel") !== fs.realpathSync(root)) throw new Error("not repository root");
  } catch (error) { throw new Error(`RELEASE_GIT_UNVERIFIED: real Git HEAD required: ${error.message}`); }
  if (!SHA.test(commit) || !SHA.test(tree)) throw new Error("RELEASE_GIT_INVALID: invalid Git commit/tree");
  if (status) throw new Error(`RELEASE_GIT_DIRTY: cannot release modified tracked files: ${status.slice(0, 350)}`);
  if (process.env.YADILAB_EXPECTED_COMMIT && process.env.YADILAB_EXPECTED_COMMIT !== commit) {
    throw new Error("RELEASE_COMMIT_MISMATCH: checked out HEAD differs from required commit");
  }
  return { ...contract, sourceCommit: commit, sourceTree: tree };
}

export function assertBundledRelease(dir, release) {
  const marker = json(path.join(dir, "build-marker.json"));
  const expected = { version: release.version, checkpoint: release.checkpoint, marker: `yadilab-v${release.version}`, sourceCommit: release.sourceCommit, sourceTree: release.sourceTree };
  if (marker.formatId !== "yadilab.browser-build-marker" || Object.entries(expected).some(([k,v]) => marker[k] !== v) || !SHA.test(marker.sourceCommit ?? "") || !SHA.test(marker.sourceTree ?? "")) {
    throw new Error("RELEASE_MARKER_MISMATCH: build-marker.json does not describe the verified Git source");
  }
  const js = fs.readFileSync(path.join(dir, "assets/app.js"), "utf8");
  // Defense-in-depth: compiled UI must contain the committed identity, not just a rewritten build marker.
  for (const value of [release.version, release.checkpoint, release.sourceCommit]) {
    if (!js.includes(value)) throw new Error(`RELEASE_UI_MISMATCH: compiled UI omits ${value}`);
  }
  if (!js.includes("data-yadilab-build-version") || !js.includes("data-development-checkpoint") || !js.includes("data-source-commit")) {
    throw new Error("RELEASE_UI_MARKER_MISSING: actual rendered UI identity contract absent");
  }
  return marker;
}
