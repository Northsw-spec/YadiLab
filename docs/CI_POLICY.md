# CI-001 — verifieringsgränser vid det helt nya repot

Denna första workflow kör Python unittest på dokumentlänkar, minimifamiljer, required-funktioner och negativa mutationsfall som försöker påstå felaktig PT-paritet. **Den verifierar inte** att någon nätverksmotor, Excelparser eller Linux-app har implementerats.

När R1-kod utvecklas ska separata jobs läggas till för engine type/static safety, oberoende byte/state/timer-orakel, 2-processers determinism, integration med CLI och API, referens-PDU-spår, source import-fixturer, verklig Chromium/ELK-geometry och Linux packaging tests. Inga av dessa får markeras gröna utan verkliga körningar.

GitHub branchskydd/rulesets är en separat administrativ inställning och kan inte anses etablerad av att denna YAML har pushats. Projektägaren ska verifiera att Required checks och squash/förbud mot force push är aktiverade. På en första tom repo initieras README på main; styrpaketet föreslås genom en PR. Ingen gammal kod eller historiska arkitekturtest importeras.
