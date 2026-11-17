# Ren nätverkslabb-app — kanonisk topologi

**Självständig nyimplementation.** Repositoryts tekniska namn är inte produktens namn. Ändra endast `APP_NAME` i `network_core/config.py` för att byta appens visningsnamn. Alla användarsynliga namn hämtas från den deklarationen. Ingen äldre produktkod har kopierats in.

Version 0.1 är en körbar lokal desktop/webb-hybrid för att dokumentera enheter, portar, zoner och **uttryckligen deklarerade** fysiska länkar. Grafspårningen är avsiktligt begränsad. Projekt lagras på riktigt i `.yadilab`-filer. Programmet fungerar helt lokalt utan npm-installation, moln eller tredjepartsbibliotek i runtime.

## Permanent utvecklingsdirektiv

Utvecklingen styrs av [Masterprompten](docs/MASTERPROMPT.md) och den korta operativa instruktionen i [AGENTS.md](AGENTS.md). Läs båda före varje utvecklingsetapp. Dokumentet beskriver slutmål och kvalitetskrav; alla planerade funktioner är **inte** redan implementerade.

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

## Fristående Layer 2-kärna (under utveckling)

`network_core/ethernet.py` erbjuder en **endast Python-baserad, deterministisk MAC-forwardingmodell** ovanpå projektets uttryckligen deklarerade länkar. Den lär käll-MAC från faktisk switchingress, floodar broadcast och okänd unicast samt riktar känd unicast. Avstängda portar och länkar används inte; switchloopar avvisas eftersom STP saknas. 23 nya beteendetester ingår.

Detta är **inte** en färdig Ethernet-/ARP-/IP-simulator. En avgränsad ARP-diagnostik har nu UI/HTTP-integration, men ingen fullständig paket-/IP-stack finns. Inga MAC-adresser skapas eller tilldelas nätverksenheter automatiskt. Se [Layer 2-kontrakt och begränsningar](docs/ETHERNET_FORWARDING.md).

## Ethernet II-ramar och explicita MAC-bindningar (isolerat Python-API)

Den fristående Layer 2-motorn kan nu serialisera och tolka väldefinierade Ethernet II-ramar utan FCS, med strikt EtherType- och MAC-validering. En simuleringssession kan få **uttryckliga port-MAC-bindningar** och avvisar ramkällor utan sådan bindning eller med fel källadress. MAC-tabeller lärs fortfarande in av verkligt simulerade inkommande ramar, inte av IP-adresser eller påhittade enheter.

**Utökat i schema 1.1:** Explicit MAC-adress kan sparas per icke-switchport via Builder och verklig Save/Open. Den isolerade Python-motorn använder sparade bindningar eller validerade sessionsbindningar. Inlärda MAC-tabeller och ARP-cache är fortfarande flyktiga; IP-forwarding och ping stöds inte. VLAN-forwarding kan nu aktiveras explicit per Python-session. Se [MAC-kontraktet](docs/MAC_CONFIG.md). Se [Ethernet II-kontrakt](docs/ETHERNET_FRAMES.md) och [forwardingkontrakt](docs/ETHERNET_FORWARDING.md).

## Isolerad ARP-fråga och svar (Python och begränsad GUI-diagnostik)

Den separata modulen `network_core/arp.py` modellerar ARP-meddelanden enligt Ethernet/IPv4-formatet och kör en uttrycklig **request → broadcast-forwarding → reply → ARP-cache** över redan deklarerade och aktiva länkar. Både IPv4-gränssnitt och MAC-bindningar måste anges uttryckligen. Resultaten gäller **bara den begränsade simuleringssessionen** och är inte ping, IP-routing eller verklig nätverksreachability. ARP kan nu begränsas till explicit konfigurerade access-/trunk-VLAN via `ArpSession(..., vlan_ports=...)`. Builder kan nu göra enskilda ARP-diagnostikanrop mot den riktiga Pythonmotorn; verkliga transmissionslänkar, VLAN-droppar samt tillfälliga MAC-/ARP-tabeller visas. Inget sessionscache sparas eller återanvänds mellan HTTP-anrop. Explicita MAC-adresser läses ur schema 1.1/1.2. Se [ARP-kontraktet](docs/ARP.md).

## Stegvisa Layer 2-sessioner (Pythonmotor och Builder)

Det finns nu ett **explicit startat och återställbart sessionsläge** i Builder: enskilda ARP-förfrågningar och opaka Ethernet II-ramar kan köras i följd, med bevarad **faktiskt inlärd switch-MAC-tabell** och **ARP-cache** mellan operationer. En andra ARP-fråga till samma redan upplösta IP blir en riktig sessionsbaserad `CACHE_HIT` utan extra trafik. Fysiska transmissionsspår och VLAN-droporsaker redovisas; inga nätverksobjekt, ping eller IP-paket fabriceras. Sessions-ID är tillfälliga, servern kräver **oförändrat projekt** för varje operation, och explicit nollställning tömmer tabellerna. Att ändra projektet, dess portar eller topologi avslutar sessionen i Builder. Endast dokumenterade MAC-adresser används som sändaridentitet. **Inga sessionstabeller sparas i .yadilab** och en omstart av lokal server avslutar sessioner. Det tidigare engångstestet för ARP är fortsatt tillgängligt. Se [sessionskontrakt](docs/SIMULATION_SESSION.md).

## Första Layer 3-steget – connected IPv4-route lookup

`network_core/routing.py` läser nu **endast explicit konfigurerade IPv4/CIDR på aktiverade portar** och bygger en separat routingtabell per vald klient, router eller brandvägg. Builder och `POST /api/routing/connected` kan visa tabellen samt välja **längsta matchande prefix** för en uttryckligen angiven destinations-IPv4. `MATCH` betyder bara att ett konfigurerat lokalt prefix matchar, **inte** att IP-paket har skickats eller kan nå destinationen. Saknad match ger `NO_ROUTE`; lika specifika överlappande gränssnitt ger `AMBIGUOUS` utan påhittat tie-break. Frånkopplad kabel ändrar inte matematisk routeuppslagning, men är inte någon verifierad fysisk anslutning. Statiska routes kan nu konfigureras uttryckligen i schema 1.3; IP-forwarding, TTL och ICMP/ping finns fortfarande inte. Se [connected-routingkontraktet](docs/ROUTING_CONNECTED.md).

## Statiska IPv4-routes – schema 1.3

Enheter av typen **host, router eller firewall** kan nu ha valfria `staticRoutes` med stabilt route-ID, explicit destinationsprefix, next-hop och utgående port. Builder validerar konfigureringen mot Pythonmodellen innan arbetsytan ändras och skriver ingen fil utan användarens **Spara**. Next-hop måste vara en unicastadress på den deklarerade utgående portens eget IPv4-subnät och får inte vara portens egen adress, subnet-/broadcastadress eller en gissad gateway. Avaktiverad port behåller den dokumenterade konfigurationen men installerar inte routen i routingtabellen.

Longest-prefix match omfattar nu både `CONNECTED` och `STATIC`; lika specifika alternativ ger `AMBIGUOUS` (ingen metric eller administrative distance antas). Statiska default routes anges uttryckligen som `0.0.0.0/0`. Schema **1.0–1.2** kan fortsätta läsas och sparas oförändrade, medan uttrycklig route- eller portredigering uppgraderar arbetsminnet till schema **1.3** utan autosave. Routingtabellerna är read-only resultat från dokumentationen: ingen faktisk forwarding, next-hop-ARP, TTL eller ICMP/ping finns ännu. Se [kontraktet för statiska routes](docs/STATIC_ROUTES.md).

## Explicit VLAN-forwarding (endast Python-API)

`EthernetFabric(project, vlan_ports=...)` kan nu forwarda mellan uttryckligen konfigurerade access- och trunkportar med **isolerade MAC-tabeller per VLAN**, begränsade allowlists och korrekt 802.1Q-tagging på trunkar. `EthernetFrame` kan serialisera och tolka en C-tagg. Explicit VLAN-portkonfiguration kan nu lagras i `.yadilab` schema **1.2**, redigeras i Builder och läsas direkt av `EthernetFabric` och `ArpSession`. Inlärda MAC-tabeller och ARP-cache är fortfarande endast sessionsdata. Den separata ARP-sessionen kan återanvända samma VLAN-forwarding för request och reply. Endast explicit sparad 1.2-konfiguration eller tillagd sessionskonfiguration får användas; inget VLAN antas. Se [VLAN-kontraktet](docs/VLAN.md).

## Avsiktligt INTE implementerat

**Topologisk grafväg är inte ping, IP-routing, VLAN-medveten reachability, brandväggslogik eller ett bevis på nätverksanslutning.** Första versionens grafspårning traverserar dokumentationsgrafen, inte verkliga protokoll.

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

UTF-8 JSON, `.yadilab` (befintlig dokumentfiländelse, inte ett produktnamn):

```json
{
  "schemaVersion": "1.3",
  "name": "Lab 1",
  "zones": [],
  "nodes": [
    {"id":"pc-1","label":"Klient","kind":"host","x":100,"y":100,"zoneId":null,"ports":[{"id":"eth0","name":"eth0","enabled":true,"ipv4":"192.0.2.10/24","mac":"02:00:00:00:00:0A"}]},
    {"id":"sw-1","label":"Switch","kind":"switch","x":420,"y":100,"zoneId":null,"ports":[{"id":"ge1","name":"Gi1","enabled":true,"ipv4":null}]}
  ],
  "links": [{"id":"link-1","a":{"node":"pc-1","port":"eth0"},"b":{"node":"sw-1","port":"ge1"},"enabled":true}]
}
```

Schema **1.0** och **1.1** kan fortfarande läsas, valideras och sparas utan tyst migrering. Version **1.1** tillåter ett valfritt portfält `"mac"` (null eller sex kolonseparerade hexoktetter för icke-switchportar). En explicit MAC-redigering i Builder uppgraderar ett öppet 1.0-projekt i minnet; filen skrivs endast vid **Spara**. MAC kräver icke-noll unicast, är unik inom projektet och normaliseras till versaler. Ingen MAC tilldelas automatiskt. Schema **1.2** tillåter dessutom `vlan: {"mode":"access","vlan":10}` eller `vlan: {"mode":"trunk","allowedVlans":[10,20]}` på **switchportar**. Inställningarna kan redigeras som `access:10` respektive `trunk:10,20` i Builder. En explicit redigering uppgraderar äldre schema till 1.3 **i minnet**, och sparar inte förrän användaren väljer Spara. Avsaknad av VLAN-konfiguration betyder **inte** VLAN 1. För simulering måste varje aktiv ansluten switchport vara konfigurerad när VLAN har aktiverats. Schema **1.3** stöder även statiska IPv4-routes på icke-switch-enheter. Se [VLAN-lagringskontrakt](docs/VLAN_PERSISTENCE.md), [statiska routes](docs/STATIC_ROUTES.md) och [MAC-kontraktet](docs/MAC_CONFIG.md).

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
