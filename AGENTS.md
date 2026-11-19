# Utvecklingskontrakt för nätverksapplikationen

## Permanent Masterprompt

**Läs [docs/MASTERPROMPT.md](docs/MASTERPROMPT.md) före varje utvecklingsetapp.** Den är projektets långsiktiga utvecklingsdirektiv fram till användarens slutgodkännande. Denna AGENTS-fil anger korta, operativa regler; den fullständiga målbilden, prioriteringen, acceptanskriterierna och rapporteringskontraktet finns i Masterprompten. Vid konflikt ska den senaste uttryckliga användarinstruktionen följas och aktuell källkod/CI kontrolleras.

## Projektgräns

- Detta är en **ny, fristående implementation**, inte en fork eller ompaketering av äldre produktkod.
- Kopiera inte källfiler, komponentträd, bakåtkompatibilitetslager eller testkod från äldre projekt utan ett separat uttryckligt beslut baserat på verifierad funktionalitet.
- Undvik parallella arkitekturer. En kanonisk dokumentationsmodell och en presentationsväg.
- Körbar nytta prioriteras över mängden kod, projektbeteckningar eller antalet passerade kontroller.

- **Produktnamn:** `APP_NAME` i `network_core/config.py` är den enda deklarationen av appens visningsnamn. Repositorynamnet är inte appnamnet. HTML, fönstertitel, loggar, hälsosvar och terminal måste härleda namnet härifrån. Alla klass-, funktions-, paket- och filnamn måste vara generiska. Ingen gammal produktidentitet får förekomma i källtext, dokumentation eller testfixturer utöver den bibehållna, tekniska filändelsen för projektformatet. `tests/test_naming_contract.py` måste passera.

## Oförhandlingsbara funktionella invariants

1. **Inga implicita länkar:** IP-adresser, default gateways, geografisk zon, nodposition och liknande får aldrig skapa en kabel, router eller enhet.
2. **Förlustfri eller avvisad import:** okända eller ogiltiga data får inte tyst försvinna; avvisa hellre formatet med ett begripligt fel.
3. **Äkta identiteter:** noder, portar, zoner och länkar ska överleva Save/Open med exakt samma identifierare och deklarerade ändpunkter.
4. **Begränsa sanningsanspråk:** topologisk grafväg är inte verklig Layer-2-/Layer-3-reachability. Bygg aldrig en generisk ping-PASS ovanpå BFS.
5. **Avgränsa nya funktioner:** lägg till en beteenderegel och ett negativt test före en ny integrationsväg.
6. **Beständighet:** skriv bara efter användarens uttryckliga Save. Ingen autosave, dold overwrite eller falsk verifiering av webbläsarnedladdning.
7. **Ingen skönmålning i tester:** riktiga negativa tester, riktig fil på disk och omstart ska skiljas från en simulerad filväljare eller syntetisk stub.

## Scope och process

- Fokus är korrekt funktionalitet, begripliga användarflöden och borttagning av onödig eller felaktig kod. Starta inte pentest eller separata säkerhetshärdningsprojekt utan användarens begäran.
- Gör så små verifierbara ändringar som möjligt. Ha bara en aktiv utvecklingsgren/PR.
- Kör `python3 -m unittest discover -s tests -p 'test_*.py' -v`, `npm run check` och `python3 tests/browser_smoke.py` före kodleverans när miljön tillåter.
- Om webbläsaren blockerar lokal HTTP kan browser_smoke använda sin uttryckligt märkta bro, men det är **inte** bevis för normal direkt HTTP i den miljön.
- **Stående användargodkännande för automatisk merge:** Merga varje färdig och avgränsad PR automatiskt via GitHubs normala mergeflöde när den exakta PR-HEAD har PASS på alla obligatoriska CI-kontroller, negativa/funktionella tester är verifierade, PR är konfliktfri och mergebar, inga blockerande reviews finns och `main` fortfarande är förväntad bas. Använd squash när lämpligt. Begär inte nytt mergegodkännande per PR. **Merga aldrig** vid FAIL/PENDING/okänd CI-status, konflikter, oklara ändringar, obehörighet eller när branchskydd skulle behöva kringgås. Rapportera hindret i stället. Automatiken innebär ett beslut vid varje körning, inte ett påstående om obevakad bakgrundskörning.

## Styrd importspecificering för etapp 4

Vid arbete med dokumentationsläsning eller import måste `docs/IMPORT_SOURCE_CONTRACT.md` läsas före design, kodning, PR och slutsatser. Etapp 4A är nästa godkända byggsteg; senare steg har uttryckliga startgrindar. Dokumentet reglerar **hur** okända externa tabeller ska inspekteras och när någon nätverksmappning får byggas. Chatthypoteser och forskningsuppsatser är inte importkontrakt. Nuvarande stödda CSV/XLSX/ODS-format förblir oförändrade under 4A.

## Explicit CSV-import

- Använd endast `network_core/csv_import.py` för de namngivna tabellerna Devices/Interfaces/Links/Zones. Ingen heuristisk import och ingen implicit kabelskapning.
- Validera hela importen före användarens uttryckliga godkännande att ersätta arbetsytan; ingen autosave.
- Funktionella negativa tester ska omfatta saknade, dubblerade, okända och inkonsekventa uppgifter. Verifiera också verklig browser-import och Save/Open.
