# YadiLab – Masterplan för källkodskvalitet 10/10

**Dokumentversion:** 1.0  
**Datum:** 2026-11-21 (ISO)  
**Repository:** https://github.com/Northsw-spec/YadiLab  
**Verifierad bascommit:** `32bcefdf3eff25bc6a4f7986a7d88c05f704214c`  
**Mål:** Högsta möjliga verifierbara källkodskvalitet inom appens uttryckligen stödda omfattning.  
**Status:** QUALITY-001 integrerad; QUALITY-002 konfigurerad men inte negativt enforcement-testad; QUALITY-003–011 planerade.

> **Gällande styrning:** `AGENTS.md` och `docs/MASTERPROMPT.md` gäller övergripande. För import gäller dessutom `docs/IMPORT_SOURCE_CONTRACT.md` och tillhörande tekniska kontrakt. Denna fil är den **enda aktuella samlade kvalitetsfärdplanen**, inte en ersättning för dessa kontrakt. Faktisk kod, CI och den senaste uttryckliga användarinstruktionen avgör aktuell implementationsstatus. Äldre etappanteckningar har bevarats oförändrade i [QUALITY_IMPROVEMENT_HISTORY.md](QUALITY_IMPROVEMENT_HISTORY.md); deras historiska framtidsuttalanden är **inte** aktuella order eller verifierade nulägesuppgifter.

## 1. Syfte och kvalitetsprinciper

YadiLab ska gå från en användbar simulator till en kodbas vars korrekthet, underhållbarhet och tillförlitlighet kan bedömas oberoende. 10/10 är ett **krävande revisionsmål**, aldrig något som deklareras därför att CI är grön eller en viss mängd kod levererats. Det kräver inte stöd för alla nätverksprotokoll eller operativsystem. En smal, korrekt modell är bättre än ett brett system med falska resultat.

Bindande invariants:

1. **En auktoritativ kanonisk nätverksmodell** för deklarerade noder, portar, länkar och zoner.
2. **Inga implicit skapade kablar, gateways, routes, enheter eller MAC-adresser** utifrån namn, placering eller antaganden.
3. **Ingen falsk simulatorframgång:** grafväg, route lookup och ARP är inte automatiskt IP-reachability eller ICMP Reply.
4. **Förlustfri eller avvisad import:** källfakta, cellidentiteter och proveniens får inte tyst tappas.
5. **Beständighet först efter uttrycklig Save:** exakta objekt-ID, bytes, SHA-256, konfliktskydd och omstart måste fungera.
6. **Protokollbeteende testas mot oberoende referenser**, inte enbart mot utfall beräknade av samma produktionskod.
7. **Minsta sammanhängande ändring** per PR. Ingen parallell motor, datamodell eller omotiverad abstraktion.
8. **Tester ska kunna misslyckas av verkliga fel**; positiva och negativa regressioner är obligatoriska.
9. **CI och branchregler måste blockera felaktig merge**, inte enbart observeras frivilligt.
10. **Ärlig status:** VERIFIED, NOT_VERIFIED, UNSUPPORTED eller CONFIRMED_DEFECT. Ingen oprecis PASS.
11. **Begränsningar dokumenteras**, inte döljs bakom allmänna produktpåståenden.
12. **Inga nya funktioner utan motiverad nytta** och en separat verifierbar funktionsdefinition.

## 2. Verifierad utgångspunkt per 2026-11-21

| Kontroll | Verifierat läge |
|---|---|
| `main` | `32bcefdf3eff25bc6a4f7986a7d88c05f704214c` |
| Senaste main-CI | [#44904476735](https://github.com/Northsw-spec/YadiLab/actions/runs/44904476735): SUCCESS på exakt commit |
| Öppna PR:er | 0 vid planens verifiering |
| Python | 636 tester PASS i verifierad CI |
| JavaScript | 10 Node-tester PASS, `npm run check` ingår i CI |
| Chromium | PASS i DIRECT_HTTP, med riktig Save/Open |
| Aktivt main-ruleset | ID 27419615; required status check `unit-tests` **CONFIGURED** |
| Rulesetets blockerande effekt | **NOT_VERIFIED** genom negativ test-PR |
| Strict up-to-date-krav | `strict_required_status_checks_policy=false`; ska riskbedömas |

Redan korrigerade fel: PR #76 (importacceptans), #77 (stale Builder HTTP-svar), #78 (IPv4 host network/broadcast), #79 (VLAN-statistik och full JS-CI). Dessa ska skyddas med regressioner, inte implementeras om.

**Kända riskområden, inte automatiskt belagda buggar:** otillräcklig oberoende protokolljämförelse; okända variationer i verkliga företagsdokument; komplexa större moduler; stora och oregelbundna nät; otestade plattformar; historiskt missvisande README/arkitekturstatus; tangentbordsberoende delar av Builder.

## 3. Etappöversikt och beroenden

| Etapp | Mål | Prioritet | Status |
|---|---|---|---|
| QUALITY-000 | Spårbar baslinje för kod, tester och risker | Hög | DELVIS |
| QUALITY-001 | VLAN-kandidatstatistik + full JS-CI | Hög | ACCEPTED |
| QUALITY-002 | Bevisat obligatoriskt GitHub-mergeskydd | Kritisk | CONFIGURED / ENFORCEMENT NOT_VERIFIED |
| QUALITY-003 | Oberoende nätverksprotokollverifiering | Kritisk | PLANNED |
| QUALITY-004 | Arkitektur, modularisering och förenkling | Hög | PLANNED |
| QUALITY-005 | Dataintegritet, samtidighet och robusthet | Kritisk | PLANNED |
| QUALITY-006 | Verklig dokumentationsimport och proveniens | Hög | PLANNED |
| QUALITY-007 | Prestanda, skalning och resursgränser | Hög | PLANNED |
| QUALITY-008 | Frontend, pedagogik och tillgänglighet | Medel–hög | PLANNED |
| QUALITY-009 | Distribution och plattformsmatris | Medel–hög | PLANNED |
| QUALITY-010 | Aktuell dokumentation och reproducerbar QA | Hög | PLANNED |
| QUALITY-011 | Oberoende slutrevision och betyg | Kritisk | PLANNED |

**Rekommenderad ordning:** QUALITY-002 → QUALITY-003 → QUALITY-004 → QUALITY-005 → QUALITY-006 → QUALITY-007 → QUALITY-008 → QUALITY-009 → QUALITY-010 → QUALITY-011, med QUALITY-000-baslinjen uppdaterad löpande. Ett nytt bekräftat P0/P1-fel bryter ordningen och korrigeras först. Protokollverifiering ska ske före större motorrefaktorering. Etapper får delas i små verifierade del-PR:er; bara en aktiv utvecklingsgren/PR åt gången.

## 4. QUALITY-000 – Kvalitetsbaslinje och spårbarhet

**Syfte:** Skapa objektiva mätpunkter före förändringar.

**Arbete:** inventera produktionsmoduler, ansvar, importgraf, HTTP-gränser, kanonisk projektmutation, asynkrona anrop/stale-guards, duplicering, testtäckning per funktion, bekräftad teknisk skuld, deklarerade plattformar och resursgränser. Mät filstorlek och komplexitet endast som observation, aldrig som automatisk defekt.

**Leverans:** versionshanterad modul-/ansvarskarta, testmatris, lista över bekräftade defekter och osäkerheter, prestandabaslinje, riskrankning. Klassificera allt VERIFIED / NOT_VERIFIED / UNSUPPORTED / CONFIRMED_DEFECT.

**Acceptans:** en oberoende utvecklare kan identifiera en enda sanningskälla för varje funktion samt vilka positiva/negativa kontrakt som redan är verifierade.

## 5. QUALITY-001 – VLAN-statistik och komplett JavaScript-CI

**Status: IMPLEMENTED, PR #79 MERGED, main-CI SUCCESS.**

- Kandidatens VLAN-statistik läser kanonisk `port.vlan`, inte `port.vlanMode`.
- Chromium kontrollerar importerad kandidat med 0, access, trunk och två VLAN-portar.
- Node-test täcker `null`, frånvarande fält och giltiga VLAN.
- GitHub Actions kör hela `npm run check` som del av `unit-tests`.
- Python, Node, Chromium och riktig Save/Open har passerat på integrerad commit.

**Acceptans:** `VLAN CANDIDATE METRICS: PASS`; `FULL JAVASCRIPT CI: PASS`. Ingen ny implementation utan ny reproducerad regression.

## 6. QUALITY-002 – GitHub som verklig kvalitetsgrind

**Status: CONFIGURED, ENFORCEMENT NOT_VERIFIED.**

**2A – Inventering:** verifiera aktiva `main`-regler: PR-krav, linjär historik, deletion/non-fast-forward-skydd, obligatoriska `unit-tests` från rätt GitHub Actions-app. Inga bypass-aktörer får oavsiktligt tillkomma.

**2B – Negativ enforcement-verifiering:** skapa en tydligt namngiven tillfällig testbranch och test-PR med avsiktligt misslyckad `unit-tests` eller tillåten reproducerbar misslyckad status. **Test-PR:n får aldrig mergas.** Bevisa via GitHubs mergebarhets-/regelsvar att merge blockeras. Verifiera även PENDING/missing-status när det går utan kringgående. Stäng test-PR och ta bort testbranch. Ingen försämring av `main`.

**2C – Strict-policy:** riskbedöm `strict_required_status_checks_policy=false` jämfört med krav på uppdaterad branch. Bedöm både race mellan bas och PR-HEAD samt extra CI-kostnad. Behåll alltid den befintliga manuella grinden för förväntad bas.

**2D – Policy:** förbjud direktcommit, force-push, bypass, merge på FAIL/PENDING/UNKNOWN och tyst CI-bortkoppling.

**Acceptans:** `REQUIRED STATUS CHECKS: ENFORCED` först när ett faktiskt misslyckat försök **bevisligen** stoppas. Saknad verifiering = NOT_VERIFIED, inte PASS.

## 7. QUALITY-003 – Oberoende protokollverifiering

**Prioritet: KRITISK.** Referensmatrisen ska fastställa förväntat utfall **före** YadiLab-körning. Förväntade svar får inte genereras av testad produktionskod.

**3A Ethernet / Layer 2:** source-MAC-inlärning, known/unknown unicast, flooding, broadcast, tabeller, kabel-/portfel, alternativa vägar och explicita loop-/STP-begränsningar. Visuella koordinater får aldrig ändra forwarding.

**3B VLAN:** access/trunk, tillåtna VLAN, tagg-/isolationssemantik inom stödd modell, dropporsaker, broadcast och inlärning per korrekt VLAN. Oimplementerade features får ej antas.

**3C ARP (RFC 826):** Request/Reply, MAC- och IP-identitet, cache, svarslös ARP, ogiltigt paket, dubblerad adress, fel VLAN, kabelbrott.

**3D IPv4/routing (RFC 791, RFC 1812, RFC 3021 och relevanta adressregler):** subnät, /30-/31-/32-semantik, connected/static, longest-prefix match, next-hop, fel interface, TTL, returväg, ingen route och paketleverans. Route lookup är inte bevis på reachability.

**3E ICMP (RFC 792):** Echo Request/Reply, korrekta checksummor, type/code, identifierare, sekvens, payload, routerfel inom stödd omfattning; fall med framåtväg utan returväg får aldrig ge REPLIED.

**3F DHCP (RFC 2131):** Discover/Offer/Request/ACK, lease, renewal, felaktig Layer 2-väg, tillstånd, sessioner och separering av virtuell DHCP-tid från processklocka.

**Referensmetoder:** publicerade standarder, oberoende beräkningar av paketbytes och checksummor, referensimplementationer och/eller kontrollerade paketfångster från extern testmiljö. Minst en verkligt oberoende förväntanskälla per stödd regelklass; dokumentera källversion och avgränsning.

**Metamorfa negativa tester:** en raderad nödvändig kabel ska inte förbättra reachability; irrelevant nod ska inte förändra en isolerad väg; nodposition ska inte påverka routing; ogiltig VLAN-övergång ska inte passera; saknad returroute ska aldrig ge Echo Reply; Save/Open får inte ändra nätverkets betydelse.

**Leverans:** `Protocol Reference Matrix` med standard, scenario, förväntad och observerad observation, testkod, avvikelse, status samt dokumenterat UNSUPPORTED.

**Acceptans:** alla avtalade oberoende referensfall PASS utan oförklarade avvikelser; inga kända falskt positiva dataplanresultat; full lokal och CI-regression PASS.

## 8. QUALITY-004 – Arkitektur, modularisering och underhållbarhet

**Syfte:** minska faktiskt svårbegripliga beroenden och regressionsrisk, inte bara radantal.

**Kandidater för undersökning:** `web/app.js`, `web/features/projects/import-review.js`, `network_core/import_plan.py`, HTTP/server- och sessionsgränser. Mät ansvar, upprepade regler, sidoeffekter, testbarhet, beroendegraf, asynkronitet och konkurrerande tillstånd.

**4A:** märk varje del KEEP / REWRITE / DELETE och ange observerad orsak. **4B:** isolera välavgränsade presentations- eller kommandofunktioner med tydligt input/output. **4C:** ersätt belagd duplicering med en gemensam källa. **4D:** bevisa beteendeekvivalens via fokuserade och fulla regressioner.

**Förbud:** ingen total frontend-omskrivning, ny ogrundad state management, parallell importmodell eller ny paketmotor. Ingen kod raderas på grund av storlek/ålder/AI-misstanke utan verifierad inverkan.

**Acceptans:** uppmätt minskning av motiverade ansvarskonflikter och duplicering; oförändrad projektsemantik, Save/Open, import och protokollbeteende.

## 9. QUALITY-005 – Dataintegritet, samtidighet och robusthet

**5A Projekt:** exakta ID, länkändpunkter, schema 1.0–1.4, ogiltiga/okända fält, dubbletter, referenser och ofullständiga objekt; ingen tyst sanering.

**5B Lagring:** atomisk Save, bytes/SHA-256, samtidiga sparningar, namnbyte, filkonflikt, avbrott, projektbyte, äldre fil och full processomstart. Ingen autosave.

**5C Frontend:** kartlägg alla HTTP-svar som kan påverka projekt, diagnos, session eller UI. Testa sena 200/422, överlappande anrop, förändrade indata, New/Open/Import, Stop/Start, Reset/Run, timeout och förlorade svar. Bevara PR #77:s Builder-korrigering.

**5D Server:** registerlås, sessionskapacitet, utgångna ID:n, cleanup, parallella API-anrop, avbruten operation och korrekt processavslut. Flyktiga paket/cache får inte ändra lagrad modell.

**5E Parsergränser:** stora och korrupta filer, ZIP/ODS/XLSX/CSV-kantfall, numeriska och parsergränser, begränsad RAM/CPU och tydlig avvisning utan truncering.

**Acceptans:** inget reproducerat tyst datatapp, inkonsekvent Save-status, föråldrad UI-återställning eller falskt lyckad sessionsoperation. Okända race klassificeras och planeras.

## 10. QUALITY-006 – Verklig dokumentationsimport och proveniens

**Syfte:** pröva källtrogen import av oberoende insamlade, anonymiserade arbetsböcker och CSV-filer som **inte** skapats utifrån YadiLabs egna mallar.

**6A Korpus:** CSV, XLSX, ODS, flera blad/roller, tomma eller oregelbundna rader, avvikande rubriker, partiella och motsägelsefulla port-/VLAN-/länkfakta samt dokumentfamiljer med olika organisationskonventioner. Avidentifiera före offentlig incheckning.

**6B Manuellt facit:** separera direkta cellfakta från användarval, saknade uppgifter, konflikter och ej stödda format. Facit ska bestämmas oberoende av importmotorn.

**6C Test:** exakta source IDs, cellpositioner, MappingViews, ImportPlan, beroenden, valda atomära beslut, historisk importEvidence, replay, källhash, schema 1.4, verklig Save/Open och omstart. Inga implicit skapade kablar.

**6D Användarflöde:** observera verkliga mappningsbeslut och begriplighet. En förenkling får aldrig ersätta källfakta med gissningar.

**Acceptans:** importerad kandidat innehåller exakt uttryckligen valda och verifierbara fakta; oklarheter avvisas eller presenteras som olösta. Ingen tyst datatapp; proveniens kan återverifieras.

## 11. QUALITY-007 – Prestanda, skalbarhet och resursgränser

**Teststorlekar:** flera punkter såsom 3, 47, 100, 500, 1 000 och upp till faktisk deklarerad maxgräns, även varierande port-/länk-/cellantal. Hårdkoda inte specialbeteende för en teststorlek.

**Topologier:** stjärna, kedja, träd, förgrenad routing, segmenterade VLAN, frånkopplade delar och oregelbundna nät. Loopar prövas enligt dokumenterat stöd/avvisning.

**Mät:** validering, importinspektion, kandidatbyggnad, Save/Open, minnes- och CPU-användning, svarstid, SVG-rendering, Builder-interaktion och simuleringsanrop. Dokumentera maskin, OS, Python/Node/Chromium-version, profiler och reproducerbara kommandon.

**Beslutsregel:** bestäm acceptabla budgetar **efter baslinjemätning men före optimering**. Ta inte siffror ur luften. Prestanda får aldrig köpas med utelämnade objekt, förändrade ID:n, avstängd validering eller fabricerade paket.

**Acceptans:** uppfyllda reproducerbara budgetar inom uttalade gränser; utanför gräns tydligt fel utan datatapp.

## 12. QUALITY-008 – Frontend, pedagogik och tillgänglighet

**8A Builder:** förståelig port-/kabelgeometri, tydliga valideringsfel, exakta projektmutationer, rätt Save-indikator och skiljelinje mellan dokumenterat fakta och temporär simulering.

**8B Diagnostik:** visa observationer och stöd för slutsatser. Separera NO_ROUTE, ARP_FAILED, VLAN-drop, felaktig returväg och UNSUPPORTED. Inga orsakspåståenden utan evidens.

**8C Pedagogiska uppgifter:** junior IT-tekniker ska kunna tolka symptom, välja undersökning, pröva hypotes, identifiera stödd orsak och verifiera återställd kommunikation; inte bara klicka fram förprogrammerat PASS.

**8D Tillgänglighet:** testa och rätta centrala tangentbordsflöden, särskilt fokuserbart portval och kabelskapande, samt tydliga namn/feedback. Verifiera fullt arbetsflöde i Chromium.

**8E Oberoende användarprov:** låt personer som inte utvecklat appen utföra realistiska uppgifter. Registrera faktisk uppgiftsframgång, feltolkningar och behov av stöd utan påhittade frekvenser.

**Acceptans:** UI avspeglar alltid kanoniskt tillstånd, begränsningar och faktiska simuleringsresultat; kärnuppgifter kräver inte rå JSON.

## 13. QUALITY-009 – Distribution och plattformskompatibilitet

**Syfte:** endast annonsera plattformar som faktiskt verifierats.

Definiera uttryckligt supportkontrakt för Linux, Windows om avsett, webbläsare, Python, lokalt filsystem, installation, uppstart, nedstängning och uppgradering.

För varje **stödd** kombination: ren installation, skapa/topologi, import, simulering, Save, processstopp, återstart och Open av exakt samma fil med oförändrade ID:n/bytes. Exakta versioner och miljöer ska anges.

**Acceptans:** reproducerbar ren installation enligt dokumentationen. Allt annat märks NOT_VERIFIED och marknadsförs inte som färdigt.

## 14. QUALITY-010 – Dokumentation och reproducerbar QA

**10A Dokumentationsrevision:** synkronisera README, ARCHITECTURE, denna kvalitetsplan, AGENTS, MASTERPROMPT, import- och protokollkontrakt. Historiska påståenden om ”ännu inte implementerat” ska inte utges för aktuella fakta.

**10B Funktionsmatris:** IMPLEMENTED / PARTIALLY_SUPPORTED / UNSUPPORTED / NOT_VERIFIED per central funktion, med kod/testreferens och begränsningar.

**10C Reproducerbara tester:** exakta kommandon, Python/Node/Chromium-versioner, beroenden, miljö, direkt-HTTP-verifiering, faktisk processomstart och förväntade fel.

**10D Kompletterande analys:** överväg Python-typning, JS-kontroller, oanvänd kod, importcykler, duplicering och komplexitet endast med verifierad nytta. Linter-PASS är inte beteendebevis.

**10E Kostnadseffektiv CI:** undvik onödiga upprepningar, men bevara alla obligatoriska negativa och riktiga integrationstester. Ändra inte CI för att dölja fel.

**Acceptans:** en oberoende utvecklare kan följa aktuell dokumentation och reproducera verifierad funktion på ren miljö.

## 15. QUALITY-011 – Oberoende slutrevision och 10/10-mål

**11A Scope:** granska exakt release-`main`: kanonisk modell, Ethernet/VLAN/ARP/IPv4/ICMP/DHCP, import och proveniens, sessionslogik, frontend, persistens, CI-regler, deklarerad distribution och dokumentation.

**11B Nya oberoende scenarier:** använd testfall som inte bara kopierar utvecklarens fixturer: alternativa topologier, felaktiga paket och källfiler, överlappande UI-anrop, gränsvärden, omstarter och prestanda.

**11C Defektklasser:** P0 katastrofalt/systemiskt fel; P1 allvarlig falsk framgång eller tyst datatapp; P2 betydande stödd funktionsbrist; P3 mindre defekt/UX/dokumentation. P0/P1 och materiella P2 ska vara korrigerade före slutgodkännande.

**11D Bedömningsram:**

| Dimension | Vikt |
|---|---:|
| Protokoll- och nätverkskorrekthet | 25 % |
| Kanonisk modell och persistens | 15 % |
| Import och proveniens | 15 % |
| Tester och CI-skydd | 15 % |
| Arkitektur och underhållbarhet | 10 % |
| Robusthet, samtidighet och prestanda | 10 % |
| Frontend och tillgänglighet | 5 % |
| Dokumentation och distribution | 5 % |
| **Totalt** | **100 %** |

Varje dimension betygsätts 0–10 med evidens; viktningen ger ett samlat bedömningsunderlag, inte ett automatiskt pris. 

**11E Krav för ett välmotiverat 10/10:** inga kända P0/P1, inga väsentliga kända P2 inom stödd omfattning, oberoende protokollfall utan oförklarade avvikelser, bevisad dataintegritet och verklig Save/Open, negativa import- och race-tester, verifierat GitHub-mergestopp vid FAIL, dokumenterad prestanda och plattformskompatibilitet, ingen omotiverad duplicering/hallucinerad motor, reproducerbar ren miljö och extern kritisk granskare som anser att kvaliteten är högsta nivå. Absolut frånvaro av framtida fel kan aldrig garanteras.

Om granskningen finner 9/10 redovisas evidens, återstående brister och nya avgränsade åtgärder. Självdeklarerad 10/10 utan oberoende belägg är förbjuden.

## 16. Gemensam process och acceptansgrindar per PR

**Före kod:** läs AGENTS, MASTERPROMPT och relevant kontrakt; kontrollera aktuell `main`, CI, öppna grenar/PR:er; välj verifierat problem; skriv testbar positiv/negativ DoD.

**Under kod:** minsta sammanhängande lösning, ingen parallell datamodell, inga tysta mutationer, dokumentera nya begränsningar; regressionsfall ska först kunna påvisa problemet.

**Lokala kontroller:**

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- `npm run check`
- `python3 tests/browser_smoke.py`
- `git diff --check`
- Etappens egna oberoende verifieringsfall.

**Före squash-merge:** exakt PR-HEAD, samtliga obligatoriska checkar SUCCESS, clean/mergeable, inga blockerande reviews, förväntad `main`-bas och aktiva skyddsregler. Ingen merge vid pending/unknown/fail, konflikt eller behörighetsproblem.

**Efter merge:** verifiera squash-SHA och `main`; kontrollera efterföljande main-CI på exakt SHA innan FINAL ACCEPTED. Misslyckad main-CI kräver separat korrigering; inget falskt godkännande.

**En aktiv utvecklingsgren/PR åt gången.** Separera produktionskod från dokumentations-/mätetapper så att varje PR kan granskas.

## 17. Permanent regel: spara Codex Credits

Codex får aldrig vänta passivt på GitHub Actions.

När kod och lokala tester är färdiga: publicera PR, kontrollera CI **en gång**, merga endast om exakt HEAD redan är godkänd och samtliga andra grindar uppfyllts. Om CI är PENDING/IN_PROGRESS eller okänd: utför endast verkligt produktivt arbete oberoende av CI, annars **avsluta sessionen direkt** med PR-länk, HEAD, run-länk, aktuella resultat och nästa grind.

Förbjudet: `sleep` för CI-väntan, polling-loop, `gh run watch`, upprepade statuskontroller eller tom väntan. CI kontrolleras i separat senare session. Credits-sparande berättigar aldrig bypass av kvalitetskraven.

## 18. Genomförandeordning och avbrottsregler

1. Slutför QUALITY-002 med negativt GitHub-enforcementbevis utan att mergea test-PR.
2. Genomför QUALITY-003 med oberoende protokollreferensmatris och nya negativa tester.
3. Genomför QUALITY-004 efter att motorns förväntade beteende är externt förankrat.
4. Genomför QUALITY-005 dataintegritet, race och resursrobusthet.
5. Genomför QUALITY-006 med autentiskt varierade, anonymiserade externa dokument.
6. Genomför QUALITY-007 med baslinje och deklarerade prestandabudgetar.
7. Genomför QUALITY-008 med verkliga användaruppgifter och tillgänglighet.
8. Genomför QUALITY-009 med deklarerad plattformsmatris.
9. Genomför QUALITY-010 med aktuellt och reproducerbart dokument-/QA-underlag.
10. Genomför QUALITY-011 som oberoende slutrevision på exakt release-SHA.

QUALITY-000:s spårbarhet och risklista uppdateras vid varje etapp. Vid P0/P1 stoppas den normala ordningen tills felet är hanterat. Dokumentation/CI får aldrig hävda mer än det som testats.

## 19. Obligatorisk rapport per etapp

| Fält | Minimikrav |
|---|---|
| Etapp och bas | QUALITY-ID, exakt före-HEAD |
| Ändringar | Filnamn, varför och faktiskt beteende |
| Reproduktion | Ursprungligt bevis eller dokumenterat förbättringsbehov |
| Positiva och negativa tester | Exakta PASS/FAIL och testnamn |
| Oberoende verifiering | Standard/referens, metod, avgränsning |
| Chromium | DIRECT_HTTP eller ärligt angivet annat testläge |
| Persistens | Verkliga bytes, Save/Open, omstart när relevant |
| CI | Exakt HEAD, körningslänk och status |
| GitHub | PR, merge YES/NO, squash-SHA och main-CI |
| Återstående | Kända P0–P3, NOT_VERIFIED, UNSUPPORTED |
| Acceptans | ACCEPTED / PENDING / FAILED |
| Nästa etapp | Konkreta återstående verifieringsgrindar |

Inga hypotetiska PASS, inga uppfunna täckningssiffror, inga påståenden att en pågående Action är godkänd.

## 20. Slutdirektiv

**YadiLab ska inte bli 10/10 genom att bli större.** Målet är verifierbart korrekt, deterministisk, begriplig, användbar, databevarande och lättunderhållen kod inom ärligt stödda gränser.

Endast faktisk evidens, negativ testning och kritisk oberoende revision kan motivera högsta betyg. Ett känt fel får aldrig döljas för att höja resultatet.
