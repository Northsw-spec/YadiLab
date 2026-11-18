# YadiLab – kontrakt för källtrogen dokumentationsläsning och import

**Dokumentversion:** 1.0  
**Beslutat läge:** Arkitektur fastställd; etapp 4A är nästa implementation. Etapp 4B–4D är spärrade av uttryckliga verifieringsgrindar nedan.  
**Kodbas:** `Northsw-spec/YadiLab`, referens-`main` `17acb51c8c64c3b4b7a1026514cb8b0a2177a127`.  
**Omfattning:** Källdata från tabellbaserad nätverksdokumentation. Detta är det normativa kontraktet för etapp 4, inte en rapport om redan implementerade funktioner.

## 1. Prioritet och ansvar

1. `AGENTS.md` och `docs/MASTERPROMPT.md` gäller övergripande. För **etapp 4** anger detta dokument det detaljerade, versionshanterade funktionskontraktet.
2. Verifierad källkod och senaste uttryckliga användarinstruktion har företräde framför gammal statusinformation i dokumentation och chattar.
3. Varje utvecklingsuppdrag avser exakt **en** av etapperna nedan. Börja alltid med 4A. Ett godkänt 4A är inte behörighet att på eget initiativ skapa 4B-, 4C- eller 4D-kod.
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
- Gränser per request: högst 8 MiB CSV; högst 5 MiB komprimerad XLSX/ODS; högst 12 MiB totalt expanderat arkiv, högst 5 MiB per XML-del; högst 24 ZIP-poster för XLSX och 10 för ODS. Högst 8 kalkylblad, 5001 fysiska rader per blad och 64 fysiska kolumner. Ovanför gränserna: deterministisk HTTP 422 utan partiellt resultat.
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

## 5. Etapp 4B – explicit enhetsmappning (egen framtida PR)

4B kan startas **först efter** 4A är mergad med main-CI PASS och användaren uttryckligen godkänt ett separat förslagskontrakt baserat på minst två verkliga, anonymiserade och strukturellt olika inventeringsblad. Kontraktet ska specificera källkolumnernas faktiska betydelse och vilka fält som kan representeras i schema 1.3.

4B ska då bygga:
- en versionsbunden mappning med `sourceSha256`, `tableId`, uttryckligt `headerRow`, exakt källkolumn och semantisk roll `device_inventory`;
- en känd och begränsad uppsättning mål: nodens `id`, `label`, `kind` samt uttryckligen representerbar dokumentation; enhets-`kind` måste uttryckligen vara en av de fyra stödda värdena eller styras av ett separat, användarbekräftat värdemappningskontrakt;
- verifiering av unika, giltiga käll-ID:n utan automatisk slugifiering, konvertering eller hopslagning;
- deterministiska presentations-`x/y` endast där de behövs för renderingen, explicit märkta som genererade presentationsvärden, aldrig källfakta;
- en kandidat som förblir blockerad när ett befolkat relevant källfält är omappat eller inte kan representeras i nuvarande modell;
- full `validate_project()`-kontroll och exakt redovisade källreferenser innan befintligt användargodkänt arbetsytebyte.

**Kvalitetsgrind:** Ingen implementerad 4B-profil får namnges efter en produkt, konsultorganisation eller “branschstandard” utan en konkret offentligt dokumenterad och versionslåst exportdefinition eller användartillhandahållna verkliga fixturer. Data som modellen inte kan representera ska avvisas; en utökning av kanoniskt schema kräver separat beslutad versionsmigration och roundtrip-tester före importen.

## 6. Etapp 4C – explicita port- och kabelrelationer (egen framtida PR)

4C kan startas endast efter verifierad 4B och ett godkänt kontrakt med riktiga, anonymiserade port-/kabelregister.

4C ska:
- bygga portobjekt bara från explicit identifierad enhet och explicit port-ID;
- ta värden för `enabled`, IPv4/CIDR, MAC, VLAN och statiska routes endast från uttryckliga fält med korrekt semantik; annars ska den berörda kandidaten blockeras när målkontraktet kräver ett sådant värde;
- skapa en fysisk länk endast från ett explicit kabel-/länkpåstående med två identifierade och existerande portändpunkter och ett explicit unikt länk-ID;
- avvisa okända eller dubbla port-ID:n, inkompatibla VLAN-värden, tvetydiga grannar, portbeskrivningar utan två ändpunkter, motstridiga uppgifter och länkar som bryter `validate_project()`;
- inte konvertera LLDP, management-IP, subnät, routingtabell, närhet eller topologisk placering direkt till fysiska kablar;
- verifiera identitetsbevarande, referenser och roundtrip via Save/Open med verklig `.yadilab` och oförändrade källfiler.

## 7. Etapp 4D – evidensbaserad profilutökning (egen framtida PR eller granskning)

Efter 4B/4C ska ett versionsbundet corpus med flera oberoende verkliga dokumentationsstrukturer användas som regressionsevidens. Varje källa behöver laglig behörighet, anonymisering och en manuellt granskad facitlista.

Mät och redovisa på corpusnivå:
- antal dokument/bladscheman faktiskt testade;
- antal korrekta respektive avvisade representerbara fakta;
- antal kvarstående/omappade källfält och uttryckliga användarbeslut;
- antal falska eller implicit skapade fysiska länkar (**acceptanskrav: noll**);
- alla verkliga Save/Open-roundtripfel, felaktiga SHA-förändringar och manuella mappningssteg.

Inga generella marknadsandelar, procentsatser om kompatibilitet eller påstådd buggreduktion får rapporteras utan publicerat råunderlag, testpopulation och beräkningsmetod.

## 8. Leveransregler för varje PR

- En aktiv branch/PR åt gången, från senast verifierade `main`.
- Små sammanhängande ändringar; återanvänd befintliga kod- och domänkontrakt. Ingen andra kanonisk nätverksmodell, ingen parallell simuleringmotor och ingen autosave.
- Negativa tester är förstklassiga acceptanskriterier. Testdata ska vara äkta CSV/OOXML/ODF-bytes och faktiska användarhandlingar över lokal HTTP.
- Rapportera vilka funktioner som faktiskt är implementerade och vad som återstår; dölja inte PENDING eller blockerande begränsningar.
- Följ endast stående mergegates i `AGENTS.md`; dokumentstatus är inte CI-evidens.

**Starta kodningen med etapp 4A.** Detta dokument specificerar senare mål men ger inte tillstånd att implementera dem samtidigt eller fylla dataluckor genom antaganden.
