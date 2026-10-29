# DRAWIO-P3 — frozen source-bound compressed page oracles

**Status at creation: PLANNED / UNIMPLEMENTED / NOT_TESTED.** Canonical baseline `main=802fab085406a193fc9ed08df8bb0a7a8bc3418e`, tree `b2fc3acad411fe2cbe424103f9ae72b2dd851b9b`; no open PRs. `AGENTS.md` applies. PREP must precede parser changes. No local diagrams.net installation or user manual tests needed for synthetic Chromium CI.

## Primary format/technology sources
- diagrams.net official file format wiki, `Graph.compress` / `Graph.decompress`: https://github.com/jgraph/drawio/wiki/File-Format
- diagrams.net official generation guide: https://www.drawio.com/docs/reference/diagram-generation/
- MDN `DecompressionStream("deflate-raw")`: https://developer.mozilla.org/en-US/docs/Web/API/DecompressionStream/DecompressionStream

Official page content encoding: `<diagram id="...">Base64(rawDeflate(encodeURIComponent(mxGraphModelXML)))</diagram>`. Decode Base64 bytes strictly; stream DEFLATE-raw to bounded UTF-8 ASCII percent-encoded text; decodeURIComponent once; parse resulting `mxGraphModel` using existing strict `parseSafeXml` and exactly the same P1/P2 structural validators. The `<mxfile>` itself is uncompressed XML. Process pages sequentially, NOT in parallel. No network requests or dependencies.

## Frozen limits and privacy
- Original `.drawio` size ≤2 MiB; max 16 pages (existing P1). Strict maximum *base64 text* 512 KiB / page; strict alphabet/canonical base64 and padding, no whitespace/internal data URLs; compressed binary ≤384 KiB / page. Raw DEFLATE only; zlib-wrapped/gzip/repeated payload fails.
- Streamed output of raw DEFLATE ≤1 MiB per page, total decompressed percent-encoded bytes across pages ≤4 MiB, with explicit reader cancellation on over-limit, no `Response.arrayBuffer()` or whole unbounded buffer read. Decompression errors, unsupported browsers or stream failures must return stable `DRAWIO_*` error code without any untrusted input.
- Require decompressed bytes **ASCII only**, not UTF-8 multibyte or NUL. Run `decodeURIComponent` exactly once and cap decoded XML UTF-8 length ≤1 MiB/page; reject malformed percent-escapes, control chars, URI encodings that would result in forbidden XML/DTD/PI via the shared parser. Validate re-parsed root exactly `mxGraphModel`. No nested `mxfile`, executable content, external image render or style interpretation.
- Preserve SHA256 over *original, unmodified .drawio bytes*, existing original P1/P2 `profileId`, `TOPOLOGY_DECLARED`, status `PREVIEW_ONLY`, exactly the same aggregate vertex/edge counts, no page/node IDs, IPs, names, labels, SVG/HTML, source endpoints or XML in result/DOM/errors/export. Add only `compressedPageCount` numeric field so users can tell what was decoded. No Builder/ScenarioSource/Engine mutation or topology verification.
- Valid mixed uncompressed and compressed `diagram` children are accepted with explicit local handling per page, but `mxfile compressed="false"` plus compressed page, and `compressed="true"` plus embedded uncompressed model are contradictory and BLOCKED. Bare `mxGraphModel` remains supported as before. Unsupported groups, UserObject, layers and diagram wrappers remain unsupported per P1.
- Runtime without native `DecompressionStream("deflate-raw")` BLOCKED; no fallback or guessed parsing.

## Independent positive synthetic oracles
1. Two-page `mxfile`: page 0 compressed per **independent Node zlib deflateRawSync + encodeURIComponent**, two vertices and one drawn edge; page 1 uncompressed, one vertex. Expected pages=2, vertices=3, edges=1, compressedPageCount=1, source SHA unchanged. A second test has both pages compressed; a third is one compressed page. Use real browser's native decompressor at CI.
2. Compare compressed and equivalent uncompressed structural summaries (excluding original SHA/compression count) deterministically. No leaks of malware-looking labels or IP/hosts in any return/DOM. Original source bytes preserved.
3. Actual **compiled Chromium**: local file picker, valid compressed and mixed pages, invalid/XXE/over-limit replacements clear prior PASS, close/reopen reset, no external requests, exact unmodified canonical Builder JSON and no Engine activation.

## Required fail-closed adversarial cases
Invalid/missing padding, malformed alphabet, whitespace, base64 that is valid but not DEFLATE, zlib-wrapped DEFLATE, malformed percent sequence, double encoded XML, non-ASCII raw inflated output, compressed XML wrong root, malformed mxGraphModel, DTD/ENTITY/stylesheet PI inside inflated XML, outer DTD/invalid UTF-8, mixed page-content, contradiction with compressed flag, truncated DEFLATE, forged huge inflate bomb output >1MiB/per-page and aggregate >4MiB, inflated XML huge node counts, oversized compressed/outer file, nested group parent, dangling edge, 17 pages. Error code never includes source strings; no partial success. Regressions P1/P2 acceptance may need version-adjusted contradictory-case expectations **only** if explained and pinned in tests, never silently weakened.

## Required merge and release
All independent source/SSR tests, genuine compiled Chromium and existing import/safety workflows must be SUCCESS **on the same exact PR head** before squash merge. Verify merged-main Linux-release SUCCESS and artifact. NOT_RUN Parrot remains NOT_RUN (per CI-first policy). GitHub journal Issue #3 gets exact SHAs, red/fixed cycles, CI and artifact IDs. Limit scope strictly to compression support.
