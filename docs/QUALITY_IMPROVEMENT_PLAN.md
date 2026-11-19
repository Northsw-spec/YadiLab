# Kvalitetslyft: etappordning och verifieringsläge

Utgångspunkt för etapp 4A: `main` vid `17acb51c8c64c3b4b7a1026514cb8b0a2177a127`.
En etapp räknas som verifierad först när dess funktionella och negativa
tester har körts. Detta dokument ger inte någon produktbetygsättning.

| Etapp | Område | Läge |
|---|---|---|
| 1 | Lokal HTTP-gräns | Integrerad i `main` |
| 2 | Samtidighetssäker Save/Open | Integrerad i `main` |
| 3A | Fristående DOM- och API-moduler | Integrerad i `main`; CI godkänd |
| 3B1 | Save/Open och projektlista | Integrerad i `main`; CI godkänd |
| 3B2 | Säker import/export | Integrerad i `main`; CI godkänd |
| 3C | ARP-, routing-, IPv4- och ICMP-vyer | Integrerad i `main`; CI godkänd |
| 3D1 | DHCP Investigation-sessionens livscykel | Integrerad i `main`; CI godkänd |
| 3D-SGC | Server Session Garbage Collection | Integrerad i `main`; CI godkänd |
| 3D2 | ICMP Investigation-sessionens livscykel | Integrerad i `main`; CI godkänd |
| 3D3 | DHCP/DORA-sessionens livscykel | Integrerad i `main`; CI godkänd |
| 3D4 | ARP/Ethernet-sessionens livscykel | Integrerad i `main`; CI godkänd |
| 3E | Frontend-entrypoint och integrationsgränser | Integrerad i `main`; CI godkänd |
| 4A | Skrivskyddad källtrogen tabellförhandsvisning | Kontrakt fastställt; ej implementerad | 
| 4B–4D | Explicit mappning, relationer och evidensutvärdering | Heltäckande kontrakt v3.1; etappvisa DoD-grindar och en aktiv PR åt gången |
| 5 | Oberoende protokollreferenser | Planerad |
| 6 | Pedagogiskt felsökningsflöde | Planerad |
| 7 | Prestanda, tillgänglighet och distribution | Planerad |
| 8 | Oberoende slutgranskning och omvärdering | Planerad |

## Etapp 4: bindande implementationskontrakt (v3.1)

Läs [IMPORT_SOURCE_CONTRACT.md](IMPORT_SOURCE_CONTRACT.md) före nästa kodetapp. Etapp 4A är den enda omedelbart tillåtna kodleveransen: skrivskyddad inspektion av CSV/XLSX/ODS utan nätverkstolkning, kandidatprojekt eller Save. 4B–4D är separata etapper med verifieringsgrindar. Samma kontrakt specificerar flera roller per blad, flera mål per rad, en exakt gemensam ImportPlan/responsmodell, radunika användarbeslut, verifierbara originalrader efter 25-radersförhandsvisningen, historiskt provenienskvitto med oberoende källverifiering, schema-1.4-säker editor, VLAN-konvertering och nätverksprojektion för protokollanrop. En etapp får delas upp i små verifierade PR:er men endast en PR är aktiv åt gången; inga nya fristående planeringsdokument behövs. Detta avsnitt anger planeringsstatus, inte verifierat genomförande.

## Etapp 3E: ICMP-panelens presentationsgräns

Tidigare låg ICMP Investigation-panelens observationsformatering,
DOM-val, knappstatus, diagnos, återställning och svensk rapport direkt i
`app.js`. Den läste projektet och ICMP-controllerns kopierade vy men
ägde inget av deras tillstånd. Hela detta presentationsblock finns nu i
`web/features/diagnostics/icmp-investigation-panel.js`. Modulen importerar
bara `ui/dom.js` och får projektet och sessionsvyn som explicita argument.
`app.js` avgör fortsatt när panelen renderas och äger fortsatt det enda
kanoniska projektet, Save/Open, revisioner och händelser. De fyra
sessionscontrollers är oförändrade.

`app.js` gick från 2 421 till 2 237 rader. Det är endast en mätpunkt;
den förbättrade gränsen är att ICMP-presentationen inte längre ligger
bland projektmutation och sessionsanrop. `renderInspector()` ligger kvar
eftersom den muterar projektet och hanterar många port- och routeval.
Troubleshooting- och DORA-panelerna har fler inbördes kopplade
inmatningsval, så de flyttades inte i denna avgränsade etapp.

Den faktiska ES-importgrafen kontrolleras automatiskt från `app.js`:
varje import måste peka på en befintlig lokal fil, alla moduler måste
vara nåbara och grafen får inte innehålla cykler. `index.html` har
fortfarande bara en modul-entrypoint. Den nya modulen tillåts endast på
sin exakta HTTP-sökväg och måste laddas som JavaScript i Chromium.
Riktade U01–U10-kontroller täcker upprepad rendering, bevarade val,
serverbehandlad misslyckad Echo, korrekt diagnos och återställd Echo,
New/Open/Import samt oförändrade sparade bytes.
Lokalt passerade 515 Python-tester, `npm run check` och hela Chromium-smoke
i `DIRECT_HTTP`. PR-CI är ännu inte verifierad.

## Etapp 3D4: ARP/Ethernet-session

Tidigare ägde `app.js` Layer 2-sessionens ID, generation, busy, räknare,
senaste diagnostik och kabelljus. Start, Run, Reset, Stop och
projektinvalidation muterade dessa fält direkt. Stop rensade lokalt utan
att kontrollera serverns svar.

`web/features/sessions/simulation-session.js` äger nu hela sessionens
livscykel och importerar bara `services/api.js`. `app.js` äger fortfarande
kanoniskt projekt, revisioner, DOM, användarens port och mål, Save/Open
och övrig diagnostik. Den ger controllern en fryst projektsnapshot per
anrop och läser en kopierad vy för rendering och transmissionsmarkering.

Start/Run/Reset/Stop fångar ID, generation och projektkontext. Run fångar
dessutom operation, källa och mål. Ett serverbehandlat Run uppdaterar den
verkliga räknaren och tillfälliga ARP/MAC-status även när målet hunnit
ändras; det gamla resultatet och dess kabelljus visas då inte för det nya
valet. Reset efter en behandlad Run tömmer inlärningen, och ett sent Run
kan inte återställa den. Projektbyte ogiltigförklarar lokalt direkt.

Stop kräver serverns `STOPPED` eller dess exakta saknat/utgånget-fel.
Osäkra ID behålls för ett begränsat riktat nytt försök medan sidan är
öppen. Ett sent Start-ID städas riktat. Serverns 60-minuters idle-worker,
kapacitetsgränser och Layer 2-motor är oförändrade; ingen heartbeat finns.

Chromium i `DIRECT_HTTP` testar L01–L22 mot verklig `LabHTTPServer`:
fördröjda svar efter serverbehandling, målbyten, New/Open/Import,
Run/Reset/Stop, förlorade Stop-anrop och svar, exakt retry-422,
serverexpiration och operation limit. Befintliga positiva ARP-, VLAN-,
Ethernet- och Save/Open-flöden bevaras. En verklig projektfil jämförs med
SHA-256. Modulen tillåts bara på sin exakta statiska sökväg; katalog,
okända vägar och extra segment nekas.
Lokalt passerade 514 Python-tester, `npm run check` och hela Chromium-smoke
i `DIRECT_HTTP`, inklusive L01–L22. PR #58 är nu integrerad i `main`
med godkänd CI.

## Etapp 3D3: DHCP/DORA-session

`web/features/sessions/dora-session.js` äger nu den processlokala
DHCP-sessionens ID, generation, busy, serverstatus, DORA-/renewal-spår,
klockhändelser och temporära kabel-, port- och VLAN-felhändelser. Den
importerar endast `services/api.js`. `app.js` behåller projekt,
revisioner, Save/Open, DOM, tillgängliga val, validering och rendering.
De fristående `runDora()` och `runDhcp()` förblir diagnostik utanför
den långlivade sessionen.

Controllern fryser sessions-ID, projektsnapshot, arbetsyte- och
redigeringsrevision samt relevanta inmatningsval för varje anrop. En
serverbehandlad operation uppdaterar status, räknare och leases även
om användaren bytt målval innan svaret når appen; det gamla resultatet
visas då inte som om det gällde det nya valet. Projektbyte ogiltigförklarar
omedelbart sessionen och begär riktat Stop. Gammalt svar eller `finally`
kan inte mutera en ny generation.

Stop kräver `STOPPED` eller serverns exakta `INVALID_PROJECT`-svar för
saknat/utgånget ID. Osäkra ID behålls för riktat nytt försök medan sidan
är öppen. Ett sent Start-ID får egen cleanup. Ett annat 422 behandlas som
valideringsfel. Serverns 60-minuters idle-policy och den separata virtuella
DHCP-klockan är oförändrade; ingen heartbeat finns. Lång inaktiv läsning
kan kräva ny Start.

Chromium använder verklig lokal HTTP-server och fördröjer riktiga svar
efter serverbehandling för Start, Run, Renew, Advance, Reset, felinjektion
och Stop. Den testar måländring, New/Open/Import, gammalt 422, förlorat
Stop-svar, nytt försök, ny session och serverexpiration. Sparad projektfil
kontrolleras med SHA-256. Den nya JS-modulen tillåts endast på sin exakta
statiska sökväg; katalog, okända vägar och extra segment nekas.
Lokalt passerade 514 Python-tester, `npm run check` och hela Chromium-smoke
i `DIRECT_HTTP`, inklusive de riktade DORA-racetesterna. PR #57 är nu
integrerad i `main` med godkänd CI.

## Etapp 3D2: ICMP Investigation

Tidigare låg ICMP-övningens ID, generation, busy-flagga, serverstatus,
observationslogg, diagnos, återställning och fel i `app.js`. Start,
Probe, Diagnose, Repair, Stop och projektinvalidation skrev dessa fält
direkt. `invalidateDoraSession()` var kopplingen från projektändringar.

`web/features/sessions/icmp-investigation.js` är nu ensam ägare för
övningens tillstånd och importerar bara `services/api.js`. `app.js` äger
fortsatt det kanoniska projektet, revisionerna, DOM, inmatningsval,
Save/Open och övriga sessioner. Den ger controllern en fryst projektsnapshot
per anrop och läser en kopierad tillståndsvy vid rendering.
`invalidateDoraSession()` ogiltigförklarar fortfarande ICMP-övningen.

Varje asynkront anrop fångar sessions-ID, generation, arbetsyte- och
redigeringsrevision, projektsnapshot samt relevanta inmatningar.
Sena svar och gamla `finally`-block får inte ändra en ny session.
En mätning vars målval ändrades efter serverbehandlingen räknas i
serverstatus men visas inte som aktuell observation. En äldre hypotes
kan konsumera ett verkligt serverförsök utan att dess verdict visas som
om den gällde det nya valet. Repair kräver verifierat korrekt verdict.

Stop riktas mot fångat ID och verifierar serverns `STOPPED`-svar.
Samtidiga Stop delar ett anrop. Nätverksfel behåller ID för ett begränsat
nytt försök i den öppna sidan; ett sent Start-ID får riktad cleanup.
Backendens exakta `INVALID_PROJECT`/`icmp investigation: unknown or expired
session` efter en operation rensar lokalt tillstånd och erbjuder ny Start
utan meningslöst Stop. Ett annat 422 förblir ett vanligt valideringsfel.
Serverns 60-minuters idle-policy och dess skydd vid förlorat ID är
oförändrade. En användare som läser längre utan anrop kan fortfarande
behöva starta om.

Chromium utökar det befintliga fulla routade och lokala ICMP-förloppet
med riktiga, serverbehandlade svar som hålls före leverans: dubbel och
sent Start, måländringar för alla sex Probe-typer, Probe/Diagnose/Repair
över invalidation, ändrad hypotes, Stop/ny Start, gammalt 422, osäkert
Stop och retry, serverexpiration och övergiven sida. Verklig projektfil
kontrolleras med SHA-256. Statisk HTTP-allowlist omfattar endast den
exakta nya modulsökvägen; katalog och andra filer förblir nekade.
Lokalt passerade 514 Python-tester, `npm run check` och hela Chromium-smoke
i `DIRECT_HTTP`, inklusive de riktade racetesterna. PR #56 är nu
integrerad i `main` med godkänd CI.

## Etapp 3D-SGC: temporära serversessioner

De fyra processlokala registren för Layer 2, DHCP/DORA, DHCP Investigation
och ICMP Investigation hade tidigare ingen serverbaserad städning av
övergivna sessioner. De omfattas nu av en gemensam policy: **60 minuters
verklig inaktivitet**, mätt med monotonic-klocka. Valet ger utrymme för
normala längre övningar och begränsar kvarvarande resurser. En lyckad
operation för ett giltigt ID förnyar endast den sessionens stämpel;
ogiltiga ID:n, misslyckade operationer, startsida och hälsokontroll gör
det inte. Ingen heartbeat införs: en användare som läser i över 60
minuter utan API-anrop kan därför förlora sessionen och får starta om.

Varje `LabHTTPServer` äger en cleanup-tråd, som blockerar på en Event
och vaknar högst var 60:e sekund. Därmed frigörs en övergiven session
utan nytt klientanrop senast cirka 61 minuter efter sista giltiga
aktivitet, förutsatt att serverprocessen och dess worker kör. Start
rensar även förfallna poster före kapacitetskontrollen. `server_close()`
väcker workern och inväntar den i högst fem sekunder; om den fortfarande
lever rapporteras ett fel i stället för ett falskt lyckat avslut. En
pågående lokal operation kan fördröja avslutet tills registerlåset släpps.

Expiration, operation och Stop använder samma `RLock` per register.
Ingen session tas bort mitt under en operation, och ett gammalt ID kan
inte återaktiveras. Städningen släpper bara temporära minnesobjekt;
sparade projekt och protokollsimulering ändras inte. Den virtuella
DHCP-klockan påverkar aldrig den monotonic-baserade livslängden.
Frontendens DHCP Investigation-controller tolkar en operations exakta
"unknown or expired session" som ett utgånget ID och erbjuder ny Start.
Osäkra Stop-resultat, inklusive ett svar som inte bevisar att just det
avsedda ID:t stoppades, behålls för nytt försök.

Deterministiska tester täcker alla fyra register, aktiv och ogiltig
operation, virtuell tid, kapacitetsåtervinning, cleanup mot operation
och Stop, två separata serverinstanser, oförändrade projektbytes och
schemalagd städning utan HTTP. Chromium täcker övergiven sida,
förlorat Stop, fortsatt aktiv session, utgånget ID och ny Start.
En session som ännu inte nått timeout finns kvar; ett skickat Stop är
fortfarande bara best-effort tills servern bekräftar frånvaro. Vid
processavslut försvinner allt processlokalt sessionstillstånd.

## Etapp 3D1: DHCP Investigation

`web/features/sessions/dhcp-investigation.js` äger övningens enda
sessions-ID, serverstatus, generation, busy-flagga, observationslogg,
diagnos, återställningsresultat, fel och klockhändelse. `app.js` äger
fortsatt det kanoniska projektet, revisionerna, inmatningsfält och DOM.
Den ger controllern en projektsnapshot och visar en kopierad tillståndsvy.
Övriga DHCP- och ICMP-sessioner har inte flyttats.

Vid varje anrop fångas sessionens ID, generation, arbetsyte- och
redigeringsrevision, projektsnapshot och relevanta inmatningar. Svaret
används bara om alla fortfarande hör till samma övning. Stop kan avbryta
en pågående operation; ett sent svar för den operationen kan då inte
återställa logg, klocka, diagnos eller resultat. Invalidation tömmer
frontendens övning direkt och skickar riktad Stop för dess tidigare ID.
Om Start redan skapade en serverresurs men svaret blivit inaktuellt,
skickas Stop för ID:t i det sena svaret. Samtidig Stop för samma ID delas
av ett enda anrop. Misslyckad städning sparar ID:t för ett senare försök;
ett skickat Stop räknas aldrig som bevis för att servern tog bort resursen.
Serverns egen låsning och projektsnapshotkontroll är oförändrade.

Chromium-regressionen täcker befintligt fullständigt förlopp med DORA,
lease, T1/T2, observationsinsamling, diagnos, verklig DHCP-återställning
och Stop. Nya negativa fall håller riktiga HTTP-svar efter serverns
bearbetning: Start och projektbyte, dubbel Start, Probe och invalidation,
Advance följt av ny session, ett verkligt sent Diagnose-422 efter
projektbyte, Repair följt av Stop, sen Stop efter ny Start samt API-fel
med ny giltig mätning och misslyckad Stop följd av lyckat nytt försök.
Den kontrollerar serverns sessions-ID där
endpointen medger det. Lokalt passerade 505 Python-tester,
`npm run check` och Chromium med direkt HTTP.

En osäkerhet återstår när Stop misslyckas på nätverksnivå: frontend kan
inte avgöra om servern hann radera ID:t. Controllern behåller då ID:t för
försök vid nästa Start i samma öppna sida. Om sidan stängs kan ID:t
förloras. Servern begränsar antalet aktiva sessioner men har ingen
verifierad automatisk sessionsstädning vid borttappat ID.
Nästa avgränsade delsteg är 3D2: granska
övriga långlivade sessioner med samma kontrakts- och raceanalys.

## Etapp 3C: fyra diagnostikflöden

`web/features/diagnostics/queries.js` skickar separata projektsnapshots
till befintliga API-endpoints för ARP, route lookup, IPv4 trace och ICMP
Echo. `presenters.js` returnerar statusklass och samma svenska resultattext
för respektive svar. Ingen av modulerna äger tillstånd eller DOM, och
ingen nätverksmotor har flyttats eller duplicerats.

`app.js` äger fortsatt projekt, revisioner, användarval,
diagnostikresultat, länkmarkeringar, canvas och alla sessioner. Varje
startad diagnos får en generation per typ samt fångar arbetsyterevision,
redigeringsrevision, projektets serialiserade innehåll och alla relevanta
inmatningsvärden. Både lyckade och felaktiga API-svar förkastas om något
har ändrats eller en senare körning startats. Ändrade inmatningar
ogiltigförklarar den visade diagnosen; ARP rensar då även markerade
länkar. Samma kontroller gäller fördröjda 422-fel och överlappande
anrop. API:t får en fristående kopia av klickets projektsnapshot.

Chromium kontrollerar normal ARP med MAC-tabell och fysisk länkmarkering,
fördröjd ARP efter arbetsytebyte, ändrad route-destination, ändrad IPv4
TTL, ändrat ICMP-mål, två överlappande route lookups och ett äldre
HTTP-fel som svarar efter en giltig route lookup. Befintliga tester
kontrollerar statusar, svenska protokollförklaringar, länkreferenser,
Save/Open, import/export och sessionsfunktioner. Den exakta statiska
HTTP-listan omfattar bara de två nya modulerna.
Lokalt passerade 505 Python-tester, `npm run check` och den utökade
Chromium-regressionen med direkt HTTP och riktiga API-svar.

3D återstår för DHCP-/ICMP-övningarnas och de långlivade sessionernas
livscykler; deras delade generationer och server-ID:n får inte brytas
isär utan egna race-tester. 3E återstår för en tunnare entrypoint.
Slutlig CI- och mergeverifiering för 3C återstår.

## Etapp 3B2: import/export med arbetsyteskydd

`web/features/projects/transfer.js` innehåller strikt UTF-8-avkodning,
filstorlekskontroller, förberedelse av redan stödda CSV-, XLSX-, ODS-
och projektformat, API-anrop samt beredning av exportbytes och MIME.
Modulen håller inget projekttillstånd och importerar bara `api()`.
`app.js` äger fortsatt projekt, filnamn, SHA, revisioner, dialogbeslut,
`resetProject()` och start av webbläsarnedladdning.

Vid importstart fångar `app.js` arbetsyte- och redigeringsrevision,
filnamn och projektets serialiserade innehåll. Den kontrollerar dem
efter asynkron filinläsning och efter API-svaret, före dialogerna.
Sena svar avvisas även om en ny arbetsyta har identiskt JSON-innehåll,
eftersom arbetsyterevisionen då har ändrats. Export använder en
separat snapshot från klicket och kontrollerar samma kontext innan
nedladdningen startas. Projektfilens namn fångas vid samma tidpunkt
som dess innehåll. Inga importer autosparas och inga svar ändrar SHA.

Chromium testar fördröjd import följd av redigering eller arbetsytebyte,
nekad import, ogiltig UTF-8/schema/filtyp, fördröjd projekt- och
XLSX-/ODS-export utan inaktuell nedladdning samt normal import och
verifierade nedladdningsbytes. Befintliga Save/Open-, 409- och
omstartstester körs fortfarande. HTTP-servern tillåter endast den
exakta nya modulvägen; kataloger och andra sökvägar nekas.
Lokalt passerade 505 Python-tester, `npm run check` och den utökade
Chromium-regressionen med direkt HTTP och kontrollerade nedladdningsbytes.
Etapp 3B2 har därefter integrerats i `main` med godkänd CI. 3C behandlas
ovan; 3D och 3E återstår.

## Etapp 3B1: projektlagring utan dubbelt tillstånd

`app.js` äger fortfarande `project`, `filename`, `savedName`,
`savedSha`, `savedSnapshot`, `editRevision`, `workspaceRevision` och
`savePending`. Den ansvarar för användarbekräftelse, Save-indikator,
rendering och ogiltigförklaring av diagnostiksessioner vid Open.
`web/features/projects/persistence.js` är statslös: den fryser
filnamn, revisioner, förväntad SHA och projektets serialiserade innehåll
vid Save-klicket, anropar API:t, sköter konfliktens eventuella andra
anrop och läser projekt eller projektlista. Den har ingen långlivad
projektkopia och importerar bara `api()`; importgrafen är acyklisk.

Vid konflikt kontrollerar `app.js` arbetsyta, redigeringsrevision,
filnamn och projektinnehåll innan användaren får godkänna en overwrite.
Vid lyckad Save tillämpar den SHA och sparad snapshot endast på samma
arbetsyta och fil. Nyare redigeringar lämnas kvar och visas som
osparade. Ett sent Open-svar kräver samma arbetsyta, redigeringsrevision,
filnamn, projektinnehåll och valda projektfil innan det får ersätta
arbetsytan. Backendens fil- och processlås samt HTTP-kontrakt är
oförändrade.

Chromium-regressionen fördröjer leveransen av verkliga HTTP-svar efter
att servern har behandlat dem och kontrollerar Save följt av redigering,
Save följt av arbetsytebyte, dubbel Save, en diskbaserad 409-konflikt
följd av lokal redigering och en senare giltig Save, Open följt av
redigering samt Open följt av nytt filval. Den befintliga Save/Open-
kontrollen över omstart finns kvar. Den nya modulen kontrolleras för
direkt HTTP och JavaScript-MIME; negativa HTTP-tester nekar fortfarande
okända vägar. Etapp 3B1 är nu integrerad i `main` med godkänd CI.
Lokalt passerade 505 Python-tester, `npm run check` och den utökade
Chromium-regressionen med direkt HTTP och verkliga projektfiler.

3B2 har därefter flyttat filberedning och API-anrop för import/export.
Kvarvarande risk är den stora entrypointen och de delade diagnostik-
och sessionsberoendena; 3C–3E följer beroendekartan nedan.

## Etapp 3A: modulgränser och fortsättning

`web/app.js` är fortsatt enda ägare av projekttillstånd, sparad SHA,
redigeringsrevisioner, diagnostikresultat och sessionsgenerationer. De
nio generiska DOM-hjälpfunktionerna (`$`, `el`, `field`, `heading`,
`small`, `button`, `input`, `dropdown`, `check`) ligger i `web/ui/dom.js`.
`api()` ligger i `web/services/api.js` och behåller GET/POST, JSON och
felmetadata. Båda modulerna är tillståndslösa och importerar inget från
appen. `app.js` importerar dessutom den rena projektmodellen från
`model.js` och `TopologyCanvas` från `canvas.js`; `canvas.js` importerar
endast `truncate` från `model.js`. Därmed finns ingen cirkulär import.
HTML startar fortfarande bara `app.js` som ES-modul. HTTP-servern
tillåter exakt de två nya modulvägarna utöver sina tidigare statiska
resurser.

Fortsatt beroendekarta:

| Steg | Möjlig gräns | Beroenden som måste lösas först |
|---|---|---|
| 3B | `saveProject`, `openProject`, import/export och projektlista | `project`, `filename`, `savedName`, `savedSha`, `savedSnapshot`, `editRevision`, `workspaceRevision`, `savePending`, `isDirty`, `changed`, `render`, `notify`, `api`; behåll ett enda tillstånd och skyddet mot sena Save-svar. |
| 3C | Visning och mätanrop för ARP, IPv4, route lookup och ICMP | `project`, valda noder, `canvas`, markerade länkar, `render`, diagnostikresultat och `api`; skilj vyfunktioner från anrop utan att skapa en ny simuleringsmotor. |
| 3D | DHCP-, DORA- och ICMP-övningarnas livscykler | Sessions-ID, generationer, busy-flaggor, loggar och ogiltigförklaring i `changed`; flytta varje livscykel som en enhet så att sena svar inte kan återuppliva gammalt tillstånd. |
| 3E | Tunnare entrypoint och importgranskning | 3B–3D:s stabila gränser; koppla ihop rendering och händelser i `app.js`, kontrollera importgraf och regressioner. |

Den kvarvarande `app.js` är fortfarande stor och dess delade tillstånd
är en risk vid senare extraktioner. Etapp 3A flyttar inget sådant
tillstånd. Etapp 3B1 har därefter avgränsat Save/Open-flödet.
Vid 3A minskade `app.js` från 3 323 till 3 267 rader. Lokalt passerade
505 Python-tester, `npm run check` och Chromium-regressionen med direkt
HTTP, inklusive modulladdning och MIME-kontroll. Radantalet är enbart
en mätpunkt; de isolerade ansvaren är skälet till extraktionen.

## Etapp 2: samtidiga Save-anrop

Före ändringen låg SHA-256-kontrollen utanför en gemensam kritisk
sektion. Barriärstyrda tester på den gamla koden gav två lyckade
skrivningar mot samma gamla hash, även i två riktiga Python-processer,
vid create-only och över HTTP. Den ena uppdateringen kunde då tyst
försvinna.

På lokal Linux använder `ProjectStore.save()` nu `fcntl.flock` på en
separat, beständig `.lock-<projektnamn>` i projektkatalogen. Låset
identifieras av det validerade projektnamnet och byter inte inode när
`.yadilab`-filen ersätts. Samma projekt synkroniseras mellan trådar,
`ProjectStore`-instanser och processer; olika projektnamn har olika
lås. Hashkontroll, temporär fil, fil-`fsync`, `os.replace` och
katalog-`fsync` sker medan låset hålls. `finally` frigör det även vid
konflikt eller skrivfel. Formatet och de explicita Save/Open-anropen
ändras inte.

Verifierade lokala fall: exakt en vinnare och en `ProjectConflictError`
för samtidiga uppdateringar och create-only, korrekt HTTP 200/409,
oförändrad originalfil efter fel före ersättning, städad temporär fil,
och möjlig ny Save efter fel. Chromium verifierar Save, Open, ny Save
med läst SHA och avvisad konflikt efter en separat diskändring. Den
fulla Python-sviten passerade med **504 tester** (varav fem nya
samtidighetstester), `npm run check` passerade och Chromium-regressionen
passerade med **DIRECT_HTTP**. Etapp 2 har därefter integrerats i `main`.

Lösningen är verifierad för YadiLabs lokala Linuxmiljö och samverkande
skrivare som använder `ProjectStore`. Externa verktyg som ändrar
`.yadilab` utan låset följer inte kontraktet. Låsfilerna måste finnas
kvar som stabila låsobjekt; att radera dem medan skrivare är aktiva
kan bryta synkroniseringen. Portabilitet till andra plattformar eller
nätverksfilsystem har inte verifierats.

## Etapp 1: hotmodell och HTTP-kontrakt

Servern lyssnar bara på `127.0.0.1`, men en webbsida på en annan domän
kan försöka nå den via användarens webbläsare. DNS-rebinding kan styra
ett främmande namn till loopback. Därför måste varje `GET` och `POST`
ha exakt en `Host` med serverns faktiska bindningsadress **och port**.
Endast `http://127.0.0.1:<faktisk port>` tillåts som `Origin` när fältet
finns. `Sec-Fetch-Site` får bara vara `same-origin` eller `none` när det
finns; främmande och samma-site-anrop från en annan origin avvisas.
Absoluta HTTP-mål och mål som börjar med `//` avvisas. Ingen CORS-header
ges och `OPTIONS`-preflight avvisas.

Det egna gränssnittet använder samma origin och JSON. Dokumenterade
lokala skript får anropa API:t utan `Origin` eller Fetch Metadata, men
`POST` måste ha `Content-Type: application/json` (valfri charset).
Den medietypen kräver preflight i en annan origins webbläsarskript;
vanliga cross-site-formulär kan inte skriva JSON via denna API-gräns.
En nekad förfrågan når varken projektlagring eller simuleringssessioner.

Detta är en **webbläsargräns, inte autentisering**. En annan process med
användarens lokala åtkomst kan förfalska HTTP-fält eller läsa filer med
samma filbehörighet. Ingen skyddsgaranti mot sådan lokal kod påstås.

Före ändringen gav en riktig socketförfrågan med `Host: evil.example`
`200` och projektdata, och främmande `Origin` fick också `200`.
`tests/test_http_boundary.py` reproducerade dessa fel före rättningen.
Efter rättningen måste testet visa 403 före läsning/skrivning, 415 för
form-liknande POST, nekad preflight samt fortsatt legitima anrop.
