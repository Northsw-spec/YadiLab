# CI-001 — verifieringsgränser vid det helt nya repot

**Nytt referensbeslut:** [PT-DOC-BASELINE-001](PT_DOCUMENTATION_BASELINE_POLICY.md). Governance-kontrollen får INTE kräva installerad Cisco PT-binär, PT_RUN_PASS eller binär-checksum i PT-scope-registrets G0–G6. I stället testar den att källgranskade Cisco-dokumentations-ID, source evidence och verkliga native CI-evidens finns innan status kan höjas. Det är inte verifierat att någon motor är implementerad.


**Verifierad repo-status 2026-11-26:** GitHub API visar ruleset `main` (id 28193830), `enforcement=active`, branch target default main, och `governance-contracts` konfigurerad som required check. Pull-request-regel, förbud mot branch deletion/non-fast-forward och linear history är definierade. Detta är en verifierad policykonfiguration, INTE ett dokumenterat avvisningsprov för direktpush/röd PR. Alla nya motor-/browser-/import-checks ska läggas till bland Required när de verkligen existerar. [REPO-READINESS-001](REPO_READINESS_AUDIT.md) är uppdaterad.


**Ny Required governance-regel:** [BRAND-IDENTITY-001](BRAND_IDENTITY_CONTRACT.md) och `tests/test_brand_identity.py` granskar deklaration, kod- och filvägsidentifierare, kända gamla produktnamn/akronym, samt mutationstest för rename av public metadata. Detta är **inte** en godkänd desktop/UI-rename-regression ännu; R3 måste lägga till verkliga Chromium-/Linux-launchertest för namnbyte. Scan ska **INTE blockera korrekt tillverkarspecifik kod**: Cisco, Juniper etc är uttryckligen tillåtna.


Denna första workflow kör Python unittest på dokumentlänkar, minimifamiljer, required-funktioner och negativa mutationsfall som försöker påstå felaktig PT-paritet. **Den verifierar inte** att någon nätverksmotor, Excelparser eller Linux-app har implementerats.

När R1-kod utvecklas ska separata jobs läggas till för engine type/static safety, oberoende byte/state/timer-orakel, 2-processers determinism, integration med CLI och API, referens-PDU-spår, source import-fixturer, verklig Chromium/ELK-geometry och Linux packaging tests. Inga av dessa får markeras gröna utan verkliga körningar.

GitHub branchskydd/rulesets är en separat administrativ inställning och kan inte anses etablerad av att denna YAML har pushats. Projektägaren ska verifiera att Required checks och squash/förbud mot force push är aktiverade. På en första tom repo initieras README på main; styrpaketet föreslås genom en PR. Ingen gammal kod eller historiska arkitekturtest importeras.
