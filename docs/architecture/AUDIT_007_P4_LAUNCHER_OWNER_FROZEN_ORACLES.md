# AUDIT-007 P4 — immutable launcher owner negative/positive oracles

**Frozen FIRST from protected main `23f38afcfe37360a231619a8fabda9a8153972e9`**, tree `8dc780998e23bb914034718e40333cf9dc453f1b`. [AUDIT-007 issue #96](https://github.com/Northsw-spec/YadiLab/issues/96); owner-directed full bug-first policy in [AGENTS.md](../../AGENTS.md).

**Observed source:** `start-yadilab.sh:76-102` currently accepts any same-UID listener whose mutable `/proc/PID/comm` equals `app-launcher` as a stale instance and sends SIGTERM/SIGKILL. The earlier PIDFILE code validates executable path; the stale-port code does not. **This is a source-grounded hypothesis pending actual negative regression, not an exploit certificate.**

**Test `tests/security/run_audit007_p4_launcher_process_owner_tests.py` (unchanged across the freeze and production patch):**
- Run AFTER building signed-off distribution in GitHub Ubuntu, in both mandatory PR CI and exact-main independent Linux release.
- Create an ephemeral local copy of the actual start script, built distribution and runtime directory; use fresh loopback ports; never access external networks.
- Spawn and exclusively own a disposable Python listener, set its Linux `comm` to `app-launcher`, verify same UID and different `/proc/PID/exe`, verify owner PID via `ss`. Starting YadiLab on its port MUST fail closed and MUST NOT kill or replace the disposable listener.
- Spawn the real exact-built YadiLab binary, then run the start script on its port: this legitimate verified same-binary stale launcher MUST be safely restarted, preserving the existing UX.
- Cleanup acts ONLY on the test's own spawned PIDs. The test MUST fail on the existing name-only behavior and pass after a narrowly justified identity correction; no manual Parrot verification.
- Preserve existing launcher smoke, source checksums, original PIDFILE constraints, Dev11/Engine/Office/Chromium/AUDIT-006. Never turn UNKNOWN into a PASS or downgrade a correct negative assertion. Revalidate the executable's canonical path and inode/device immediately before termination; acknowledge that bash cannot make PID checks and signals atomic.

**At freeze:** `ORACLES_FROZEN / REPRODUCTION_PENDING / CODE_UNCHANGED`. A failed prepatch CI result is expected as evidence, not a permitted merge.
