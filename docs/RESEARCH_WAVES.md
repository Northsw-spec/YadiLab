# FORSKNING I VÅGOR — bakgrund före nya YadiLab

**Tillagd våg 6 — direkt källkodskontroll av föregående YadiLab.** Legacy commit `aac82926ced3dbf4cac09242530762ac3da1fe80` granskad via GitHub: HTML har 284 unika element-ID:n; CSS definierar mörka färgvariabler och från 951px en fullbreddscanvas överst samt nedre två utfällbara panelkolumner; import-review.js hanterar originalceller, MappingViews, profiler, radbeslut och explicit apply; elk.js validerar tvåpass Worker-/portgeometri och runtime timeout; verkliga browser_elk_layout/elk_import browser tester finns som referens. [Fidelity kontrakt](LEGACY_UI_FIDELITY_CONTRACT.md) och [case manifest](requirements/legacy_ui_manifest.json) låser källorna. **Detta är källgranskning, ingen körd screenshot parity eller migration av gamla motorn.**

Datum: 2026-11-26. Detta är en dokumenterad första källvåg, INTE ett påstående om fullt genomgången installerad Cisco PT-binär, genomförda prestandamätningar eller implementerad programvara. Evidence-klass: DOC_VERIFIED eller IMPLEMENTATION_NOT_VERIFIED.

## Våg 1 — faktiska Cisco-funktioner och begränsningar
Primär Cisco Packet Tracer Introduction: https://tutorials.ptnetacad.net/help/default/intro.htm . Cisco listar logical/physical, device types, simulation, Multiuser, Activity Wizard och en bred LAN/WAN/TCP/IP/routing/security/QoS-lista. Cisco noterar uttryckligen att flera modeller har substantial modelling limitations. Slutsats: "lika bra som PT" omfattar hela arbetsflödet, men samma PT-paketutfall är INTE automatiskt korrekt enligt RFC/IEEE/IEC.

Cisco 9.0 What's New: https://tutorials.ptnetacad.net/help/default/whatsNew.htm ; Industrial OT features: https://tutorials.ptnetacad.net/help/default/industrial_otFeatures.htm . Nya industriella enheter, OT-scenarier, fiber och Cyber Observer/Data Historian kan inte ignoreras. Aktivitetsskapande har scoring/scripting https://tutorials.ptnetacad.net/help/default/activityWizard.htm och https://tutorials.ptnetacad.net/help/default/activityWizard_scoringModelAndScripting.htm . IoT Python/JS, MCU/SBC https://tutorials.ptnetacad.net/help/default/iot.htm . Multiuser https://tutorials.ptnetacad.net/help/default/multiuser.htm . Allt detta är scope-kandidater med Cisco publicerade dokument, inte verifierade testkörningar på en lokal PT-installation.

Uppföljning: Installera lagligen aktuell PT på jämförelsemaskin, registrera exakta build/version/SHA och OS, inventera alla enhet-/module-/CLI-/scenario-/formatunderfall, kör exempel. 9.0-hjälp är inte bevis för all 9.0.1 eller framtida PT-funktion.

## Våg 2 — standardprotokoll före implementation
TCP RFC9293 https://www.rfc-editor.org/info/rfc9293/ , IPv6 RFC8200 https://www.rfc-editor.org/info/rfc8200/ , OSPFv2 RFC2328 https://www.rfc-editor.org/info/rfc2328/ , BGP4 RFC4271 https://www.rfc-editor.org/info/rfc4271/ . Viktigt 2026-fynd: DHCPv6 RFC9915 ersätter RFC8415 (https://www.rfc-editor.org/info/rfc9915/). Slutsats: en källa måste kontrolleras avseende nu gällande revision och errata varje gång en protokollmodul implementeras. "Den kör PT-provet" räcker inte för teknisk riktighet.

## Våg 3 — motorarkitektur utan att återanvända fel
Python heapq dokumenterar priority queue och tie-breaker https://docs.python.org/3/library/heapq.html ; en eventkö med virtual time/event-id och typed state actors är en rimlig DES-kandidat, men prestanda och förmågan att bära alla PT-featurefamiljer är ÄNNU INTE EMPIRISKT VERIFIERAD. Vi utformar event/kernel/device/port/link/CLI-kontrakt från början och mäter POC0/POC1 innan teknologi och kapacitetslöften låses. Inga GNS3/FRR/ns-3/IOS runtime eller en andra "truth engine".

## Våg 4 — tidigare UI-känsla, ELK och nätverksimport
ELK layered https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html har portconstraints och orthogonal edge routing. elkjs https://github.com/kieler/elkjs ger klientbaserad layout. Slutsats: behåll separation mellan diagramgeometri och verkliga nätverkslänkar; visual accuracy kräver mätning av SVG handle-centers, särskilt under PENDING/rerender.

pandas read_excel https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_excel.html dokumenterar calamine för xls/xlsx/xlsm/xlsb/ods, men vårt system måste prova egna fixtures. OWASP file upload https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html varnar för archive/XML bombs och file type; CSV injection https://owasp.org/www-community/attacks/CSV_Injection kräver exportskydd. Slutsats: evidence/provenance pipeline med source bytes+cells+mapping/conflict+explicit commit; ingen gissad kabel.

## Våg 5 — Linux desktop, licens, genomförande
Qt for Python https://doc.qt.io/qtforpython-6/ och Qt WebEngine licensing https://doc.qt.io/qtforpython-6/overviews/qtwebengine-licensing.html visar att PySide6/Qt WebEngine är en möjlig kandidatshell men kräver tillämplig licensgranskning och Linux distribution test. Lokal browser/launcher är en annan prövbar shell, inte ett låst val innan R0-prototyp. Bevara backend+frontend via interface, inte via specifikt desktopbibliotek. Inga Windows/macOS-builds.

## Kända kunskapsluckor och nästa faktiska forskning
- Saknar verifierad licensierad Cisco Packet Tracer-build och fullständig lista över ALLA enhets- och kommandovarianter: G0 kan inte passera.
- **Uppdaterad källverifikation:** Äldre UI finns i [YadiLab_legacy på aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80), inklusive web/index.html, web/styles.css, web/canvas.js, web/features/layout/elk.js, UI- och importtester. Därmed finns faktisk design/interaction-källa utan ZIP. Däremot saknas fortfarande exekverbara screenshot-/DOM-/golden-benchmarks i två olika Chromium-processer, så pixelidentitet kan inte ännu betygsättas.
- Saknar verklig benchmark Python vs Rust, desktop package/Wayland/X11, stora topologier: prestanda och val av shell ej låst.
- Saknar verkliga godkända importfiler från användaren: XLSB/XLS/ODS-formatstöd för YadiLab ej verifierat även om biblioteken annonserar läsning.
- PKT/PKZ/PKA-interoperabilitet och Cisco-specifikt CLI/firmware-behavior är BLOCKED_LEGAL_OR_SPEC till respektive legal/spec path är verifierad.
- Användarstudie för faktiskt bättre inlärning är NOT_RUN och måste vara frivilligt samtyckt, utan att ersättas med påstådd objektiv förbättring.

Denna forskning ger en försvarbar startARKITEKTUR men kan inte garantera att ny YadiLab blir bättre än Packet Tracer. Release och etiketter styrs av faktiska oberoende tester enligt VERIFICATION och RELEASE_GATES.
