# Ren nätverkslabb-app — kanonisk topologi

**Självständig nyimplementation.** Repositoryt heter `YadiLab-a`, men det är **inte appens namn**. Ändra endast `APP_NAME` i `network_core/config.py` för att byta appens visningsnamn. Ingen kod har kopierats från det äldre projektet.

Version 0.1 är en körbar lokal desktop/webb-hybrid för att dokumentera enheter, portar, zoner och **uttryckligen deklarerade** fysiska länkar. Grafspårningen är avsiktligt begränsad. Projekt lagras på riktigt i `.yadilab`-filer. Programmet fungerar helt lokalt utan npm-installation, moln eller tredjepartsbibliotek i runtime.

## Starta på Linux (Python 3.10+)

```bash
python3 -m network_core
```

En lokal webbläsare öppnas på `http://127.0.0.1:8765/`. Vill du styra datamapp och webbläsare:

```bash
python3 -m network_core --data-dir ~/NetworkProjects --no-browser --port 8765
```

Öppna därefter `http://127.0.0.1:8765/`. Avsluta servern med `Ctrl+C`.

## Fungerar i första versionen

- Skapa, redigera, flytta och ta bort dokumenterade hosts, switchar, routrar och brandväggar.
- Lägg till namngivna, uttryckligen deklarerade portar, valfri IPv4/CIDR, och zoner.
- Anslut två **lediga portar** genom att klicka på dem, skapa och radera kablar.
- Injicera enkla fel genom att inaktivera en port eller en deklarerad länk.
- Spåra om det finns en grafväg över **aktiverade** länkar och portar; visa faktiskt använda länk-ID:n och ändpunkter.
- Spara `.yadilab` på lokala disken (atomär filersättning, SHA-256, konfliktkontroll), lista och öppna projekten även efter omstart.
- Importera/exportera kanoniskt JSON; okända fält avvisas så att de inte försvinner tyst.
- Offline-baserat gränssnitt med SVG-linjer direkt i respektive ports synliga anslutningspunkt.

## Avsiktligt INTE implementerat

**Topologisk väg är inte ping, IP-routing, VLAN-forwarding, brandväggslogik eller ett bevis på nätverksanslutning.** Första versionens grafspårning traverserar dokumentationsgrafen, inte verkliga protokoll.

Ännu inte implementerat: XLSX/ODS-import eller godtyckliga CSV-format, IP forwarding, Layer 2 bridging, DHCP, DNS, brandväggsregler, ACL, fysisk kabeltyp, nätverksemulering, automatisk ELK-layout, portöverlappskontroll, multi-user, produktionsinstallatör och omfattande tillgänglighetsverifiering. Ingen funktion visar påhittade enheter eller kablar. Inga gamla simuleringsmotorer har förts över utan bevis.

## Import av explicit CSV-dokumentation

Markera `Devices.csv` samt valfria `Interfaces.csv`, `Links.csv` och `Zones.csv` samtidigt i **Importera**. Appen validerar samtliga tabeller före uttryckligt godkännande att ersätta aktuell arbetsyta. Ingenting sparas automatiskt.

Det är ett **definierat CSV-utbytesformat**, inte en generell importerare för godtyckliga kalkylblad. Varje tabell kräver exakt följande kolumner (i valfri ordning):

| Tabell | Kolumner |
| --- | --- |
| `Devices.csv` (krävs) | `id,label,kind,x,y,zoneId` |
| `Interfaces.csv` | `nodeId,id,name,enabled,ipv4` |
| `Links.csv` | `id,aNode,aPort,bNode,bPort,enabled` |
| `Zones.csv` | `id,label` |

`kind` är `host`, `switch`, `router` eller `firewall`. `x` och `y` är uttryckligen angivna presentationskoordinater. `zoneId` och `ipv4` kan lämnas tomma (motsvarar null); övriga värden krävs. `enabled` måste vara exakt `true` eller `false`. Länkar skapas **enbart** från `Links.csv` med ändpunkter som deklarerats i `Interfaces.csv`.

Okända fält, odeklarerade portar, ogiltiga referenser och malformed CSV avvisas helt. Exempel finns i `examples/csv/`. XLSX/ODS och godtyckliga CSV-format stöds inte ännu.

## Filformat

UTF-8 JSON, `.yadilab`:

```json
{
  "schemaVersion": "1.0",
  "name": "Lab 1",
  "zones": [],
  "nodes": [
    {"id":"pc-1","label":"Klient","kind":"host","x":100,"y":100,"zoneId":null,"ports":[{"id":"eth0","name":"eth0","enabled":true,"ipv4":"192.0.2.10/24"}]},
    {"id":"sw-1","label":"Switch","kind":"switch","x":420,"y":100,"zoneId":null,"ports":[{"id":"ge1","name":"Gi1","enabled":true,"ipv4":null}]}
  ],
  "links": [{"id":"link-1","a":{"node":"pc-1","port":"eth0"},"b":{"node":"sw-1","port":"ge1"},"enabled":true}]
}
```

Inga anslutningar härleds från adresser, nodnamn, närhet eller zoner. En port kan ha högst en fysisk länk i schema v1. Okända formatversioner avvisas, i stället för att data tappas.

## Testa

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --check web/model.js
node --check web/canvas.js
node --check web/app.js
python3 tests/browser_smoke.py  # valfritt, kräver Playwright + Chromium installerade
```

CI kör automatiska tester på Linux. Extern Internetåtkomst används inte av själva appen.

## Utvecklingsprinciper

En kanonisk dokumentationsmodell, tydliga begränsningar, små moduler, negativa tester, inga gissade länkar. Funktioner tas in först när det finns ett konkret användarfall och tester som provar samma beteende som gränssnittet.

**Ingen licens har ännu valts för källkoden.**
