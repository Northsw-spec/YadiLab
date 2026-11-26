# LEGACY-UI-FIDELITY-001 — obligatorisk visuell och funktionell paritet med YadiLab_legacy

**Normativt användarbeslut 2026-11-26:** Nya Linux-YadiLab **SKA SE UT OCH FUNGERA SOM** [YadiLab_legacy](https://github.com/Northsw-spec/YadiLab_legacy). Det är inte längre en lös "inspirationsreferens". **Auktoritativ version låst till [legacy commit aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80).** Källkoden/HTML/CSS/ELK/UI-funktionerna har lästs och registrerats; den körda visuella browser-baslinjen och screenshots har **inte** samlats in ännu. UI_REFERENCE_SOURCE_AVAILABLE, RENDERED_GOLDENS_NOT_CAPTURED, UI_PARITY_NOT_VERIFIED. Inga påståenden om pixelperfekt jämförelse före Chromium baseline.

## 1. Det faktiska Legacy-utseendet, inte ett påhittat GUI

Referens: `web/index.html`, `web/styles.css`, `web/ui/workspace-panels.js`, `web/canvas.js`.

- **Mörkt tema som standard** med originalets färgtoken: --bg #0b1420, --panel #121e2d, --panel2 #162537, --surface #1c3045, --line #2b3d52, --text #e7edf5, --muted #9db1c8, --accent #5ad3bd, --blue #78aef5, --orange #fac886, --red #fa8890. Originalets Inter/system-sans, kontroller, täthet, card/toolbar-utseende och språk/etiketter är startkrav. Designa inte en generisk "ny modern dashboard" som ersätter dessa.
- **På breda skärmar (min-width 951px)** ligger **topologicanvasen överst i HEL bredd**. Under den ligger **Inventering och Sparade projekt/mallar till vänster**, **Inspektör och diagnostik till höger**, i horisontellt ordnade, utfällbara `details.dropdown-card`. Detta är viktigare än den äldre bakomliggande `.workspace`-trekolumnsregeln: den senare överskuggas i aktuellt CSS för desktop. Bevara `toggle-dropdowns` (expandera/kollapsa) och alla ursprungliga panelgrupper.
- Topbar (minst 76px) med YadiLab-branding, Nytt, Strikt import, Extern dokumentation, Förhandsgranska tabeller, Exportera JSON/XLSX/ODS och Spara projekt. Underheader med projekt-breadcrumb/Save-indikator. Respektive knappar ska utföra exakt observerbar workflow, inte bara finnas i DOM.
- Centralt `svg#topology` med enheter, portar, zoner, färgade kablar, länk-/nodmarkering, dragging, click-two-ports connection, zoom/pan/fit, popup/context actions, import/simulation overlay. Den ursprungliga nodformen är ungefär 202 enheter bred, header 66 och port-rad 23 i canvas.js; dessa är **render-referensvärden**, inte absolut framtida geometribegränsning för fler Packet Tracer-enheter.
- Anpassning för smala skärmar enligt faktiskt CSS (<=950 och <=650px) och parvisa From/To indata. Ingen ny specifik accessibility/keyboard-only-paritetsutveckling krävs enligt användarbeslutet.

## 2. Faktiska funktionella Legacy-flöden

**Inventering/Builder:** lägg till/ändra enhet, portar och zoner, visa listor och räknare, skapa och välja verkliga explicit ändpunktskablar, nodflytt, kabelfel, inspector, saved-project chooser, öppna, nytt, Save och återställ utan tysta effekter.

**Import:** `#preview-dialog` tabellförhandsvisning; `#external-dialog` i fyra synliga huvudsteg: **1 Originalfiler**, **2 Explicita mappningsvyer**, **3 Vald kandidat**, **4 Historisk proveniens**; original-cell/sheet/rad-paginering, ValueMaps, reusable MappingProfiles med export/bind, radunika beslut/exkludering, planfingerprint/diagnostik, candidate preview, explicit Apply, source bundle export och historisk referens/återanslutning. Strikt CSV/XLSX/ODS plus nya format implementeras UTAN att ändra det ursprungliga flödets igenkännbara utseende.

**Layout:** den nuvarande legacy-versionen använder lokalt vendored elkjs 0.13.0 och en **tvåpass Worker-layout** med FIXED_POS-portgeometri, ortogonala kabelstigar, strikt endpointvalidering, reject vid stale/timeout/fel. Efter accepterad strikt dokumentimport görs första layouten **automatiskt utan extra preview-klick**, men **inte auto-Save**. Vid frivillig ny layout gäller Föreslå ELK-layout -> Preview -> Tillämpa placering/Avbryt. Endast användarbekräftad nod X/Y blir dirty, transient ELK-rutt sparas inte; öppnat projekt bevarar faktiska kablar och projektdata. **Notera källskillnad:** äldre kontrakt nämner aspectRatio 1.6, men nuvarande `web/features/layout/elk.js` kod har `elk.aspectRatio: '3'`. Använd **versionslåst exekverbar kod** före äldre dokument när de motsäger varandra, och verifiera i browser.

**Inspektör/diagnostik:** grafväg, ARP, DHCP Discover/Offer, DORA med lease/renew/advance/fault, stegvis nätverkssession, routingtabell, IPv4-spår, ICMP Echo/packet journey, guidad felinjektion/återställning, hypotes/test/observation/motbevis och protokolllektioner. **Samma användarflöde och terminologi behålls**, men alla nya nätverksresultat måste komma från den NYA självständiga DES-motorn. Det är förbjudet att återanvända gamla Ethernet/ARP/DHCP/IPv4-simulatorer för att "snabbt" få igenom UI-test.

**Lokal auth:** samma förståeliga upplåsningsdialog för åtkomstnyckel, inget hemligt token i URL/disk, inga UI-utlovade skydd utan verklig backendpolicy. Ny Linux-desktop-lösning får modernare, säker implementation bakom identiskt begripligt flöde.

## 3. Auktoritativa källfiler och jämförbara tester

- `web/index.html`, `web/styles.css`, `web/ui/workspace-panels.js` = DOM, strukturell layout, ordning, teman, etiketter. **Visuell baslinje när riktig Chromium körs**.
- `web/canvas.js`, `web/features/layout/elk.js`, `docs/ELK_LAYOUT_CONTRACT.md` = kabelportgeometri, tvåpasslayout, automatisk post-import och manuell preview/cancel.
- `web/features/projects/import-review.js`, `mapping-profiles.js`, `workspace-revisions.js` = explicit import- och stale-felsäkerhet.
- `web/features/sessions/simulation-session.js`, `web/app.js`, `web/index.html` = synliga session/diagnosflöden (observed contract), inte protokollfacit.
- `tests/browser_elk_layout.py`, `tests/browser_elk_import.py`, `tests/browser_smoke.py`, `tests/session_stale_responses_test.mjs`, `tests/workspace_panels_test.mjs`, `tests/mapping_profiles_test.mjs` = **testupplägg att studera**, inte automatiskt passerade tester för ny kod.

[Maskinläsbar spårbarhetsmatris – 55 obligatoriska UX-fall](requirements/legacy_ui_manifest.json). Den är **ett startregister**, inte fullständigt inventerad visuell baslinje. Hela källträdet och varje verklig UI-funktion ska revideras innan slutligt UI_PARITY.

## 4. Praktisk, objektiv acceptans av "samma UI"

1. Starta *legacy på exakt SHA aac82926ced3dbf4cac09242530762ac3da1fe80* i en kontrollerad Linux-browsermiljö (kör inte gamla data/obetrodda imports okontrollerat). Frys foton av blank state, demo, vald enhet/port, kablar, paneler kollapsade/öppna, import steg 1–4, felhantering, ELK auto/preview, Save/Open, packet replay och guidad övning. Registrera Chromiumversion, fonts, skärm/DPR, CSS/HTML-fingerprint och scenario-fixture. Riktiga screenshot golden-filer kan lagras i framtida tests/assets med tydlig licens/proveniens.
2. Starta nya YadiLab på samma upplösningar/DPR och testfixturer, först 1366x768 och 1920x1080, sedan smal responsiv viewport. Jämför **komponentpositioner, tema, panelordning, interaktionsförlopp och renderade endpoints**, inte bara pixel-diff utan tolerans för font/renderavvikelser.
3. Varje obligatoriskt UI-namn och synligt flöde får en status: NOT_IMPLEMENTED, PARTIAL, BEHAVIOR_VERIFIED, VISUAL_VERIFIED, UI_PARITY_VERIFIED. För slutstatus krävs riktiga E2E-interaktioner och screenshots på identiska fixtures/versioner. Ett nytt, utökat PT-gränssnitt får addera paneler/kommandon, men aldrig tyst omplacera eller radera befintliga legacy-flöden.
4. Stale async requests/Worker-responses måste ignoreras efter workspace/versionbyte. En import, preview eller layout får inte göra auto-Save, och en felsimulering får inte ändra nätverksdokumentation eller ackumulera falska "success".
5. Systemet måste kunna växa med Cisco Packet Tracers hela featurebredd (CLI, PDU/OSI, Physical Workspace, IoT/OT, Activity Wizard etc) genom **nya sammanhängande ytor inom samma design**, utan att den grundläggande legacy-UI-upplevelsen försvinner.

## 5. Regler för återanvändning och förbud

- **Tillåtet:** hämta färg-/typografi-/spacing-/layout-/DOM-fakta, funktionsnamn, användarresor och tester från de faktiskt versionslåsta legacy-filerna; rena, licensgranskade presentationsassets kan eventuellt återanvändas efter isoleringsbevis. Syftet är att se ut och fungera som legacy, inte att skapa en ny generisk dashboard.
- **Ej tillåtet som ny enginekod:** alla gamla simulation-/DHCP-/Ethernet-/ARP-/IPv4-/routing-/sessionmotorer, logik som beräknar topologisk reachability, gammal time/state, implicit project validator eller security bypass. UI-tester får ALDRIG bli enda orakel för korrekt nätverksforwarding.
- **Resultatstatus idag:** Legacy-referensens Git-SHA och UI-källfiler är VERIFIERADE. Legacy screenshot- och runtime-beteende på en jämförbar Linuxmiljö är **NOT_RUN**. Nya YadiLab UI är **NOT_IMPLEMENTED**. Behåll dessa tre statusnivåer separata.

Detta dokument har företräde över formuleringar som säger att det tidigare UI:t saknar källreferens, endast är "inspiration", eller måste vänta på en separat ZIP. ZIP kan fortfarande användas för offline/browser-test, men Git-repot ovan är redan en autentiserad, versionslåst källreferens.
