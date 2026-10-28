# IMPORT-004: Imported Inventory -> Modeled Runtime Probes

Status: development checkpoint; manual Parrot verification pending.

## Verified parent checkpoint
User-confirmed IMPORT-003 GitHub commit `eedbbdc4b48607889c6b203c977a0ca4df238d76` remains unchanged as a Git ancestor. Original user-verified Dev11 source archive SHA-256: `cce1deddc0b28b5b1b1c0aa467731d9cbfa2aa6be65f2db088c46c93846372d1`.

## Root cause
Document-import activation previously left the workspace in Builder; active probes require Runtime. Also `endpoint.windows`/`endpoint.linux` (explicit node types in a canonical Excel workbook) were not recognized by the observation/active-probe OS allowlist. This yielded no valid probe sources even when the learner found the Runtime panel.

## Repair
- Preserve the existing **Create topology in Builder (edit only)** action.
- Add **Open modeled Runtime + Probes**, which compiles + lays out the imported source, calls the existing `previewRuntime`, and rejects activation when no known Windows/Linux source host is present.
- Explicitly treat `endpoint.windows` and `endpoint.linux` as their declared OS; never infer OS from hostnames, addresses, zones or `server.generic`.
- Open the existing Active Probe panel upon Runtime activation and expose a visible **Run Modeled Probes** control in Runtime.
- Leave the original workbook, imported source resources, IPs, links, topology layout and Engine truth untouched.

## Truth boundary
These are **simulated, read-only** queries against YadiLab's Engine state, not real pings, TCP sockets, DNS requests or scans of a municipal network. The workbook is synthetic. The presence of Nodes, Interfaces and Links alone does **not** prove routing, firewall policy, switch forwarding, listener state or DNS. The Engine may correctly return UNKNOWN or FALSE. Never synthesize `TRUE`, a green delivery marker, an IP route, ACL, DNS server, DHCP lease or listener.

## Tests
`npm run test:network-topology-import`; `node tests/browser/run_import004_probe_runtime_tests.mjs` after `tsc -p tests/tsconfig.browser.json`; `npm run test:dev11-ui`; `npm run build:browser`; browser UI smoke test optional. Test with the separately supplied (not checked in) Arvidsjaur workbook using `YADILAB_IMPORT004_TEST_XLSX=...`.
