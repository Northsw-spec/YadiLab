# REPO-READINESS-001 — revisionskontroll av nya simulatorprojektet

**Nyare användarbeslut och faktisk GitHub-status (2026-11-26):** [PT-DOC-BASELINE-001](PT_DOCUMENTATION_BASELINE_POLICY.md) upphäver behovet av installerad Cisco Packet Tracer-binär, obligatorisk PT_RUN eller build-checksum. Cisco officiella versionerade publikationer + fristående standard-/native-tester är obligatoriska. **GitHub ruleset `main` (28193830) är nu `enforcement=active`, med `governance-contracts` som required check.** Detta har verifierats via aktuellt GitHub API. Negativa avvisningsprov för direktpush och röd PR har ännu inte rapporterats. `.gitignore` finns.


**Revisionsdatum:** 2026-11-26. **Granskad main:** `5c55be0a5c33f73106353db9f895db07c98b5c68`. **Typ:** dokumenterad arkitektur-/repository-audit, INTE implementationstest och INTE en andra roadmap.

## Beslut

**GO för den första isolerade R1-POC:n** när nödvändiga R1-kontrakt och oberoende tester byggs. **NO-GO för påståenden om full funktion, full Cisco Packet Tracer-paritet, bättre kvalitet eller produktionsrelease.** Det finns ännu INGEN nätverksmotor, ingen frontend, ingen Linux-appinstallation och inga importerade Excel-/CSV-fixturer som körts i det nya repot. Endast `core/identity.py`, `core/metadata.py`, styrdokument och governance-tester är nu verklig kod.

## Verifierad inventering

| Kontroll | Resultat | Källa/bevis |
|---|---|---|
| Rent nytt repo | **PASS för legacy-isolering** | Git-trädet på granskad main: ingen gammal network runtime eller frontend kod, endast neutral metadata-kod och styrning |
| Mastermandat | **PASS på kravformulering** | `MASTERPROMPT.md`, `AGENTS.md`, `docs/PRODUCT_SCOPE.md`: alla PT-funktioner, Linux-only; ingen ny keyboard-only/accessibility-paritet |
| Enda plan och mål | **PASS på struktur** | `docs/ROADMAP.md` R0–R14, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` |
| Nya engine | **NOT_IMPLEMENTED** | Ingen EventKernel, packet data path, link actor, CLI, port/state machine existerar än |
| Packet Tracer-målbredd | **INITIAL INVENTORY ONLY** | 36 REQUIRED-familjer / 108 initiala fall i `docs/requirements/pt_scope.json`; `inventory_complete=false`, full källgranskad Cisco-enhets-/CLI-dokumentation och underfallsinventering återstår; ingen Packet Tracer-binär behövs |
| Legacy-UI | **SOURCE_VERIFIED, RUNTIME_NOT_RUN** | Låst `Northsw-spec/YadiLab_legacy` @ `aac82926ced3dbf4cac09242530762ac3da1fe80`; 55 UI-case seeds, inga goldens på ny UI |
| Importformat | **REQUIREMENT_ONLY** | `docs/IMPORT_CONTRACT.md`; inga verkliga XLS/XLSB/ODS/CSV-parsertester här |
| Namnbyte | **PARTIAL_CODE_TESTED** | Endast `core/identity.py::APP_DISPLAY_NAME` och `core/metadata.py` fungerar; ännu ingen UI/launcher/installer att end-to-end-verifiera |
| Standard-/CI-verifiering | **GOVERNANCE ONLY** | En GitHub Actions-jobb `governance-contracts`; senast passerade main, men testar inte motor, CLI, webbläsare, Excel, packager, fuzz eller Packet Tracer |
| GitHub regler | **RULESET ACTIVE; NEGATIVE ENFORCEMENT TEST NOT_RUN** | `main`-ruleset 28193830 har `enforcement=active` med `governance-contracts` som required check, PR-regel och non-fast-forward/deletion-skydd. Bekräftat mot GitHub API 2026-11-26. Riktade avvisningsprov ej dokumenterade. |
| Repo-säkerhet | **PARTIAL** | Publikt repo, `.gitignore` och hygiene-tests finns efter PR #4, men ingen `LICENSE`-fil eller uttryckligt licensbeslut; aldrig lägga hemligheter/proprietär binär/kunddata i repository |
| Juridisk kompatibilitet | **OPEN/BLOCKED** | PKT/PKA/PKZ och vissa Cisco-specifika förlopp kräver faktiska lagliga specifikationer/interop-evidens |

## Högsta återstående risker, prioriterat

**P0 — kontrollera faktisk enforcement mot negativa fall.** Ruleset `main` (28193830) har nu `enforcement=active` och required `governance-contracts`. Vid avsedd säker testmetod, verifiera att direktpush och en PR med underkänd Required check stoppas; gör inte en riskabel test på produktionsprojekt utan kontrollerad metod. Allt arbete ska redan nu ske på PR, aldrig med bypass/force-push. När R1-motorjobb tillkommer måste de läggas till som Required. Detta är ingen längre blockerare för ett isolerat R1-POC men policytesterna är inte färdigutvärderade.

**P0 — verkligt testbart motorgrundkontrakt.** R1-1 och R1-2 måste implementera Device/Port/Link/Config/CLI och kernel med tid, eventkedja, determinism samt negativa gränser. Integrera inte ett nytt protokoll för att "få demo" innan detta passerat oberoende oracle/2 processstarter. Ingen gammal nätverksmotor eller parallell "temporary" network path.

**P0 — komplett konkurrensbaslinje före paritetsanspråk.** Inventera aktuell **officiell Cisco-dokumentation och versionssatta källor** för alla device/module/CLI/protocol/UI/OT/IoT/service/file-varianter; en installerad eller hashad PT-binär är **inte ett krav** enligt [PT-DOC-BASELINE-001](PT_DOCUMENTATION_BASELINE_POLICY.md). De 108 startfallen är **inte** "alla features". Upptäckta nya fall måste öka nämnaren i registret. Cisco-approximationer separeras från standardkorrekthet och juridiska hinder får inte hemligt exkluderas.

**P1 — fotografera/kör Legacy-UI.** Kör versionslåst Legacy i verklig Chromium-miljö och spara jämförbara fixture/screenshots + DOM/portgeometri före R3 påstår "samma UI". Bevara 55 seedflöden inklusive importer/ELK/Builder/sessions; inga gamla sessionsmotorer som nätverksimplementering.

**P1 — riktiga import-/projektfixturer.** R2 måste bevisa CSV/TSV/XLS/XLSX/XLSM/XLSB/ODS och övriga format i sitt deklarerade stödomfång, byte-for-byte proveniens, konflikter, no fabricated cables, Save/Open/SHA/recovery. Library-marknadsföring bevisar inte vår adapter.

**P1 — riktig Linux paketering och prestanda.** R0 behöver license/spike för Qt/Tauri/browser-shell, Wayland/X11, dependency pins, testade 5/50/500-device arbetslaster, resource ceilings och ett objektivt Python/Rust-beslut. Dokumenterade mål är inte mätresultat.

**P1 — licens-/öppenkodsbeslut.** Repon är publik och saknar LICENSE. Det innebär inte automatiskt att andra har öppenkodslicens att återanvända koden. Projektägaren bör uttryckligen välja licens eller dokumentera att koden tills vidare är all-rights-reserved; inga tredjeparts- eller Cisco-/kundfiler ska committas utan kontrollerade rättigheter. Licensen får inte hittas på av kodagenten.

**P1 — fortsatt repo-hygien.** `.gitignore` och negativa hygienkontroller finns redan. För framtida testfixturer gäller syntetiska/saniterade filer, strikta rättigheter och ingen incheckning av kunddata eller Cisco-binärer; utöka ignore-regler först med faktiskt behov.

## Vad som faktiskt skyddas redan nu

- Hårt namnscope: `YadiLab`-strängen endast i `core/identity.py` som koddeklaration; `YL` som källkods-prefix förbjudet. Vendor-specifika namn Cisco, Juniper m.fl. tillåtna.
- Kravscope: Linux-only, inga särskilda nya keyboard-only/accessibilitykrav; alla andra Packet Tracer-scopefamiljer REQUIRED utan tyst undantag.
- Historisk UI-källreferens låst till exakt SHA; 55 obligatoriska UX-startfall; skärmbildsresultat är ännu NOT_VERIFIED.
- Negativa mutationsprov mot falska featurepass, falskt full-parity-claim och falsk branding. Varken mutationstester eller grönt governance-CI är ett bevis på programvarufunktion.

## Definition av "repo klart för kodstart" och "redo att kalla komplett"

- **Klar för R1-POC:** syfte och interfaces tydliga, en enda plan, ägare och kö för nästa kort, grundläggande governance/tester gröna, dokumenterat aktivt ruleset (28193830) och fortsatt ändring endast via PR, med framtida negativt enforcementtest.
- **Klar för produktionsutveckling i större skala:** P0 main ruleset aktiverad/verifierad, real packet tests i Required CI, versionslåsta beroenden, känd data- och säkerhetsmodell, UI-fixturer och schema-conformance.
- **Klar att hävda "allt Packet Tracer":** G0–G5 i `docs/RELEASE_GATES.md` med full källgranskad Cisco-dokumentationsnämnare, egen verklig native-test-evidens och standardorakel (riktig PT-binär frivillig), inga okända/blockerade fall (utom uttryckliga scopeundantag).
- **Klar att hävda "bättre än Packet Tracer":** dessutom G6 med i förväg låsta oberoende mätningar. En universell direktjämförelse kräver dock ett jämförbart referensresultat; kan inte påstås på enbart Cisco-help. Ett generiskt Packet Tracer-liknande GUI eller statisk ping är inte sådan evidens.

**Ingen utvecklingsplan, AI-modell eller Github-README kan garantera från början att en programvara senare kan utföra varje proprietär Cisco-funktion.** Rapportera blockerare tidigt; ändra aldrig målets omfattning utan användarbeslut.
