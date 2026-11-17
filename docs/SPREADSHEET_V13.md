# Explicit versioned XLSX/ODS interchange format — schema 1.3

The Builder offers two real binary schema-1.3 example workbooks (XLSX and ODS) under the saved-project controls. Each is a **labelled demo**, not an observed network. Their routes are declared facts but do not imply successful reachability. Validation failures for versioned cells include the original source cell address when the row/column is unambiguous. See [template downloads and diagnostics](SPREADSHEET_TEMPLATES.md).

## Schema version selection

**Unversioned** workbooks continue to have exactly the original four-sheet schema-1.0 contract. No automatic schema migration is performed. To import **schema 1.3** the workbook **must** have a sheet named `Project` whose entire content is precisely:

```csv
schemaVersion
1.3
```

Only these sheets are recognized, in any order:

| Sheet | Required | Exact named columns (order immaterial) |
|---|---|---|
| Project | For 1.3 | schemaVersion |
| Devices | Yes | id, label, kind, x, y, zoneId |
| Interfaces | No | nodeId, id, name, enabled, ipv4, mac, vlanMode, accessVlan, allowedVlans |
| Links | No | id, aNode, aPort, bNode, bPort, enabled |
| Zones | No | id, label |
| StaticRoutes | No | nodeId, id, destination, nextHop, outPort |

If `Project` is absent, `StaticRoutes` is forbidden and `Interfaces` must have only the legacy five columns. If `Project` is present, `Interfaces` must have all nine columns, including any blank optional fields. A version other than exactly `1.3`, duplicate metadata rows or unknown columns is an error. Data cells representing identities, MACs, IPv4/CIDRs, destination prefixes, gateways and VLAN IDs must be **text**. Native numeric `x/y` and boolean `enabled` cells remain supported. IDs and endpoints must be declared, not inferred.

## MAC and VLAN columns

MAC is either blank (no declared binding) or a six-octet, colon-delimited, nonzero unicast MAC on a nonswitch port. No duplicated endpoint MACs are allowed. The canonical schema 1.3 normalizes valid MACs to uppercase.

A switch port's VLAN columns must match exactly one form:

| vlanMode | accessVlan | allowedVlans | Meaning |
|---|---|---|---|
| *(empty)* | *(empty)* | *(empty)* | No explicit VLAN configuration |
| access | 10 | *(empty)* | VLAN 10 access |
| trunk | *(empty)* | 10&#124;20 | Trunk, permitted VLAN 10 and 20 |

VLAN IDs must be canonical decimal text from 1 through 4094, with no leading zeroes or duplicates; trunk members are separated by a literal pipe character `|`. A nonswitch port must not declare VLAN configuration. The importer never assumes VLAN 1 or invents a switchport mode.

## Static route rows

`StaticRoutes` is optional. Every row must declare `nodeId`, per-node unique `id`, canonical IPv4 network `destination` (e.g. `203.0.113.0/24`), explicit unicast `nextHop`, and an existing `outPort`. The next-hop must lie in the output port's configured IPv4 subnet and must not be the port's own address, network address or broadcast address. Layer-2 switches cannot own routes. Route ordering and all link/port identities are retained across Save/Open. A declared route is not evidence of reachability by itself.

## Architecture and limits

Both physical workbook parsers retain their existing ZIP/XML checks and reading limits. The shared `spreadsheet_schema.py` selects the version by sheet presence, uses the **existing CSV row parser** to validate named columns and build the legacy common model, then adds explicitly declared schema-1.3 MAC/VLAN/route fields. The existing `validate_project` validates the final 1.3 model. Invalid or unsupported input is **rejected with HTTP 422**; there is no alternate import engine, implicit physical connection, or skipped unknown data.

The Builder validates the *entire* workbook before asking for permission to discard unsaved changes and replace the workspace. It never writes a file until **Save** is selected. Previously saved project files remain byte-for-byte unchanged.

## Verification

`tests/spreadsheet_v13_fixture.py` independently constructs a five-node network with two explicit switches, VLAN 10 access ports, a VLAN 10/20 trunk, endpoint MACs, a router, and bidirectional static routes. Both independently created OOXML and ODF ZIP workbooks must produce exactly the same separately constructed expected canonical schema-1.3 project. Real ICMP Echo is tested through the existing IPv4/ARP/Ethernet/VLAN engine, not a graph-only stub. Negative tests cover missing/malformed versions, unknown fields, invalid/duplicate MAC, inconsistent VLANs, invalid static routes, wrong next-hop, wrong identities, and unchanged persisted bytes. Chromium accepts and saves both real file formats, reopens them, and checks SHA-256 and previous legacy project integrity.

Unsupported: arbitrary spreadsheet layouts, unknown fields, formulas, hidden data, auto-discovery, dynamic routing, VLAN range syntax, macros, rich annotation objects, or implicit default gateways.
