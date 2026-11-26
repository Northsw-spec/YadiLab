# YadiLab

**Status: ny, tom Linux-applikation under arkitekturplanering. Ingen nätverksmotor eller färdig simulator är implementerad.**

YadiLab är ett nytt, självständigt projekt med målet att uppnå **full funktionell paritet med Cisco Packet Tracer på Linux**, inklusive alla dokumenterat och i en lagligen installerad baslinje faktiskt verifierade funktioner, enheter, protokoll, arbetsytor, CLI/GUI, Simulation Mode, PDU, IoT/OT, samarbete, lärarverktyg och projektformat. Därefter ska det med oberoende mätningar ge **verifierbart bättre korrekthet, diagnostik, precision och funktioner**. Projektet får inte kalla sig komplett innan bevisen finns.

**Två produktundantag:** ingen Windows-/macOS-utveckling och ingen ny särskild tillgänglighets- eller tangentbordsstyrningsfunktion som paritetskrav. Grundläggande säkerhet och användbarhet undantas inte.

En ny, oberoende och deterministisk diskret händelsemotor ska byggas från grunden. Ingen gammal YadiLab-nätverksmotor kopieras. Den tidigare YadiLab-användarupplevelsen och ELK-/dokumentimportfunktionerna är önskad referens, men **visuell och beteendemässig likhet är ännu ej verifierad** eftersom ZIP/skärmdumpar med versionslåst referens saknas.

**Startpunkter när styrpaketet finns:** `MASTERPROMPT.md` (agentmandat), `AGENTS.md` (utvecklingsregler), `docs/ROADMAP.md` (enda utvecklingsplan), `docs/PRODUCT_SCOPE.md` (funktionsmål), `docs/ARCHITECTURE.md` (motor), `docs/VERIFICATION.md` (bevis).

**Ingen hallucinerad implementation:** planerade features märks PLANNED/NOT_VERIFIED; dokumentation och grön dokumentations-CI är inte fungerande nätverkssimulering.

Källor för kravinventering: [Cisco Packet Tracer Introduction](https://tutorials.ptnetacad.net/help/default/intro.htm), [Cisco 9.0 What's New](https://tutorials.ptnetacad.net/help/default/whatsNew.htm), [ELK Layered](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html).
