# ANSIBLE-INI-PREP-001 — frozen independent oracles before parser

**Coding authority at checkpoint start:** actual GitHub `main` `687542062d657446932e9e5b7555811e892dfb38`; the repository's `AGENTS.md` is mandatory. The historical archive is context only and does not supply source code.

## Wave 1 — authoritative syntax and semantic boundaries

Primary sources:
1. [Ansible builtin INI inventory plugin](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/ini_inventory.html)
2. [Ansible inventory guide](https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html)
3. [Python shlex lexical analysis](https://docs.python.org/3/library/shlex.html)
4. [Ansible host pattern/range documentation](https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html#adding-ranges-of-hosts)

The actual Ansible INI plugin supports ungrouped hosts, `[group]` host membership, `[group:children]` nested GROUPS, `[group:vars]` assignments, inline `key=value` and host aliases. Ansible itself supports more grammar, including host ranges, quotes, Python-literal conversion on host lines, and type-sensitive value handling. **YadiLab will NOT claim full INI equivalence.** It uses its own explicitly narrower, offline, non-executing *static preview profile*.

Crucial distinction: Ansible's inline host `key=value` values are evaluated as Python literals, while `[group:vars]` values remain strings. YadiLab must NOT evaluate Python expressions or infer values/identity from either form. Group membership and `:children` describe Ansible target selection/inheritance, NOT network cables, L2/L3 reachability, or Engine PASS.

## Wave 2 — frozen bounded v1 input contract

- Proposed profile ID: `ansible.inventory.static.ini.v1`; semantic track `CONFIG_DOCUMENTED`; `status: REVIEW_REQUIRED`, `canActivate: false`.
- Accept **only** a single nonempty UTF-8 byte source, maximum **256 KiB**, **500 hosts**, **200 named groups**, **2,000 direct group memberships**, **5,000 lines**, **4,096 characters/line**, **10 child-group levels**. Additional tested bounds may tighten these values but must be recorded.
- Accept empty lines, complete lines starting with `#`, ungrouped host lines, unique `[group]` sections, unique `[group:children]` sections, unique `[group:vars]` sections, host lines with an explicit bare hostname/alias optionally followed by whitespace-separated, unquoted `key=value` atoms. Full-line comments only in v1.
- Name subset (group/host): `^[A-Za-z_][A-Za-z0-9_.-]{0,127}$`. The planned profile intentionally **does not** support literal IPv4/IPv6 inventory keys, ranges, shorthand `hostname:port`, escaped/quoted host fields, mixed inline comment syntax, semicolon comments, or non-UTF8. These are *unsupported v1 shapes*, not claims that Ansible rejects them.
- Only `ansible_host` is interpreted: one literal simple DNS-name or IPv4 address (IPv4 octets 0–255). No URL, path, whitespace, Jinja, shell substitution, IPv6, bracket syntax, or variable interpolation. Record as `REPORTED_NOT_VERIFIED`. Absent address becomes `UNKNOWN`. Do not infer DNS lookup.
- Host/group variables other than literal `ansible_host` may exist, but do not appear in API outputs, browser DOM, errors, logs, sidecars, scenario packages or Engine. We do not inspect their values. Version 1 may reject ambiguous quoting/tokenization instead of approximating Ansible's Python-literal or shlex behavior.
- A host may appear in multiple groups with exactly the same literal declared `ansible_host` (including both absent); deduplicate its identity by **inventory name**, attach each **direct** membership and original source line locator. Conflicting present/missing addresses or differing addresses block the whole source. The same address on two different aliases does NOT prove the same physical host.
- `[group:children]` edges are group relationships only. Require every referenced nonreserved group to be defined, reject self/indirect cycles. `all` may be used for variables but never to infer physical infrastructure.
- Repeated identical section headings block, even when Ansible might tolerate them, to prevent ambiguous provenance. `[group:vars]` values are ignored and must not be serialized. Reject unsupported section modifiers, range syntax, malformed `key=value` tokens and source-side commands/includes.
- No external filesystem reads, remote network requests, Ansible subprocess, plugins, Jinja, Python evaluation, inventory script execution, or linked file resolution. Never mutate the Builder, its revision, source scenario or simulation Engine as a side effect of preview.
- Provenance of each direct membership: raw bytes SHA-256 (including line endings and comments), source line number (1-based), section identifier, host key. Identity/association to an existing Builder resource, if later implemented, requires *separate explicit unverified consent*; not in v1 PREP/P1.
- On invalid, unsupported or ambiguous content: **BLOCK entirely** with stable diagnostic code. No best-effort partial preview or source code execution.

## Wave 3 — independently frozen test oracles

The machine-readable frozen case list is `tests/fixtures/import/ansible-ini/oracles.json`. Files in that folder are synthetic; reserved RFC 5737 addresses do not imply real reachable nodes. Positive file host counts, exact aliases, direct group membership, group-parent relationships, declared vs unknown connection address, and ZERO created links are enumerated there.

| Fixture family | Independent oracle |
| --- | --- |
| `valid-ungrouped` | Four hosts, including an ungrouped alias, three reported addresses, app02 UNKNOWN |
| `valid-hierarchy` | Group hierarchy `site -> routers,servers`; 3 direct host memberships; zero cables |
| `valid-multigroup` | app01 appears twice but is one identity, two direct locators; no inferred single-machine proof |
| `valid-sensitive-vars` | Secret canary values appear only in the SOURCE; absent from all output and diagnostics |
| `valid-group-vars-string` | Different Ansible type semantics cannot leak values or set Engine state |
| `valid-comments` | Explicit full-line comments and empty lines do not become hosts |
| All `invalid-*` fixtures | Reject unsupported grammar, group cycles, ambiguous host address, unknown child, malformed variable, injection-like input |

**Safety/adversarial tests required at P1:** malformed UTF8, NUL, over-budget bytes/line/group/host/depth/membership, CRLF-vs-LF source SHA identity, deterministic second parse, conflicting declared/missing address, variable-only secret canaries, proto pollution strings, input no-mutation, source failure does not affect Builder/Engine, source-based line locator exactness, no inferred links and legacy adapter regressions.

## Implementation sequence and gates

1. **PREP-001 (this commit):** freeze this architecture contract, positive/negative fixtures and oracle JSON in GitHub, plus an integrity-only CI check. Do not mistake fixture inventory checks for parser PASS.
2. **P1:** implement strictly bounded read-only INI interpreter at `enterprise-import/src/ansible-ini-preview.ts` that obeys this pre-existing contract, with independent exact-value, redaction and adversarial tests. Do not register it as a generic active import adapter.
3. **P2:** source-file bridge, English-only read-only inspection panel, safe escaping, consent/no-action boundary and REAL compiled React Chromium file-selection tests; no Engine state mutation.
4. **P3 (optional):** explicit reviewed sidecar associations to existing Builder resources, kept unverified, stale-source/Builder guards and true downloaded JSON verification.
5. Before each gate: fetch *current* GitHub main, branch, commit all code, check exact-head CI, merge only after green tests, then verify merged-main release; manual Parrot remains NOT RUN until physically run.

**Known limitations:** no promise of full Ansible INI grammar, no automatic host-ranges, no Python ast/shlex parity, no full YAML/INI inventory semantics, no physical topology proof. None of these exclusions is a correctness claim about real Ansible.
