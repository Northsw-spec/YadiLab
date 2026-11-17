# Persistent VLAN port configuration — schema 1.2

## Source format and migration

The canonical project schema now supports versions **1.0, 1.1 and 1.2**. Reading, validating, saving and exporting existing 1.0 or 1.1 documents **never upgrades them implicitly**. Version 1.0 excludes MAC and VLAN keys; version 1.1 permits the existing optional non-switch `mac` key. Version 1.2 permits both existing `mac` semantics and an additional optional `vlan` on **switch ports only**.

Supported switch-port configurations:

```json
{"vlan": {"mode": "access", "vlan": 10}}
{"vlan": {"mode": "trunk", "allowedVlans": [10, 20]}}
```

The `vlan` key may also be absent or `null` on switch ports. Both mean **no declared membership**. Concrete and null VLAN fields on non-switch ports are rejected, as are VLAN fields in schema 1.0 or 1.1, unknown keys, unknown modes, duplicate VLANs, empty trunk allowlists, booleans and IDs outside integer 1..4094. A trunk list's explicit order is preserved. The model never creates an access VLAN 1 or native VLAN by default.

**Partial source documentation is allowed:** the user can save a project with some unconfigured switch ports, preserving incomplete real-world documentation. **VLAN simulation is not allowed** when at least one persisted switch port declares a VLAN but an active wired switch port is missing configuration. The engine raises a clear error rather than silently falling back to unsegmented forwarding. If no port declares a VLAN and no session configuration is supplied, the earlier unsegmented behavior is preserved.

## Builder and storage behavior

For each switch port, the inspector accepts an **explicit** string `access:10` or `trunk:10,20`; an empty value removes the VLAN key. Input is translated to the precise JSON schema, validated by the actual Python `/api/validate` endpoint and committed to browser memory only on success. Invalid data leaves the previous model intact. Modifying a legacy 1.0/1.1 project explicitly upgrades its **in-memory** version to 1.2; only the user's Save writes a file. Switching a configured switch to another device type is refused until its VLAN configuration is cleared.

Existing `ProjectStore` storage, optimistic SHA-256 concurrency, atomic writes, explicit Export and Open behavior are reused unchanged. A real Chromium acceptance test enters both types of VLAN configurations, saves genuine files, verifies SHA-256, restarts the entire server and Chromium process, reopens and verifies the same VLAN facts, and checks exported JSON.

## Layer 2 integration

`EthernetFabric(project)` detects explicit 1.2 switch-port VLAN configuration and uses it for access/trunk forwarding. `ArpSession(project)` uses the same mechanism for request/reply. The `vlan_ports` session argument can **supply missing port configurations**, but cannot contradict persisted switch-port configurations. When VLAN-aware, all active and connected switch ports must be configured, and incompatible switch-switch or endpoint-trunk links are rejected as before.

Only config is persistent. Inferred/learned MAC tables, ARP cache, transmitted frames, session overrides and simulation diagnostics remain transient. **No IP-routing or ICMP/ping is claimed.** VLAN forwarding is still a Python API feature; the Builder edits configuration but does not run packet-level VLAN/ARP sessions or display Layer 2 diagnostics.

The strict four-table CSV importer still emits schema 1.0, without guessing VLANs or changing existing CSV columns.

## Verification

`tests/test_vlan_persistence.py`: versions 1.0/1.1/1.2, exact MAC/VLAN preservation, invalid formats, incomplete declarations, contradictions between persisted and session configuration, real disk SHA/Save/Open across new stores, no cache persistence, no automatic schema rewrite and no partial writes on validation failure. `tests/browser_smoke.py`: real Builder input, server API validation, explicit save, process restart and export. Full Python, JavaScript and Chromium CI is required on the PR's exact final HEAD.
