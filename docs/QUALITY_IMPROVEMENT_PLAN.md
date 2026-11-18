# Kvalitetslyft: etappordning och verifieringsläge

Utgångspunkt för etapp 3D1: `main` vid `2916ca7c9c3f3c5edf7dbb5d07a35f97f632dcb8`.
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
| 3D1 | DHCP Investigation-sessionens livscykel | Lokalt verifierad; ej mergad |
| 3D2–3E | Fortsatt frontendmodularisering | Planerad |
| 4 | Källtrogen, användarstyrd dokumentationsimport | Planerad |
| 5 | Oberoende protokollreferenser | Planerad |
| 6 | Pedagogiskt felsökningsflöde | Planerad |
| 7 | Prestanda, tillgänglighet och distribution | Planerad |
| 8 | Oberoende slutgranskning och omvärdering | Planerad |

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
