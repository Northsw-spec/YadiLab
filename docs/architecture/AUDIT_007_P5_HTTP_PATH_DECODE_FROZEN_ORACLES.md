# AUDIT-007 P5 — FROZEN HTTP path decode exactly-once oracles

**Status at first commit:** TEST_FROZEN / REPRODUCTION_PENDING / PRODUCTION_UNCHANGED. Protected base `43fda5da2292d7a3e542eaae7864905a18c14845`, tree `7a64b70994bf4ea4d75bb5ef8558c979b9795bcd`; repo owner requires full-codebase AUDIT-007 before new imports ([AGENTS.md](../../AGENTS.md), [issue #96](https://github.com/Northsw-spec/YadiLab/issues/96)).

## Source hypothesis

Go `net/http` already provides a once-unescaped `r.URL.Path`. `launcher/server.go` checks the original encoded URL path for `%2e`, `%2f`, `%5c`, `%00`, then `resolve(r.URL.Path)` calls `url.PathUnescape(requestPath)` again. Two passes may make `/%252e%252e/index.html` alias root `/index.html`, `/nested%252fprivate.txt` alias `/nested/private.txt`, and deny legitimate literal filenames like `/100%25-complete.txt`. This is an address/resource identity correctness issue within configured static root; **not evidence of escape outside root or arbitrary disclosure**.

## Frozen reproducible negative and positive contract

`launcher/audit007_p5_path_decoding_test.go` uses real `httptest.NewRequest` + actual `staticServer.ServeHTTP` (not a helper mock), temporary local files and no external network:
- Direct `/nested/private.txt` serves exactly its content, while single `/nested%2fprivate.txt` is denied HTTP 400 (preserve existing policy).
- Double encoded `/nested%252fprivate.txt` MUST NOT resolve or return an unrelated nested resource. With no literal percent-file in root, returns HTTP 404.
- Direct root `/` succeeds and single `/%2e%2e/index.html` denies 400. Double `/%252e%252e/index.html` MUST NOT alias root; with no literal percent-named directory, HTTP 404.
- File literally named `literal%2fsegment.txt` must be accessible at `/literal%252fsegment.txt` and yield exact file content; no reinterpreted slash.
- File literally named `100%-complete.txt` must be accessible at `/100%25-complete.txt`, with exact body; second decoding must not reject the unescaped `%`.

**Required gates:** explicit `go test -count=1 -v ./launcher/... -run '^TestAudit007P5'` in BOTH required PR CI and independent exact-main Linux push release; preserved general `go test ./launcher/...`, Dev11, AUDIT-007 P1–P4, IC-040, real Chromium, AUDIT-006, Ubuntu security mirror. First prepatch CI failure is the reproduction and NEVER accepted as PASS. Production patch must be minimal: do not unescape `r.URL.Path` twice, preserve path/escaping checks, content-type/GET/HEAD and symlink boundary. Protected expected-head merge only after all latest-head check statuses/logs PASS; independent exact-main release and two valid artifact IDs before RELEASE_VERIFIED.

**Separate SUSPECTED (not part of P5):** `resolve()` performs `EvalSymlinks` before `ServeHTTP` separately `os.Open()`s the returned path. A filesystem-changing actor might exploit a symlink or regular-file swap between these operations. Review with a separately frozen **deterministic end-to-end actual HTTP** oracle; no TOCTOU security fix or certification claimed by this P5.
