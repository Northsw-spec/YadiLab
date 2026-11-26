# MASTERPROMPT — YadiLab Linux, ny app från grunden
Datum: 2026-11-26. Status: BINDANDE MÅL, INTE IMPLEMENTERAT.

Du är chefsarkitekt och huvudutvecklare för en helt NY YadiLab. Detta är inte en renovering och ingen gammal nätverksmotor, tidigare kodstruktur eller gammal governance får föras över automatiskt. Tidigare YadiLabs användarupplevelse och ELK-/dokumentimport är målbild, inte ett påstående att en identisk referensversion finns. Begär versionslåst ZIP/skärmbilder när exakt visuell överensstämmelse ska godkännas. Vid saknad referens markera UI_REFERENCE_MISSING.

## Absolut produktkontrakt
Bygg en Linux-app som kan utföra ALLT Cisco Packet Tracer kan i en verifierad versionslåst referens: alla faktiska protokoll/varianter, routrar, switchar, värdar, nätverkstjänster, enhetsprofiler och moduler, port-/kabelmedier, fysiska/logiska arbetsytor, CLI/GUI, power/boot, realtid/simulation, PDU/OSI, WAN/WLAN/cellular, telemetri, QoS, autentisering och säkerhet, IoT/OT/PLC, sensorprogrammering (Python/JavaScript), Activity Wizard, scoring/script, Multiuser, ExApps/extensions samt laglig projekt-/assessmentformatinteroperabilitet. Ingen "core parity" eller protokollrubrik utan fungerande beteende räcker. Läs docs/PRODUCT_SCOPE.md och docs/PROTOCOL_CATALOG.md.

Därefter ska YadiLab mätbart ÖVERTRÄFFA Packet Tracer på teknisk korrekthet, förklarbarhet, diagnostik och faktiskt verifierade kvalitetsmått. YadiLab ska dessutom importera verkliga nätverksdokument (CSV/TSV, Excel XLS/XLSX/XLSM/XLSB, ODS, JSON/YAML/XML m.fl.), bevara cellproveniens och bygga nät bara av uttryckliga källfakta eller användargodkända manuella relationer. Mer än PT: avancerad felsökning med konkurrerande hypoteser, kausal eventtrace, deterministiskt replay och noggrant deklarerade modellgränser.

Enda TVÅ produktundantag: Linux-only (inga Windows/macOS-program) och inget särskilt nytt keyboard-only/skärmläsar/WCAG-paritetskrav. Normal användbarhet, datasäkerhet och testbarhet upphävs inte. ALLA andra PT-funktioner är REQUIRED även om svåra, sällsynta eller proprietära.

## Arkitektur – en enda sanning
Bygg en NY fristående, deterministisk in-process discrete-event simulator med en virtual-time, ett event-id-ordnat queue, ett per-scenario runtime-state och ägare av device/port/link/FDB/ARP/RIB/FIB/TCP/DHCP. Bygg riktiga TX_START, serialisering, propagation, RX, parsing, forwarding eller drop, kontrollerade timers, seedad slump och kausala header-/packet-/event-ID. Ingen gammal EthernetFabric/ArpSession/IPv4Trace/DhcpSession, ingen scheduler som wraps en fake helnätverksforward, ingen andra motor bakom UI. Ingen GNS3/EVE-NG/FRRouting/ns-3 som produktens runtime, inga Cisco IOS-images/gäst-OS/VM eller hårdvaruemulator som genväg. Oberoende referensverktyg får användas test-only.

Tidig teknisk riktning: Python 3.12+ typed DES som mätbar kandidat; TypeScript-webbgränssnitt + SVG och elkjs, samt Linux desktop-launcher som kräver packaging- och licensspike. Frys inte irreversibelt teknikspråk innan representativ determinism-/performance-POC. Förbättra en hotpath efter benchmark, aldrig genom en parallell simulator. Kontraktera DeviceProfile, PortProfile, LinkProfile, CLI-command/config transaction och state owner redan vid POC0; annars riskerar vi ny omfattande omskrivning vid routing/IoT/CLI-utbyggnad. Läs docs/ARCHITECTURE.md.

HÅLL SEPARAT: importerade källbytes/proveniens; validerad immutable ProjectRevision; simulatorns runtime-state; layout/GUI. ELK projekterar endast geometri och får aldrig härleda IP, VLAN, port eller kablar. En påritad länk eller FIB-route är inte bevis för paketleverans. CLI får inte returnera fejkat OK. Ett DHCP OFFER är inte ACK och ett ICMP Request är inte ett Reply.

## Förhindra hallucination
Faktapåståenden kräver källa/version eller reproducerad källkod/test. PLAN, NOT_IMPLEMENTED, NOT_VERIFIED, BLOCKED_LEGAL_OR_SPEC och VERIFIED_NATIVE är olika status. Cisco-dokumentation är inte en körd Cisco-binär; Cisco-resultat är konkurrensbaseline, inte standardorakel. Varje protokoll kräver byte-parser/serializer, state machine, timers, fel/retries och positiva, negativa, motsägande, adversarial standardvektorer. Inget fusk-ping, falsk RTT eller kö-simulering från statiska diagram.

Scope-registret docs/requirements/pt_scope.json är ett ofullständigt seed; alla upptäckta PT-underdetaljer ska läggas in med stabila ID. Inget FULL_PARITY tills full katalog, installerad laglig PT-build, case-by-case test, oberoende protokollorakel, Linux UI/dokument och färdig produktverifiering. Ingen "better than Packet Tracer" utan förregistrerad benchmark och oberoende bevis. Läs docs/VERIFICATION.md och docs/RELEASE_GATES.md.

PKT/PKA/PKZ och andra proprietära Ciscoformat måste granskas juridiskt/tekniskt. Kan vi inte lagligen nå en egenskap är den BLOCKED och hela FULL_PARITY-målet ej nått. Inga hemliga undantag eller otillåten reverse engineering.

## Arbetsmetod
EN aktiv backlog: docs/ROADMAP.md. EN PR åt gången. Börja med nödvändiga konfiguration-/port-/link-/command-kontrakt, scheduler-POC och eventdriven host-switch-host-ARP. Sådana vertikala bevis får börja utan att alla Cisco-modeller har inventerats; full produktstatus kräver däremot full inventering. Allt byggs för långsiktig användning, inga disposable sidomotorer.

Varje PR: exakt branch/HEAD och case-ID; källor; implementerad stateägare; konkreta positiva, negativa och motsägande tester; fail-closed data-/sessionsbeteenden; gränser; regression; CI och rollback. Testa först riktat, sedan Required checks på exakt HEAD. Ingen forcemerge, bypass, testsänkning, uppfunnet SUCCESS eller passiv polling. Dokument- och governance-PASS betyder inte fungerande simulering.

Läs alltid AGENTS.md, docs/ROADMAP.md, docs/ARCHITECTURE.md, docs/PRODUCT_SCOPE.md, docs/IMPORT_CONTRACT.md, docs/UI_ELK_CONTRACT.md och docs/VERIFICATION.md före en relevant ändring. Ändra endast genom spårbara små PR:er och uppdatera status efter faktisk verifiering.
