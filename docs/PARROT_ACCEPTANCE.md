# Parrot OS acceptance harness

This harness is the target-runtime gate for the browser/PWA delivery baseline defined by Masterprompt v1.2.

## Run on the exact candidate

From the extracted checkpoint root on a supported Parrot OS x86-64 host:

```bash
bash scripts/run_parrot_acceptance.sh
```

The harness writes `parrot-acceptance-report.txt` unless `YADILAB_ACCEPTANCE_REPORT` selects another path.

## PASS requires

- `/etc/os-release` identifies Parrot OS;
- `uname -m` is `x86_64`;
- candidate distribution SHA-256 verification passes;
- the precompiled launcher starts with an empty runtime toolchain `PATH`;
- the listener binds only to `127.0.0.1`;
- static path-traversal and security-header checks pass;
- a Chromium-based browser loads the loopback acceptance page and proves secure-context, IndexedDB, CacheStorage and service-worker operation;
- Firefox renders the loopback application successfully.

A missing browser or failed probe is a FAIL on the Parrot target. A non-Parrot host returns exit code 77 / `BLOCKED` and can never create target acceptance PASS.

## Status semantics

`PASS` means the exact candidate passed this harness on Parrot x86-64.

`FAIL` means the harness ran on Parrot but one or more required target gates failed.

`BLOCKED` means the current machine is not the required Parrot target. BLOCKED is not PASS and must not be promoted to VERIFIED RELEASE.

The harness does not change the semantic source of truth. It validates delivery/runtime behavior only.

`npm run accept:parrot` is only a developer convenience alias. Target acceptance itself does not require Node/npm; the precompiled distribution and Bash harness are sufficient.
