# AUDIT-007 P7 — FROZEN nonblocking special-file HTTP oracles

**Status:** ORACLES_FROZEN / REPRODUCTION_PENDING / SERVER_UNCHANGED. Protected source main `6f8c6cca6e0f1d43f72b1d73b2f3796560621245`, Git tree `64df00c99780cca92fb8b2f74ce82d8fdd1c51d9`; full-source priority [AGENTS.md](../../AGENTS.md) and [AUDIT-007 #96](https://github.com/Northsw-spec/YadiLab/issues/96).

## Source hypothesis and narrow threat model

After independently verified P6, `launcher/server.go` uses `syscall.Openat` with `O_RDONLY|O_CLOEXEC|O_NOFOLLOW`. It checks `f.Stat().Mode().IsRegular()` **only after the open**. On Linux, opening an existing named pipe/FIFO for reading without `O_NONBLOCK` blocks until a writer appears. Thus a **local actor capable of creating files inside the served static tree** may induce a permanently blocked HTTP worker via an asset path or directory `index.html`. This is a local filesystem integrity prerequisite, not a claim that arbitrary remote users can upload files into release assets. Do not claim this is already reproduced before inspecting the actual prepatch CI log.

## Freeze-first actual Go acceptance

`launcher/audit007_p7_fifo_nonblock_test.go` uses real `staticServer.ServeHTTP` and `httptest` with a disposable temp-root and Linux stdlib `syscall.Mkfifo`. No external network, no third-party dependencies, no Parrot tests.

- Direct URL `/stalled.txt` is a named pipe with no writer. Handler MUST finish within a bounded 1.2 seconds and return HTTP **404**, never wait for a writer. Afterwards a valid `/app.js` still serves its exact normal content (200).
- Directory URL `/special/` contains a FIFO named `index.html`. Handler MUST finish within 1.2 seconds and return 404. Afterwards valid root `/` still serves built-in index (200).
- Normal nested regular file GET and HEAD must still work and produce exact content/length.
- P1–P6 and all other source/Go/Dev11/IC-030/IC-040/Chromium/AUDIT-006/Ubuntu mirror regressions remain mandatory.

**Patch only after negative reproduction:** Open the final candidate with Linux `O_NONBLOCK` in both direct terminal component and directory index paths, **before** final `f.Stat`; only a regular file is served, special files remain blocked, and all existing `O_NOFOLLOW` FD confinement remains. Using `O_NONBLOCK` on the regular static release files does not change their file-data semantics. Retain source SHA and release identity.

The test is an evidence-bound proof for FIFO blocking only, not for all special-file types or all conceivable resource exhaustion cases. No merge of prepatch failure; subsequent PR exact-head CI must all pass, protected expected-head merge, independent exact-main SUCCESS Linux release + valid Linux/DOM artifacts, then record in #96. All future import work remains ON_HOLD.
