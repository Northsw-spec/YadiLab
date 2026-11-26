# CI-001 — verifieringsgränser vid det helt nya repot

**Verifierad repo-status 2026-11-26:** GitHub `GET /rulesets?includes_parents=true` returnerade **en tom lista**, och branch-protection endpoint returnerade **HTTP 403** med aktuell integration. Detta innebär att branch protection och required status checks **inte kan intygas**. Endast workflow-resultat `governance-contracts` är bevisat genomfört. [REPO-READINESS-001](REPO_READINESS_AUDIT.md) beskriver exakt administrativ åtgärd: ägaren måste skapa/aktivera ruleset för `main` med PR-krav, check, force-push-/delete-förbud och verifiera att en direktpush/röd PR faktiskt stoppas. GitHub Apps anslutna åtkomst kan inte själv garantera detta. Regeln om att alltid invänta grön CI gäller fortsatt även innan systemskydd finns.


**Ny Required governance-regel:** [BRAND-IDENTITY-001](BRAND_IDENTITY_CONTRACT.md) och `tests/test_brand_identity.py` granskar deklaration, kod- och filvägsidentifierare, kända gamla produktnamn/akronym, samt mutationstest för rename av public metadata. Detta är **inte** en godkänd desktop/UI-rename-regression ännu; R3 måste lägga till verkliga Chromium-/Linux-launchertest för namnbyte. Scan ska **INTE blockera korrekt tillverkarspecifik kod**: Cisco, Juniper etc är uttryckligen tillåtna.


Denna första workflow kör Python unittest på dokumentlänkar, minimifamiljer, required-funktioner och negativa mutationsfall som försöker påstå felaktig PT-paritet. **Den verifierar inte** att någon nätverksmotor, Excelparser eller Linux-app har implementerats.

När R1-kod utvecklas ska separata jobs läggas till för engine type/static safety, oberoende byte/state/timer-orakel, 2-processers determinism, integration med CLI och API, referens-PDU-spår, source import-fixturer, verklig Chromium/ELK-geometry och Linux packaging tests. Inga av dessa får markeras gröna utan verkliga körningar.

GitHub branchskydd/rulesets är en separat administrativ inställning och kan inte anses etablerad av att denna YAML har pushats. Projektägaren ska verifiera att Required checks och squash/förbud mot force push är aktiverade. På en första tom repo initieras README på main; styrpaketet föreslås genom en PR. Ingen gammal kod eller historiska arkitekturtest importeras.
