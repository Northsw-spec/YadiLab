# RELEASE-GATES — verifierat Cisco-dokumenterat scope och därefter verifierade förbättringar

**Bindande metod:** [PT-DOC-BASELINE-001](PT_DOCUMENTATION_BASELINE_POLICY.md). En installerad Cisco Packet Tracer-binär, binär-hash eller head-to-head-körning är **FRIVILLIG**, aldrig R0–R14- eller G0–G6-blockerare. Alla G0–G6 är NOT_RUN per 2026-11-26. **Funktionsmålet sänks inte.**

**Repo readiness:** [REPO-READINESS-001](REPO_READINESS_AUDIT.md): GitHub ruleset `main` har `enforcement=active` och `governance-contracts` required vid senare faktisk kontroll 2026-11-26. Negativt enforcementtest mot direktpush/röd PR är ännu NOT_RUN. Riktig runtime-/UI-/import-CI och verifierat branchskydd, riktig runtime-/UI-/import-CI, laglig fildokumentation och säker release är egna R0/G5-blockerare. Dokument- och governance-SUCCESS räcker inte.

**Varumärkesregel:** [BRAND-IDENTITY-001](BRAND_IDENTITY_CONTRACT.md) – ett enda deklarerat visningsnamn; alla framtida UI/desktop/exportnamn visas från denna källa. Tillverkarnamn såsom Cisco är tillåtna och behövs för korrekt utrustning/CLI.

### G0 – dokumentationsinventering

Samtliga **publicerade och faktiskt källbelagda** Cisco Packet Tracer-familjer/enhets- och modulprofiler/CLI-kommandon, protokoll, UI, filformat, undervisningsflöden, IoT/OT, Multiuser/ExApps inventerade med URL och käll-/versionsstatus. Alla upptäckta underfall får stabilt ID, positiva/negativa testkrav, dokumentägargranskning och spårbar evidens i [PT-scope-registret](requirements/pt_scope.json). Inga okända **kända dokumentationsluckor** accepteras som COMPLETE. Odokumenterade PT-beenden är UNKNOWN, inte föremål för gissade paritetslöften. **Ingen PT-binär behövs.**

### G1 – oberoende standardkorrekthet

Varje deklarerat protokoll/variant har korrekt standard/errata, byteparser/serializer, tillståndsmaskin, timers och oberoende positiva/negativa/motsägande fall, inga kända allvarliga falska paketleveranser.

### G2 – en enda integrerad nätverksmotor

En enda scenario-runtime/klocka, autentiska TX/serialization/propagation/RX/drop-events, verkliga device/port/link-profiles, konfigurations-CLI och GUI med samma ägd runtime-sanning, Save/Open/ELK-beteende från oberoende backend.

### G3 – verifierat publicerat PT-funktionsomfång

Alla **upptäckta källbelagda** enheter, kommandon, physical/logical, PDU/OSI, Activity Wizard, scoring, IoT/OT, scripting, Multiuser, ExApps, säkerhet och laglig interoperabilitet har egna godkända native-integrations-/funktionstester. Inga öppna SOURCE_UNCERTAIN/NOT_IMPLEMENTED/BLOCKED för funktioner som ingår i den påstådda fullständiga dokumentationspariteten. Här finns ingen skyldighet att köra PT.

### G4 – juridik och säkerhet

Inga otillåtna Cisco-binära delar eller osäkra skript, sandbox med resursgränser, opt-in autentiserad Multiuser, inga reala PLC/NIC-side effects, säker import, verkligt Save/Open/SHA och rollback. Proprietära format som inte kan lagligen implementeras kvarstår BLOCKED_LEGAL_OR_SPEC och blockerar omfattande paritetsanspråk.

### G5 – Linux-produkt och Legacy-UI

Fullt installerbar och återställbar Linux-app; Legacy-UI-fidelitet enligt [UI-kontraktet](LEGACY_UI_FIDELITY_CONTRACT.md) och [55 UI-seedfall](requirements/legacy_ui_manifest.json), riktig Chromium/ELK/Import/Data/Network/CLI/IoT/OT CI samt security test på exakt HEAD, oberoende code/protocol review, inga blockerande fel och **aktivt verifierat** main-ruleset med Required checks.

### G6 – ärligt verifierad förbättring

Förregistrerade tester av standardkorrekthet, simuleringsprecision, kausala felorsaker, dokumentimport, pakettrace, säkerhet, stabilitet och pedagogisk användbarhet. Visa förbättring mot **versionerade publicerade Cisco-begränsningar och/eller jämförbara tredjepartsdata eller genom egna kontrollerade användartester**, där det är relevant. Om någon påstår "snabbare än Packet Tracer" eller "bättre i ALLT" krävs faktisk jämförbar mätning för de specifika domänerna; den kan inte konstrueras ur en hjälptext. Bättre inlärningsutfall kräver verklig frivillig människostudie.

## Tillåtna statustyper

- **IN_PROGRESS:** en gate saknar evidens.
- **DOCUMENTED_PT_SCOPE_VERIFIED:** G0–G5 PASS, samtliga kända officiellt dokumenterade PT-underfall implementerade och oberoende verifierade. Betyder INTE att programmen körts mot varandra.
- **EXCEEDS_DOCUMENTED_PT_SCOPE:** G0–G6 PASS för de explicit påstådda förbättringsområdena, med faktiska bevis; direkt uppmätt universell överlägsenhet får INTE påstås utan direkt jämförelsedata.
- **BLOCKED:** funktion med saknad rättslig/specifikationsmässig väg; aldrig ett dolt undantag.

Krav på Packet Tracer-binär, installations-SHA eller PT_RUN_PASS finns **inte** längre. Om ny Cisco-dokumentation publiceras inventeras nya featurefall och status öppnas igen. Det är fortsatt förbjudet att använda grön governance-CI som bevis för simuleringsfunktion.
