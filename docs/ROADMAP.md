# ENDA AKTIVA ROADMAP — YadiLab Greenfield

Version 1.0 / 2026-11-26 / alla faser NOT_STARTED. Denna fil är enda exekveringskö. Scope ligger i PRODUCT_SCOPE.md och requirements/pt_scope.json; dessa är INTE separata roadmaps.

## Fasordning och verkliga beroenden
| Fas | Status | Resultat | Grind |
|---|---|---|---|
| R0 Baslinjer | NOT_STARTED | Verifiera PT-binär/build och full Cisco funktionskatalog; få ägarens gamla UI-/import- ZIP och screenshots; Linux launcher-spike, dependency/security/CI-verktyg | versionerade referenser; detta kan pågå parallellt med R1 |
| R1 Foundation/POC0 | NOT_STARTED | Immutable ConfigSnapshot, DeviceProfile/PortProfile/LinkProfile, CommandAST/CLIError och en enda ScenarioRuntime; deterministisk virtual-time scheduler | 2 processers identiska hash, tie/cancel/overflow/livelock/eventbudget negativa fall |
| R1 POC1 | NOT_STARTED | Verkliga host-switch-host TX/RX och ARP request/reply, explicit link timing, portdown, VLAN isolation | inga gamla motorimports, inget topologi-ping-fusk |
| R2 Projekt & import | NOT_STARTED | v1 project JSON/schema, safe Save/Open/SHA, CSV/TSV/XLS/XLSX/XLSM/XLSB/ODS och source evidence → mappning → commit | golden source cell/row/sheet, no inferred cable, round-trip, fail-closed |
| R3 Linux UI/ELK | NOT_STARTED | desktop-launcher, palette, canvas, Builder, inspector, ELK SVG/port geometry, event trace, Simulation controls | browser real geometry+screenshots, no UI networking logic |
| R4 Basprotokoll | NOT_STARTED | 802.3/VLAN/FDB/ARP/IPv4/ICMP/DHCP, IPv6/ICMPv6/ND, interfaces/CLI | oberoende bytes/state/time tester samt multi-hop negativ |
| R5 L2/L3 state | NOT_STARTED | STP/RSTP/MST, LACP, RIB/FIB, interVLAN/MTU/fragment, physical semantics | timers, convergence, actual packet forwarding, failover |
| R6 Transport/services | NOT_STARTED | UDP/TCP FSM, DHCPv6, DNS, HTTP(S), FTP/TFTP, mail, SSH/Telnet, SNMP/NTP/Syslog, VoIP | verkligen trafik via L2-L4, inte statiska returvärden |
| R7 Routing | NOT_STARTED | RIP/RIPng, OSPFv2/v3, EIGRP, BGP4, redistribution, policies | verklig neighbor/control state, riktig FIB och race cases |
| R8 Säkerhet | NOT_STARTED | ACL, NAT/PAT/NATv6, firewall/AAA/802.1X, GRE/IPsec/ISAKMP/IPS, rate limits | ingen osäker påstådd kryptografi, packet- och state-facits |
| R9 WAN/Wireless/QoS | NOT_STARTED | Fiber, PPP/HDLC/FrameRelay, DSL, Wi-Fi/radio/cellular, queues/shaping/jitter/DSCP/HA | testad media-/tids-/felmodell; PT-equivalence + standard |
| R10 IoT/OT | NOT_STARTED | Things, MCU/SBC Python/JS, PLC/HMI, Modbus/CIP/PROFINET/OPC UA/IEC 61850/PTP/PRP, Industrial/Cyber Observer | sandbox + verklig simulerad process/transport och negative cases |
| R11 Full produkt | NOT_STARTED | CLI/GUI samtliga PT-featurecases, logical/physical/power, Activity Wizard, assessment, Multiuser, ExApps, filformat/PKT-PKZ-PKA | per-feature versioned comparison; proprietary blockers hålls öppna |
| R12 YadiLab-extra | NOT_STARTED | avancerad AI-oberoende pedagogik, source-provenance-import, nätverksfelsökning, moderna extrastandarder och kausal förklaring | mätt nytta, regression-free på observerade kärnfall |
| R13 Global verification | NOT_STARTED | fullt PT-underfallsinventarium, Cisco-binärjämförelse, standard-orakel, invariants, fuzz, browser+import+security | G0–G5 enligt RELEASE_GATES.md |
| R14 Release superiority | NOT_STARTED | Förregistrerade och oberoende jämförda mått för teknisk kvalitet/diagnostik/nytta/stabilitet | G6; annars endast PARTIAL och NOT_VERIFIED |

## Första PR-serien
R0-1 = detta styrpaket; R1-1 = typing+config/device/port/link/CLI-kontrakt; R1-2 = scheduler och oberoende determinismforskning; R1-3 = host-switch-host reala events+ARP; R2-1 = source-preserving projektformat/import; R3-1 = en första enkel lokal canvas och versionerade referensbilder.

**Ingen slutförd PT-inventering krävs innan isolerad POC0**, men det betyder inte att full paritet kan deklareras. R0 måste fortsätta inventering och juridisk granskning, parallellt med den tekniska basmotorn.

## PR-kortmetadata
Varje PR måste redovisa: card ID, scope-ID och källrevision, minsta fungerande resultat, event/state ägare, standard och errata, positivt + negativt + motsägande test, timing/resource/cancel-budget, import/UI regression där relevant, exakta checks på head SHA, rollback och verklig coverage status. Ingen feature är VERIFIED med enbart Markdown eller ett visualiseringsexempel.
