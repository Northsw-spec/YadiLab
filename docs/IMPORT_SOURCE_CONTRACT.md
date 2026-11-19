# Kontrakt för källtrogen dokumentationsläsning och import

**Dokumentversion:** 2.0 – fullständigt målkontrakt 4A–4D  
**Beslutat läge:** Hela målarkitekturen, användarflödet, avgränsningarna, data- och API-kontrakten och slutacceptansen är fastställda i denna fil. 4A implementeras först; 4B–4D genomförs därefter i separata verifierade PR:er, utan ytterligare planeringsdokument.  
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
2. **Dokumentroll och profil:** Ett blad tilldelas högst en explicit semantisk roll i en given mappning. Profiler består av versionshanterade mappningsregler, inte kompletta konkurrerande filparsers eller nätverksmotorer.
3. **Kandidatöversättning:** Användargodkända fält och identitetsrelationer omvandlas med spårbar referens till källcell. Där information inte kan representeras förblir kandidaten blockerad.
4. **Kanonisk validering:** Det slutliga projektet valideras av `validate_project()`; ingen adapter kan kringgå dess regler.
5. **Förhandsvisning och godkännande:** UI visar importerbara fakta, blockerande fel och alla olösta källfält före någon projektförändring. Save förblir en separat handling.

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


## 5. Slutlig funktionsgräns och arkitektur

### 5.1 Användarnytta och huvudkedja

Den fullständiga funktionen ska ge användaren två separata arbetssätt:
1. **Strikt inbyggd import** av redan etablerade och testade CSV/XLSX/ODS-schema 1.0/1.3. Befintlig fil-/valideringskedja är oförändrad och behöver ingen ommappning.
2. **Användarstyrd extern tabellimport** där filen först läses som källceller, användaren tilldelar varje blad en dokumentroll, mappar rubriker och värden, granskar importerbara respektive olösta uppgifter, och därefter godkänner ett kanoniskt kandidatprojekt.

Målkedjan för extern import är: originalbytes → kontrollerad formatparser → full källcellsmatris med ursprungspositioner → explicit tabellroll/kolumn-/värdemappning → kandidatutkast plus fullständigt källarkiv → gemensam modellvalidering → granskningsrapport → uttryckligt arbetsytebyte → separat Save.

**En enda slutlig nätverksmodell.** Källspecifika adaptrar får endast översätta deklarerad semantik. De får inte innehålla alternativa nätverks-, routing- eller simulatorregler. CSV/OOXML/ODF-avkodning återanvänds mellan roller. Det byggs ingen separat fullständig motor för varje dokumentationskonvention.

En dokumentroll beskriver hur *användaren* vill tolka en tabell. Den utgör aldrig en extern branschstandard. Ingen Cisco-, Microsoft-, NetBox-, konsult- eller leverantörsprofil får uppfinnas ur allmän kunskap, rubriklikhet, filnamn, visuell layout eller AI.

### 5.2 Ofullständigt nätverk och sanningstyper

Appen ska stödja en uttryckligt märkt **partiell inventering**: dokumenterade noder utan portar eller kablar är tillåtna. Frånvaron av en rad i dokumentet bevisar inte fysisk frånvaro. Tre kategorier hålls isär:
- **Källuppgift:** exakt vad den angivna dokumentfilen innehåller; källan är inte verifierad mot verkligheten.
- **Användarbeslut:** explicit roll, typmappning, konstant, exkludering eller ID-bindning; inte en källuppgift.
- **Härledd presentation:** koordinater och andra rent visuella värden; aldrig bevis för topologi.

En import kan verifiera att källans deklarationer är konsekventa med appens schema. Den får aldrig påstå att de beskriver den verkliga miljön korrekt eller att trafik kan nå fram. Dokumentationsproveniens får inte påverka ARP, Ethernet, IP, routing, DHCP, ICMP eller felinjicering.

### 5.3 Explicit scope för full produkt

Fullt stöd omfattar generiska roller för **enheter, portar, kablar, zoner, statiska routes och en begränsad IP-plan**, inklusive en roll för rena dokumentationsblad. För återkommande dokumentationskonventioner kan användaren exportera/importera en granskad JSON-mappningsprofil; profilimport innebär inte automatiskt godkännande av en ny källfil.

Avsiktligt utanför målomfattning: PDF/DOCX, fotografier/OCR, Visio, CMDB-/IPAM-API-synk, SNMP/LLDP-liveupptäckt, konfigurationsparser, brandväggs-ACL/NAT-deduktion, dynamiska routingprotokoll, DNS/DHCP-autogenerering, LLM-/ML-schemamatchning, körning av Excel-formler och okända filtyper. En avvisning av dessa format är **korrekt beteende**, inte ofärdig implementation.

## 6. Gemensam data- och proveniensmodell för 4B–4D

### 6.1 Schema 1.4: enda kanoniska projektutökningen

Etapp 4B ska införa en validerad, versionerad projektmodell **schema 1.4**. Behåll alla nätverksfält och valideringsinvariants från 1.3; utöka endast projektroten med den obligatoriska nyckeln **importEvidence** för v1.4. Den har exakt tre arrayer: **sources**, **mappings**, **decisions**. Denna del är dokumentationsmetadata, inte alternativa nätverksobjekt.

Äldre projekt 1.0/1.1/1.2/1.3 ska läsas och sparas utan automatisk migration, förlust eller ändrad käll-SHA. V1.4-projekt ska gå att spara, öppna och exportera som oförändrat kanoniskt JSON och .yadilab utan att förlora evidens. Befintlig XLSX/ODS-export ska **avvisa** v1.4 när den inte kan exportera hela importEvidence förlustfritt, i stället för att tyst producera ett schema 1.3-dokument.

**sources[]**: exakt `{id,filename,kind,sha256,tables}`.
- id: interna källreferenser `src-1`, `src-2` i användarens godkända filordning; de är inte nod-ID:n.
- filename: verkligt enkelt filnamn, utan katalog.
- kind: `csv`, `xlsx` eller `ods`.
- sha256: gemena 64 hextecken över originalbytes.
- tables: en array i verklig bladordning med exakt `{tableId,name,cells}`. Varje cell har exakt `{address,type,value}` enligt avkodningskontraktet i 4A. **Alla** avkodade, lagrade källceller ska ingå, inte bara de 25 förhandsvisade raderna. Dubblettadresser är fel. För CSV avser radnummer logiskt record och för XLSX/ODS fysisk cellkoordinat.

Arkivet är en **fullständig representation av stödda avkodade cellvärden och deras koordinater** – inte en byte-identisk kopia av hela källarbetsboken. Originalets verkliga bytes kontrolleras med SHA-256 separat. Innehåll som inte går att avkoda eller arkivera utan relevant informationsförlust ska avvisas, inte utelämnas. En källa med icke-stödda formler, dold data eller betydelsebärande objekt ska inte delaccepteras.

**mappings[]**: exakt `{sourceId,tableId,role,headerRow,columns,valueMaps,constants}`. sourceId/tableId måste referera ett verkligt blad. role är en av §7:s sju roller. headerRow är ursprungligt positivt radnummer eller null för headerlös tabell. columns mappar tillåtna målfältsnamn till verkliga kalkylbladskolumner (bokstäver A–BL); valueMaps är explicit användarbekräftade literal→literal-tabeller för varje mål; constants är explicit användarinmatade, typade värden med dokumenterad ursprungsmarkering. Varje blad har en enda roll.

**decisions[]**: exakt `{sourceId,tableId,row,disposition,target,origins,reason}`. Varje datarad som inte är rubrik förekommer exakt en gång, oavsett om den skapade ett objekt.
- disposition är `mapped`, `unresolved` eller `excluded_by_user`. `reason` är null för mapped/unresolved och en uttrycklig 1–240 tecken lång användarmotivering för excluded_by_user; värdet ska bevaras efter Save/Open.
- target är null när inget nätverksobjekt skapas; annars exakt `{type,id}` där type är `node|port|zone|link|staticRoute` och id är kanoniskt (port: `nodeId/portId`; route: `nodeId/routeId`).
- origins är en array av exakt `{targetField,sourceCell,originKind}` med originKind `source_cell|user_constant|derived_layout`. sourceCell måste referera en faktisk avkodad källcell när originKind=source_cell; annars null med motsvarande explicit användarkonstant eller dokumenterad koordinatregel.

En mappad kanonisk fältuppgift måste ha entydig proveniens. En olöst rad skapar **inget** nätverksobjekt men bevaras i sources. Användarexkluderad rad bevaras med sin exkluderingsstatus och redovisas; ingen rad ignoreras tyst. Motstridiga uppgifter om samma fält ska blockeras och rapportera båda källcellerna; ingen last-write-wins. Samma faktavärde från två källor får bevaras med två ursprungsreferenser utan duplicerat objekt.

`validate_project()` ska vara enda slutvaliderare för både v1.4:s proveniensintegritet och den befintliga kanoniska grafen. De nya fälten ska inte läsas av simuleringsmotorerna. Uppdatera de frontend-delar som nu uttryckligen kontrollerar schemaVersion eller projektstrukturen så att v1.4 kan visas utan att gammal data omtolkas. Gör inga tysta migrationer.

**Gränser:** Den kompletta serialiserade v1.4-kandidaten måste rymmas inom serverns **faktiska** 8 MiB requestlimit även vid uttrycklig Save (inklusive JSON/UTF-8 och base64 om tillämpligt). Om fullständig källarkivering inte ryms ska importen blockeras med tydligt fel. Ingen automatisk beskärning av cells, rader eller källfakta.

### 6.2 Käll- och mappningsintegritet

En källhash ska beräknas om från originalbytes när en kandidat genereras, inte litas på som en klientuppgift. Käll-ID, tabell-ID, radnummer och celladress i varje mappnings- och beslutsrecord ska finnas i sources; dubbletter eller korsreferenser till annan källa blockeras.

Ett dokument kan innehålla flera roller för olika blad och en kandidat kan kombinera flera källfiler. **Samma dokumentroll får inte vara en universell parser som läser vilket källdataformat som helst.** Alla fält måste komma från konkreta valda kolumner eller uttryckligen dokumenterade användarbeslut.

Källkolumner som saknar plats i kanoniskt schema (exempelvis tillverkare, serienummer, produktmodell, rackplacering, anteckning, management-IP utan portbindning) bevaras som ursprungliga celler i importEvidence. De får inte omklassificeras till port-IP eller tappas bort, och simuleringsmotorn får inte läsa dem som nätverksfakta.

### 6.3 Exakta former för mappning och värden

**columns:** JSON-objekt med semantiska målfältsnycklar från §7 och källkolumner i formatet `A`–`BL` (stora ASCII-bokstäver, utan radnummer). Källkolumnen ska finnas i valt blads verkliga kolumnområde. Vald rubrikrad kontrolleras men rubriktexten tillmäts ingen automatisk semantik. Data hämtas från faktiska efterföljande rader. Ett målfält får exakt en källkolumn ELLER en användarkonstant, inte båda.

**valueMaps:** JSON-objekt `{"<targetField>":{"<literalSourceText>":"<literalTargetText>"}}`. Det är tillåtet endast för ett målfält som har en vald källa i columns och för celler av typen text. Mapparna är exakta och skiftlägeskänsliga; inget trim eller fuzzy-match. Målfältet måste tillhöra aktuell roll. Mappad kind har värden `host|switch|router|firewall`; boolean har `true|false`; andra mål måste accepteras av slutvalideraren. Olistade textvärden får inte tolkas genom likhet. För textfält utan valueMaps används rå text; native boolean får användas för enabled. Numeriska identitetsceller avvisas.

**constants:** JSON-objekt `{"<targetField>":{"type":"text|boolean|null","value":"..."|true|false|null}}`. En konstant gäller **samtliga datarader i bladet**. Radunika undantag är inte del av kontraktet: sådana rader förblir unresolved tills användaren ändrat källa eller tillhandahållit separat tabell. Målfältet måste höra till vald roll. Canonical ID-/relationsfält får inte vara tabellkonstanter eftersom flera records annars skulle kunna sammanblandas; varje mappad rad måste ha explicit identitetscell. Konstantvärdet är ett användarbeslut, inte källfakta. Null är endast tillåtet för nullable fält och representerar "ej dokumenterat", inte bevis för faktisk frånvaro.

**Headerregler:** En vald headerRow måste existera och innehålla unik, icke-tom rubrik för varje vald datakolumn; datarader börjar efter rubrikraden. HeaderRow=null betyder att alla faktiskt lagrade records är datarader och att sparad profils expectedHeaders är tom array. Källrader före en vald senare rubrikrad arkiveras som unresolved; de får inte tyst ignoreras. Tomma blad kan arkiveras men ger inga mappade dataobjekt.

**Värdefel kontra avvisning:** Ogiltiga request-nycklar, profildefinitioner, källreferenser eller osäker parsing ger HTTP 422. En semantiskt ofullständig men giltigt avkodad källrad blir unresolved utan något nätverksobjekt och med originalceller i arkivet. Ett påstått färdigmappat nätverksobjekt som bryter validate_project() ger däremot HTTP 422 för hela kandidaten. Ingen partiell HTTP 200 som döljer serverfel.

**sourceSetSha256:** beräkna från UTF-8 utan ASCII-escape över JSON-objektet `{sources:[{sourceId,sha256}],tables:[...fullständiga mappningsobjekt...],excludedRows:[...inklusive reasons...]}` där alla objektfält sorteras lexikografiskt rekursivt och JSON-separatorerna är `,` och `:`. Sortera källor på sourceId, tabeller på sourceId/tableId samt excludedRows på sourceId/tableId/row. Dubbletter avvisas innan hashning. Hashen är kandidatidentifiering, inte autentisering. UI ska även jämföra fångade käll- och mappingversioner samt workspace/edit-revision vid sena HTTP-svar.

## 7. Fullständig lista över dokumentationsroller och semantik

Detta är de enda sju stödda generiska rollerna. En dokumentationskonvention kan använda valfria rubriker och bladnamn, men måste mappas till exakt dessa tillåtna mål.

| Role | Tillåtna semantiska målfält | Projektresultat |
|---|---|---|
| `device_inventory` | `node.id`, `node.label`, `node.kind`, `node.zoneId` | Dokumenterade noder |
| `interface_inventory` | `port.nodeId`, `port.id`, `port.name`, `port.enabled`, `port.ipv4`, `port.mac`, `port.vlanMode`, `port.accessVlan`, `port.allowedVlans` | Portar under explicita noder |
| `cable_register` | `link.id`, `link.aNode`, `link.aPort`, `link.bNode`, `link.bPort`, `link.enabled` | Fysiskt deklarerade länkar |
| `zone_inventory` | `zone.id`, `zone.label` | Dokumenterade zoner |
| `static_route_register` | `route.nodeId`, `route.id`, `route.destination`, `route.nextHop`, `route.outPort` | Statiska routes |
| `ip_plan` | `ip.nodeId`, `ip.portId`, `ip.ipv4` | Enbart uttryckligt portbunden IPv4/CIDR, annars endast arkiv |
| `documentation_only` | inga | Ursprungliga celler arkiveras; inga nätverksobjekt skapas |

- device_inventory: node.id är obligatorisk unik käll-/användardeklaration. node.kind måste vara en av `host|switch|router|firewall`, antingen ordagrant eller via en explicit bekräftad värdeöversättning. En accesspunkt, NAS, skrivare, hubb eller telefon får **inte** automatiskt bli host/switch; utan användarbeslut ska raden förbli unresolved.
- interface_inventory: varje port kräver exakt referens till existerande nod samt explicit port.id. port.name och port.enabled kommer från källa eller uttrycklig användarkonstant. IPv4/CIDR, MAC och VLAN följer existerande modellregler. Okänd enabled får inte antas vara true. Ett management-IP utan bekräftad portbindning blir inte port.ipv4.
- cable_register: kräver explicit link.id, link.enabled, **båda** dokumenterade (nod, port)-ändpunkterna, samt att ändpunkterna redan finns och är lediga enligt validate_project(). En text som `connected to core switch`, LLDP-granne, VLAN, IP, geografisk placering eller grafik är inte en fullständig kabelpost. Saknas ena ändpunkten blir raden unresolved och ingen kabel skapas. Dubbla/konflikterande förbindelser avvisas.
- zone_inventory: zone.id och label måste vara explicita. Ingen automatisk zon skapas från inventeringsplats eller rackfritext.
- static_route_register: destination, nextHop och outPort måste vara uttryckliga och uppfylla nuvarande v1.3-validering. En route betyder inte reachability.
- ip_plan: om både nodeId och portId är explicit och entydigt identifierade kan en faktisk IPv4/CIDR bindas till just den porten. Alla andra IPAM-, subnäts-, gateway-, DHCP-reservations-/poolvärden är dokumentationsceller, inte nya nätverksobjekt eller routingslutsatser.
- documentation_only: innehåller hela avkodade cellmatrisen, radvis status `unresolved` eller användarbeslutad `excluded_by_user`; ingen semantisk konvertering.

Obligatoriska booleska fält accepterar källans exakta `true/false` eller verkliga booleska celltyp. Kodvärden som `UP`, `yes`, `1` mappas bara efter explicit användarvärdeöversättning. Identifierare med ledande nollor måste vara källtext; en numeriskt lagrad identitet får inte rekonstrueras från utseende eller format.

**Presentationskoordinater:** sortera godkända nod-ID:n lexikografiskt; index `i` börjar 0. `x=110+(i%4)*260`, `y=110+floor(i/4)*220`. Ursprung `derived_layout`. Följ samma koordinatgräns som modellen. Detta skapar inga fysiska relationer.

**Relationer och bearbetningsordning:** konstruera zoner → noder → portar → routes/IP-plan-bundna adresser → kablar. Bearbetningsordningen bestäms av semantik och är oberoende av tabellordning. Join sker bara via explicita, validerade kanoniska ID:n, aldrig heuristisk namn/IP-matchning. En blockerat objekt kan inte samtidigt vara giltig referens för en kabel eller route.

## 8. Etapp 4B – användarstyrd inventeringsmappning och version 1.4

**Start:** 4A MERGED + main-CI SUCCESS. Ingen extra plan eller utomstående leverantörsprofil behövs. Implementera schema 1.4, §6 och rollerna device_inventory/documentation_only.

### 8.1 Kandidat-API

Inför en enda ny endpoint, `POST /api/import/build-candidate`. Den ska återanvändas i 4C/4D.

Request har exakt `contractVersion`, `projectName`, `sources`, `tables`, `excludedRows`.
- contractVersion: exakt strängen `"1"`.
- projectName: 1–120 tecken enligt gällande modell.
- sources: 1–8 objekt, var och en med `sourceId`, `filename`, `contentBase64`, och `csvDelimiter` enbart för CSV. sourceId är unik `src-1` etc. Max 5 MiB **sammanlagt** av ursprungliga källbytes så hela base64-JSON-HTTP-requesten kan rymmas inom serverns MAX_BODY. Enskilda 4A-gränser gäller dessutom.
- tables: en mappningspost enligt §6 för **varje faktisk tabell exakt en gång**. Så snart en tabell inte ska mappas används documentation_only, inte tyst utelämnande.
- excludedRows: array med exakt `{sourceId,tableId,row,reason}`; reason är 1–240 tecken och beslutet måste komma från uttrycklig användarhandling. Rubrikrader kan inte exkluderas som data.
- Alla källfiler inspekteras om från råbytes. Ingen lagrad serveruppladdningssession, inget mellanresultat får litas på som källa.
- headerRow är ett positivt källradnummer eller null för en tabell utan rubrik; den blir aldrig en nätverksenhet. En vald headerRow måste finnas och överensstämma med den faktiskt avkodade tabellstrukturen.
- columns mappar §7:s mål till faktiska kolumnbokstäver. valueMaps är explicita literal-value-översättningar knutna till målsemantik; constants är typade användardeklarationer. Ogiltig/kolliderande/feltypad mapping ger HTTP 422.

Svar 200 är exakt `{candidateVersion,sourceSetSha256,project,report}`: candidateVersion `"1"`; sourceSetSha256 är SHA-256 av kanoniskt serialiserad ordnad källhash-/mappningsmanifest (specificera deterministisk sortering i implementation och testa byteidentitet); project är komplett validerat schema-1.4-objekt; report är exakt `{mappedRows,unresolvedRows,excludedRows,nodes,ports,links,zones,staticRoutes,warnings}`. Antalsfält är heltal >=0. warnings är array `{sourceId,tableId,row,cell,message}` med cell=null om ingen specifik cell bevisar felet. HTTP 422 har befintligt `INVALID_PROJECT`-format; inget partiellt projektsvar vid fel.

En giltig partiell kandidat får innehålla unresolved-rader om källarkivet bevarar dem **och UI tydligt visar "PARTIELL DOKUMENTATION – INTE VERIFIERAD TOPOLOGI"**. Minst en giltig nod krävs för ett kandidatprojekt; en ren källförhandsvisning får däremot vara helt utan nätverksobjekt.

### 8.2 UI-kontrakt

Filval → inspektion → exakt en tabellroll per blad (single select, **inte konkurrerande checkboxar**) → deklaration av headerRow → val av källkolumn för målfält → explicit kind-/bool-/VLAN-värdeöversättning och valfria konstanter → full kandidatsammanställning → uttryckligt godkännande att ersätta arbetsytan → separat Save.

För varje blad visas vilka kolumner som används och alla övriga som **bevaras som dokumentationsceller**, med källa och rad. Varje mappning har en användarsynlig skillnad mellan `source_cell`, `user_constant` och `derived_layout`. En importvy får aldrig använda en redan existerande projektrendering för att påstå att något är nätverksmässigt verifierat.

Frys vid anrop exakt källhash, tabell-/kolumnmappning, eventuella uteslutningar, workspaceRevision och editRevision. Ett sent svar från förra filen, förra mappningen eller förra arbetsytan får inte påverka aktuell UI, kandidat eller Save. En giltig kandidat kräver nytt, aktuellt användarklick för arbetsytebyte.

### 8.3 Testfall

Minst två oberoende *syntetiska, uttryckligen märkta* inventeringstabeller med olika headernamn, rubrikrad/kolumnordning ska ge en identisk separat handskriven expected canonical model efter explicit mapping. Feltesta saknade/dubblerade ID, okänd typ, numerisk identitet med förlorad ledande nolla, motstridig dubbelkälla, felaktig headerRow, tom label, missing sourceCell, out-of-bounds arkiv och stale UI-svar. Bevisa att omappade celler och beslut överlever riktig diskbaserad Save/Open och serveromstart. Nya projektschema-versionen får inte ändra tidigare filers bytes eller skapa extra protokollbeteende.

## 9. Etapp 4C – port-, kabel-, zon-, route- och IP-plan-mappning

**Start:** 4B MERGED + main-CI SUCCESS. Implementera resten av de sju rollerna i §7 med **samma** kandidat-API, samma källa, samma 1.4-evidens, samma kanoniska validator.

Bygg endast en port när både nodeId och portId uttryckligen identifierats och noden finns; annars unresolved. Bygg en fysisk länk endast med explicit link.id, enabled och två fullständiga, redan deklarerade portändpunkter; annars unresolved. När informationen motsäger annat källunderlag blockerar kandidaten den berörda relationen och visar båda ursprungscellerna. Ingen automatisk kabel från IP, text, LLDP, plats eller grafväg. Statiska routes, IP, VLAN, MAC använder respektive nuvarande validators exakta domänregler. Importerade IPAM-rader utan nod/port ska förbli dokumentation.

I en sammanslagen import från flera källor gäller samma exakta käll-/kolumn-/radkontroll som 4B. Ett uteslutet eller olöst objekt får inte refereras som en accepterad ändpunkt. Om data saknas redovisa avvisning eller partiell kandidatuppsättning med kvarvarande evidens; inga fejkade noder för att få relationen att gå ihop.

Testa minst två separat konstruerade riktiga OOXML/ODF/CSV-uppsättningar med olika kolumnrubriker och korrekt komplett explicit nätverk; jämför med oberoende handskriven förväntad v1.4-projektmodell. Testa dessutom två partiella underlag samt negativa dubbelportar, saknad kabeländpunkt, inkonsekvent VLAN, felaktig next-hop, icke dokumenterat gateway-ID, management-IP utan port, och samtida käll-/projektbyte. Den befintliga verkliga ARP/IPv4/ICMP/DHCP-testningen måste fortfarande passera oförändrat och får bara se uttryckliga kanoniska fakta.

## 10. Etapp 4D – kompletta användarprofiler, tvärkälla och slutacceptans

**Start:** 4C MERGED + main-CI SUCCESS.

### 10.1 Profilformat och återanvändning

Användaren ska kunna **exportera** och **importera** en mappningsprofil som vanlig JSON endast efter uttryckligt användarklick. Inget tyst sparande till browser storage, profilregister, projekt, lokala filer eller moln. Profilformatet har exakt `{profileVersion,role,headerRow,expectedHeaders,columns,valueMaps,constants}`, profileVersion exakt `"1"`, expectedHeaders den kompletta ordnade listan av verkliga rubriker. Allt annat avvisas.

Varje återanvänd profil kräver en ny källinspektion. Alla rubriker, positioner, roll-/kolumnkontrakt och kodvärdeöversättningar kontrolleras; mismatch ger blockering och tydlig manuell rättning. Även vid exakt rubrikmatchning krävs uttryckligt användargodkännande av semantiken för den **nya filen**. Ingen profil tillåts kringgå originalbyte-hash, validering eller användarbeslut.

Kalla profilen "egen mappningsprofil", inte en certifierad bransch-/leverantörsstandard. Inga inbyggda NetBox/Cisco/SolarWinds/Atea-profiler uppfinns utan verklig versionslåst exportdefinition och separata tester; sådana profiler är inte nödvändiga för att målomfattningen ska vara färdig.

### 10.2 Komplett slutligt UI

Färdig importvy ska kunna: välja flera filer inom fastställda bounds; visa källtrogen blad- och cellförhandsvisning; välja en roll per blad; mappa identiteter/fält/värdekoder och tydliga konstanter; identifiera omappade och motstridiga fakta; visa antal mappade, olösta och uteslutna rader; navigera till originalcell; se om varje kanonisk uppgift är från källcell, användarbeslut eller presentationsregel; granska exakt kandidat och partiellhetsmarkering; bekräfta ersättning av arbetsytan; spara senare explicit; exportera/importera profilschema; efter Save/Open kunna granska proveniens i v1.4 utan att den presenteras som fysisk nätverksverifiering.

Ett dokument som saknar all nödvändig semantik ska fortfarande kunna **inspekteras** och arkiveras via giltig partiell kandidat med minst en explicit accepterad nod, men aldrig tolkas om till ett falskt komplett nät. Fullständigt irrelevanta eller icke representerbara dokument får ett begripligt avslag för projektimport, men tydlig källförhandsvisning.

### 10.3 Oberoende evidens och kriterier

Skapa en versionsbunden regression med verkliga anonymiserade filer **endast om verkliga filer faktiskt finns och lagligen kan användas**. Annars ange `synthetic only`, utan påstående om verklig marknadstäckning. För varje fil med facit rapporteras: källblad/antal källrecords, mappade fakta, olösta/exkluderade, misslyckade och korrekt avvisade mappningar, manuella användarbeslut, importerade noder/portar/kablar, verkliga Save/Open-roundtrips och käll-SHA.

Obligatoriska slutgrindar: **0 implicit skapade fysiska kablar**, **0 tyst tappade källcellvärden**, **0 ogiltigt accepterade referenser**, **0 autosave/otillåten överskrivning**, **0 simulerade positiva protokollresultat härledda enbart från proveniens**, **0 falska PASS-rapporter**.

Kör alla Python-regressioner, verklig DIRECT_HTTP-Chromium, `npm run check`, ES-importgrafstest, negativ HTTP/ZIP/OOXML/ODF-testning, filbytes/SHA och konflikttester på varje nödvändig etapplämning. Varje PR måste ha obligatorisk CI SUCCESS på exakt HEAD och verifierad main-CI efter merge enligt AGENTS.

## 11. Slutdefinition, kontroller och ändringspolicy

Etapp 4 är klar först när: 4A:s trygga källinspektion; 4B:s v1.4 med kompletta avkodade källceller och proveniens; 4C:s samtliga sju explicit valda dokumentroller och korrekta relationer; samt 4D:s profilåteranvändning och slutliga UI alla är implementerade och verifierade. Inga andra separata planeringsdokument behövs. Utför arbetet i etappordning, en PR åt gången från verifierad main, med befintlig mergepolicy.

Vid en verifierad motsägelse eller verklig ny källbegränsning: avbryt den drabbade kodvägen, formulera ett reproducerbart negativt test och **ändra denna enda versionshanterade kontraktsfil** efter teknisk granskning. Skapa inte konkurrerande "Masterprompt"-dokument. Att kontraktet är heltäckande för beslutad scope betyder inte att framtida helt nya dokumenttyper eller oförutsedda filkonstruktioner kan stödjas utan uttryckligt nytt beslut; de ska avvisas korrekt.

**Detta är hela den beslutade målarkitekturen för etapp 4A–4D, inte enbart ett förarbete till 4A.**
