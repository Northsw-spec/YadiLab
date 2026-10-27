# IMPORT-003 — One-click native network document import

Parent: IMPORT-002 (commit `f615d41f44ef478200c0b571050d93618e1ec4f4`). This development checkpoint does not alter the original user-verified Dev11 commit `8fbf429f2eeab83066ae78d49d64ff9483868b2e`.

## Reproduced defect

The IMPORT-002 `MAIN ACTIONS` button set a React boolean that rendered an import panel **below** the mission banner. It never launched the operating system’s file picker. The panel appeared near the viewport bottom (or farther below on smaller screens), making the button appear inert. The previous test only asserted source strings and the production bundle, not a real browser click.

## Repair

- A primary user click now synchronously calls the native `<input type=file>.click()` handler; browsers require the file chooser to originate in the user gesture.
- After selection, the exact same existing `previewNetworkTopologyFile()` reader/validator runs; `.xlsx`, `.ods`, `.csv` and `.tsv` remain supported. The selected file is cleared from the input, permitting repeated imports of the same file.
- Import preview uses a foreground accessible dialog (`role=dialog`, `aria-modal=true`) rather than a panel hidden below the header. It opens even if the user cancels the native file picker. Escape and Close dismiss it without overwriting the current workspace.
- Only the separately labeled **Create topology in Builder** action may replace the workspace, and only when preview/compilation/layout checks pass.
- Linux version `1.8.0-dev.13`, build checkpoint `IMPORT-003`, default port `18235`; the launcher checks a marker to prevent accidental old-app reuse.
- No Word/PDF parsing added. No inferred links from IP addresses.

## Evidence and limitations

- Browser click integration using Chromium and the actual compiled `ui/dist/assets/app.js` injected into an offline page: native filechooser event, real CSV preview (four devices, three links), and blocked invalid link case.
- Exact-source compiler validation in Node, plus previous Dev11 regression tests and production browser build.
- The offline injected test page has an opaque `about:blank` origin without `crypto.subtle`. Therefore, it cannot validate the final **Create topology** action in Chromium without a secure HTTP origin. That activation must be tested on Parrot at `http://127.0.0.1:18235/`. This limitation is **not** represented as a PASS.
- This is a development candidate until the user tests it on Parrot.
