# AGENTS — utvecklings- och sanningspolicy

2026-11-26. Detta repo är nytt. Alla funktionspåståenden är NOT_IMPLEMENTED tills faktisk kod och oberoende test finns.

1. Normativa dokument: MASTERPROMPT.md (mandat), docs/ROADMAP.md (enda aktiva utvecklingsplan), docs/PRODUCT_SCOPE.md (full funktionell PT-paritet), docs/PROTOCOL_CATALOG.md (protokollinventering), docs/ARCHITECTURE.md (motor), docs/PROJECT_DATA_CONTRACT.md, docs/UI_ELK_CONTRACT.md, docs/IMPORT_CONTRACT.md, docs/VERIFICATION.md, docs/RELEASE_GATES.md och docs/SECURITY_LEGAL.md.
2. Ny motor från noll. Ingen import av gamla YadiLab-nätverksmoduler eller gamla projektstyrningsspärrar. Tidigare ZIP får studeras ENDAST för UI/ELK/importreferens och dokumentkontrakt efter oberoende granskning, inte för gammal simuleringsemantik.
3. En auktoritativ DES, en scenario-tid och scenario-state. Inga fuskbevis från GUI, CLI, FIB-route, nodposition eller gamla code paths. En fysisk link endpoint är ett explicit node/port-ID-par, aldrig ELK:s ritade kurva.
4. Alla Cisco Packet Tracer-funktioner är REQUIRED med endast två undantag: Windows/macOS och nytt separat accessibility/keyboard-only-mål. Nya upptäckta featureunderfall ska registreras, inte strykas. Ingen funktionsflagga gör det möjligt att kalla en sak implementerad utan verklig beteendeverifiering.
5. Protokollutveckling kräver en offentlig standard och errata eller en legal vendor-specific källa, bytevektorer, state machine, tidsmodell, positiva/negativa/motsägande fall och tests med oberoende facit. Alla stödpåståenden versioneras.
6. Projektdokument, ursprungsbytes och runtime-state är olika ägare. Import kan aldrig uppfinna saknade IP/MAC/gateway/routes/VLAN/länk/port. Endast explicit användarbeslut får fylla ut osäkra källor. Endast explicit Save muterar projektfilen.
7. UI måste ha möjlighet till exakt matchning mot gammal YadiLab-reference ZIP/screenshots. Om dessa saknas får UI inte hävda PIXEL_PARITY; implementera isolerat, med geometriska porttester och browser screenshot-golden-fixturer. ELK är bara layout.
8. Första motor-POC kräver tidiga device/port/link/power/config/CLI-kontrakt. Bygg inte först ett hårdkodat ping och försök sedan lägga BGP/IoT/PLC ovanpå.
9. Linux-only; offline-first. Ingen autentiserad peer, fjärranslutning eller fysisk PLC förrän explicit opt-in med säkerhetsmodell. Ingen exekvering av XLSM-makron, skript från filer eller obetrodd kod i värdprocessen.
10. All kodförändring har liten godkänd arbetskort-ID, test och rollback. En aktiv PR i taget. Main skyddas när regelsystemet är konfigurerat. Ingen falsk eller återanvänd CI-status från annan SHA.
11. Konfigurerbara format och externa bibliotek får föreslås men påstå inte att ett visst XLSB/ODS/PDF-exempel redan har lästs innan fixture-test. Särskilt PDF/diagram är låg evidens och får aldrig autogenerera kabelrelationer utan bekräftelse.
12. För en feature som är proprietär och inte går att stödja lagligt: markera BLOCKED_LEGAL_OR_SPEC, låt den fullständiga slutfunktionsgrinden förbli öppen. Sänk aldrig scope tyst.
13. Bevara även negativa och fuzz-fall; ändra inte tests för att få green när implementationen är fel. README/plan får uppdateras, men dokumentändring bevisar inte produktfunktion.
14. En PR merges med squash först när alla obligatoriska CI-jobb faktiskt visar success på senaste PR-HEAD och inga blockerande reviews finns. Om CI saknas är dess skydd inte etablerat: redovisa detta öppet.

## Definition of done
Verklig implementation, typad ägarmodell, positivt och negativt oberoende test, deterministisk replay där relevant, gränsfall, korrekt docsstatus, exakt SHA/CI och ingen falsk funktionalitet. Ett architecture/design-dokument får status DESIGN_VERIFIED, aldrig VERIFIED_NATIVE.
