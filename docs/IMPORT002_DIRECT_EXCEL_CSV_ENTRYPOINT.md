# IMPORT-002 — Always-visible Excel/CSV network import and correct build identity

Status: automated candidate. Human acceptance on Parrot OS pending.

Parent: IMPORT-001 at `2a4360f62e1562de186a9be9582bbe33737e34dd`.
Locked user-verified Dev11 source archive SHA-256: `cce1deddc0b28b5b1b1c0aa467731d9cbfa2aa6be65f2db088c46c93846372d1`.

## Fixed UX

- Previous IMPORT-001 entrypoint existed *only inside* collapsed `Import / Export` details. This was not discoverable enough; user reported seeing only the progress and session JSON operations.
- `MAIN ACTIONS` now displays a permanent primary button **Import Excel / CSV → Network Topology** above all collapsed menus in runtime *and* builder mode, with clear supported extension text.
- Button expands a standalone preview panel, with a second file-picker control and an explicit **Create topology in Builder (replace current workspace)** action. The source is parsed and validated before workspace replacement; errors block modification.
- Supported files: `.xlsx`, `.ods`, `.csv`, `.tsv`. **No** generic `.docx` / `.pdf` parsing.
- Connections are created only from explicit workbook `Links` / `Connected To`, never inferred from IP or gateway.
- Original old nested Import / Export action remains as alternative.

## Version clarity / stale-app isolation

- Version is `1.8.0-dev.12`, development checkpoint `IMPORT-002` in the UI.
- `package.json`, `package-lock.json`, browser manifest builder, and Linux startup HTTP marker agree on the version.
- Linux startup defaults to `http://127.0.0.1:18234/` (instead of legacy 18233) to isolate stale background servers and service workers. An explicit `YADILAB_PORT` override remains supported.
- Startup requires the exact version AND checkpoint fields in the HTTP build marker; a wrong or older app fails verification.

## Tests

- `npm run test:network-topology-import`
- `npm run test:dev11-ui`
- `npm run test:import-helper`
- `npm run build:browser`
- `npm run test:import002-ui`
- `YADILAB_TEST_ONCE=1 ./start-yadilab.sh` on the packaged release

Browser human acceptance: open port 18234 and confirm the top-level import button (without opening menus), select sample CSV and confirm preview shows four devices and three explicitly modeled links. Test an XLSX file and invalid references; verify replacement requires explicit confirmation. Check the header shows `v1.8.0-dev.12` and `IMPORT-002`. No user verification is claimed before that test.
