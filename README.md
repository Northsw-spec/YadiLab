# YadiLab

**Status: ny, tom Linux-applikation under arkitekturplanering. Ingen nätverksmotor eller färdig simulator är implementerad.**

YadiLab är ett nytt, självständigt projekt med målet att uppnå **full funktionell paritet med Cisco Packet Tracer på Linux**, inklusive alla dokumenterat och i en lagligen installerad baslinje faktiskt verifierade funktioner, enheter, protokoll, arbetsytor, CLI/GUI, Simulation Mode, PDU, IoT/OT, samarbete, lärarverktyg och projektformat. Därefter ska det med oberoende mätningar ge **verifierbart bättre korrekthet, diagnostik, precision och funktioner**. Projektet får inte kalla sig komplett innan bevisen finns.

**Två produktundantag:** ingen Windows-/macOS-utveckling och ingen ny särskild tillgänglighets- eller tangentbordsstyrningsfunktion som paritetskrav. Grundläggande säkerhet och användbarhet undantas inte.

En ny, oberoende och deterministisk diskret händelsemotor ska byggas från grunden. Ingen gammal YadiLab-nätverksmotor kopieras. **UI:t ska däremot se ut och fungera som [YadiLab_legacy](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80) på exakt commit aac82926ced3dbf4cac09242530762ac3da1fe80.** De faktiska Legacy-källorna för HTML/CSS, layout, ELK, import, Builder och diagnostik är nu tillgängliga. [Bindande same-UI kontrakt](docs/LEGACY_UI_FIDELITY_CONTRACT.md) och [55 källmappade UI-fall](docs/requirements/legacy_ui_manifest.json). Källan är verifierad, men inga runtime-skärmbilder eller nya UI-interaktioner är ännu godkända.

**Startpunkter när styrpaketet finns:** `MASTERPROMPT.md` (agentmandat), `AGENTS.md` (utvecklingsregler), `docs/ROADMAP.md` (enda utvecklingsplan), `docs/PRODUCT_SCOPE.md` (funktionsmål), `docs/ARCHITECTURE.md` (motor), `docs/VERIFICATION.md` (bevis).

**Ingen hallucinerad implementation:** planerade features märks PLANNED/NOT_VERIFIED; dokumentation och grön dokumentations-CI är inte fungerande nätverkssimulering.

Källor för kravinventering: [Cisco Packet Tracer Introduction](https://tutorials.ptnetacad.net/help/default/intro.htm), [Cisco 9.0 What's New](https://tutorials.ptnetacad.net/help/default/whatsNew.htm), [ELK Layered](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html).
