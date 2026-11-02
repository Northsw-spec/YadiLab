# SCALE-001 P1a — large Office source table structure, frozen oracle

**Date:** 2026-11-02. **Starting source:** protected SCALE-001 P0 merged main `bbd809c81de966286c4e7f59ebeaf34bf3aa6f3d`. No P1a pass or P0 independent release inferred from this file.

## Strictly limited first scale slice

New versioned opt-in capacity key: `office.scaled-structural-review.v1`, **structure-only**, 1,000 source rows in Devices plus 999 Links rows (with headers: 1001 and 1000 rows), up to 20,000 structural cells in aggregate, max 16 cells per row, max 20 tables, XML part max 4 MiB, original compressed ZIP max 16 MiB, existing decompression/archive budgets and all active/embedded/relationship/markup bans preserved. This new path is NOT an active import adapter or reviewed Builder candidate, does not reveal cell content, and cannot justify an Engine PASS, physical link or runtime activation. The existing no-option original DOCX/ODT structural previews MUST remain bounded to 200 rows per table, 2,000 total cells, 1 MiB part, and all P4–P10 flows remain unchanged. Invalid/surplus capacity options fail closed. Both DOCX and ODT are required.

## Independent synthetic source oracles (must precede product code)

1. Genuine DOCX and ODT ZIPs with 100 declared device IDs/99 explicitly tabulated Links rows, and 1,000 IDs/999 original Links rows; 2-table original sources, each with one header row.
2. Without separate explicit opt-in, existing 1,000-row original previews throw `DOCX_ROW_COUNT_UNSUPPORTED` or `ODT_ROW_COUNT_UNSUPPORTED`. New scoped opt-in reveals ONLY structural ordinals, lengths and source-bound locators, exact original SHA, no header, device ID, IP, password or cell text in the preview result.
3. Both formats preserve original table ordinals and source SHA for the final device and link cells, counts (at 1,000: 1001 device table rows, 1000 link table rows and 6002 cells), and status `REVIEW_REQUIRED`, `canActivate:false`, `engineVerified:false`, `physicalTopologyVerified:false`.
4. Surplus 1002-row table (incl. header), arbitrary capacity flag/fields and unsupported markup are blocked; old security/provenance test gates unchanged. This preview is NOT a benchmark of 1,000 actual SVG nodes, a bulk approval of original cells, or a claim that DOCX/ODT imports 1,000 network devices into Builder.

## Frozen-red/green evidence process

Commit this plan and original 100/1000 DOCX/ODT real ZIP test before production changes, add shared P1a npm test to mandatory Ubuntu PR and independent exact-main Linux release gate. First observe failed required CI on pre-implementation P1a cases; do not merge red. Then isolate minimal parser-budget changes by explicit profile selector, preserve P4–P10 and old no-option behavior. Require latest-HEAD 5/5 SUCCESS, real logs, protected SHA-guarded merge, independent Linux+Chromium exact-main release with two distinct valid artifacts. Then P1b implements **separate** source-indexed consented batch review without N repeated whole-ZIP parses and exact Builder identity, followed by real scalable DOM navigation.
