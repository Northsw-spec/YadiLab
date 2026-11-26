# ENDA AKTIVA ROADMAP — YadiLab Greenfield

**Obligatoriskt första infrastrukturkort R0-BRAND:** [BRAND-IDENTITY-001](BRAND_IDENTITY_CONTRACT.md) är ett tvärgående, prioriterat kod- och releasekrav, inte en extra utvecklingskö. `core/identity.py::APP_DISPLAY_NAME` är enda produktnamnsliteral; `core/metadata.py` är neutralt metadataadapter. Runtimeklass-, modulsökvägar, persistent JSON/schema/filändelse, loggers, env-variabler, API routes och CSS-ID:n är brandneutrala. R3 UI och Linux-shell ska hämta namn från en källa och E2E-prova byte av *endast deklarationsvärdet* (UI, fönstertitel, desktopfält, projektstabilitet). Varumärket är aldrig ett protokoll- eller enhetstillverkarnamn; Cisco/Juniper/Arista m.fl. tillåts där tekniskt korrekt. De nya core-filerna och governance-testerna är inte ett bevis på fungerande launcher/UI.


**Uppdaterat användarbeslut:** Den tidigare YadiLab-UI:n är NU versionslåst till [Northsw-spec/YadiLab_legacy @ aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80). [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) kräver samma utseende och samma användarflöden; exakt visuell matchning är fortfarande NOT_VERIFIED tills verkliga screenshots finns. R0-UI-baslinjens källupptäckt är gjord men dess kör-/bildgrind är **inte** slutförd. Detta ersätter tidigare 'invän­ta ZIP'-krav. R3 är ett obligatoriskt same-UI-resultat, inte fri redesign.


Version 1.0 / 2026-11-26 / alla faser NOT_STARTED. Denna fil är enda exekveringskö. Scope ligger i PRODUCT_SCOPE.md och requirements/pt_scope.json; dessa är INTE separata roadmaps.

## Fasordning och verkliga beroenden
| Fas | Status | Resultat | Grind |
|---|---|---|---|
| R0 Baslinjer | NOT_STARTED | Cisco PT-binär/build och full funktionskatalog; **Legacy UI-källan är redan låst vid aac82926ced3dbf4cac09242530762ac3da1fe80**; utför återstående kontrollerad Linux/Chromium-körning av den låsta källan, spara screenshot-/DOM-/interaktions-goldens, kartlägg samtliga original-UI-flöden; Linux launcher-/dependency/security/CI-spikes | [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) + [UI-baseline](requirements/legacy_ui_manifest.json); samma UI ska vara möjligt att verifiera, R1 kan pågå parallellt |
| R1 Foundation/POC0 | NOT_STARTED | Immutable ConfigSnapshot, DeviceProfile/PortProfile/LinkProfile, CommandAST/CLIError och en enda ScenarioRuntime; deterministisk virtual-time scheduler | 2 processers identiska hash, tie/cancel/overflow/livelock/eventbudget negativa fall |
| R1 POC1 | NOT_STARTED | Verkliga host-switch-host TX/RX och ARP request/reply, explicit link timing, portdown, VLAN isolation | inga gamla motorimports, inget topologi-ping-fusk |
| R2 Projekt & import | NOT_STARTED | v1 project JSON/schema, safe Save/Open/SHA, CSV/TSV/XLS/XLSX/XLSM/XLSB/ODS och source evidence → mappning → commit | golden source cell/row/sheet, no inferred cable, round-trip, fail-closed |
| R3 Linux UI/ELK | NOT_STARTED | **Verklig same-UI-paritet med låst Legacy:** identiskt mörkt tema, topbar, fullbreddscanvas ovanför två nedre utfällbara panelkolumner, SVG/portgeometri, Builder/inspector, originaldialoger, dokument-/simuleringsvyer, lokal auth och alla 55 UI-case seeds; därefter tilläggsytor för PT | verklig Chromium/Playwright-skärmbild/DOM/E2E vid 1366x768 och 1920x1080, [UI-matris](requirements/legacy_ui_manifest.json), [fidelity kontrakt](LEGACY_UI_FIDELITY_CONTRACT.md); ingen ny gammal motor |
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
R0-1 = ursprungligt styrpaket; R0-UI = låst Legacy-referens + källbaserad UI-matris + browser screenshots/DOM-basline; R1-1 = typing+config/device/port/link/CLI-kontrakt; R1-2 = scheduler och oberoende determinismforskning; R1-3 = host-switch-host reala events+ARP; R2-1 = source-preserving projektformat/import; R3-1 = en första enkel lokal canvas och versionerade referensbilder.

**Ingen slutförd PT-inventering krävs innan isolerad POC0**, men det betyder inte att full paritet kan deklareras. R0 måste fortsätta inventering och juridisk granskning, parallellt med den tekniska basmotorn.

## PR-kortmetadata
Varje PR måste redovisa: card ID, scope-ID och källrevision, minsta fungerande resultat, event/state ägare, standard och errata, positivt + negativt + motsägande test, timing/resource/cancel-budget, import/UI regression där relevant, exakta checks på head SHA, rollback och verklig coverage status. Ingen feature är VERIFIED med enbart Markdown eller ett visualiseringsexempel.
