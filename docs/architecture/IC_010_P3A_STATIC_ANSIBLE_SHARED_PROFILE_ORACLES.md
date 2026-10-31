# IC-010 P3a: static Ansible inventory profiles in shared read-only inspection

Baseline: protected main 5878d7e8d0c05458ad718e1a2d859006e56541cc; Git tree 2b966547dde3d7a9b4b8a97d1809da1bca44456d. Requirements frozen before code.

Scope:
- Extend the P2 shared file chooser with two producer-validated static inventory profiles: Ansible YAML (.yaml/.yml) and Ansible INI (.ini).
- Reuse existing strict bounded parsers only. Maximum 256 KiB for each Ansible source; preserve existing 2 MiB XML limit.
- No source parsing until explicit user consent. Filename and MIME are not authorization; original validated bytes determine acceptance.
- Output only immutable aggregate data: profile, classification CONFIG_DOCUMENTED, original SHA-256, document locator, host/group counts and validated per-host original source-locator count.
- Check each existing host locator against the original source hash. Do not disclose hostnames, addresses, source strings, credentials, variables or raw item locators in the shared summary.
- Keep literal no-activation and no-Engine-verification state. No inference of physical links, live hosts, probes, Builder or Engine changes.
- Preserve the original four XML profile behaviors, existing five enterprise adapters and separate review/replay UI.
- Add positive, malformed, size-limit, wrong-format and sensitive-data-redaction Node tests. Add compiled Chromium chooser, consent, rejection, workspace-immutability and source-switch tests.
- Execute gates in required PR CI and independent merged-main Linux release. Record exact SHAs and links.

Excluded: universal importers, generic YAML/INI parsing, new network model mappings, per-item manual Builder decisions and new probes. P3a is a small IC-010 checkpoint; P3b continues the reviewed item-level workflow.
