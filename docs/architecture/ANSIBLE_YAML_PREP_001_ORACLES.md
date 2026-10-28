# ANSIBLE-YAML-PREP-001 — evidence contract frozen before parser code

**Authority:** only GitHub `main` `2fa45b7e7073790f1aac065bc5390c24c49dabf6` at checkpoint start, in accordance with root `AGENTS.md`. This SHA is provenance, not a future pinned codebase.

## Primary source documentation

- Ansible YAML inventory plugin: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/yaml_inventory.html
- Ansible inventory group/host hierarchy, inheritance and duplicate host membership: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html
- YAML 1.2.2 specification: https://spec.yaml.io/main/spec/1.2.2/
- Maintained YAML parser API and strict/unique keys options: https://eemeli.org/yaml/
- Locked implementation parser: `yaml@2.8.3`. Do not hand-write a general YAML parser. Only add it with a reproducible npm lock and verified `npm ci` in GitHub Actions.

## P1 scope, not a generic YAML or Ansible execution feature

Profile `ansible.inventory.static.yaml.v1`, `CONFIG_DOCUMENTED`, **read-only preview**, not an active YadiLab import adapter. Accept one UTF-8 static inventory YAML document with root `all`, nested `hosts`, `children` and `vars`. `vars` can exist at group and host levels but are **never copied to preview, logs, scenario, Engine or exported artifacts** in the initial profile. Only host-level literal string `ansible_host` is surfaced as **REPORTED_CONNECTION_ADDRESS**, not independently verified identity or current reachability. Host IDs and group names represent Ansible-controlled inventory entries, never proof of physical devices.

- A host may intentionally occur under multiple groups; combine identical identifiers with matching explicitly declared addresses, recording each group membership and each typed YAML path locator. If addresses conflict, **BLOCK** instead of "last wins".
- Nested groups are hierarchy of automation targets, NOT network adjacency. No L1/L2/L3 links, IP subnet or service inference, no Engine PASS, no live Ansible process or network request.
- `all` is the only root in this strict initial subset; dynamic plugins, playbooks, ad hoc `group_vars` files, INI inventory, Cisco CML YAML and unrelated YAML are **UNSUPPORTED/BLOCKED**.
- No execution of Jinja expressions, Ansible lookup plugins, Python tags, custom YAML constructors, vault decryption, or remote includes. A variable string is inert, never executed.
- Reject YAML merge keys, anchors, aliases, custom tags, duplicate mapping keys, multi-document streams, non-scalar `ansible_host`, unknown collection shapes and cyclic group names. Rejected ≠ invalid Ansible in general; it means outside this explicitly versioned profile.
- Enforce byte, group, host, depth and semantic-count limits before unbounded expansion. Parser reports stable error codes. UI remains separate P2 gate.
- Redact by **never traversing or serializing** secret host/group variable values outside the selected `ansible_host` field. Source SHA-256 is computed from ORIGINAL bytes and output typed paths point back to the exact host occurrence.

## Independent synthetic test oracles (authored BEFORE parser code)

| File | Expected gate/outcome |
|---|---|
| `valid-nested.yml` | READ_ONLY: distinct `control01`, `rtr01`, `app01`, `app02`; exact reported IPv4 values for first three; app02 has UNKNOWN address; group ancestry all/routers/servers; ZERO inferred physical links |
| `valid-repeated-host.yml` | READ_ONLY: `app01` in east and west, deduplicated ONLY for identical reported address; app02 separate; ZERO inferred links |
| `valid-sensitive-vars.yml` | READ_ONLY: one host/provenance; declared 203.0.113.10 address; **NO secret canary or private path** in serialized preview/diagnostics |
| `invalid-duplicate-key.yml` | BLOCK duplicate host key (not first/last wins) |
| `invalid-alias.yml` | BLOCK `&` anchor / `*` alias even though valid full YAML |
| `invalid-custom-tag.yml` | BLOCK custom `!vault` tag, no constructors or decryption |
| `invalid-dynamic-plugin.yml` | BLOCK dynamic plugin source; never invoke plugin |
| `invalid-playbook.yml` | BLOCK playbook list; never run task |
| `invalid-multiple-documents.yml` | BLOCK multi-doc stream |
| `invalid-nonscalar-address.yml` | BLOCK `ansible_host` sequence rather than literal string |
| `invalid-group-recursion.yml` | BLOCK recursive group ancestry |
| `invalid-merge-alias.yml` | BLOCK merge/alias source outside static subset |

## Required implementation/test and delivery gates

1. Parsing with maintained pinned YAML package; reproducible `npm ci` on GitHub CI runner verifies exact lock integrity. Never bypass lock or dynamically load scripts from URLs.
2. Positive fixtures match independent list above and maintain SHA-256/typed locator provenance; test deterministic repeat.
3. Every negative fixture produces explicit BLOCKED diagnostics; parser performs **no partial scenario activation**.
4. Inject source with conflicting repeated `ansible_host`, deeply nested structure, excessive length, prototype-polluting keys, alias bomb and secrets in `vars`: all BLOCK or safely omit as appropriate.
5. Assert absence of `ScenarioSource`, physical links, Engine flags, local file reads beyond selected upload, external requests and executable content.
6. Existing JSON/CSV/TSV/XLSX/ODS and GraphML/Nmap import/probe/UI regressions PASS.
7. True browser and Parrot acceptance **NOT RUN** until separately implemented. Filename `.yml` does not activate any supported adapter.
8. Keep profile identifiers in planning registry **NOT_IMPLEMENTED** until UI and end-user import review/confirmation gates are separately satisfied.

**Evidence states:** PREP fixtures exist before P1 code; a green preflight parser gate proves only the supported narrow `CONFIG_DOCUMENTED` preview. No broad YAML support or Ansible inventory execution can be claimed.
