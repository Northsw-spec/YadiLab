import assert from "node:assert/strict";
import fs from "node:fs";
import crypto from "node:crypto";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { previewNmapXmlFileReadOnly } from "../../dist-browser-test/ui/src/browser/nmap-xml-file-preview.js";
import { NmapObservationPanel, NmapObservationDetails } from "../../ui/app/nmap-observation-panel.mjs";

let checks = 0;
const eq = (a,b,label) => { assert.deepEqual(a,b,label); checks++; };
const read = (name) => Uint8Array.from(fs.readFileSync("tests/fixtures/import/nmap-xml/" + name));
const valid = read("valid-observed-hosts.xml");
const named = (name, data = valid, size = data.length) => ({
  name, size, async arrayBuffer() {
    return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
  },
});
const rejects = async (file, code) => {
  await assert.rejects(previewNmapXmlFileReadOnly(file), (err) => err?.code === code, code);
  checks++;
};

const result = await previewNmapXmlFileReadOnly(named("scan.XML"));
eq(result.filename, "scan.XML");
eq(result.preview.status, "EVIDENCE_ONLY");
eq(result.preview.canActivate, false);
eq(result.preview.semanticTrack, "EVIDENCE_OBSERVED");
eq(result.preview.hosts.map((x) => [x.ipv4,x.observedStatus]), [["192.0.2.10","up"],["192.0.2.11","down"]]);
eq(result.preview.hosts[0].ports.map((x) => [x.protocol,x.port,x.observedState]),
  [["tcp",22,"open"],["tcp",443,"closed"]]);
eq(result.preview.sourceSha256, crypto.createHash("sha256").update(valid).digest("hex"));
eq(Object.hasOwn(result, "scenario"), false);
eq(Object.hasOwn(result, "workspace"), false);
eq(Object.hasOwn(result, "connections"), false);
eq(Object.hasOwn(result.preview, "engineState"), false);

const html = renderToStaticMarkup(React.createElement(NmapObservationDetails,{result}));
for (const token of [
  'data-nmap-observations="EVIDENCE_ONLY"',
  'data-nmap-summary="true"',
  'data-nmap-source-hash="true"',
  'data-nmap-host="0"',
  'data-nmap-host="1"',
  'data-nmap-port="0:0"',
  'data-nmap-activation-status="BLOCKED"',
  '192.0.2.10',
  'TCP/22',
  'observed open',
  'service hint: ssh',
  'EVIDENCE_OBSERVED',
  'No physical cables',
]) {
  assert.ok(html.includes(token), "Missing evidence-only UI: "+token); checks++;
}
const empty = renderToStaticMarkup(React.createElement(NmapObservationDetails,{result:null}));
eq(empty.includes('data-nmap-empty="true"'), true);
const panel = renderToStaticMarkup(React.createElement(NmapObservationPanel,{
  inspectFile: previewNmapXmlFileReadOnly, onClose() {},
}));
for (const token of [
  'role="dialog"', 'aria-modal="true"', 'data-nmap-panel="EVIDENCE_ONLY"',
  'data-nmap-file="true"', 'accept=".xml"', 'data-nmap-close="true"',
]) { assert.ok(panel.includes(token),token); checks++; }
eq(/data-nmap-confirm|data-nmap-activate|data-network-import-activate/.test(panel),false,"No import/activation button");
const hostile = {...result,preview:{...result.preview,hosts:[
  {...result.preview.hosts[0],hostnames:['<img src=x onerror=alert(1)>'],ports:[
    {...result.preview.hosts[0].ports[0],serviceName:'<script>alert(2)</script>'}
  ]}] }};
const escaped = renderToStaticMarkup(React.createElement(NmapObservationDetails,{result:hostile}));
eq(escaped.includes("<img src=x"),false,"No injected HTML image");
eq(escaped.includes("<script>alert(2)</script>"),false,"No injected script");
eq(escaped.includes("&lt;img"),true,"React must escape observed hostnames");
eq(escaped.includes("&lt;script&gt;"),true,"React must escape service hints");

const dialogSource = fs.readFileSync("ui/app/nmap-observation-panel.mjs","utf8");
const executable = dialogSource.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g,"");
const forbidden = /\bsetWorkspace\s*\(|\bonConfirm\s*[:=]|\bonActivate\s*[:=]|dangerouslySetInnerHTML/;
eq(forbidden.test(executable),false,"No workspace/activation/html injection APIs");
eq(forbidden.test(executable+"\nsetWorkspace(null);"),true,"Mutation negative control");
eq(forbidden.test(executable+"\ndangerouslySetInnerHTML: {}"),true,"Unsafe HTML negative control");
const main = fs.readFileSync("ui/app/main.mjs","utf8");
assert.match(main,/data-inspect-nmap": "EVIDENCE_ONLY"/); checks++;
assert.match(main,/onInspectNmap: \(\) => setNmapObservationOpen\(true\)/); checks++;
assert.match(main,/nmapObservationOpen \? e\(NmapObservationPanel, \{/); checks++;
assert.match(main,/inspectFile: previewNmapXmlFileReadOnly,/); checks++;
assert.match(main,/onClose: \(\) => setNmapObservationOpen\(false\),/); checks++;
const isolated = (source) => /nmapObservationOpen \? e\(NmapObservationPanel, \{[\s\S]*?inspectFile: previewNmapXmlFileReadOnly,[\s\S]*?onClose: \(\) => setNmapObservationOpen\(false\),[\s\S]*?\}\) : null,/.test(source);
eq(isolated(main),true);
eq(isolated(main.replace("inspectFile: previewNmapXmlFileReadOnly,","inspectFile: undefined,")),false,"Wiring negative control");

await rejects(named("graph.graphml"),"NMAP_XML_FILE_EXTENSION_INVALID");
await rejects(named("report.nessus"),"NMAP_XML_FILE_EXTENSION_INVALID");
await rejects(named("dir/scan.xml"),"NMAP_XML_FILE_EXTENSION_INVALID");
await rejects(named("empty.xml",new Uint8Array()),"NMAP_XML_FILE_SIZE_INVALID");
await rejects(named("big.xml",valid,2*1024*1024+1),"NMAP_XML_FILE_SIZE_INVALID");
await rejects(named("spoof.xml",read("invalid-wrong-root.xml")),"NMAP_XML_ROOT_INVALID");
await rejects(named("xxe.xml",read("adversarial-xxe.xml")),"IMPORT_XML_DTD_FORBIDDEN");
await rejects(named("bad-port.xml",read("invalid-port-range.xml")),"NMAP_XML_NUMBER_INVALID");

console.log("PASS NMAP-XML-P2: "+checks+" SSR, browser-file-bridge, hostile-label, no-activation and negative cases. Real browser separately gated.");
