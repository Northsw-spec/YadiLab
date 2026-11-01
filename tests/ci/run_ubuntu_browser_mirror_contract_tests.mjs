import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const helper="scripts/ci-normalize-ubuntu-mirror.sh";
const body=readFileSync(helper,"utf8");
const syntax=spawnSync("bash",["-n",helper],{encoding:"utf8"});
assert.equal(syntax.status,0,"CI-only Ubuntu mirror normalization must be valid bash: "+syntax.stderr);
assert.ok(body.includes("set -Eeuo pipefail"),"Mirror correction must fail closed");
assert.ok(body.includes("azure.archive.ubuntu.com/ubuntu"),"Only specific failing Ubuntu mirror rewritten");
assert.ok(body.includes("archive.ubuntu.com/ubuntu"),"Replace with canonical Ubuntu archive");
assert.ok(body.includes("sudo sed -i"),"Runner-local APT configuration only");
assert.ok(body.includes("exit 1"),"Unexpected mirror configuration must BLOCK");
for(const unsafe of ["playwright install --no-shell","apt-get install -y --force-yes","--allow-unauthenticated","npm install","git push"]){
 assert.equal(body.includes(unsafe),false,"No dependency or security policy bypass: "+unsafe);
}
const paths=readdirSync(".github/workflows").filter(x=>x.endsWith(".yml")).sort();
let guarded=0;
for(const path of paths){
 const source=readFileSync(".github/workflows/"+path,"utf8");
 if(!source.includes("playwright install --with-deps chromium"))continue;
 const externalHelper=source.includes("bash scripts/ci-normalize-ubuntu-mirror.sh");
 const legacyInline=source.includes("sudo sed -i") &&
   source.includes("azure.archive.ubuntu.com/ubuntu") &&
   source.includes("archive.ubuntu.com/ubuntu");
 assert.ok(externalHelper||legacyInline,
   "Chromium dependency installation on ubuntu-24.04 has no Azure mirror normalization: "+path);
 assert.equal(source.includes("playwright install --with-deps chromium"),true,
   "Required operating-system Chromium dependencies must stay enabled");
 guarded++;
}
assert.ok(guarded>=30,"Unexpected removal of independent Chromium acceptance gates");
for(const critical of [
 "graphml-p2c-real-browser.yml","docx-tables-p2-real-browser.yml",
 "ansible-ini-p6-real-browser.yml","ansible-yaml-p5-real-browser.yml",
 "docx-p4-real-browser.yml","docx-p6-real-browser.yml",
 "required-ci.yml","release-identity.yml"
]){
 const source=readFileSync(".github/workflows/"+critical,"utf8");
 assert.ok(source.includes("playwright install --with-deps chromium"),
   "Existing critical Chromium acceptance removed: "+critical);
}
console.log("PASS CI Ubuntu Chromium mirror source/security contract: "+guarded+
 " independent pinned --with-deps workflows retained; syntax PASS, no bypass");
