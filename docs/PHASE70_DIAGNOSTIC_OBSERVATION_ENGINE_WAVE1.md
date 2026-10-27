# Phase 70 — Diagnostic / Observation Engine, Wave 1

YadiLab Foundation v0.70.0 adds the first deterministic learner-facing observation layer over Runtime Engine state.

## Boundary

The engine is explicitly **model-based**. Familiar command names are a pedagogical interface; YadiLab does not execute a Windows/Linux guest, PowerShell, shell, `systemctl`, `ip`, `nft`, `ss`, or kernel command in this phase.

Every transcript is marked:

- engine ID `foundation.observation`;
- engine version `0.1.0`;
- `modeled: true`;
- boundary `NO_GUEST_COMMAND_EXECUTION`;
- exact scenario ID/hash and Runtime `stateRevision`;
- exact target and command ID.

The engine reads only the current deterministic Engine state. Missing state is shown as `<not modeled>`. Malformed modeled values are shown as `<malformed modeled value>` with an explicit warning instead of being repaired or guessed.

## Windows Wave 1

Seven modeled command surfaces are available for Windows guest resource types:

1. `ipconfig /all` — interface addresses, DHCP, gateway and DNS state;
2. `route print` — modeled default gateway and route declarations;
3. `Get-NetIPConfiguration` — PowerShell-shaped interface/DHCP/gateway/DNS view;
4. `Get-NetFirewallProfile` — modeled network profile and host ACL default action;
5. `Get-NetConnectionProfile` — modeled Windows network profile;
6. `Get-NetTCPConnection -State Listen` — enabled modeled services with listening ports;
7. `Get-Service TermService,LanmanServer,WinRM` — modeled RDP/SMB/WinRM service state.

## Linux Wave 1

Seven modeled command surfaces are available for Linux guest resource types:

1. `ip addr show` — interface addresses;
2. `ip route show` — modeled default gateway and route declarations;
3. `resolvectl status` — modeled systemd-resolved, DNS servers and search domains;
4. `nmcli device show` — modeled NetworkManager, DHCP, gateway, DNS and addresses;
5. `nft list ruleset` — modeled host ACL/firewall default action;
6. `ss -lntup` — enabled modeled services with listening ports;
7. `systemctl is-active sshd NetworkManager systemd-resolved` — modeled SSH/HTTP/NetworkManager/systemd-resolved state.

## Evidence contract

Each transcript contains direct evidence references to the exact modeled paths used to build it. Observation output never reads `faultOrigin`, generator hidden truth, canonical recovery, or instructor-only ground truth.

Observation is read-only:

- no Engine mutation;
- no Runtime history entry;
- no checkpoint change;
- no source change;
- no fault-overlay change.

The same Engine state + target + command produces the same transcript.

## Fault visibility

Permanent regression proves that Wave 1 observations expose the already verified Windows/Linux fault families, including:

- wrong default gateway;
- replaced DNS resolvers;
- disabled DHCP client;
- host ACL default-deny;
- APIPA/link-local addressing;
- stopped RDP/SMB/WinRM/SSH/HTTP services;
- moved RDP/SSH listener ports;
- Windows public network profile;
- disabled NetworkManager;
- disabled systemd-resolved.

The engine also observes compatible generic network-pack mutations when they alter the same modeled host state paths.

## Runtime UI

Runtime now exposes **Diagnostic / Observation Engine** in the sidebar. The learner chooses a modeled Windows/Linux target and one of the applicable commands, then runs **Run modeled observation**.

The panel displays:

- explicit model/execution boundary;
- exact Runtime revision;
- deterministic transcript;
- direct modeled evidence paths and states.

Builder cannot execute Runtime observations.

## Non-goals

v0.70.0 does not introduce:

- real VM/container guest command execution;
- terminal/PTY access;
- PowerShell remoting or SSH;
- live Event Viewer, journalctl, packet capture, registry or filesystem reads;
- automatic diagnosis or causal ranking from observations;
- AI/ML/LLM reasoning;
- temporal/intermittent fault scheduling;
- network-appliance CLI simulation.

Those capabilities require separately verified execution/observation contracts rather than fabricated transcripts.
