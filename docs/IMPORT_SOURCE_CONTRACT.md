# Kontrakt för källtrogen dokumentationsläsning och import

**Dokumentversion:** 3.1 – korrigerat integrations- och API-kontrakt 4A–4D  
**Beslutat läge:** Ett enda normerande målkontrakt för 4A–4D, reviderat efter direkt granskning av öppna importimplementationer. 4A byggs först och 4B–4D därefter i separata PR:er. Dokumentet anger krav, inte redan uppfyllda funktioner.  
**Kodbas:** `detta repository`, referens-`main` `17acb51c8c64c3b4b7a1026514cb8b0a2177a127`.  
**Omfattning:** Hela den beslutade funktionen för tabellinspektion, explicit fältmappning, ofullständig nätverksdokumentation, proveniens, import, profilåteranvändning och slutacceptans. Funktionerna är målkrav, inte statuspåståenden.

## 1. Prioritet och ansvar

1. `AGENTS.md` och `docs/MASTERPROMPT.md` gäller övergripande. För **etapp 4** anger detta dokument det detaljerade, versionshanterade funktionskontraktet.
2. Verifierad källkod och senaste uttryckliga användarinstruktion har företräde framför gammal statusinformation i dokumentation och chattar.
3. En etapp får bestå av flera små, sammanhängande PR:er. Genomför 4A → 4B → 4C → 4D i ordning; avsluta och verifiera varje del-PR på main före nästa. En etapp räknas färdig först när dess samlade DoD passerat på main. Endast en aktiv PR åt gången. Detta enda kontrakt styr samtliga steg; en framtida implementerare får inte kräva eller skapa ett nytt planeringsdokument för att fylla i uteblivna funktionskrav. Om den faktiska källan saknar avgörande fakta, redovisa blockerande indata i stället för att gissa.
4. En egenskap som inte finns i kod, test eller kontrakt får inte påstås vara implementerad eller verifierad. Okänd semantik ska ge en explicit olöst uppgift eller avvisning – aldrig nätverksobjekt.
5. Forskningsessäer, procentbedömningar, exempel på företagsmallar och föreslagna profilnamn är **inte** maskinläsbara scheman, produktstöd eller implementationsinstruktioner.

## 2. Befintliga kontrakt som ska förbli auktoritativa

- `network_core/model.py` och `validate_project()` är enda slutliga projektvalidator. Nätverkets kanoniska ID:n och explicita länkändpunkter bevaras.
- `network_core/csv_import.py` importerar det exakta befintliga CSV-kontraktet `Devices.csv`, `Interfaces.csv`, `Links.csv`, `Zones.csv`.
- `network_core/xlsx_import.py`, `ods_import.py` och `spreadsheet_schema.py` äger de **redan stödda** namngivna kalkylbladen, schema 1.0 och explicit schema 1.3.
- `network_core/storage.py` äger beständighet, SHA-256 och konfliktkontroll. `web/app.js` äger det enda aktuella arbetsprojektet, revisioner, arbetsytebyte och uttrycklig Save. Befintliga redigeringsvägar skriver i flera fall `attempt.schemaVersion = '1.3'`; de måste ändras innan schema 1.4 kan aktiveras, annars riskeras avvisad Save eller osynlig nedgradering.
- Nuvarande modell har nodtyperna `host`, `switch`, `router`, `firewall`. Ett annat källvärde får inte mappas till någon av dessa genom namnmönster eller gissning.
- Nodposition `x/y` är **presentationsdata**, aldrig källa till fysisk topologi. IP, gateway, zon, management-IP, hostname, portbeskrivning, LLDP-granne eller skärmläge är inte tillräckliga fakta för att skapa en fysisk kabel.
- Befintliga endpoint-kontrakt för CSV/XLSX/ODS och direkt `.json/.yadilab` bevaras oförändrade tills ett separat migreringskontrakt uttryckligen godkänts.
- Inget importflöde får skriva projektfil före användarens uttryckliga Save eller ersätta arbetsytan före fullständig validering och användarbekräftelse.

## 3. Fastslagen målarkitektur

Läsning och import ska ha fem åtskilda ansvar:

1. **Källavkodning:** Formatgränsspecifik, resursbegränsad inläsning av faktiska filer till källtrogna celler och positioner. Ingen nätverkstolkning.
2. **Dokumentroll och profil:** Ett blad kan få flera användarbekräftade, namngivna mappningsvyer; en rad får bidra till flera objekt och flera rader får bidra till samma objekt. Profiler innehåller explicita mappningsregler, inte kompletta konkurrerande filparsers eller nätverksmotorer.
3. **Importplan:** Användarbekräftade fält ger typade, flera-till-flera-kopplade planändringar med stabil identitet, beroenden, separata dispositioner, konfliktstatus och spårbara cellreferenser. Ingen skrivning sker vid planering. Ofullständiga uppgifter är blockerade eller uttryckligt exkluderade, inte uppfunna.
4. **Kanonisk validering:** Det slutliga projektet valideras av `validate_project()`; ingen adapter kan kringgå dess regler.
5. **Förhandsvisning och godkännande:** UI visar importerbara fakta, blockerande fel och alla olösta källfält före någon projektförändring. En liten projektbunden proveniensmanifest följer med när användaren sparar, men originalfilbytes lagras inte automatiskt i projektet. En separat uttrycklig källexport gör full source-retention möjlig. Save förblir separat.

Källfakta, härledda presentationskoordinater och faktisk simulering är olika kategorier. En lyckad import betyder att ett avgränsat datakontrakt uppfyllts – inte att nätverket observerats, är komplett eller har verifierad reachability.

## 4. Etapp 4A – exakt nästa kodleverans

**Leverans:** Skrivskyddad granskning av en enskild CSV-, XLSX- eller ODS-fil med faktiska blad, råa cellvärden, koordinater, typer och tydliga gränsmeddelanden. **Ingen mappning till nätverksobjekt, ingen importkandidat och inget nytt sparformat i 4A.**

### 4A.1 Backend och HTTP

Inför en läsfunktion i `network_core/import_inspection.py`. Utveckla eventuella interna, formatavgränsade läshjälpare bara om de krävs; duplicera inte befintliga validatorer eller ZIP-skydd. Befintliga produktionsimportörer ska ge identiskt resultat före och efter ändringen.

Inför exakt en ny endpoint: `POST /api/import/inspect`.

Request är ett JSON-objekt med exakt dessa fält:
- `filename`: ett enda källfilnamn, utan sökväg, med filändelsen `.csv`, `.xlsx` eller `.ods` (skiftlägesokänslig ändelse).
- `contentBase64`: standard-base64 för filens **oförändrade bytes**, strikt avkodad.
- `csvDelimiter`: endast för CSV, exakt `,` eller `;`. Fältet är obligatoriskt för CSV och förbjudet för XLSX/ODS; inget automatiskt avskiljarval. Ett syntaktiskt giltigt enkolumnsresultat kan bero på fel val men går inte generellt att särskilja från en avsiktlig enkolumnstabell utan ett kolumnschema.

Requesten innehåller inga projektdata, ingen destinationsfil och inget Save-kommando. Endpointen är statslös och skriver varken projekt, originalfil eller temporära användarfiler till beständig lagring.

Returnera HTTP 200 med följande entydiga struktur vid fullständigt stödd inspektion:

```json
{
  "inspectionVersion": "1",
  "source": {
    "filename": "inventory.xlsx",
    "kind": "xlsx",
    "sha256": "<lowercase SHA-256 of exact original bytes>"
  },
  "tables": [
    {
      "tableId": "sheet-1",
      "name": "Inventory",
      "rowCount": 2,
      "populatedRowCount": 2,
      "columnCount": 2,
      "previewRows": [
        {
          "row": 1,
          "cells": [
            {"address": "A1", "type": "text", "value": "Hostname"},
            {"address": "B1", "type": "text", "value": "Management IP"}
          ]
        }
      ]
    }
  ],
  "previewRowLimit": 25
}
```

Exakt betydelse:
- `tableId` = `sheet-1`, `sheet-2`, … i dokumentets verkliga ordning; för CSV är det alltid `sheet-1`.
- `name` = verkligt bladnamn för arbetsbok; för CSV är det filnamnet. Namn ska inte användas för att härleda dokumentroll.
- För XLSX/ODS är `rowCount` det högsta ursprungliga radnumret med lagrat cellvärde, inklusive mellanliggande radgap. För CSV är `rowCount` antalet **logiska CSV-records**, med första record på radindex 1: en citerad cell med inbäddad radbrytning räknas som **ett** record. `columnCount` är högsta position med ett lagrat värde (för CSV: antal fält i ett record). Rader eller kolumner komprimeras aldrig så att originalpositionerna ändras.
- `previewRows` = de första högst 25 källrecords/rader med lagrade värden, i stigande ordning, utan att välja ett syntetiskt rubrikområde. För CSV är `row` ett logiskt record-index; celladresser använder samma record-index. För XLSX/ODS är `row` och `address` faktiska källkoordinater. `previewRowLimit` anger gränsen. UI visar `Förhandsvisade X av Y källrader`, där Y är antalet records/rader med data och inte får förväxlas med det högsta radnumret när det finns gap. Detta kräver att API-svaret dessutom innehåller `populatedRowCount` per tabell.
- `type` är endast `text`, `number` eller `boolean`. `value` är den bokstavliga cellsträngen enligt dokumentet, utan trimning, datumtolkning, formelberäkning eller omklassificering. Tomma celler listas inte; deras position förblir härledbar genom koordinaterna.
- Ingen rad antas vara rubrik. En rad med `IP Address` ger aldrig automatiskt en `ipv4`-mappning.
- `sha256` bindes till exakt inlästa bytes. Detsamma kan kontrolleras oberoende i tester.

Vid fel returneras den befintliga feltypen `ProjectValidationError` / HTTP 422 med en begriplig felorsak som, när det går att fastställa, nämner blad och originalcell eller rad. Ge inget partiellt framgångssvar med tyst tappad data. HTTP-status och felobjekt ska följa serverns etablerade `_respond_error()`-kontrakt.

### 4A.2 Stödda lässemantiker och gränser

- CSV: strikt UTF-8 med valfri BOM; `csv.reader` med uttryckligen vald avskiljare, `strict=True`, korrekt quoting och stabilt logiskt record-index. Felaktig UTF-8, NUL, obalanserade citat och inkonsekvent antal CSV-fält per icke-tomt record avvisas. En fil med konsekvent en enda kolumn är **giltig** även om användaren valt en annan avskiljare än upphovspersonen; visa då `En kolumn identifierad – kontrollera avskiljaren` utan påstående om upptäckt fel. Den senare explicit valda dokumentrollen får avvisa otillräcklig kolumnstruktur. Bevara ledande nollor som text; varje CSV-cell får typen `text`.
- XLSX: verifiera riktig OOXML-ZIP med lokala relationer. Läs endast synliga blad med vanliga literala text-, nummer- eller booleska celler. Bevara rå numerisk sträng, särskilj celltyp, och använd faktisk OOXML-koordinat. XLSX-serialiseringens numeriska ID är **inte** bevis för ursprunglig ledande nolla.
- ODS: verifiera riktig ODF-paketering och manifest; läs endast synliga tabeller med vanliga literala text-, nummer- och booleska celler. Bevara faktisk position inklusive korrekt uttryckta tomma upprepningar.
- Alla format: avvisa formler och cached formula results, makron, externa referenser, dolda rader/kolumner/blad, sammanslagna celler, kryptering, otolkade objekt med potentiellt relevant innehåll, icke-stödda celltyper, ogiltig struktur och ZIP/XML-problem. Visa ett specifikt `unsupported`-fel hellre än förvanska innehåll.
- Resursgränser för **nya 4A-läsaren**, inte en ändring av äldre strikta importer: högst 5 MiB CSV; högst 5 MiB komprimerad XLSX/ODS; högst 12 MiB totalt expanderade ZIP-poster; högst 5 MiB per XML-del, högst **256 ZIP-poster**, **32 blad**, **5001 fysiska rader per blad**, **256 fysiska kolumner**, **100 000 lagrade celler per fil**. Samma gräns gäller efter expandering av ODS-upprepade rader/kolumner; kontrollera antalet *före* materialisering för att motverka resursförbrukning. Överskridande ger deterministisk HTTP 422 utan partiellt resultat. Bevara befintliga parsergränser oförändrade för gamla strikta importvägen. Gränserna är fastställda implementerings- och säkerhetstak, **inte belägg för bred verklig kompatibilitet**; verifiera med vanliga genererade och, när de faktiskt finns, anonymiserade riktiga arbetsböcker, inklusive fall med >24 ZIP-poster och >64 kolumner. Justering av dessa tak kräver kontrollerad revision av denna fil, inte Codex-gissning.
- Ingen extern process, Excel/LibreOffice-automatisering, nätverkskontakt, makroexekvering eller LLM-tolkning.
- Samma källfil och avskiljarval ska ge exakt samma JSON-semantik oavsett OS och radordning i ZIP-manifestet.

### 4A.3 Frontend

Skapa en separat användarhandling **Förhandsgranska tabeller** vid befintlig importfunktion. Den tar en **fil** och vid CSV ett uttryckligt val `komma` eller `semikolon`. Den får inte återanvända en knapp som påstår att import är slutförd.

Använd den befintliga lokala API-klienten och en statslös filberedningsfunktion. Dekoda källfil som bytes och base64 utan att ersätta tecken. Visa:
- faktiskt filnamn och beräknad source-SHA-256;
- varje faktiskt blad/CSV-tabell med ursprungligt namn;
- exakt antal rader och kolumner samt de första högst 25 visningsbara dataraderna med ursprungsceller;
- uttrycklig begränsning `Endast förhandsvisning – inga nätverksobjekt importerade`;
- exakt fel utan att ta bort användarens aktuella projekt.

UI skapar ingen ny session, ingen dokumentprofil och ingen kandidatmodell. Ingen användarkontroll i 4A kan bekräfta en kartläggning eller ersätta projektet. UI ska hantera ny fil, ny förhandsgranskning och projektbyte utan att ett gammalt svar kan återställa föregående fil eller gammal vy. Skydda med separat preview-generation och exakt source-fingerprint; behåll `app.js` som ägare av aktuell arbetsyta.

### 4A.4 Testbevis som krävs före merge

1. En verklig CSV med komma, en verklig CSV med semikolon, en faktisk OOXML-XLSX och en faktisk ODF-ODS ger rätt bokstavliga värden, celltyper, koordinater, rader, kolumner, bladordning och korrekt SHA-256.
2. Förhindrad semantikförlust: ledande nollor i text, Unicode, citerade celler, radbrytningar, rad-/kolumngap, blandad text/nummer/bool och en rubrik på annan rad än 1 förblir oklassificerade källfakta.
3. Negativa fall: felaktig CSV-struktur, trasig UTF-8, korrupt ZIP/XML, ogiltig ODF-mimetype, dubbla ZIP-delar, dolda celler/blad, formler, merged cells, externa länkar, makron, storleksgränser och felaktiga cellkoordinater. Separat **positivt** test: en syntaktiskt giltig enkolumns-CSV med användarvalt (möjligen fel) avskiljartecken ger 200, enkolumnsvisning och neutral kontrolluppmaning; parsern får inte fabricera ett säkert fel. Ett osäkert innehåll får aldrig ge partiell HTTP 200.
4. Real-HTTP med riktiga binära testfiler och `DIRECT_HTTP` Chromium; verifiera minst två fördröjda svar (gammal fil kontra ny fil, och projektbyte) samt att ingen projektimport eller Save sker.
5. Verklig sparad `.yadilab` förblir byte-identisk och SHA-identisk före/efter alla förhandsvisningar. Befintliga CSV/XLSX/ODS-importer, schema 1.0/1.3 och Save/Open passerar oförändrat.
6. Ny frontend-JS-modul (om skapad) måste inkluderas i `npm run check`, tillåtas endast på exakt statisk HTTP-väg, nekas på okänd/katalog/extra-segment-sökväg och passera `test_web_import_graph.py`.
7. Kör `python3 -m unittest discover -s tests -p 'test_*.py' -v`, `npm run check`, `python3 tests/browser_smoke.py`, `git diff --check`. PR-CI på exakt HEAD och efterföljande main-CI krävs enligt `AGENTS.md`.

**4A färdig:** läsbar, källtrogen, testad och strikt skrivskyddad förhandsvisning. Ingen adapter, projektöversättning eller profilsamling har införts.


## 5. Målomfattning och verifierade arkitekturval

### 5.1 Slutanvändarens arbetsflöde

Målfunktionen ska stödja både:
1. **Inbyggd strikt import** av de redan stödda, namngivna CSV/XLSX/ODS-tabellerna (schema 1.0/1.3); denna väg fortsätter med samma faktiska parser- och valideringskontrakt.
2. **Extern källtrogen tabellimport:** välj filer → inspektera utan projektändring → tilldela en eller flera explicita mappningsvyer per blad → välj källrader och kolumner → granska typade förslag, fältursprung och konflikter → lös, exkludera eller lämna blockerat → välj ändringar och kontrollera beroenden → bygg ett giltigt projekt → godkänn ersättning av arbetsytan → Save endast på separat kommando.

En dokumentprofil anger källans semantik, inte dess filändelse. En och samma CSV kan innehålla enhetsdata, kablar eller ingendera. En XLSX/ODS-bok kan innehålla blandade strukturer på samma blad. Inga bladnamn, producentnamn eller enstaka rubriker får på egen hand fastställa nätverkssemantik.

### 5.2 Kända implementerade referenser – designbevis, inte kod att kopiera

Följande öppna implementeringar har granskats på exakt angivna commitversioner. De styr **arkitekturprinciper** men deras beteenden är inte automatiskt acceptabla för projektets säkerhets- och källtrohetskontrakt.

- [NetBox Data Import Plugin, källadaptrar](https://github.com/marcinpsk/netbox-data-import-plugin/blob/7f521ddbad3069e6f97109faa81c24a93108a2f0/netbox_data_import/adapters.py) och [neutral importplan](https://github.com/marcinpsk/netbox-data-import-plugin/blob/7f521ddbad3069e6f97109faa81c24a93108a2f0/netbox_data_import/plan.py): en adapter kan ge flera utdatafamiljer; granskningsenheter kan innehålla flera förändringar, beroenden och statusar.
- [Pluginens genomförandemotor](https://github.com/marcinpsk/netbox-data-import-plugin/blob/7f521ddbad3069e6f97109faa81c24a93108a2f0/netbox_data_import/import_engine.py) och [testade regler](https://github.com/marcinpsk/netbox-data-import-plugin/blob/7f521ddbad3069e6f97109faa81c24a93108a2f0/netbox_data_import/tests/test_import_plan.py): källinläsning, planering och verkställighet är separata.
- [netviz mellanmodell](https://github.com/blechschmidt/netviz/blob/f3f3202d6392316ba7b5c02917abeec16396b9d1/src/netviz/importer/draft.py) och [CSV-kabelläsare](https://github.com/blechschmidt/netviz/blob/f3f3202d6392316ba7b5c02917abeec16396b9d1/src/netviz/importer/csvlinks.py): preliminära objekt kan vara ofullständiga. **Kopiera inte** dess automatiska enhets-/portskapande från kabelrader.
- [HPE Cani, CSV-konventioner](https://github.com/Cray-HPE/cani/blob/d0e92098178d58630a6510ba72773522d131a629/pkg/devicetypes/connections/csv.go) och [regressioner](https://github.com/Cray-HPE/cani/blob/d0e92098178d58630a6510ba72773522d131a629/pkg/devicetypes/connections/csv_test.go): två riktiga rubrikbaserade kabelkontrakt. **Kopiera inte** dess tysta överhoppning av ofullständiga rader.
- [Nautobot NetBox Importer, source adapter](https://github.com/nautobot/nautobot-app-netbox-importer/blob/5125b2a88534e1e40b7a5ec10d37cf77a814f0f8/nautobot_netbox_importer/diffsync/adapters/netbox.py): planering och transaktionsskydd, men annan databasbaserad produkt och källdomän.

Inga externa projekt har körts i denna granskning; referenserna belägger inspekterad källkod och närvaron av testfall, inte oberoende testresultat. Källkod, algoritmer och databasramverk får inte kopieras utan separat uttrycklig granskning och beslut enligt AGENTS.

### 5.3 Fem separata lager

1. **Source Readers** – gemensamma, begränsade filformatläsare för CSV, XLSX och ODS; skapar källceller med bevarade värden/koordinater. Filavkodaren gissar aldrig nätverkstyp.
2. **Mapping Views / Source Adapters** – deklarativa, användarbekräftade mappningar av valda celler till *typade källpåståenden*. Flera vyer kan läsa samma blad eller samma rad. Adaptrar får inte mutera projektet.
3. **Target Planners** – enhet, zon, port, route, IP-bindning och kabel använder varsin liten måltypad planeringsregel. De skapar en enda gemensam **ImportPlan** med explicita beroenden och diagnostik. Ingen adapter får skriva till målmodellen.
4. **Canonical Project Builder** – väljer endast godkända planändringar och bygger ett fullständigt projekt som alltid passerar en och samma validate_project(); inga alternativa simulerings- eller projektvalidatorer.
5. **Review / Commit Controller** – bevarar arbetsyterevision, versionsbundna källhashar, planfingeravtryck, användarval och fullständiga varningar. Inget skrivs förrän användaren bekräftar arbetsytebyte respektive trycker Save.

**Ingen andra komplett importmotor per konvention.** Ingen databas, bakgrundsjobb, AI-schemamatchning eller ny frontendteknik krävs för detta mål.

### 5.4 Uppgifternas betydelse

Skilj mellan (a) *källans utsaga*, (b) *användarens uttryckliga tolkning eller komplettering*, (c) *härledd visuell layout*, (d) *observation från en verklig nätverksenhet* och (e) *simuleringsresultat*. Import ger enbart a–c. Den får aldrig framställa något som d–e utan annan befintlig verifieringsfunktion.

Partiell inventering utan kablar är tillåten. Ett saknat kabelregister betyder **okänd kabeldragning**, inte ett bevis om ett kabelfritt verkligt nät. Från management-IP, VLAN, default gateway, portbeskrivning, LLDP-rad, zon, diagramposition eller liknande får ingen fysisk kabel skapas.

## 6. Källvyer, typade källpåståenden och flervärdesmappning

### 6.1 Ett blad – flera mappningsvyer

I etapp 4B–4D har varje källa en stabil referens, t.ex. sourceId=src-1. Varje faktiskt blad behåller tableId=sheet-1 etc från 4A. En **MappingView** har exakt följande fält:

- viewId – användarangiven unik intern ID-sträng matchande ^view-[1-9][0-9]*$; skapad lokalt av UI endast som kontroll-ID, aldrig ett nätverksobjekt.
- sourceId, tableId – verkliga källreferenser som kontrolleras mot avkodade originalbytes.
- role – en av de sju produktdefinierade rollerna i §8.
- headerRow – faktiskt radnummer eller null för tabell utan rubrik.
- selectedRows – sorterad, unik array av faktiska, befolkade källradindex. Varje rad måste finnas, får inte vara headerRow och måste uppfylla rad-/resursgränser.
- columns – objekt där varje **tillåtet målfält** är en nyckel och värdet en eller flera explicita källkolumnbokstäver, t.ex. ["A"] eller ["B","F"]; ingen implicit igenkänning av rubriktext.
- valueMaps – objekt med exakt källtext→kanonisk värdetext för valt målfält; bara användarbekräftade, exakta, skiftlägeskänsliga översättningar. Olistat värde är olöst, inte automatisk trim/översättning.
- constants – objekt med typad explicit användarkonstant för ett målfält. Fältet får inte samtidigt ges värde via columns. Identitets- och relationsfält får inte vara tabellkonstanter.
- expectedHeaders – array av ursprungliga, exakt avkodade rubrikvärden för valt headerRow, eller [] när headerRow=null. Används för jämförelse, inte för gissning.
- label – en användarvald, ofarlig beskrivning av vyn; aldrig bevis för källsemantik.

Ett blad får ha **noll eller fler** vyer, även flera av samma roll. Samma källrad får vara vald av flera vyer. Samma källkolumn får av användaren mappas till olika fält/roller; kollisioner på samma målfält går alltid genom konfliktkontroll.

En vy kan vara dokumentations-only och sakna semantiska columns. Avsaknad av vy betyder att alla bladets värden är **omappade källfakta**; de redovisas, inte tyst importerade. HeaderRow måste vara en existerande rad med de förväntade rubrikerna; eventuella före-rubrik-rader förblir omappade. För varje dokumentationsblad ska importöversikten visa om någon rad/kolumn fortfarande saknar granskning.

**Läsning av samma rad i två vyer skapar inte två källrader.** Källradens identitet är (sourceId,tableId,row). Dess användningar identifieras med (viewId,sourceId,tableId,row).

### 6.2 Strängar, typer och användarvärden

CSV-cell är text; native Excel/ODS-cell är explicit text/number/boolean enligt 4A. Källtext ändras aldrig på lagrings-/inspektionsnivå. För målvalidatorns format kan ett **separat, explicit transformationsbeslut** skapa ett kanoniskt värde; bevara då ursprungscell och transformations-ID i planen.

- node.kind måste bli exakt host|switch|router|firewall. Okända objekttyper får inte antas vara host.
- Ett numeriskt Excel-ID får inte omvandlas till en uppfunnen identifierare med antagna ledande nollor. Kräv textbaserad källidentitet eller en separat explicit radunik användardeklaration; en sådan deklaration är *inte* källfakta.
- IPv4/CIDR, MAC, VLAN och statiska routes måste uppfylla aktuell validate_project(); ingen dold gissad netmask, gateway eller portbindning.
- Boolska fält tar native boolean eller exakt true/false. Text som yes/up/1 blir booleans endast via explicit värdemappning. Tom cell är aldrig false eller enabled.
- För ett målfält med flera källkolumner accepteras exakt lika kanoniska värden; konflikter gör påståendet BLOCKED med alla motstridiga celler i rapporten, aldrig first/last-wins.
- Användarkonstanter innehåller exakt {type:"text"|"boolean"|"null",value:...}; gäller bara vald vy och alla dess valda rader. Radunik komplettering uttrycks enbart genom `rowValues[]` i kandidat-API:t (§9.1), nycklad av (viewId,row,targetField). Den ska komma från ett separat användarval, bevaras i SourceClaim och importEvidence som `user_decision`, och får aldrig ändra källcellen. Om samma fält har en befolkad källcell med ett annat värde blir enheten BLOCKED med både källvärdet och beslutet redovisade; `rowValues` får inte tyst skriva över källfakta.

Alla deklarationer ska strikt typkontrolleras; okända målnamn och extra request-nycklar avvisas. En rubrik som "IP Address" eller "Connected To" betyder inget utan bekräftad roll och fälttolkning.

### 6.3 Typade källpåståenden

En MappingView skapar för varje vald rad noll eller flera typade SourceClaims. En claim är {claimId,viewId,sourceRef,role,targetKind,targetKey,fields,origins}. sourceRef är (sourceId,tableId,row). fields innehåller endast de uttryckliga målfälten för rollen. origins har exakt varje fälts källcell(er), user_constant/user_decision eller derived_layout; referenserna valideras mot inspektionen.

En rad får via flera vyer skapa Device + Interface + andra claims. Två källrader kan beskriva samma enhet eller samma kabel; en identisk utsaga ger flera evidensreferenser men högst ett kanoniskt objekt. Motsägelser är BLOCKED och identifierar samtliga källceller.

SourceClaims är mellanmodellen och **behöver inte** uppfylla alla krav för ett färdigt nätverksobjekt. De får aldrig skickas direkt till simuleringsmotor eller Save. Endast en uttryckligt vald, komplett och slutvaliderad konstruktion får bli projekt.

## 7. Gemensam ImportPlan, proveniens och beständighet

### 7.1 Planens fullständiga och ENDA svarskontrakt

Planering är ren, skrivskyddad och deterministisk. **Ett enda** svar, utan dubbla plan-/projekt-/fingeravtrycksfält, är:

```json
{
  "plan": {
    "planVersion": "1",
    "fingerprint": "<64 lowercase hex>",
    "sourceManifest": [],
    "mappingViews": [],
    "rowValues": [],
    "excludedUses": [],
    "selectedUnitIds": [],
    "claims": [],
    "units": [],
    "recordReviews": [],
    "diagnostics": [],
    "report": {
      "sourceRows": 0, "sourceUses": 0, "actionable": 0, "noOp": 0,
      "blocked": 0, "invalid": 0, "excluded": 0, "unmappedCells": 0,
      "selectedUnits": 0, "nodes": 0, "ports": 0, "links": 0, "zones": 0,
      "routes": 0
    },
    "proposedProject": null,
    "canApply": false
  }
}
```

Detta JSON-exempel anger **exakta nycklar och datatyper**. Den verkliga responsen ersätter tomma arrayer och nollor med kontrollerade värden. `proposedProject` är antingen null eller det enda giltiga, kanoniska schema-1.4-projektet; det finns inget andra `project` utanför `plan`. `plan.fingerprint` är det enda fingeravtrycket i svaret. `canApply` är sant om och endast om `proposedProject` är icke-null och alla valda enheter, explicita beroenden och slutvalidering är godkända. Ett sant `canApply` utför aldrig själv en import eller Save. `sourceManifest` innehåller endast fakta verifierade från originalbytes och de format-/bladmetadata som definieras i §7.3, inte fullständiga källbytes.

**claim** har exakt `{claimId,viewId,sourceRef,role,targetKind,targetKey,fields,origins}`, där `sourceRef` är `{sourceId,tableId,row}`. `fields` är ett JSON-objekt med endast uttryckligen valda målfält och typade, ännu inte sammanfogade kanoniska värden. `origins` är ett objekt `{ "<targetField>": [Origin, ...] }`; Origin är exakt `{kind,sourceId,tableId,row,address,decisionId}`. kind är `source_cell|user_constant|user_decision|derived_layout`; källcell kräver källa, blad, rad och originalcelladress och `decisionId:null`. För användarbeslut krävs ett verifierat `decisionId`, medan irrelevanta källkoordinater är null. Alla icke-null referenser måste existera i samma inspektion eller deklarationsmängd. En SourceClaim får vara ofullständig; dess roll och targetKind ska vara förenliga med §8.

**unit** har exakt `{unitId,kind,targetKey,changes,dependencies,status,diagnostics,sourceUses}`; `kind` är `node|port|zone|link|staticRoute|ipBinding`. `targetKey` och `unitId` ska följa §7.2. `sourceUses` är unik, sorterad array av `{viewId,sourceId,tableId,row,claimId}`; fler än en use kan knytas till samma unit. `dependencies` är sorterad unik array av andra unitId. `status` är en av de fem nedan; en null- eller tom-källrad får inte ge ett ACTIONABLE-objekt.

**change** har exakt `{changeId,operation,targetKind,targetKey,fieldValues,fieldOrigins}`, där operation är `create|setExplicitField`, `fieldValues` är ett typat objekt som vid fullständigt urval kan bli en del av den kanoniska projektmodellen, och `fieldOrigins` är motsvarande `{ "<fieldPath>": [Origin,...] }`. En change kan ha flera giltiga ursprung per fält. Varje id ska följa §7.2. Denna representation är en granskningsplan, inte ett extra beständigt nätverksschema.

**Status och betydelse**:
- `ACTIONABLE`: komplett, entydigt källstyrkt och validerbar tillsammans med dess explicita beroenden.
- `NO_OP`: en deklarerad användning eller planerad enhet som inte tillför nya kanoniska fakta; ett identiskt dubbelt källpåstående får inte bli ett andra objekt.
- `BLOCKED`: saknad eller tvetydig information, ofullständigt användarbeslut eller ej tillåten referens; inte körbar.
- `INVALID`: objektet eller någon explicit regel bryter det kanoniska slutkontraktet, även om cellerna gick att avkoda.
- `EXCLUDED`: uttryckligen utesluten användning med användarens motivering; aldrig tillämpad.

**diagnostic** är exakt `{code,severity,message,sourceRefs,unitId}` med `severity:INFO|WARNING|ERROR`. `sourceRefs` är en unik array av `{sourceId,tableId,row,address}` där address får vara null när problemet avser en hel rad. `unitId` får vara null om inget mål ännu finns. `code` är stabil ASCII-kod (t.ex. `MISSING_PORT`), inte en översatt sträng. Status bestäms av planeringsreglerna och får inte härledas ur `message`. Vid konflikt ska alla relevanta källceller finnas i sourceRefs.

**recordReview** har exakt `{sourceId,tableId,row,viewUses,unmappedAddresses}`. Varje faktiskt befolkat originalrecord finns exakt en gång på denna nivå. `viewUses` är sorterad array av `{viewId,claimIds,unitIds,status,reason}` där status är `ACTIONABLE|NO_OP|BLOCKED|INVALID|EXCLUDED|DOCUMENTATION_ONLY` och reason är null utom vid explicit EXCLUDED. `unmappedAddresses` är sorterad array av de *faktiskt avkodade* källcelladresser som inte använts av någon vy. Ett record som används av två vyer får en recordReview med två viewUses, inte två recordReviews. Ett record som är endast delvis använt ska markeras delvis använt i rapporten, aldrig som helt importerad källrad. `report.unmappedCells` räknar distinkta adresser över källor. Fulla cellvärden visas bara om den verifierade originalfilen/källpaketet finns anslutet.

En valid men ofullständig källa ger en 200-plan med BLOCKED/INVALID utan att skapa ett projekt. Ogiltig parsning, okända requestfält, intern planmismatch eller korrupta källreferenser ger HTTP 422 i befintligt `INVALID_PROJECT`-kontrakt. En invalid unit får inte göra övriga, oberoende units oanvändbara; en selectedUnitId som är BLOCKED/INVALID/EXCLUDED eller har ouppfyllt beroende ger `proposedProject:null`, `canApply:false` och deterministisk diagnostik. Ingen partiell HTTP 200 får dölja ett fel i det faktiska request- eller filkontraktet.

### 7.2 Identiteter, beroenden och normalisering

Planen är en riktad acyklisk graf. Normativ konstruktionsordning är `zone → node → port → (ipBinding,staticRoute) → link`. Källfilernas rad- och blador­dning får inte ändra vilka kanoniska fakta som blir godkända.

**Målidentitet**: `targetKey` är för node, zone eller link exakt dess validerade kanoniska `id`. För port och ipBinding är det en JSON-sträng med exakt två element `[nodeId,portId]` serialiserad utan whitespace. För staticRoute är det `[nodeId,routeId]` på samma sätt. Därmed finns ingen tvetydig slash-join när ID:n innehåller tecknet `/` eller andra skiljetecken.

**Internt, deterministiskt id**: `claimId = "cl-" + sha256(utf8(canonicalJson([viewId,sourceId,tableId,row,targetKind,targetKey])))[0:32]`; `unitId = "u-" + sha256(utf8(canonicalJson([kind,targetKey])))[0:32]`; `changeId = "c-" + sha256(utf8(canonicalJson([unitId,operation,fieldPath])))[0:32]`. CanonicalJson för dessa identifierare följer exakt §7.4. En intern ID-kollision mellan olika identiteter ska ge HTTP 422; välj inte en ny slumpmässig ID. Dessa är **kontrollidentiteter**, aldrig nätverks- eller kabel-ID. En enhet med samma kind+targetKey förekommer högst en gång i en ImportPlan. Vid lika fakta samlas samtliga ursprung på denna unit; dubblett-claims får NO_OP-status på användningsnivån.

Varje dependency måste peka på en existerande planunit med tillräckligt godkänt resultat eller på uttryckligen redan definierade fakta i samma, validerade kandidatprojekt. Inga beroenden på den arbetsyta som ska ersättas får implicit antas. Saknade beroenden, cykler och beroenden till BLOCKED/INVALID/EXCLUDED-enheter ger ett icke-tillämpbart urval. En port kräver en nod; en kabel kräver två redan deklarerade portar; en route kräver definierad nod och port. Ett ipBinding kräver redan uttryckligt deklarerad port.

Urval av en unit utökar inte automatiskt andra enheter. UI får erbjuda "Välj även beroenden" men måste först visa exakt de ytterligare units och kräva ett nytt, uttryckligt användarklick. En fysisk länk får aldrig skapa saknade noder eller portar. Vid konflikt mellan två källvärden på samma målfält ska den berörda unit markeras BLOCKED, båda källreferenserna redovisas och ingen first-/last-write-wins förekomma.

### 7.3 Kompakt, historiskt importkvitto och separat källa

**Bindande beslut:** ingen inbäddning av alla avkodade kalkylbladsceller eller original-CSV/XLSX/ODS-bytes i den kanoniska .yadilab-filen. Behåll de uttryckligen validerade nätverksobjekten, ett **historiskt importkvitto** i `importEvidence` och originalfilerna separat hos användaren. Detta minskar projektfilens storlek och förebygger oavsiktligt arkiverande av okänd information i simuleringsprojektet. Det bevisar **inte** att användaren faktiskt sparat en extern backup.

**Schema 1.4** har exakt samma nätverksfält som 1.3 samt en ny obligatorisk rot-nyckel `importEvidence`. `importEvidence` är exakt:

```json
{
  "evidenceVersion": "1",
  "baselineNetworkSha256": "<64 lowercase hex>",
  "sources": [],
  "mappingViews": [],
  "rowValues": [],
  "decisions": [],
  "acceptedChanges": [],
  "sourceStorage": "external_not_embedded"
}
```

- `baselineNetworkSha256` beräknas **en gång** vid importgodkännandet av det validate_project-normaliserade nätverksinnehållet, utan proveniens, via canonicalNetworkView och canonicalJson enligt §7.5 och §7.4. Manifestet är därefter **oföränderlig historik**, inte en självläkande förteckning över arbetsytans aktuella värden. Vanlig redigering ändrar aldrig detta hash, originalreferenser eller accepterade importbeslut.
- `sources[]`: `{sourceId,filename,kind,sha256,byteLength,tables}`, där tables innehåller `{tableId,name,rowCount,populatedRowCount,columnCount}`. Alla källhashar kommer från originalbytes. Inga fullständiga `cells` i projektet.
- `mappingViews[]`: verifierade snapshots enligt §6.1 vid importerad tidpunkt; innehåller källroll, vald kolumnmappning, header och row selections, även när senare användarredigering ändrar nätverket.
- `rowValues[]`: explicit radunika beslut enligt §9.1 med typer och identiteter; även dessa bevaras oförändrade.
- `decisions[]`: `{sourceId,tableId,row,viewId,status,reason,unitIds}`; status är en av §7.1:s dispositioner inklusive `DOCUMENTATION_ONLY`, reason är null om ingen användarexkludering finns. Den historiska dispositionen får inte felaktigt visas som aktuell resursstatus.
- `acceptedChanges[]`: `{unitId,changeIds,targetKind,targetKey,fieldOrigins}`. `fieldOrigins` följer §7.1 och innehåller källa eller användarbeslut; inga uppdiktade originalvärden.
- `sourceStorage` är alltid `external_not_embedded`.

**Två separata integritetsnivåer** visas i UI och testsvar:
1. **MANIFEST_VALIDATED** – endast typ-/format-/referensintegritet i det sparade manifestet, inklusive baselineNetworkSha256:s syntax. Detta betyder **inte** att originalceller eller historiska ändringsenheter har omverifierats mot dokumentet.
2. **SOURCE_VERIFIED** – den namngivna originalfilen/källpaketet har återanslutits, dess verkliga SHA-256 har kontrollerats byte för byte och refererade celler/rader har lästs och verifierats mot aktuell granskning. Statusen får bara visas för respektive källa när kontrollen faktiskt utförts.

**En tredje oberoende dimension gäller arbetsytan:** `BASELINE_MATCH` när sha256(canonicalJson(canonicalNetworkView(currentProject))) är exakt lika med baselineNetworkSha256, annars `CHANGED_SINCE_IMPORT`. Detta är en konservativ, **projektomfattande** jämförelse; ett senare fält kan aldrig markeras `CURRENT_SOURCE_VERIFIED` enbart på grund av gammal importproveniens. När något nätverksfält ändras eller ett objekt försvinner visar UI `Historisk import; aktuellt projekt har ändrats efter import` och originalets cellreferenser som historik. En ändring som senare återställs till byte-identisk kanonisk projektsnapshot ger BASELINE_MATCH, men gör inte originalfilen SOURCE_VERIFIED utan separat källkontroll.

**Validering och mutation:** `validate_project()` validerar manifestets typer, enumvärden och **intern** referenskonsistens mot manifestets egna sources/views/decisions. Den får **inte** kräva att ett historiskt accepterat targetKey fortfarande finns i aktuell projektgraf efter användarens redigering eller att aktuell nätverks-hash fortfarande matchar baseline; då skulle vanlig edit/Save brytas. Importplanens `proposedProject` valideras däremot mot både faktiskt källinnehåll och alla målfält **innan första importgodkännande**. Efter Save/Open utan originalfil utges aldrig ett nytt påstående om verifierad originalcell.

**Separat källpaket** (explicit export): JSON `{sourceBundleVersion:"1",sources:[{sourceId,filename,kind,sha256,contentBase64}]}`. Innehåller *exakta originalbytes* i standard-base64 och är inte del av .yadilab. Export får starta endast från ett aktivt, inspekterat originalfil-set, vid ett uttryckligt klick; appen ska säga `Nedladdning initierad, filens skrivning till disk ej verifierad`, aldrig lova att filen har arkiverats. Vid återanslutning av verifierad källfil eller källpaket kontrolleras ID, SHA-256, filtyp, bladstruktur och källreferenser mot manifestet. Felaktig hash eller olika celler ger avslag och får inte ändra projekt eller historik. Utan källpaket/originalfil ska UI visa `Källfil ej ansluten; ursprungsceller kan inte kontrolleras`.

**Obligatorisk användarupplysning före importgodkännande:** `Originaldokumenten lagras inte i projektfilen. Behåll källfilerna eller exportera separat källpaket för senare kontroll av ursprungsceller. Enbart projektfilen kan inte återskapa den ursprungliga arbetsboken.` Om användaren inte uttryckligen godkänner detta får arbetsytan inte ersättas. Omappade cellvärden finns i originalet men **inte** automatiskt i projektet; ingen funktion får beskriva detta som förlustfri arkivering av originalet.

**Resursgränser:** maximalt 2 MiB UTF-8-serialiserat `importEvidence` och dessutom faktisk `MAX_BODY` för hela projektets reala Save-JSON. Räkna bytes före användarbekräftelse; avvisa överstora kandidater eller erbjud ett uttryckligt mindre urval. Ursprung och decisions får aldrig tyst beskäras. Ett nytt importbeslut skapar ett nytt kvitto och ersätter det föregående **endast** genom ett separat uttryckligt projektbyte med vanlig Save-semantik; ingen dold sammanslagning av historik krävs.

### 7.4 Exakt canonicalJson, fingerprint och stale-guard

**canonicalJson(v)**: Python `json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False)` följt av UTF-8, utan BOM eller avslutande newline. Tillåt endast JSON-värden: null, boolean, Unicode-sträng, ändlig exakt representerbar heltalstyp, arrayer och objekt; flyttal, NaN och Infinity i plan-/mappnings-/proveniensmetadata **avvisas**. För projektets nätverkskoordinater används det redan normaliserade kanoniska projektet med validatorns numeriska värden; testvektorn måste täcka både heltals- och giltiga flyttalskoordinater med serverns JSON-normalisering och verifiera stabila bytes. Inga JS-fingerprint beräknas från client-side JSON.stringify av osorterade objekt; servern är auktoritativ och UI behandlar dess fingerprint som opaque.

**fingerprint-input** är exakt JSON-objektet `{contractVersion,projectName,validatorVersion,sources,mappingViews,rowValues,excludedUses,selectedUnitIds}`. `validatorVersion` = "1.4" och `sources` innehåller endast `{sourceId,sha256,csvDelimiter}` (csvDelimiter=null för XLSX/ODS) efter verklig bytesverifiering. Projektnamn normaliseras med befintlig `_name()` innan hashning. Sortera källor stigande efter numeriskt src-index; mappingViews efter numeriskt viewId; rowValues efter viewId,row,targetField; excludedUses efter viewId,row; selectedUnitIds lexikografiskt. Varje dubblett eller ogiltigt element avvisas **före** canonicalJson. Nycklar i objekt sorteras som ovan. `fingerprint` är hex(SHA-256(canonicalJson(fingerprint-input))). Den kan användas för ändringsdetektion, inte autentisering. **Endast detta plan.fingerprint** finns i svarskontraktet.

Status-, report- och planunit-arrayer sorteras också deterministiskt (units: kind,targetKey; claims: viewId,sourceId,tableId,row,targetKind,targetKey; diagnostics: code,unitId,sourceRefs; recordReviews: sourceId,tableId,row). Sorteringsnycklar och serialisering ska få **testvektorer med exakta förväntade bytes och SHA-256** i testsviten. Samma logiska request med annan JSON-nyckelordning ger samma fingerprint, medan ändrat källbyte, avskiljare, roll, radval, rowValue, excludedUse, projektName, selectedUnitId eller valideringsversion ger nytt hash.

**Stale-guard:** Före varje asynkront 4A-/4B-/4C-anrop fångar UI aktuella originalfilers SHA-256, previewGeneration, mappingRevision, plan.fingerprint (om plan redan finns), workspaceRevision och editRevision. Efter svar och vid slutligt godkännande måste **alla** relevanta komponenter fortfarande matcha. Ett gammalt svar får inte ändra källvy, plan, aktuellt projekt eller Save-status. Den slutliga valda ImportPlan måste beräknas på nytt av servern från aktuella bytes och hela requesten; godkänn bara om fingerprint och alla kontrollrevisioner matchar senast granskad plan. Ingen server- eller browsercache får vara enda aukktoritet för ett importgodkännande.

### 7.5 Schema 1.4, befintlig editor och simulatorprojektion

Schema 1.4 har **exakt** samma kanoniska nätverksbetydelse som 1.3 men kräver historiskt `importEvidence`. `network_core/model.py` ska acceptera gamla 1.0–1.3 helt oförändrat och 1.4 med korrekt manifest. All 1.3-funktionalitet för `staticRoutes`, MAC och VLAN måste också tillåtas för 1.4; idag gör flera kodvägar jämförelsen `version == SCHEMA_VERSION` där SCHEMA_VERSION="1.3". Samtliga sådana gränser och frontend-schemakontroller måste täckas av test.

**Kritisk redigeringsinvariant:** I befintliga `web/app.js` finns flera uttryckliga `attempt.schemaVersion = '1.3'` vid ändring av MAC, VLAN och route. Vid en avsiktlig funktion som redan kräver uppgradering ska **endast** dokument 1.0–1.2 uppgraderas till 1.3, enligt befintlig policy. Dokument 1.3 förblir 1.3; dokument **1.4 förblir alltid 1.4 med samma historiska importEvidence** vid alla ändringar, radering, validering, Save/Open och projekt-export. Ingen redigering får skriva tillbaka "1.3" på ett 1.4-projekt, radera importEvidence eller skapa automatisk 1.4-migration av äldre filer. Testa ALLA inspector-/Builder-vägar som kan skriva över project, inklusive async validator-svar, nod-/zon-/port-/kabelborttagning och staticRoutes. Att projektets aktuella nätverksdel ändras ska endast påverka härledd `CHANGED_SINCE_IMPORT`-status; den historiska provenance-delen ska vara oförändrad.

**canonicalNetworkView(project)** definieras för beräkningar/transport som en **icke-mutativ, djupt kopierad och separat validerad** projektion med exakt `{schemaVersion:"1.3", name, zones, nodes, links}`, innehållande alla verkligt deklarerade 1.3-kompatibla nätverksfält och inga `importEvidence`-fält. Den byggs från ett redan validate_project()-validerat original 1.4, bibehåller nod-, port-, länk-, VLAN-/MAC-/route-ID och ordning, och valideras även med gamla 1.3-vägen. Projektionen är en **transportvy**, inte ett parallellt kanoniskt lagringsformat eller en extra auktoritet. För schema 1.0–1.3 skickas deras faktiska oförändrade nätverksdokument enligt existerande kontrakt.

Alla simulerings-/diagnostik-/sessionsanrop som annars skickar `JSON.stringify(project)` ska skicka `canonicalNetworkView(project)` **för 1.4** så att importEvidence inte kopieras med varje trafik- eller sessionsrequest. Befintligt original, sparad SHA, full-revisionssnapshot och sessionernas invalidationsregler förblir knutna till den verkliga fullständiga projektmodellen, inte bara transportvyn. Protokollmotorer ska aldrig läsa proveniens som alternativa nätverksfakta. Före och efter separationen måste verkliga DHCP/ARP/ICMP/IPv4-/routingfall ge samma resultat för identiska nätverksfält.

`baselineNetworkSha256` i §7.3 beräknas som SHA-256(canonicalJson(canonicalNetworkView(project))) på **originalets godkända nätverksdel vid importen**. Samma nätverksprojektion används för att jämföra aktuell arbetsyta mot historisk baseline, inte för att verifiera originalkällan.

Existerande strikta kalkylbladsexport ska fortsatt acceptera endast de gamla uttryckligen stödda schemana. För 1.4 måste den förklara att export skulle förlora manifest/proveniens och avvisa exporten, inte konvertera tyst till 1.3. Befintliga .json/.yadilab-, Save/Open- och optimistiska SHA-konfliktkontrakt gäller oförändrat. Äldre filer ska vara byte-identiska utan Save och får inte uppgraderas genom enbart Open.

## 8. Fast måltypskatalog för källpåståenden

Dessa **sju generiska roller** är produktens egna semantiska kategorier, inte påstådda industristandarder. Ett blad får innehålla flera roller genom flera views. En vy har exakt en roll.

| role | Deklarerade fält / mappningsmöjligheter | Tillåten effekt |
|---|---|---|
| device_inventory | node.id, node.label, node.kind, node.zoneId | En eller flera enheter via flera views/rows |
| interface_inventory | port.nodeId, port.id, port.name, port.enabled, port.ipv4, port.mac, port.vlanMode, port.accessVlan, port.allowedVlans | Validerad port; VLAN-fälten är **endast mappningsfält** som måste kombineras exakt till modellens nästlade port.vlan (§8.1) |
| cable_register | link.id, link.aNode, link.aPort, link.bNode, link.bPort, link.enabled | Länk med två verkligt specificerade portändpunkter |
| zone_inventory | zone.id, zone.label | Zon |
| static_route_register | route.nodeId, route.id, route.destination, route.nextHop, route.outPort | Route på explicit router/host enligt modell |
| ip_plan | ip.nodeId, ip.portId, ip.ipv4 | Endast explicit portbunden IP/CIDR |
| documentation_only | inga | Ingen nätverksändring, endast käll-/granskningsstatus |

**Identitetskrav:** Kanonisk ID för varje node/port/link/zone/route måste vara uttryckligt angivet i en textcell eller ett separat uttryckligt användarbeslut per rad. Inga slug-/förkortnings-/namnmatchningar eller indexbaserade påhittade ID:n. En säker systemgenererad viewId/unitId är kontrollidentitet, **inte** ett nätverks-ID. Syntetiska UI-koordinater får skapas enligt en enda deklarerad regel: sortera nod-ID:n lexikografiskt; index i från 0, x=110+260*(i mod 4), y=110+220*floor(i/4). De markeras derived_layout och har aldrig fysisk betydelse.

**Port-/IP-krav:** nodeId/portId måste finnas och matcha explicit deklarerad källa; management-IP utan port är en dokumenterad cell men ingen port-IP. enabled kräver bekräftad boolean; användaren får ange en tydlig generell konstant för en vy, aldrig dold true-default. MAC/VLAN/IPv4/route använder exakt validate_project()-reglerna. IP-plan får inte skapa port, kabel, route eller adresspool.

**Kabelkrav:** båda (nodeId,portId) måste vara explicita, deklarerade och unika på varsin sida, och link.id/enabled uttryckligen bestämda. Okänd port på ena sidan innebär BLOCKED/INVALID, inte "närmast rimliga" kabel. LLDP eller en portbeskrivning kan vara källevidens men utgör inte ett verifierat kabelregister.

**Sammanfogning:** Samma targetKey och samma fältvärden från flera källclaims sammanfogas med alla origins och högst ett objekt. Olika värden på samma fält ger BLOCKED och rapport om båda källcellerna. En källa som bara bidrar med ett fåtal kompletterande fält kan utgöra en del av en enhet; alla nödvändiga fält kontrolleras innan unit blir ACTIONABLE. Mellanmodellen får vara ofullständig, men inte det objekt som skickas till validate_project().

**Representation:** Modell, tillverkare, serienummer, rackplacering, anteckningar och andra uttryckliga källfält saknar i dag allmänna mål i nätverksmodellen. De ska i importöversikten visas som omappade/icke representerbara, inte omvandlas till nodtype, port eller topologi. Deras faktiska värden kan endast återvisas från ansluten originalkälla/källpaket. Användaren måste aktivt godkänna denna begränsning innan partiell import.

### 8.1 Exakt VLAN-översättning från mappningsfält

`port.vlanMode`, `port.accessVlan` och `port.allowedVlans` är **inte** fält på den kanoniska porten. Vid kandidatbygget ska de konstruera **ett** valfritt `port.vlan`-objekt enligt redan existerande `network_core/model.py::_vlan_config()`:
- Utan explicit `port.vlanMode` och utan befolkade VLAN-fält: **utelämna** `vlan` (inte automatisk `null`, ingen antagen access-VLAN).
- Explicit `vlanMode="access"` kräver exakt ett heltal `accessVlan` inom 1..4094 och att `allowedVlans` saknas. Kanoniskt resultat: `{"mode":"access","vlan":10}`.
- Explicit `vlanMode="trunk"` kräver en användarbekräftad, icke-tom lista av **unika** heltal 1..4094 i `allowedVlans`; `accessVlan` ska saknas. Resultat: `{"mode":"trunk","allowedVlans":[10,20]}`.
- Fältkombinationer med båda accessVlan och allowedVlans, null/blankt mode men befolkade fält, okänd mode, dubblett VLAN, flyttalsvärde, mellanslag som kräver gissad normalisering eller VLAN på annan nodtyp än `switch` är BLOCKED/INVALID enligt explicit diagnostic; inga delar sparas.
- Källtext som `"10,20"` är **inte automatiskt** array. Den kräver ett uttryckligt, testat användarbeslut som delar på kommatecken, och varje element typkontrolleras som heltal. Den exakta originalsträngen och beslutets ID bevaras i fältproveniens. Ordningen bevaras i kanoniskt resultat; samma identitets- och konfliktskydd gäller om flera vyer anger samma port.vlan.
- `port.mac` får bara bindas enligt nuvarande validator; switchportens MAC får inte antas vara endpoint-MAC.

Negativa 4C-fixturer måste omfatta access/trunk med förväxlade fält, tom allowedVlans, otillåten VLAN och fel nodtyp. Positiva fixturer ska jämföra den kompletta genererade `port.vlan`-JSON med oberoende handskrivet förväntat resultat.

## 9. Etapp 4B – importplan, blandade enhetsvyer och kompakta auditmanifest

**Start:** 4A mergad och efterföljande main-CI SUCCESS. Inga andra planeringsdokument får krävas.

Implementera de gemensamma kontrakten i §§5–8 och måltyperna device_inventory + documentation_only. Tillåt redan nu **flera views över samma blad och samma rad**, även om bara de två rollerna kan skapa resultat i denna etapp. Bygg den typade SourceClaim- och ImportPlan-gränsen så att 4C kan addera port/kabel utan att ändra grundsemantiken.

### 9.1 Skrivskyddat kandidat-API och radunika beslut

Inför exakt **en** ny planerings-endpoint: `POST /api/import/build-candidate`. Den tar originalbytes på varje anrop, är statslös och sparar inte filer, kandidater eller användarval.

**Exakt request-kontrakt:**
```json
{
  "contractVersion": "1",
  "projectName": "Dokumenterat nät",
  "sources": [
    {"sourceId":"src-1","filename":"inventory.csv","contentBase64":"<base64 originalbytes>","csvDelimiter":","}
  ],
  "mappingViews": [],
  "rowValues": [],
  "excludedUses": [],
  "selectedUnitIds": []
}
```

För varje fält gäller:
- `contractVersion`: exakt strängen "1"; okända toppnycklar avvisas.
- `projectName`: giltigt, servernormaliserat projektnamn enligt befintlig modell (1–120 tecken, trimning där befintlig `_name` gör det).
- `sources`: 1–8 unika objekt med exakt `{sourceId,filename,contentBase64,csvDelimiter?}`. sourceId = src-1..src-8 i verklig, användarvald ordning; inga gap/duplikat. `csvDelimiter` är obligatorisk endast för CSV och exakt komma/semikolon; förbjuden för XLSX/ODS. Högst 4 MiB **totala källbytes** och dessutom MAX_BODY för hela base64-kodade requesten. 4A:s enskilda formatgränser och samtliga strukturkontroller gäller på nytt. Servern beräknar varje källhash från verkliga bytes och avvisar identitets-/formatfel.
- `mappingViews`: array av §6.1:s **exakt** nio fält `{viewId,sourceId,tableId,role,headerRow,selectedRows,columns,valueMaps,constants,expectedHeaders,label}` (antalet är elva fält; denna uppräkning är auktoritativ). `viewId` = view-1, view-2 ... i användarens UI-registreringsordning, unika utan luckor. `columns` är `{ "<targetField>": ["A","B",...] }` med 1–64 verkliga, unika källkolumnbokstäver per målfält; samtliga målfält måste vara tillåtna för rollen. `valueMaps` är `{ "<targetField>": { "<literalSourceText>": "<literalCanonicalText>" } }` och får enbart gälla målfält med källkolumn. `constants` är `{ "<targetField>": {"type":"text|boolean|null","value":<type-matching JSON>} }`. En målbindning får inte finnas i både columns och constants. För `headerRow:null` är expectedHeaders=[]; annars måste expectedHeaders innehålla exakt alla avkodade rubrikceller i ordning för vald rad; rubriktext används aldrig som automatisk semantisk gissning.
- `rowValues`: array med exakt `{viewId,row,targetField,valueType,value}`. `viewId` måste existera; `row` måste vara en av just den vyns valda verkliga datarader. `targetField` måste vara tillåtet för vyns roll. `valueType` är `text|boolean|null`; value har motsvarande JSON-typ (sträng, boolean eller null). Dubblett (viewId,row,targetField) ger HTTP 422. En rowValue är **explicit användarinmatad**, inte källfakta. Den får ange radunik ID/deklaration och komplettera ett målfält med saknad källcell; om en källkolumn innehåller ett annat befolkat värde för samma fält blir resultatet BLOCKED och båda ursprungen redovisas. Null tillåts bara för nullable kanoniskt målfält. En rowValue ingår i planens fingerprint, SourceClaim och importEvidence.
- `excludedUses`: array av exakt `{viewId,row,reason}`. `reason` är 1–240 tecken. viewId och row måste existera i det aktuella mappingView-urvalet. Dubblett (viewId,row) avvisas. Exkludering påverkar **endast just denna användning** av raden; andra vyer får fortfarande använda originalcellen efter användarens separata uttryckliga val. Ett exkluderat source-use får aldrig skapa en unit.
- `selectedUnitIds`: sorterad unik array av existerande `unitId` från serverns tidigare plana förhandsvisning. Endast ACTIONABLE-enheter med alla uttryckligen valda dependencies får användas. Okända unitId ger HTTP 422. Förstahandsanrop med `[]` ger endast `plan.proposedProject:null` och `plan.canApply:false`; UI visar då alla förslag och låter användaren välja. Anropet med ett val rederiverar en ny plan från **samma aktuella källbytes och mappingViews** och skapar projekt endast om allt valideras. Minst en verkligt godkänd nod krävs för ett importerat kandidatprojekt; en ren dokumentationsfil får endast förhandsgranskas.

**Exakt response:** endast `{"plan": ImportPlan}`, med ImportPlan:s fullständiga egenskaper i §7.1. Det finns **inga** ytterligare `project`, `fingerprint`, `report` eller `canApply` på toppnivå eller i en andra responsrepresentation. Klienten kontrollerar `plan.planVersion==="1"`; `plan.proposedProject` kan vara null; bara `plan.canApply===true` och giltig revisions-/fingerprintkontroll får möjliggöra uttrycklig användarbekräftelse. Projektet sparas aldrig av endpointen.

Semantiskt ofullständiga, men giltigt avkodade rader ger en 200-plan med synliga BLOCKED/INVALID/EXCLUDED-diagnoser. Fel request, trasig fil, falska cell-/radreferenser, fel schemaVersion eller okänd planunit ger HTTP 422 och exakt befintligt `INVALID_PROJECT`-felobjekt `{error,message}`. Ett serverinternt fel får aldrig presenteras som en lyckad plan.

**Resultatkonsistens:** `plan.report` räknas om från samma units/recordReviews som visas i UI, inte från en oberoende summering. Fingerprint beräknas enbart som i §7.4. Ingen andra JSON-serialiseringsalgoritm får användas för just detta kontrakt.

### 9.2 Integration av schema 1.4 och sanningsstatus

Implementera §7.3:s **historiska** `importEvidence`; inga källceller eller originalbytes inbäddas i .yadilab. Alla id- och formatlänkar i manifestet ska kontrolleras, men efter vanliga manuella redigeringar får inte historiska unitIds/targetKeys krävas finnas i nuvarande nätverk. V1.4:s baseline-hash beräknas vid första import från kanonisk projektion; den uppdateras aldrig vid vanlig projektredigering. UI redovisar två oberoende fakta: `MANIFEST_VALIDATED / SOURCE_VERIFIED` och `BASELINE_MATCH / CHANGED_SINCE_IMPORT`.

Uppdatera före aktivering av v1.4 **samtliga** `web/app.js`-vägar som i dag skriver `attempt.schemaVersion = '1.3'`; v1.4 och importEvidence ska bevaras efter ändring av MAC, VLAN, statiska routes, nod/port/zon/kabel och efter valideringsresponse. Äldre versioner uppgraderas endast vid avsiktlig förändring enligt nuvarande policy, aldrig på enbart Open.

Simulerings-/diagnostik-/sessionsanrop ska använda den explicit validerade `canonicalNetworkView` från §7.5 för v1.4, inte full `importEvidence`-last. Save/Open, dirty-state och workspace-revisioner fortsätter att avse **hela** projektet. Detta är transportoptimering, inte en ny lagringsmotor.

Källpaketexport och källpaketimport enligt §7.3 ska fungera i samma etapp och ge samma tydliga förlustvarning före projektbyte. Hash-match verifieras mot faktisk källbytes, inte klientens påstådda hash. Nedladdningsstart får aldrig rapporteras som bevis på att användaren har en färdig fil på disk. Ett saknat källpaket får aldrig ge falskt SOURCE_VERIFIED.

UI måste särskilja **historisk importproveniens** från användarens senare manuella edit. Om baseline är ändrad får appen aldrig utge historiskt accepterad sourceCell som verifiering av dagens fältvärde.

### 9.3 Specifika 4B-tester

- Två oberoende syntetiska inventeringar med olika rubriker och column order ger samma kanoniska expected device efter explicit mapping; ingen rubrikheuristik.
- **En rad, två device_inventory-vyer** från samma blad, med var sin uttryckligt angiven text-ID-kolumn, ger två separata nodclaims utan att källraden dupliceras. **Två rader, ett targetKey** ger en enda nod med två källursprung vid lika fält. En uttrycklig `rowValues[]`-identitet tillåts endast om användaren angivit den själv och den ingår i fingerprint; en motstridig radunik användardeklaration ska blockeras.
- Två motstridiga celler på samma target field ger BLOCKED och ingen skapad enhet.
- En nod utan ports/links är giltigt **partiellt** projekt, inte ett fullständigt observerat nät.
- Felaktigt typed ID, okänd node.kind, saknad användardeklaration, plan-ID-kollision, obefintlig källcell, EXCLUDED som beroende, ändrad source hash och stale UI-respons hindrar projektbyte.
- importEvidence återläses exakt efter Save/Open och omstart; råa källceller är inte i .yadilab. Efter omstart visas korrekt "källan ej ansluten". Import av rätt källpaket återställer förmågan att granska celler; fel SHA blockeras. **Redigera därefter en port/IP/route och spara på riktigt:** projektet ska fortfarande vara schema 1.4, proveniensmanifestet oförändrat, `CHANGED_SINCE_IMPORT` synligt och alla simulatoranrop fria från importEvidence. Återställ exakt nätverksinnehåll och verifiera BASELINE_MATCH utan falskt SOURCE_VERIFIED.
- Bytebevis för ursprungliga filer och v1.0–1.3-filer utan Save; full DIRECT_HTTP Chromium och samtliga befintliga protokolltester.

## 10. Etapp 4C – målmoduler, kablar och sammanslagna dokument

**Start:** 4B mergad och efterföljande main-CI SUCCESS. Utöka samma ImportPlan/API, utan andra importmotorer.

Implementera Target Planners för interface_inventory, zone_inventory, cable_register, static_route_register och ip_plan enligt §8. En och samma tabellrad ska kunna bidra till **nod, port och kabel** via flera explicit definierade mappingViews utan att källraden kopieras eller får falska identiteter. Flera källrader ska kunna komplettera en entitet; alla origins finns kvar i den accepterade planen och kompakta manifestet.

Oberoende av källordning gäller planberoenden och kanonisk validering. Saknad nod/port/cable endpoint får aldrig skapas för att underlätta import. Ett källpåstående om en kabel med båda angivna ändar kan ligga BLOCKED tills de uttryckligt deklarerade noderna/portarna finns, men blir inte ACTIONABLE med implicit syntetiska objekt.

U01–U12: verkliga CSV/XLSX/ODS-filer; samma blad har device+port+link-vyer; flera blad har motstridiga claims; duplicerade grannrader ger inte dubbla kablar; okända slutportar; port redan upptagen; VLAN-/MAC-/IP-/route-konflikter; IPAM utan bindning; feltypad boolean; cyklisk/saknad planreferens; selection som saknar dependency; ordningsinvarians; Save/Open och simulerad trafik enbart från explicita modelldata. Tydligt redovisad ofullständig tabell får aldrig bli falsk fysisk länk.

Ändra inte DHCP-, ARP-, IPv4- eller ICMP-motorer; 4C:s krav gäller endast att validerat indata fungerar som före refaktoreringen.

## 11. Etapp 4D – mappningsprofiler, fullständigt UI och slutacceptans

**Start:** 4C mergad och efterföljande main-CI SUCCESS. Slutför ett enhetligt granskningsflöde utan nya fullständiga parsers.

### 11.1 Återanvändbara mappingprofiler

Exportera/importera en användarskapad JSON-profil **endast genom uttryckligt klick**. Formatet är exakt {profileVersion:"1",views:[{role,headerRow,expectedHeaders,columns,valueMaps,constants,label}]}; viewId och selectedRows ingår **inte** – de skapas/markeras på nytt för varje faktiskt dokument. En fil/profil kan därmed innehålla flera roller för ett blad. Profilen är ett deklarativt **mappningsförslag** som alltid omvalideras mot faktisk source + headerRow/kolumnposition och kräver ett nytt explicit användargodkännande.

Ingen tyst lagring i localStorage, server, projektfil eller molntjänst. Ingen inbyggd NetBox/Cisco/HPE/Atea/landsspecifik "standardprofil" utan dokumenterad versionslåst exportdefinition och verkliga fixture-bevis. Det är inte ett krav för att denna generiska slutfunktion ska vara färdig.

### 11.2 Sammanhängande UI

Slutgränssnittet ska visa:
1. befintlig strikt import och ny extern granskningsväg som tydligt skilda alternativ;
2. 4A:s fil- och bladförhandsvisning med verkliga koordinater och explicit källupplysning;
3. **flera mappningsvyer per blad**, med en roll per vy och möjlighet att markera källrader utan att omklassificera andra vyers roller;
4. exakta kolumn-/värdemappningar, radunika användardeklarationer, konflikter och omappade källfält;
5. planunits med status, beroenden, valbara ändringar, no-op, blockers och begripliga fel, med navigering till ursprungsceller;
6. en samlad rapport om partiellt dokumenterat nätverk och vilka fakta som fortfarande är okända;
7. aktuell planfingeravtryckning och explicit godkännande av arbetsytebyte;
8. separat Save, samt källpaketexport och verifierad återanslutning till tidigare projekt via SHA-256;
9. review av provenance efter Save/Open, utan att avsaknad av källfil döljs eller ersätts med gissningar.

### 11.3 Slutliga kvalitetsgrindar

Kör ordinarie Python-testsvit, npm run check, ES-importgrafstest, direkt HTTP + Chromium, negativ ZIP/OOXML/ODF/CSV-testning, objekt-/beroende-/konflikttester, riktigt lagrad .yadilab och omstart. Kör även reproducerbara racefall på ändrat file hash, mapping, selectedUnits, workspaceRevision och editRevision.

Oberoende handskrivna expected models och negativa tester krävs för:
- minst två syntetiska, strukturellt olika dokumentuppsättningar med flera roller per blad;
- minst ett fall med samma källrad som ger minst två objekt och minst två källrader som ger samma objekt;
- minst ett fall med överlappande och ett med motstridiga källpåståenden;
- dokument utan kablar, saknade portreferenser och bortvalda källrader;
- verklig Save/Open av kompakt proveniens samt korrekt explicit förlustvarning vid källfil frånvarande;
- källpaketexport/återanslutning med SHA-match samt avslag vid SHA-mismatch.

Verkliga anonymiserade företagsdokument får ingå **endast om de finns och lagligen kan användas**. Annars märks corpus "synthetic only"; inga marknadsandelar eller empiriska kompatibilitetsprocent anges.

Slutgrindar: 0 implicit skapade fysiska kablar, 0 tyst utelämnade *rapporteringspliktiga* celler, 0 ogiltigt accepterade planberoenden, 0 förlorade accepterade fältursprung, 0 oavsiktliga Save, 0 positiva nätverkspåståenden från endast proveniens, 0 falska PASS-rapporter. "Ingen tyst cellförlust" betyder att en representerbar källcell antingen blir mappad, synligt redovisas som omappad/olöst/exkluderad **och finns i oförändrat original**, eller att hela källan avvisas. Det betyder **inte** att full originalarbetsbok finns inbäddad i .yadilab.

### 11.4 Omfattning, disciplin och slutdefinition

4A–4D är komplett när **alla** specificerade funktioner och tester passerat på riktiga filer och sparade projekt. En PR per etapp på verifierad main; ingen merge vid PENDING/FAIL/oklar CI, inga extra "Masterprompt"-dokument, och inga ändringar av nätverksmotorerna som bieffekt av import.

Utanför scope: PDF, DOCX, Visio, bilder/OCR, makro-/formelutvärdering, extern CMDB/IPAM API-synk, nätverksdiscovery, ML/LLM-schemagissning, leverantörsspecifika adapters utan verifierad kontraktsevidens. Dessa är avsiktliga begränsningar; okända format avvisas med tydlig förklaring.

Om en faktisk oförenlighet med äldre kod eller ett nytt motexempel upptäcks: stoppa berörd implementation, skriv reproducerbart negativt test, och ändra vid behov **denna enda kontraktsfil** under review i samma repository. Skapa inte ett nytt konkurrerande planeringsdokument. Forskning och externa källor är underlag, inte bevis om otestad framtida kod.

**Detta är hela den beslutade målarkitekturen, inklusive källretention, flera roller och flera objekt per källrad. Etapp 4A är fortfarande nästa kodleverans.**
