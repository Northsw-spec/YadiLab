# PT-FULL-001 — absolut funktionsscope för Linux-YadiLab

**Cross-cutting BRAND-IDENTITY-001:** [Ett enda källkodsnamn](BRAND_IDENTITY_CONTRACT.md) – ingen branded package/klass/filformat, alla användarsynliga produktnamn hämtas dynamiskt. Fullt PT-device scope omfattar explicita tillverkarnamn i UI och implementation. Detta namnkrav får inte användas för att förbjuda Cisco/Juniper eller andra korrekta vendor-specifika skillnader.


**Obligatorisk produktpresentation:** Nya YadiLab ska **se ut och fungera som** [YadiLab_legacy @ aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80) enligt [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md). Same-UI-paritet är obligatorisk utöver hela Packet Tracer-omfånget; designen får utökas för PT men inte tyst ersätta legacy-layout eller dess användarresor. Verkliga screenshot-goldens och nya funktioner är ännu inte verifierade.


Status: REQUIREMENTS, NOT_IMPLEMENTED. Baslinje: Cisco Packet Tracer 9.0 HELP är dokumenterad. Den faktiska licensierade PT-builden, dess SHA och eventuell 9.0.1-funktionsdelta är NOT_VERIFIED. Produktmålet gäller ALLA funktioner hos den version av PT som slutligen jämförs, inte enbart listan här.

Obligatoriska familjer (utökas med individuella underfall i requirements/pt_scope.json):
1. Logical Workspace: topology, cluster, annotations, diagrams, palette, manipulering.
2. Physical Workspace: rooms/buildings/racks/geography, cabling, power, environment.
3. Routers/switches/hosts/hubs/bridges/firewall/ASA/phones/servers/cloud/wireless/industrial, inklusive alla modulprofiler.
4. Port media: copper/fiber/serial/console/radio, transceiver, power/link/duplex, hotspots.
5. Enhets-CLI och GUI: varje relevant kommando, mode, privilege, config, show/debug och startup/running/reload.
6. Real-time och Simulation Mode, event filters, pause/step, Simple/Complex/Periodic PDU, OSI/PDU information.
7. LAN: Ethernet, 802.3, ARP, VLAN, trunk, VTP, DTP, STP/RSTP, LACP/EtherChannel, PAgP, L3 switching/IP CEF.
8. IP: IPv4/IPv6, ND/RA, ICMPv4/v6, NAT/NATv6, DHCPv4/v6, routing/FIB.
9. Routing: static/default, RIP1/2/ng, OSPF single/multi-area v2/v3, EIGRP, BGP, redistribution.
10. Transport/appar: TCP, UDP, DNS, HTTP(S), FTP/TFTP, SMTP/POP3, VoIP, Telnet/SSH, SNMP/NTP/Syslog, tjänstekonsoler.
11. Security: ACL named/standard/extended, Zone-Based Firewall, CBAC, IPS, GRE/IPsec/ISAKMP, AAA, RADIUS/TACACS, 802.1X.
12. QoS, WAN och management: PPP/HDLC/SLARP/FrameRelay, DiffServ, queues, NBAR, NetFlow, CDP, HA, monitorer.
13. WLAN/cellular: 802.11, radio, associations och PT-stödda accessmodeller.
14. IoT smart things, physical environment, gateways, registration servers och automation.
15. MCU/SBC digital/analog signals, Python/JavaScript/visual programming, sandbox och device simulator.
16. Industrial/OT: IR1101/C8200/PT8200, PLC/HMI/Data Historian/Cyber Observer, Modbus TCP, PROFINET, CIP EtherNet/IP, OPC UA, IEC 61850, PTP, PRP.
17. Activity Wizard, instructor/learner, scoring, proficiency, script, challenge mode, assessment och feedback.
18. Multiuser peer cloud/remote network/port, remote saves, secure authenticated connections.
19. Extensions/ExApps/IPC/API och scripts med lagliga, säkra motsvarigheter.
20. PKT/PKZ/PKA och andra tillämpliga projektformat samt all relevant dokument-/övningsmigration.
21. Linux packaging, offline use, autosafe/manual save, backup/recovery/export och fungerande hel arbetsresa.
22. ALLT annat som upptäcks i en laglig licensierad PT-installation eller aktuell Cisco-dokumentation.

ALLA PT-varianter är REQUIRED: ingen tyst delmängd, fake CLI, simulation animation eller protokollkod som bara returnerar "success". Ovanstående är en översikt, inte en fullständig PT-inventering. En familj blir inte done förrän alla identifierade subfeatures testats med exakt versionssatt PT-binary samt oberoende standardspecifikation där tillämpligt.

YadiLab ska dessutom ge dokumentimport med provenance, systematisk nätverksfelsökning och kausal time-trace, mer exakta standard-/tidsmodeller än PT där test faktiskt påvisar det, samt ytterligare moderna protokoll enligt docs/PROTOCOL_CATALOG.md. Detta är mätbara produktambitioner, inte implementerade features.

ENDA UNDANTAG: Windows/macOS och nya tillgänglighets-/keyboard-only-paritetsfunktioner. Säkerhet och vanliga GUI-interaktioner kvarstår obligatoriska.

Om proprietär Cisco-kompatibilitet inte får göras lagligt: markera BLOCKED_LEGAL_OR_SPEC och lämna FULL_PARITY ouppnått. Den tekniska motorn får aldrig vara beroende av en proprietär Cisco-binär eller extern emulator.
