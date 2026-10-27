# Phase 68 — Windows + Linux Fault Packs

YadiLab Foundation v0.68.0 adds two separate versioned built-in OS Fault Packs while preserving the verified Phase 65–67 Fault Engine contract.

## Built-in packs

- `foundation.os.windows@0.1.0` — 10 deterministic Windows faults.
- `foundation.os.linux@0.1.0` — 10 deterministic Linux faults.
- `foundation.network.core@0.2.0` remains unchanged and byte-compatible with the v0.67.0 checkpoint.

The UI now requires an explicit built-in fault-pack selection before selecting a fault. Preview tokens continue to bind the exact pack ID, version and pack identity as well as scenario, Runtime revision, bindings, seed, mode and active overlay.

## Windows coverage

The Windows pack covers modeled troubleshooting states for:

- wrong default gateway;
- wrong DNS resolvers;
- disabled DHCP client state;
- Windows host-firewall default deny;
- APIPA-style primary addressing;
- disabled RDP service;
- moved RDP listener port;
- disabled SMB service;
- disabled WinRM service;
- Public network profile.

## Linux coverage

The Linux pack covers modeled troubleshooting states for:

- wrong default gateway;
- wrong DNS resolvers;
- disabled DHCP client state;
- Linux host-firewall default deny;
- IPv4 link-local primary addressing;
- disabled SSH service;
- moved SSH listener port;
- disabled HTTP service;
- disabled NetworkManager state;
- disabled systemd-resolved state.

## Cross-pack safety

Phase 68 adds a generic active-overlay mutation conflict guard. A new fault is rejected when any of its mutations overlaps the same target/path or a parent/child path already changed by an active fault. This is pack-independent and prevents one pack from silently overwriting another pack's active state.

The guard does not block the same path on different resources. Independent Windows and Linux faults can coexist in one overlay and retain separate exact pack locks.

## Engine-derived evidence boundary

Service/listener faults use the existing deterministic Service Engine and are regression-tested through `queryServiceEnabled` / `queryListeningPort`. Existing network/state semantics continue to be used for gateway, resolver, DHCP, interface and ACL properties where the current Engine supports them.

This phase does **not** claim that YadiLab already executes real `ipconfig`, `route print`, Event Viewer, `systemctl`, `journalctl`, `ip route`, `ss`, PowerShell or shell commands. Those command-style observations belong to the later Diagnostic / Observation Engine. OS faults remain declarative modeled state, not host OS execution.

## Non-goals

v0.68.0 does not introduce:

- probabilistic faults;
- AI/ML/LLM runtime logic;
- arbitrary scalar difficulty scores;
- a deterministic multi-fault curriculum generator;
- temporal/intermittent faults;
- real Windows or Linux guest execution.

The next recommended phase remains deterministic multi-fault/scenario generation over compatible locked Fault Packs.
