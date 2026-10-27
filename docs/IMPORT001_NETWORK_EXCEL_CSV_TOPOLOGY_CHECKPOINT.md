# IMPORT-001 — Network Excel/CSV → Builder topology

Status: **development checkpoint / automated verification only**. The canonical user-verified Dev11 source archive is unchanged; this work is a later commit on top of its tree SHA `6a7bf6894cd67d38717c35b2ed3d37cfb1160657` (GitHub commit `8fbf429f2eeab83066ae78d49d64ff9483868b2e`). Do not relabel IMPORT-001 as the historical user-verified Dev11 without an independent human acceptance run.

## UI

The main menu `Import / Export` now contains **Import Network from Excel / CSV** in runtime and Builder. This opens a dedicated top-level panel with file chooser (`.xlsx`, `.ods`, `.csv`, `.tsv`), detected sheet names, device count, explicit link count, diagnostics, and a separate **Create topology in Builder (replace current workspace)** action. No file selection or preview replaces the running lab. Activation requires a valid parsed source, a successful schema/compiler pass, and a successful layout; failure preserves the current workspace.

This is distinct from JSON-based progress import, sessions, and native scenario import. Those older actions remain unchanged.

## Formats and deterministic semantics

Input types:
- Excel `.xlsx` / LibreOffice `.ods` with `Devices` rows (`Asset ID`, `Hostname`, `Device Type`, `IP Address`, optional `Connected To`, `Default Gateway`) or with canonical `Metadata`, `Nodes`, `Interfaces`, `Links` sheets.
- CSV / TSV `Devices` records with equivalent headers. An example is `examples/enterprise-import/network-devices-example.csv`.
- A dedicated `Links` sheet may declare `Link ID`, `From`, `To`, `From Port`, `To Port`, or the canonical `linkId`, `nodeA`, `nodeB`, `interfaceA`, `interfaceB` fields.

Device roles (when explicitly declared): Switch → `network.switch`, Router → `network.router`, Firewall → `network.firewall`, Server → `server.generic`, Windows → `endpoint.windows`, Linux → `endpoint.linux`. Unknown or omitted roles stay `resource.generic` with a warning. IP addresses become interface addresses. Default-gateway values are preserved as source notes **without** turning into inferred links, routes, or reachability claims.

**Physical connections appear only when a source explicitly declares a peer** (`Connected To` or `Links` sheet). Missing connections produce a visible warning and isolated devices; missing/invalid targets, duplicate device IDs, and invalid IPv4 values cause a blocked preview. No IP/subnet/gateway-based cabling inference. The canonical workbook adapter's existing safe archive/active-content checks remain in effect.

Unsupported: unstructured Word/PDF extraction, topology inference from arbitrary drawings, active network discovery, vendor-proprietary spreadsheets without a deterministic header mapping. Inputs do not deploy or configure any network.

## Tests and limitations

Run:

```bash
npm run test:network-topology-import
npm run test:workbook
npm run test:import-helper
npm run test:dev11-ui
npm run build:browser
```

The new tests assert: expected device types and IP addresses, true explicit links, no invented links from default gateways, invalid endpoints/duplicates/IPv4 are blocked, unknown type remains generic, an actual `.xlsx` template parses, source schema validates, and the imported scenario compiles with real Dev11 compiler options.

**Manual browser acceptance on Parrot remains pending.** Chromium automation in the build environment returned `ERR_BLOCKED_BY_ADMINISTRATOR` on loopback navigation; do not convert that into a browser PASS. The standard user-visible Dev11 version marker remains unchanged.

## User acceptance procedure

1. Launch a freshly built application on Parrot and open `http://127.0.0.1:18233/`.
2. While runtime is active, open `Import / Export → Import Network from Excel / CSV`.
3. Choose `examples/enterprise-import/network-devices-example.csv`; expect **4 devices** and **3 explicit links** in the preview.
4. Verify the prior runtime/topology has not changed; click **Create topology in Builder** to apply.
5. Confirm switch/router/Windows/server nodes and only the three declared connections are drawn.
6. Try a spreadsheet without `Connected To`: check that there are no invented links.
7. Try a `Connected To` value pointing at an unknown device: expect **BLOCKED**, no replacement.
8. Re-test Dev11 Verified Delivery success, drop, and mixed paths to ensure legacy PASS is retained.
