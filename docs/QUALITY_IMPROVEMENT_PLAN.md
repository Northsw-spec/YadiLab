# Kvalitetslyft: etappordning och verifieringsläge

Utgångspunkt för etapp 3A: `main` vid `0ef9ec60b7b4ecdce9fee18315e1ae143c0250ea`.
En etapp räknas som verifierad först när dess funktionella och negativa
tester har körts. Detta dokument ger inte någon produktbetygsättning.

| Etapp | Område | Läge |
|---|---|---|
| 1 | Lokal HTTP-gräns | Integrerad i `main` |
| 2 | Samtidighetssäker Save/Open | Integrerad i `main` |
| 3A | Fristående DOM- och API-moduler | Implementerad och lokalt verifierad; CI/merge återstår |
| 3B–3E | Fortsatt frontendmodularisering | Planerad |
| 4 | Källtrogen, användarstyrd dokumentationsimport | Planerad |
| 5 | Oberoende protokollreferenser | Planerad |
| 6 | Pedagogiskt felsökningsflöde | Planerad |
| 7 | Prestanda, tillgänglighet och distribution | Planerad |
| 8 | Oberoende slutgranskning och omvärdering | Planerad |

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
tillstånd. Slutlig CI- och mergeverifiering återstår. Rekommenderat
nästa delsteg är 3B efter separat granskning av Save/Open-beroendena.
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
