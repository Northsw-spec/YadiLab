# Kontrakt för källtrogen dokumentationsläsning och import

**Dokumentversion:** 3.0 – empiriskt reviderat slutkontrakt 4A–4D  
**Beslutat läge:** Ett enda normerande målkontrakt för 4A–4D, reviderat efter direkt granskning av öppna importimplementationer. 4A byggs först och 4B–4D därefter i separata PR:er. Dokumentet anger krav, inte redan uppfyllda funktioner.  
**Kodbas:** `detta repository`, referens-`main` `17acb51c8c64c3b4b7a1026514cb8b0a2177a127`.  
**Omfattning:** Hela den beslutade funktionen för tabellinspektion, explicit fältmappning, ofullständig nätverksdokumentation, proveniens, import, profilåteranvändning och slutacceptans. Funktionerna är målkrav, inte statuspåståenden.

## 1. Prioritet och ansvar

1. `AGENTS.md` och `docs/MASTERPROMPT.md` gäller övergripande. För **etapp 4** anger detta dokument det detaljerade, versionshanterade funktionskontraktet.
2. Verifierad källkod och senaste uttryckliga användarinstruktion har företräde framför gammal statusinformation i dokumentation och chattar.
3. Varje PR omfattar exakt en etapp. Genomför 4A → 4B → 4C → 4D efter godkänd main-CI för föregående etapp. Detta enda kontrakt styr samtliga steg; en framtida implementerare får inte kräva eller skapa ett nytt planeringsdokument för att fylla i uteblivna funktionskrav. Om den faktiska källan saknar avgörande fakta, redovisa blockerande indata i stället för att gissa.
4. En egenskap som inte finns i kod, test eller kontrakt får inte påstås vara implementerad eller verifierad. Okänd semantik ska ge en explicit olöst uppgift eller avvisning – aldrig nätverksobjekt.
5. Forskningsessäer, procentbedömningar, exempel på företagsmallar och föreslagna profilnamn är **inte** maskinläsbara scheman, produktstöd eller implementationsinstruktioner.

## 2. Befintliga kontrakt som ska förbli auktoritativa

- `network_core/model.py` och `validate_project()` är enda slutliga projektvalidator. Nätverkets kanoniska ID:n och explicita länkändpunkter bevaras.
- `network_core/csv_import.py` importerar det exakta befintliga CSV-kontraktet `Devices.csv`, `Interfaces.csv`, `Links.csv`, `Zones.csv`.
- `network_core/xlsx_import.py`, `ods_import.py` och `spreadsheet_schema.py` äger de **redan stödda** namngivna kalkylbladen, schema 1.0 och explicit schema 1.3.
- `network_core/storage.py` äger beständighet, SHA-256 och konfliktkontroll. `web/app.js` äger det enda aktuella arbetsprojektet, revisioner, arbetsytebyte och uttrycklig Save.
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
- `csvDelimiter`: endast för CSV, exakt `,` eller `;`. Fältet är obligatoriskt för CSV och förbjudet för XLSX/ODS; inget automatiskt avskiljarval.

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

- CSV: strikt UTF-8 med valfri BOM; `csv.reader` med uttryckligen vald avskiljare och korrekt quoting. Felaktiga byte-sekvenser, NUL, brutna citat och inkonsekvent radstruktur avvisas. Bevara ledande nollor som text; varje CSV-cell får typen `text`.
- XLSX: verifiera riktig OOXML-ZIP med lokala relationer. Läs endast synliga blad med vanliga literala text-, nummer- eller booleska celler. Bevara rå numerisk sträng, särskilj celltyp, och använd faktisk OOXML-koordinat. XLSX-serialiseringens numeriska ID är **inte** bevis för ursprunglig ledande nolla.
- ODS: verifiera riktig ODF-paketering och manifest; läs endast synliga tabeller med vanliga literala text-, nummer- och booleska celler. Bevara faktisk position inklusive korrekt uttryckta tomma upprepningar.
- Alla format: avvisa formler och cached formula results, makron, externa referenser, dolda rader/kolumner/blad, sammanslagna celler, kryptering, otolkade objekt med potentiellt relevant innehåll, icke-stödda celltyper, ogiltig struktur och ZIP/XML-problem. Visa ett specifikt `unsupported`-fel hellre än förvanska innehåll.
- Gränser per request: högst 5 MiB CSV; högst 5 MiB komprimerad XLSX/ODS; högst 12 MiB totalt expanderat arkiv, högst 5 MiB per XML-del; högst 24 ZIP-poster för XLSX och 10 för ODS. Högst 8 kalkylblad, 5001 fysiska rader per blad och 64 fysiska kolumner. Ovanför gränserna: deterministisk HTTP 422 utan partiellt resultat.
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
3. Negativa fall: fel avskiljare, trasig UTF-8, korrupt ZIP/XML, ogiltig ODF-mimetype, dubbla ZIP-delar, dolda celler/blad, formler, merged cells, externe länkar, makron, storleksgränser och felaktiga cellkoordinater. Ett osäkert innehåll får aldrig ge partiell HTTP 200.
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
- Användarkonstanter innehåller exakt {type:"text"|"boolean"|"null",value:...}; gäller bara vald vy och alla dess valda rader. Radunik komplettering måste vara separat explicit användardeklaration knuten till (viewId,row,targetField). Den sparas som user_decision och får inte ändra originalcellen.

Alla deklarationer ska strikt typkontrolleras; okända målnamn och extra request-nycklar avvisas. En rubrik som "IP Address" eller "Connected To" betyder inget utan bekräftad roll och fälttolkning.

### 6.3 Typade källpåståenden

En MappingView skapar för varje vald rad noll eller flera typade SourceClaims. En claim är {claimId,viewId,sourceRef,role,targetKind,targetKey,fields,origins}. sourceRef är (sourceId,tableId,row). fields innehåller endast de uttryckliga målfälten för rollen. origins har exakt varje fälts källcell(er), user_constant/user_decision eller derived_layout; referenserna valideras mot inspektionen.

En rad får via flera vyer skapa Device + Interface + andra claims. Två källrader kan beskriva samma enhet eller samma kabel; en identisk utsaga ger flera evidensreferenser men högst ett kanoniskt objekt. Motsägelser är BLOCKED och identifierar samtliga källceller.

SourceClaims är mellanmodellen och **behöver inte** uppfylla alla krav för ett färdigt nätverksobjekt. De får aldrig skickas direkt till simuleringsmotor eller Save. Endast en uttryckligt vald, komplett och slutvaliderad konstruktion får bli projekt.

## 7. Gemensam ImportPlan, proveniens och beständighet

### 7.1 Planens struktur och dispositioner

Planering är ren och deterministisk. Servern returnerar en versionsbunden JSON-kompatibel ImportPlan utan ORM-objekt, funktionsreferenser eller HTML. Den innehåller exakt:
- planVersion (strängen "1");
- sourceManifest (hashar/namn/tabellmetadata utan originalfilbytes);
- mappingViews (validerade användarval);
- units (typade, granskningsbara ändringsenheter);
- claims (typade källpåståenden med ursprung);
- recordReviews (samtliga källrader, per vy och totalt, inklusive omappade blad);
- diagnostics (strukturerad lista);
- fingerprint (kanonisk SHA-256);
- proposedProject (giltigt projekt eller null);
- canApply (boolean).

Varje **unit** har exakt {unitId,kind,targetKey,changes,dependencies,status,diagnostics,sourceUses}. En unit får omfatta flera changes som måste godkännas/avvisas tillsammans; en källrad kan bidra till flera units och flera källrader till samma unit. Kind är node|port|zone|link|staticRoute|ipBinding. targetKey är ett av den explicita projektmodellens ID:n eller en fullt kvalificerad id-kombination.

Varje **change** har exakt {changeId,operation,targetKind,targetKey,fieldValues,fieldOrigins}. operation är create eller setExplicitField. Målobjektets identitet kommer från bekräftad källtext eller radunikt användarbeslut, aldrig position i filen eller heuristisk namnlikhet. fieldOrigins är en lista av faktiska källcellreferenser/användarbeslut per målfält; den kan innehålla flera referenser när flera rader stöder samma faktum.

unit.status är exakt en av:
- ACTIONABLE: komplett, konfliktfri och validerbar tillsammans med beroenden;
- NO_OP: påståendet sammanfaller exakt med ett redan planerat objekt/fält och duplicerar därför inget nytt;
- BLOCKED: saknad källa, oklar semantik, referens eller ej granskad beslutsregel;
- INVALID: strukturellt korrekt avläst men objektet skulle bryta uttryckligt kanoniskt valideringskontrakt;
- EXCLUDED: användaren har uttryckligen exkluderat unit/källanvändning med skäl.

Diagnostics är {code,severity,message,sourceRefs,unitId} med severity INFO|WARNING|ERROR och stabil maskinläsbar code. UI ska aldrig försöka härleda status endast från svensk meddelandetext.

**RecordReviews:** Varje faktiskt befolkat källrecord finns exakt en gång per (sourceId,tableId,row) med listade viewUses; varje vald viewUse har en status ACTIONABLE|NO_OP|BLOCKED|INVALID|EXCLUDED eller DOCUMENTATION_ONLY. Om minst en vy mappar och en annan inte gör det ska den ursprungliga raden visas som **partiellt använd**, inte som helt importerad. Unmapped source columns redovisas med exakt källa och antal; råvärden är tillgängliga endast när originalkällan är ansluten.

Planen får vara partiell men föreslaget projekt kan tillämpas endast om dess valda ändringar uppfyller alla beroenden och validate_project(); blockeringar får lämnas olösta endast om de tydligt visas och inte genom något beroende förutsätts ingå i kandidaten. Ogiltig parserstruktur, okända schemafält eller felaktig planfingeravtryckning ger HTTP 422 utan projekt.

### 7.2 Beroendegraf och stabila identiteter

Planen är en riktad acyklisk graf av enhetsberoenden. Bygg i logisk ordning: zone → node → port → (ipBinding, staticRoute) → link. Varje unit-ID baseras på (typ, explicit kvalificerat targetKey, operation), **inte** bara källradnummer eller antal deklarationer. Samma unit-ID med oförenligt payload eller preconditions är INVALID; identiskt bidrag dedupliceras och behåller alla origins.

Varje dependency måste peka på en existerande planunit med tillräckligt godkänt resultat eller en redan uttryckligen godkänd kanonisk fakta. Saknade beroenden, cykler och referenser till EXCLUDED/INVALID/BLOCKED-enheter får aldrig godtas som giltig kandidat.

Urval av en unit expanderas inte tyst till andra enheter. UI får visa "Markera även beroenden" men måste kräva ett nytt, uttryckligt klick som visar exakt vilka units som tillkommer. En fysisk länk får aldrig skapa saknade noder/portar automatiskt.

### 7.3 Separera projektmanifest från originaldokument

**Reviderat och bindande beslut:** Lägg **inte** alla lästa celler eller binär XLSX/ODS-data i varje .yadilab-projekt. Det vore stora projektfiler, dubblerat källinnehåll och otydlig sekretesshantering. Skilj på:
1. **Kanoniskt projekt** – endast de validerade nätverksobjekt som simuleringsmotorn förstår.
2. **Litet, beständigt importEvidence-manifest** – vilka filer/rader/mappningsvyer som bidrog, SHA-256, uttryckliga beslut och varningar. Aldrig hela originalfilens cellinnehåll.
3. **Separat originalkällpaket** – källbytes på uttryckligt användarval, exporterat som en fristående JSON-fil; aldrig automatisk Save, molnsynk eller osynlig kopia.

Etapp 4B inför en enda versionsbunden ändring av projektformatet: schemaVersion "1.4" med **en ny root-nyckel importEvidence**, men utan de fullständiga source.cells[] från föregående kontrakt. För 1.4 är importEvidence exakt:
- evidenceVersion: "1";
- sources: [{sourceId,filename,kind,sha256,byteLength,tables:[{tableId,name,rowCount,populatedRowCount,columnCount}]}];
- mappingViews: snapshots av §6.1:s validerade mappningsvyer;
- decisions: [{sourceId,tableId,row,viewId,status,reason,unitIds}];
- acceptedChanges: [{unitId,changeIds,targetKind,targetKey,fieldOrigins}];
- sourceStorage: konstantsträngen "external_not_embedded".

Allt ska bevaras över faktisk Save/Open och programomstart. Varje sourceId/tableId/row/viewId, unitId och fieldOrigins måste vara referensmässigt konsistent och valideras av **samma validate_project()**. Protokollmotorer ska ignorera importEvidence. Inga andra extra root-fält, inga dolda projektmigreringar och inga implicit uppgraderade 1.0–1.3-filer.

**Detta manifest är en auditindex, inte originalets dataarkiv.** Existerar inte den ursprungliga källfilen efter återöppning visar UI "Källa ej ansluten; originalvärden kan inte granskas" och dess hash/celladresser, aldrig påhittade cellvärden. Importerade kanoniska nätverksfält förblir läsbara utan källan. En användare som vill kunna verifiera ursprungsrader efter ett år måste behålla originalfil(er) eller explicit exportera källpaket.

**Källpaket:** UI erbjuder senast i 4B ett separat explicit "Exportera originalkällor" som skriver JSON med exakt {sourceBundleVersion:"1",sources:[{sourceId,filename,kind,sha256,contentBase64}]}. Det är fristående från .yadilab och innehåller originalbytes i base64. Om användaren importerar paketet senare avkodas alla filer strikt, återinspekteras av samma 4A-parser och verifieras mot det öppnade projektets hash och sourceId. Hash-/fil-/strukturmismatch ger avslag, inga metadata skrivs automatiskt. Inga externa filvägar eller skript accepteras från paketet.

**Obligatorisk användarupplysning vid godkännande:** "Originaldokumenten sparas inte automatiskt i projektet. Behåll originalfilerna eller exportera källpaket för att kunna granska ursprungsceller senare." Varje omappad/olöst cell finns kvar oförändrad i **originalkällan**, men inte i .yadilab. Tyst förlust får inte påstås vara förhindrad om användaren inte fått denna varning och valt att fortsätta.

**Gränser:** v1.4 importEvidence måste rymmas inom exakt mätt MAX_BODY/Save-gräns; sätt en separat hård maximal serialiserad importEvidence-storlek på 2 MiB och avvisa med ett begripligt fel om den överskrids. Beskär aldrig origins, sourceRefs eller decisions för att passa. Själva .yadilab-kandidatens sammanlagda serialiserade bytes ska kontrolleras före godkännande. Om modellen är för stor kan användaren importera mindre källmängd uttryckligen.

### 7.4 Replay och stale-preview

Importplanens fingerprint är SHA-256 av kanonisk JSON över planVersion, källhashar, hela mappingViews, explicit exkludering/val, projektName och målvalideringsversion; sortera JSON-objektnycklar rekursivt och serialisera UTF-8 med fasta separatorer och utan NaN/Infinity. Undvik att inkludera klockslag, UI-text eller radordning i osorterade hashtabeller. Testa att indata med annan JSON-nyckelordning får samma fingerprint och att ändrade fält, källa, val och beroenden ändrar det.

Inget serverlagrat/importerat sessionstillstånd krävs. Förhandsvisning och planering är skrivskyddade. UI fångar exakt källhashar, mappningsrev, planfingeravtryck, workspaceRevision och editRevision före varje asynkront anrop. Svar som inte matchar aktuella värden ska kastas. Precis före arbetsytebyte krävs ny kontroll av revisioner och en aktuell, validerad plan med samma fingerprint. En äldre eller annan fliks plan får aldrig ersätta nyare arbetsyta. När import godkänts blir arbetsytan osparad tills befintlig Save används.

### 7.5 Version och kompatibilitet

Modelldelen av schema 1.4 ska vara semantiskt densamma som 1.3. Bevara validering av gamla schemaVersion-strängar och deras exakta fältgränser. Uppdatera alla kodvägar som jämför 1.3 exakt (inklusive statiska routes och VLAN/MAC) så att 1.4 får samma protokollfunktioner. Schema 1.4 ska kunna användas av befintlig simuleringsmotor utan att proveniensen blir aktiv topologi.

Äldre filer ska vara byte-identiska fram till ett uttryckligt Save; öppning validerar men migrerar aldrig. Export av v1.4 till en tabellvariant som inte kan bevara manifestet ska avvisas med ett begripligt förlustmeddelande – ingen tyst nedgradering. Projekt som saknar importEvidence är inte v1.4.

## 8. Fast måltypskatalog för källpåståenden

Dessa **sju generiska roller** är produktens egna semantiska kategorier, inte påstådda industristandarder. Ett blad får innehålla flera roller genom flera views. En vy har exakt en roll.

| role | Deklarerade fält / mappningsmöjligheter | Tillåten effekt |
|---|---|---|
| device_inventory | node.id, node.label, node.kind, node.zoneId | En eller flera enheter via flera views/rows |
| interface_inventory | port.nodeId, port.id, port.name, port.enabled, port.ipv4, port.mac, port.vlanMode, port.accessVlan, port.allowedVlans | Port under uttryckligen deklarerad nod |
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

## 9. Etapp 4B – importplan, blandade enhetsvyer och kompakta auditmanifest

**Start:** 4A mergad och efterföljande main-CI SUCCESS. Inga andra planeringsdokument får krävas.

Implementera de gemensamma kontrakten i §§5–8 och måltyperna device_inventory + documentation_only. Tillåt redan nu **flera views över samma blad och samma rad**, även om bara de två rollerna kan skapa resultat i denna etapp. Bygg den typade SourceClaim- och ImportPlan-gränsen så att 4C kan addera port/kabel utan att ändra grundsemantiken.

### 9.1 Skrivskyddat kandidat-API

Inför exakt en ny endpoint: POST /api/import/build-candidate.

Request är ett JSON-objekt med exakt {contractVersion,projectName,sources,mappingViews,excludedUses,selectedUnitIds}:
- contractVersion:"1"; projectName följer validate_project().
- sources är 1–8 objekt med exakt {sourceId,filename,contentBase64,csvDelimiter?}; sourceId är src-1, src-2 etc. csvDelimiter obligatoriskt enbart för CSV och alltid komma eller semikolon. Aggregat av ursprungliga filer högst 4 MiB (base64 + JSON måste även uppfylla befintlig MAX_BODY); varje källfil ska dessutom klara 4A:s egna läsgränser.
- mappingViews är alla aktiva vyer i §6.1. En källa utan vy förblir helt omappad och måste redovisas i planen; en vy utan källstöd ger HTTP 422.
- excludedUses har exakt {viewId,row,reason}; reason 1–240 tecken och måste vara ett aktivt användarbeslut för just den användningen.
- selectedUnitIds är den explicita listan med planunits som användaren vill använda. Om listan är tom returneras en ren granskningsplan med proposedProject=null. Första vyn byggs alltid utan selectedUnitIds, därefter får användaren välja units och omplanera inför bekräftelse.

Response 200 har exakt {planVersion:"1",fingerprint,plan,project,report}, där plan följer §7 och project är null eller ett fullständigt validate_project()-godkänt projekt i schema 1.4. report har objekt med antal källrecords, användningar, ACTIONABLE/NO_OP/BLOCKED/INVALID/EXCLUDED, unmappedCells, selectedUnits, nodes,ports,links,zones,routes och warnings (strukturerade diagnostikvärden, inklusive exakta källreferenser). Inga okända fält, otydliga statussträngar eller stiliserade "success"-påståenden.

En felaktig eller osäker request eller källa ger HTTP 422 med befintligt INVALID_PROJECT-felkontrakt. Semantiskt ofullständig **giltigt avkodad** källrad är däremot BLOCKED eller INVALID i en 200-plan utan att ett projekt behöver skapas. Ett projekt får bara returneras när selectedUnitIds är kompletta, konfliktfria, beroendegiltiga och slutvaliderade. Servern skriver aldrig projekt eller källor.

### 9.2 Schema-1.4-gräns

Utöka validate_project() med importEvidence såsom §7.3 anger och **inga fullständiga source.cells[]**. Alla importerade claims och planunits ska ha en verifierbar källa, och alla valda schema-1.4-fält ska ha fältproveniens. Proveniens ska i UI granskas efter Save/Open; om källor saknas markeras tydligt "ej ansluten". Källpaketexport/-import enligt §7.3 görs i samma etapp så att användaren inte bygger på en dold antagen originalbackup.

Faktiskt projekttillstånd, filename, savedSha, revision och Save/Open förblir ägda av appens nuvarande huvudstruktur. Inget import-/planeringspaket får innehålla egen Save-implementering. Giltig kandidat ersätter den osparade arbetsytan först efter ett nytt användarklick som verifierar snapshot/fingerprint/revision.

### 9.3 Specifika 4B-tester

- Två oberoende syntetiska inventeringar med olika rubriker och column order ger samma kanoniska expected device efter explicit mapping; ingen rubrikheuristik.
- **En rad, två vyer** från samma blad ger två claims. **Två rader, ett targetKey** ger ett enda nätverksobjekt och två field origins vid lika fakta.
- Två motstridiga celler på samma target field ger BLOCKED och ingen skapad enhet.
- En nod utan ports/links är giltigt **partiellt** projekt, inte ett fullständigt observerat nät.
- Felaktigt typed ID, okänd node.kind, saknad användardeklaration, plan-ID-kollision, obefintlig källcell, EXCLUDED som beroende, ändrad source hash och stale UI-respons hindrar projektbyte.
- importEvidence återläses exakt efter Save/Open och omstart; råa källceller är inte i .yadilab. Efter omstart visas korrekt "källan ej ansluten". Import av rätt källpaket återställer förmågan att granska celler; fel SHA blockeras.
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

**Detta är hela beslutade målarkitekturen, inklusive källretention, flera roller och flera objekt per källrad. Etapp 4A är fortfarande nästa kodleverans.**
