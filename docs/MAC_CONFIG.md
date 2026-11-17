# Kontrakt: beständig explicit MAC-konfiguration (projektformat 1.1)

## Schema och bakåtkompatibilitet

- `schemaVersion: "1.0"` stöds fortfarande strikt. Alla 1.0-portar har exakt `id`, `name`, `enabled`, `ipv4`. Ett `mac`-fält i v1.0 avvisas. Save/Open eller en ren validering uppgraderar **inte** 1.0 automatiskt.
- `schemaVersion: "1.1"` utökar endast portobjektet med **valfri** `mac`-nyckel. Avsaknad eller `null` betyder **ingen konfigurerad MAC**, inte en slumpmässigt eller deterministiskt genererad adress.
- `mac` är exakt sex kolonseparerade hexoktetter, t.ex. `02:00:00:00:00:0A`, icke-noll unicast. Versaler är kanonisk representation. Dubblerade MAC-adresser i samma projekt avvisas, även om portarna är avstängda. Switchportar kan inte ha en konkret host-NIC-MAC; `null` är tillåtet.
- En av användaren explicit utförd MAC-redigering i Builder på en 1.0-fil uppgraderar **arbetsminnets** `schemaVersion` till 1.1, bevarar samtliga andra data och valideras via det riktiga Python-API:t innan den blir aktiv. **Ingen filskrivning sker före Save.** Den existerande konfliktkontrollen och SHA-256-verifieringen gäller oförändrat.
- Äldre 1.0-projekt har fortsatt exakt samma identiteter, länkar, zoner, portnamn och IPv4-information vid Open/Save. Okända och framtida schemafält avvisas; inget tappas bort tyst.
- Det gamla explicita fyrtabells-CSV-formatet importerar tills vidare 1.0 utan MAC-kolumn. Godtyckliga CSV-kolumner för MAC avvisas tills ett nytt definierat CSV-schema finns.

## Integrering med isolerad Layer 2

`EthernetFabric(project)` använder endast deklarerade, validerade `mac`-fält från 1.1. Parametern `interface_macs` kan komplettera frånvarande konfiguration i **en session**, men ett annat MAC-värde för en redan sparad port avvisas och skrivs aldrig över. Dubbleringar avvisas i båda källorna. `inject_frame` kräver matchande explicit käll-MAC.

`ArpSession(project)` kan använda dessa explicita MAC-portfält utan separat mappning; för äldre projekt kan `interface_macs` anges som tidigare. ARP-resultat avser endast simulerad broadcast och svar på explicit nådda L2-länkar.

**Inget protokolltillstånd persistieras:** switchens inlärda MAC-tabeller, utsända ramar, ARP-cache och sessionsspecifika MAC-bindningar återställs vid ny session. Ingen VLAN, IP-routing eller ping, och inga påhittade kablar eller NIC-adresser.

## Verifiering

- `tests/test_mac_persistence.py`: gamla 1.0-dokument, 1.1-normalisering, avvisning av korrupt/duplicerad/switch-MAC, riktiga filbytes, återöppning med ny `ProjectStore`, sessionskonflikter och ARP efter återöppning.
- `tests/browser_smoke.py`: explicit MAC-redigering i Builder, ingen förtida Save, verklig lokal fil, SHA-256, omstart av både server och Chromium och kontroll av MAC och export.
- Föregående funktions-, CSV- och browserregressioner måste fortsatt passera.
