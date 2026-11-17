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

`network_core/routing.py` läser nu **endast explicit konfigurerade IPv4/CIDR på aktiverade portar** och bygger en separat routingtabell per vald klient, router eller brandvägg. Builder och `POST /api/routing/connected` kan visa tabellen samt välja **längsta matchande prefix** för en uttryckligen angiven destinations-IPv4. `MATCH` betyder bara att ett konfigurerat lokalt prefix matchar, **inte** att IP-paket har skickats eller kan nå destinationen. Saknad match ger `NO_ROUTE`; lika specifika överlappande gränssnitt ger `AMBIGUOUS` utan påhittat tie-break. Frånkopplad kabel ändrar inte matematisk routeuppslagning, men är inte någon verifierad fysisk anslutning. Statiska routes kan konfigureras i schema 1.3. IPv4-forwarding, TTL och avgränsad ICMP Echo finns nu i separata verifierade moduler. Se [connected-routingkontraktet](docs/ROUTING_CONNECTED.md).

## IPv4- och routingfel i felsökningen (PR #22)

Den gemensamma jämförelsemotorn hanterar nu ytterligare tre **temporära, explicita och helt reversibla** fel: `IPV4_PREFIX_CHANGED` på en deklarerad aktiv gränssnittsport med IPv4/CIDR, `STATIC_ROUTE_REMOVED` med exakt node- och route-ID samt `STATIC_NEXT_HOP_CHANGED` med en uttryckligen vald och enligt projektmodellen **on-link** IPv4-gateway. Användaren väljer prefix, route eller next-hop i Builder. Ändringen kan orsaka `NO_ROUTE`, `ARP_FAILED` eller en misslyckad returväg, men får aldrig skapa en ny kabel, gateway eller route.

Bara tre separata genomförda ICMP-utbyten med fungerande referens, misslyckat feltest och återställd lyckad kommunikation ger `FAULT_CONFIRMED`. Om det ändrade prefixet strider mot en redan deklarerad statisk next-hop, eller om next-hop ligger utanför vald ports subnät, returneras ett tydligt valideringsfel **422**: ingen route tas bort eller justeras tyst. Alla ändringar gäller isolerade kopior; inga projektfiler eller Builder-inställningar skrivs över. Se [felsökningskontraktet](docs/TROUBLESHOOTING.md).

## Utökad felsökningsövning: portar och VLAN (PR #21)

Jämförelsemotorn kan nu också injicera tre **uttryckliga och temporära** fel på en redan deklarerad, aktiverad port: `PORT_DISABLED` (administrativt stäng porten), `ACCESS_VLAN_CHANGED` (välj ett annat explicit access-VLAN 1–4094), och `TRUNK_VLAN_BLOCKED` (ta bort ett uttryckligen tillåtet VLAN från en trunk med minst två tillåtna VLAN). Inställningarna återställs exakt, med samma tre oberoende ICMP Echo-körningar och de ursprungliga routing-/ARP-/Ethernet-/VLAN-mekanismerna. Ett fel räknas endast som **verifierat** om referensen ger Echo Reply, felkopian misslyckas och återställningen ger Echo Reply igen. VLAN som inte påverkar paketet ger i stället `NO_OBSERVED_IMPACT`. Okända, avstängda eller felaktigt konfigurerade portar och ogiltiga VLAN-ID:n avvisas; inga automatiska VLAN-antaganden eller filskrivningar görs. Builder väljer explicit feltyp, port och VLAN. Det äldre kabel-API:t finns kvar och använder samma gemensamma jämförelsemotor. Se [felsökningskontraktet](docs/TROUBLESHOOTING.md).

## Felsökningsövning: kontrollerat kabelbrott och verifierad återställning (PR #20)

En read-only jämförelse i `network_core/troubleshooting.py` och Builder kör tre separata **riktiga ICMP Echo Request/Reply-spår** genom befintlig IPv4-, ARP-, Ethernet- och VLAN-motor: **referensnät**, en tillfällig kopia med **exakt en uttryckligen vald och tidigare aktiverad kabel avstängd**, och samma projekt efter att denna kabel återaktiverats. Endast `FAULT_CONFIRMED` betyder att referensen gav `REPLIED`, den felinjicerade kopian inte gav `REPLIED`, och den återställda kopian gav `REPLIED`. Om referensen redan misslyckades returneras `BASELINE_NOT_REPLIED` och om felet inte påverkar utbytet `NO_OBSERVED_IMPACT`; inga påhittade orsakssamband. Varje körning har **egen flyktig ARP-/MAC-inlärning** och returnerar observerade faktiskt transmitterade länk-ID:n, separata förfrågnings-/svarsfel samt ett uttryckligt förslag att återaktivera den valda kabeln. Åtgärden är **en förhandsvisning**, inte en automatisk reparation eller ändring av arbetsytan. Ingen autosave, nya länkar, sparade scenarier eller extern ping. Se [felsökningskontraktet](docs/TROUBLESHOOTING.md).

## ICMP-routerfel – paket som faktiskt hittar tillbaka (PR #19)

ICMPv4-felmeddelanden **Time Exceeded (typ 11/kod 0)** vid TTL-expiration i en transitrouter, samt **Destination Unreachable / Network (typ 3/kod 0)** när en transitrouter saknar matchande route, modelleras nu enligt RFC 792. Felkoden har en egen strikt codec med riktig checksumma, fyra nollställda bytes och **originalets 20-byte IPv4-header + de första åtta databyten**. Det är inte ett påhittat diagnostikmeddelande: först efter en faktiskt observerad felhändelse på en deklarerad router skapas ett felpaket och skickas tillbaka med **samma IPv4-, ARP- och Ethernetmotor**.

Echo-diagnostiken visar `icmpError.status=RECEIVED` endast när felpaketet faktiskt når **exakt källporten** och IP-/ICMP-identitet och citerat original verifierats. En misslyckad eller ej stödd returtransport får `NOT_DELIVERED` eller `MISMATCH`; fel vid avsändarens egen route, kabel, VLAN eller ARP ger **inget** automatiskt ICMP-fel. Pingstatus förblir `REQUEST_FAILED` när Echo Request inte nådde mottagaren, även om ett ICMP-routerfel kom tillbaka. Ingen ICMP-error-in-response-to-error, inget uppmätt RTT, ingen autosave. Returtransporten är avgränsad till den observerade routeringångens port och kräver en korrekt route tillbaka via samma port. Se [kontrakt](docs/ICMP_ROUTER_ERRORS.md).

## ICMP Echo Request/Reply – verifierad tur och retur

Ny `network_core/icmp.py` kodar och validerar **ICMPv4 Echo Request (typ 8/kod 0)** och **Echo Reply (typ 0/kod 0)** enligt RFC 792, inklusive riktig Internetchecksumma, identifierare, sekvens och datalast. `network_core/icmp_ping.py` kör först en riktig simulerad ICMP Request genom samma IPv4-, ARP- och Ethernetmotor; en Echo Reply skapas **endast** om Request nådde en faktisk konfigurerad host-/routerport och routerns/klientens deklarerade returväg kan användas. Svaret måste nå **exakt källporten** med korrekt IP-identitet, ICMP-typ, checksumma, identifierare, sekvens och payload innan `REPLIED` visas. Envägsleverans ger aldrig pingframgång. Saknas returroute, ARP, MAC, länk eller VLAN-överföring visas `REQUEST_FAILED`, `REPLY_FAILED` eller `RESPONDER_UNSUPPORTED` tillsammans med faktiskt hoppspår. Varje körning är en isolerad simulering: ingen autosave, ingen verklig nätverkstrafik och ingen uppmätt RTT. **Avgränsade ICMP-routerfel Time Exceeded/Network Unreachable finns nu enligt PR #19; andra ICMP-felkoder, brandväggsregler och extern nättrafik saknas fortfarande.** Se [ICMP-kontraktet](docs/ICMP_ECHO.md).

## IPv4-datagram: faktisk ARP, Ethernet och TTL (avgränsad simulering)

`network_core/ipv4_packet.py` kodar och verifierar en minimal RFC 791 IPv4-header (20 byte, verklig headerchecksumma, TTL, IPv4-käll-/mål-IP, experimentellt protokoll **253**). `network_core/ipv4.py` använder en och samma `ArpSession`/`EthernetFabric` för varje uttryckligt paketförsök: uppslagning i den befintliga connected-/static-route-tabellen, ARP för deklarerat next-hop, Ethernet II-ram med EtherType `0x0800`, verifierad faktisk ramtransport på deklarerade kablar och VLAN, samt TTL-minskning för varje transitrouter. Endast en matchande konfigurerad mottagar-MAC **och** IPv4-adress på den verkligen nådda gränssnittsporten kan ge `DELIVERED`. Alla övriga fel förblir explicita, exempelvis `NO_ROUTE`, `ARP_FAILED`, `TTL_EXPIRED`, `NON_ROUTER` och `AMBIGUOUS_ROUTE`. Protokoll 253 är en opak experimentell datagramlast, **inte ICMP Echo eller en transporttjänst**. Protokoll 1 kan separat bära ett strikt validerat ICMP Echo-meddelande och få en riktig modellerad returresa via `/api/icmp/echo`. IP-fragmentering och ICMP Time Exceeded simuleras inte.

Builder kan skicka en **engångsspårning** via `POST /api/ipv4/trace` med explicit källport, destination och TTL. Alla hops ARP-statusar, kabeltransmissioner och ruttbeslut visas. Inga projektfiler eller sessionscache ändras; varje körning börjar med tomma ARP-/MAC-tabeller. Det tidigare UI-läget för fortsatta Layer 2-sessioner påverkas inte. Se [IPv4-forwardingkontraktet](docs/IPV4_FORWARDING.md).

## Statiska IPv4-routes – schema 1.3

Enheter av typen **host, router eller firewall** kan nu ha valfria `staticRoutes` med stabilt route-ID, explicit destinationsprefix, next-hop och utgående port. Builder validerar konfigureringen mot Pythonmodellen innan arbetsytan ändras och skriver ingen fil utan användarens **Spara**. Next-hop måste vara en unicastadress på den deklarerade utgående portens eget IPv4-subnät och får inte vara portens egen adress, subnet-/broadcastadress eller en gissad gateway. Avaktiverad port behåller den dokumenterade konfigurationen men installerar inte routen i routingtabellen.

Longest-prefix match omfattar nu både `CONNECTED` och `STATIC`; lika specifika alternativ ger `AMBIGUOUS` (ingen metric eller administrative distance antas). Statiska default routes anges uttryckligen som `0.0.0.0/0`. Schema **1.0–1.2** kan fortsätta läsas och sparas oförändrade, medan uttrycklig route- eller portredigering uppgraderar arbetsminnet till schema **1.3** utan autosave. Routingtabellerna är read-only resultat från dokumentationen; faktisk avgränsad forwarding, next-hop-ARP, TTL och ICMP Echo anropar **separata** protokollmotorer och kan inte härledas från en route-tabellmatchning. Se [kontraktet för statiska routes](docs/STATIC_ROUTES.md).

## Explicit VLAN-forwarding (endast Python-API)

`EthernetFabric(project, vlan_ports=...)` kan nu forwarda mellan uttryckligen konfigurerade access- och trunkportar med **isolerade MAC-tabeller per VLAN**, begränsade allowlists och korrekt 802.1Q-tagging på trunkar. `EthernetFrame` kan serialisera och tolka en C-tagg. Explicit VLAN-portkonfiguration kan nu lagras i `.yadilab` schema **1.2**, redigeras i Builder och läsas direkt av `EthernetFabric` och `ArpSession`. Inlärda MAC-tabeller och ARP-cache är fortfarande endast sessionsdata. Den separata ARP-sessionen kan återanvända samma VLAN-forwarding för request och reply. Endast explicit sparad 1.2-konfiguration eller tillagd sessionskonfiguration får användas; inget VLAN antas. Se [VLAN-kontraktet](docs/VLAN.md).

## Avsiktligt INTE implementerat

**Topologisk grafväg är inte ping, IP-routing, VLAN-medveten reachability, brandväggslogik eller ett bevis på nätverksanslutning.** Första versionens grafspårning traverserar dokumentationsgrafen, inte verkliga protokoll.

Ännu inte implementerat: godtycklig kalkylbladsimport, fullständig DHCP-adresstilldelning/DORA, DNS, brandväggsregler, ACL, fysisk kabeltyp, extern nätverksemulering, automatisk ELK-layout, portöverlappskontroll, multi-user, produktionsinstallatör och omfattande tillgänglighetsverifiering. Ingen funktion visar påhittade enheter eller kablar. Inga gamla simuleringsmotorer har förts över utan bevis.

## Avgränsad DHCPv4 DISCOVER/OFFER via HTTP (PR #29)

En ny read-only diagnos kan via `POST /api/dhcp/discover-offer` simulera en **DHCPDISCOVER** från en explicit vald hostport utan IP och en **DHCPOFFER** från en explicit vald serverport med MAC och IPv4/CIDR. Användaren anger också uttryckligen föreslagen ledig IPv4, transaktions-ID och leasetid. Bytekorrekt BOOTP/DHCP, UDP (68/67), IPv4-broadcast och checksummor skapas och valideras, och båda Ethernet-broadcasterna måste nå sina respektive portar via befintliga deklarerade kablar och VLAN. Olika broadcastdomäner och nedstängda länkar ger inget falskt erbjudande. **Ingen IP tilldelas, ingen lease skapas, inga projekt ändras eller sparas.** Detta är ännu **inte DORA** och saknar DHCPREQUEST/ACK, dynamiska adresspooler och relay. Builder-UI för diagnosen tillkommer i ett separat steg. Se [DHCP-kontraktet](docs/DHCP_DISCOVER_OFFER.md).

## Export av aktuellt projekt till XLSX och ODS (PR #27)

Builder har separata **Exportera XLSX** och **Exportera ODS**-knappar bredvid **Exportera JSON**. Exporten läser **arbetsytans aktuella** (även ännu osparade) nätverksdokumentation, validerar modellen och skapar verkliga binära kalkylbladsfiler med exakt definierade blad och kolumner. Noder, portar, länkar och länkändpunkter, zoner, MAC-adresser, VLAN och deklarerade statiska routes behålls. Ingen fil skrivs till serverns projektlagring. Webbläsarnedladdningen initieras separat från **Spara projekt**.

Endast **schema 1.0 och schema 1.3** kan exporteras till det nuvarande kalkylbladsformatet. Schema 1.1/1.2 avvisas utan dold uppgradering. Explicit `null` för valfri MAC/VLAN-konfiguration och uttryckligen närvarande men tomma `staticRoutes` avvisas eftersom detta kalkylbladsformat inte kan representera skillnaden mellan utelämnat och `null`/tomt fält. Ett helt tomt nätverk avvisas eftersom en `Devices`-tabell kräver en enhet. På så sätt förhindras tyst dataförlust. Exportören importerar tillbaka den genererade filen via den faktiska XLSX-/ODS-importören **innan** den levereras, och avvisar varje avvikelse i kanoniska data.

Det existerande schema 1.3-kontraktet har inget fält för projektets namn; vid återimport anger användaren därför samma projektnamn för att få identisk projektmodell. Se [roundtrip-kontraktet](docs/SPREADSHEET_EXPORT.md).

## Importmallar och cellbaserad felrapportering (PR #26)

Under **SPARADE PROJEKT** i Builder finns två nedladdningslänkar: **Excel-mall (.xlsx)** och **Calc-mall (.ods)**. Servern levererar faktiska kalkylblads- och OpenDocument-ZIP-filer från `GET /api/templates/xlsx` och `GET /api/templates/ods`; ingen arbetsfil skapas eller ändras på servern vid nedladdningen. Filerna innehåller sex blad enligt schema 1.3, med en liten **tydligt märkt DEMO-topologi**, explicita portar och länkar, MAC-adresser, access-/trunk-VLAN samt en statisk route. De är pedagogiska exempel, **inte fakta om användarens nätverk**. Byt ut demonstrationsuppgifterna innan mallen används som dokumentation. Filerna går att importera via den befintliga knappen **Importera**, men import och nedladdning sparar inte något projekt automatiskt.

Fel i de versionshanterade fälten kopplas nu när källpositionen är entydig till arbetsbokens **faktiska** rad och kolumn, exempelvis `Interfaces!F2 (mac)`, `Interfaces!H3 (accessVlan)` eller `StaticRoutes!D2 (nextHop)`. Även omordnade kolumner får rätt referens. Fel i en enskild ODS-/XLSX-cell och felaktiga tabellrubriker visar blad och position. När ett fel saknar entydig källa behålls det ursprungliga valideringsmeddelandet i stället för en gissad cell.

Se [mall- och felkontraktet](docs/SPREADSHEET_TEMPLATES.md).

## Versionshanterad XLSX-/ODS-import – MAC, VLAN och routes (PR #25)

De ursprungliga fyra tabellerna fortsätter att importeras som **schema 1.0** utan förändring. Ett uttryckligt blad `Project` med kolumnen `schemaVersion` och en enda datarad `1.3` aktiverar det nya formatet. `Interfaces` har då kolumnerna `nodeId,id,name,enabled,ipv4,mac,vlanMode,accessVlan,allowedVlans`, och det valfria bladet `StaticRoutes` har `nodeId,id,destination,nextHop,outPort`. Alla käll-ID:n och länkändpunkter bevaras; MAC-, VLAN- och routedata valideras mot den **befintliga** kanoniska modellen. Felaktiga versioner, next-hop utanför rätt subnät och motsägelsefulla switchkonfigurationer avvisas utan dataförlust.

XLSX och ODS delar samma versionskontrakt och samma existerande CSV-parser för grundobjekten. Inga nya kablar, MAC-adresser eller gateways skapas automatiskt. Separat användargodkännande och Save krävs fortfarande. Se [schema 1.3 för XLSX/ODS](docs/SPREADSHEET_V13.md).

## Import av strikt ODS-dokumentation (PR #24)

Builder kan nu importera **en riktig OpenDocument Spreadsheet-fil (`.ods`)** med tabellerna `Devices` (obligatorisk), `Interfaces`, `Links` och `Zones` (valfria). Tabellen använder **samma exakta kolumner** som CSV och XLSX, oberoende av tabell-/kolumnordning. ODS-formatet granskas med korrekt ZIP-`mimetype`, ODF-manifest, `content.xml` och strikta ODF-celltyper. Det accepterar explicita strängar, numeriska `x`/`y`-värden, booleska `enabled`-fält och tillåter tomt, upprepat fyllnadsmaterial i slutet av en tabell.

Formler, främmande tabeller, okända fält, dolda eller filtrerade rader/kolumner, makron, externa objekt, felaktiga referenser, sammanslagna celler och godtyckliga kalkylbladsformat avvisas. ODS utan versionsblad återanvänder `import_csv_tables` för **schema 1.0**; ett uttryckligt versionsblad aktiverar **schema 1.3** med MAC/VLAN/routes. Builder frågar uttryckligen innan arbetsytan ersätts och skriver ingen fil utan separat **Save**. Se [ODS-kontraktet](docs/ODS_IMPORT.md).

## Import av strikt XLSX-dokumentation (PR #23)

Builder kan nu importera **en XLSX-arbetsbok** med namngivna blad `Devices` (obligatoriskt), `Interfaces`, `Links` och `Zones` (valfria). Varje blad har exakt motsvarande CSV-tabells kolumner; kolumnordning och bladordning får variera. Det är **inte en generell Excel-importör**. Textidentiteter måste förbli textceller; numeriska celler stöds för `x`/`y`, booleanceller för `enabled`, och vanliga `inlineStr` och delade strängar stöds. Okända blad, formler, dolda rader/blad, sammanslagna celler, makron, externa länkar och extra workbookdelar avvisas. XLSX utan versionsblad importerar fortsatt **schema 1.0**; ett uttryckligt `Project`-blad aktiverar **schema 1.3**.

Import görs med **Importera**, en `.xlsx` och uttryckligt projektnamn. Servern konverterar de strikta OOXML-tabellerna till den **befintliga CSV-valideringen** och returnerar ett helt validerat dokument före något beslut om att ersätta arbetsytan. Användaren får därefter bekräfta, och **Save krävs separat** för att skriva till disk. Se [XLSX-kontraktet](docs/XLSX_IMPORT.md).

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

Okända fält, odeklarerade portar, ogiltiga referenser och malformed CSV avvisas helt. Exempel finns i `examples/csv/`. ODS och XLSX stöds nu i det **specifika fyrtabellsformatet**, men godtyckliga Excel-/ODS-/CSV-format stöds inte.

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
