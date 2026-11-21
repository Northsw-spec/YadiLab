# Ren nätverkslabb-app — kanonisk topologi

**Självständig nyimplementation.** Repositoryts tekniska namn är inte produktens namn. Ändra endast `APP_NAME` i `network_core/config.py` för att byta appens visningsnamn. Alla användarsynliga namn hämtas från den deklarationen. Ingen äldre produktkod har kopierats in.

Version 0.1 är en körbar lokal desktop/webb-hybrid för att dokumentera enheter, portar, zoner och **uttryckligen deklarerade** fysiska länkar. Grafspårningen är avsiktligt begränsad. Projekt lagras på riktigt i `.yadilab`-filer. Programmet fungerar helt lokalt utan npm-installation, moln eller tredjepartsbibliotek i runtime.

> **Dokumentstatus 2026-11-21:** README innehåller historiska etappbeskrivningar och är ännu inte en fullständigt uppdaterad funktionsmatris. För faktiskt nuläge gäller verifierad kod och CI. Den aktuella [kvalitetsfärdplanen QUALITY-000–011](docs/QUALITY_IMPROVEMENT_PLAN.md) är styrande för kommande kvalitetsarbete tillsammans med [AGENTS.md](AGENTS.md) och [MASTERPROMPT.md](docs/MASTERPROMPT.md). Den ersätter inte [importkontraktet](docs/IMPORT_SOURCE_CONTRACT.md) eller protokollens tekniska kontrakt. Tidigare kvalitetsanteckningar finns i [historikarkivet](docs/QUALITY_IMPROVEMENT_HISTORY.md).

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

Ännu inte implementerat: godtycklig kalkylbladsimport, beständig DHCP-leasedatabas och permanent klient-IPv4-konfiguration, DNS, brandväggsregler, ACL, fysisk kabeltyp, extern nätverksemulering, automatisk ELK-layout, portöverlappskontroll, multi-user, produktionsinstallatör och omfattande tillgänglighetsverifiering. Ingen funktion visar påhittade enheter eller kablar. Inga gamla simuleringsmotorer har förts över utan bevis.

## Avgränsad DHCPv4 DISCOVER/OFFER via HTTP (PR #29)

En ny read-only diagnos kan via `POST /api/dhcp/discover-offer` simulera en **DHCPDISCOVER** från en explicit vald hostport utan IP och en **DHCPOFFER** från en explicit vald serverport med MAC och IPv4/CIDR. Användaren anger också uttryckligen föreslagen ledig IPv4, transaktions-ID och leasetid. Bytekorrekt BOOTP/DHCP, UDP (68/67), IPv4-broadcast och checksummor skapas och valideras, och båda Ethernet-broadcasterna måste nå sina respektive portar via befintliga deklarerade kablar och VLAN. Olika broadcastdomäner och nedstängda länkar ger inget falskt erbjudande. **Ingen IP tilldelas, ingen lease skapas, inga projekt ändras eller sparas.** Detta **Discover/Offer-flöde i Builder** är inte DORA och saknar DHCPREQUEST/ACK; DORA-motorn finns separat via HTTP. Ingen DHCP-relay eller beständig adresskonfiguration stöds. I **Builder** finns nu panelen **DHCP – Discover / Offer** där klientport och serverport väljs ur de dokumenterade noderna, en föreslagen IPv4 anges tillsammans med transaktions-ID och leasetid, och faktiska transmissionsspår, VLAN-droppar, MAC-tabeller och resultat visas. Om ingen hostport saknar IPv4 eller ingen serverport har IPv4 kan simuleringen inte startas. Ett ändrat projekt eller ändrade indata tar bort tidigare resultat; fördröjda svar visas inte efter sådana ändringar. Se [DHCP-kontraktet](docs/DHCP_DISCOVER_OFFER.md).

## Bunden DHCPv4 DORA och tillfälliga simulerade leases (PR #31)

Det nya separata API:et `POST /api/dhcp/dora` utför nu den begränsade DHCP-sekvensen **DISCOVER → OFFER → REQUEST → ACK** med riktiga BOOTP/DHCP-optionsfält, IPv4- och UDP-checksummor och fyra genomgångar av den befintliga Ethernet-/VLAN-motorn. Användaren väljer en **uttrycklig sammanhängande pool på högst 256 adresser** i servergränssnittets dokumenterade subnät. Motorn väljer första tillgängliga adressen utan att använda dokumenterade interface-IP-adresser eller redan beviljade simulerade adresser i samma tillfälliga session. En `BOUND`-lease får skapas i minnet **endast om ACK faktiskt når klientporten**; vid kabel-/VLAN-avbrott skapas ingen lease.

**Detta är inte permanent IP-konfiguration:** projektets klient-IP förblir oförändrad och ingen fil skrivs. Varje HTTP-anrop börjar med tomt leasetillstånd, medan `DhcpSession` kan genomföra flera tilldelningar under en och samma Python-simuleringssession. Förnyelse, NAK, relay, DHCP-discovery av server, verklig adresskonfliktsdetektion och beständig lease-hantering återstår. I **Builder** finns nu också ett separat **DORA-labb** med explicita klient-/servergränssnitt, poolens start-/slutadress, transaktions-ID och leasetid. Resultatet visar verkliga modellerade kabel-/VLAN-spår för alla fyra meddelanden och simulerad BOUND-lease **endast om ACK nådde klientporten**. Ogiltiga indata och äldre HTTP-svar ger aldrig en sparad eller falsk lease. Engångsknappen börjar alltid med tom lease-tabell. De nya sessionsknapparna kan däremot behålla leases mellan olika klientkörningar i samma processlokala DHCP-session. Den äldre Builder-panelen fortsätter att visa endast Discover/Offer. Läs [DORA-kontraktet](docs/DHCP_DORA.md).

## Flera DHCP-klienter i samma simuleringssession (PR #33)

Builder har nu **Starta DHCP-session**, **Tilldela vald klient**, **Nollställ leases** och **Avsluta session** i DORA-panelen. Vid start binds den valda **serverporten och adresspoolen** till den aktuella, validerade projektsnapshoten. Flera uttryckligt dokumenterade klienter kan sedan köras mot samma pool och tilldelas olika adresser via befintlig fullständig DHCP DORA. Panelen visar operationer, observerade överföringar och hela simulerade BOUND-leasetabellen. Redan tilldelade klienter kan inte få en dubbel lease, och en tömd pool ger ett begripligt fel utan att radera tidigare leases. Nollställ tömmer inlärning och leasetabell; Avsluta frigör sessionen.

Backendens endpoints är `POST /api/dhcp/session/start`, `/run`, `/reset` och `/stop`. Varje session använder en slumpmässig session-ID, har högst 256 operationer och är bunden till exakt projektsnapshot; max 16 DHCP-sessioner ryms i en serverprocess. Samtidiga anrop serialiseras. En ändrad topologi eller ett nytt projekt avslutar den gamla UI-sessionen och servern avvisar anrop med felaktig projektsignatur. **Sessionerna är enbart i serverns arbetsminne**, försvinner vid omstart, påverkar inte annan engångssimulering och skriver aldrig projektfilen. Inga lease-timers, förnyelser, ARP-konfliktprober eller verkliga klient-IP-ändringar har införts. Se [DORA-kontraktet](docs/DHCP_DORA.md).

## Deterministisk simuleringsklocka och DHCP-lease-expiration (PR #34)

Den delade DHCP-sessionen har nu en **virtuell klocka** som startar på **0 sekunder**. En bekräftad `ACK_RECEIVED` skapar en BOUND-lease med `startedAtSeconds`, `expiresAtSeconds` och `remainingSeconds`. Den nya knappen **Flytta fram DHCP-klockan** tar ett uttryckligt heltal **1–604800 sekunder** och flyttar fram simulerad tid utan att invänta verklig tid. Ett exakt tidsgränsfall gäller: leasen är aktiv före sluttiden och markeras `EXPIRED` samt tas bort ur aktiva leases vid `clockSeconds >= expiresAtSeconds`. Så frigjorda adresser kan tilldelas en annan klient via **en ny verklig DORA-sekvens**; en ursprunglig klient får också göra ny DORA efter expiration. Det är en **ny tilldelning** och skiljer sig från T1/T2-förnyelsen av en ännu aktiv lease.

API:et `POST /api/dhcp/session/advance` kräver exakt `sessionId`, `project` och `seconds`. Svaret ger `clockSeconds`, aktiva `leases` med återstående tid, och `expiredLeases` från just detta tidssteg. Ett steg räknas som en sessionoperation. Den processlokala simuleringsklockan är högst 315360000 sekunder; ogiltiga, bakåtriktade eller alltför stora steg avvisas utan att leasetabell eller klocka ändras. Nollställning sätter både tid och leases till 0/tomma. Det finns inga timers, bakgrundstrådar för klockan, verklig väntetid, **automatiska** renewals, NAK eller reell IP-leasekonfiguration. T1/T2-förnyelse kräver ett särskilt knapptryck och verifierade DHCP-paket (se nästa avsnitt). Dokumenterade klient-IP:n och filernas diskbytes är oförändrade.

## DHCP lease renewal vid T1 och T2 (PR #35)

I **Builder → DHCP-session** kan användaren nu klicka **Förnya vald lease (T1/T2)**. Knappen är aktiv först efter att vald klient fått en faktiskt ACK-bekräftad, ännu giltig lease och den **virtuella klockan** nått den aktuella förnyelsegränsen. Serverns givna leasetid används; det finns ännu ingen option 58/59 i DHCPACK och standardgränserna beräknas deterministiskt: `T1 = ceil(leaseSeconds / 2)` och `T2 = ceil(7 × leaseSeconds / 8)`. Ett framflyttat tidsvärde **skickar aldrig automatiskt DHCPREQUEST**.

Vid **T1 (RENEWING)** skickas ett riktigt serialiserat DHCPREQUEST med tidigare leasade IP i BOOTP-`ciaddr`, utan option 50/54, som **unicast till den ursprungligen valda serverns dokumenterade MAC/IP**. Vid **T2 (REBINDING)** skickas samma typ av korrekt DHCPREQUEST som **broadcast** i den dokumenterade Layer 2-/VLAN-domänen. En korrekt unicast-DHCPACK till klientens IP/MAC får förlänga leasen endast efter faktisk mottagning på klientens deklarerade port. Missad REQUEST eller ACK lämnar **exakt samma adress och expiration**; leasen löper ut enligt vanlig simulerad tid om inget ACK kommer. Framgångsrik förnyelse nollställer `startedAtSeconds`, `expiresAtSeconds`, T1/T2 och ökar `renewalCount` medan IP-adressen förblir densamma. Loggarna visar verkligt simulerade överföringar, VLAN-droppar och DHCP-status.

API:et `POST /api/dhcp/session/renew` kräver exakt `sessionId`, `project`, `clientNode`, `clientPort` och `transactionId`. Ogiltig klient, projektsnapshot, transaktions-ID, för tidig renewal, redan utgången lease eller överskriden sessionsbudget avvisas. En T2-broadcast får i detta **avsiktligt begränsade enserverlabb** endast svar från den explicit valda DHCP-servern; vi påstår inte stöd för konkurrerande servrar, DHCP-relay eller IP-routing mellan subnät. Inga automatiska retries, NAK, ARP-konfliktprober, verkliga klient-IP-ändringar eller skrivningar till projektfilen införs. Läs [DHCP-protokollkontraktet](docs/DHCP_DORA.md).

## Tillfälliga kabelavbrott i en aktiv DHCP-session (PR #36)

I Builder kan användaren nu välja en **ursprungligen aktiv, dokumenterad kabel** och klicka **Bryt kabel i sessionen** eller **Återställ kabel i sessionen**. Avbrottet ändrar **endast den pågående DHCP-sessionens EthernetFabric**: båda kabelriktningarna kopplas bort/återställs, och switcharnas tidigare inlärda MAC-tabeller töms vid varje övergång. Nätverkets kanoniska länkar, portstatus och projektfilens bytes ändras aldrig. Detta är **inte en ändring av nätverksdokumentationen** och inte ett verkligt nätverkskommando.

**Praktiskt labb:** Kör verklig DORA tills en klient fått ACK och en BOUND-lease. Bryt därefter serverns dokumenterade kabel. Vid T1 skickas fortfarande ett giltigt DHCPREQUEST som unicast; switchen kan flooda okänd unicast till andra aktiva portar efter att MAC-tabellen tömts, men **serverporten nås inte** och ingen lease förlängs. Vid T2 går DHCPREQUEST som broadcast i de faktiska återstående kablarna, men kan fortfarande inte nå den frånkopplade servern. Leasen upphör vid den gamla sluttiden när användaren flyttar fram den virtuella tiden. Återställ kabeln; en ny korrekt DORA kan då tilldela en frigjord IP. Återställning innan expiration kan också möjliggöra en korrekt ACK-bekräftad T1-/T2-förnyelse.

API `POST /api/dhcp/session/link-fault` kräver exakt `sessionId`, `project`, `linkId` och `disabled` (äkta boolean). Kabeln måste ha varit aktiv redan vid sessionens start; okända, från början inaktiva och redan i begärt tillstånd avvisas. Operationer serialiseras, räknas mot sessionsbudgeten (max 256) och framträder i `faultedLinks` för alla sessionssvar. Felaktig projektsnapshot avvisas. **Nollställ** tar bort avbrott, leases, MAC-inlärning och simulerad tid; **Avsluta** frigör sessionen. Separata simulatoranrop och andra DHCP-sessioner påverkas inte.

## Administrativt switchportavbrott och access-VLAN-isolering (PR #37)

DHCP-sessionens **felinjicering** stöder nu tre separata, tillfälliga operationstyper: kabelavbrott (PR #36), **administrativt avstängd switchport** och **felaktig access-VLAN-tilldelning**. Alla ändringar gäller endast sessionens EthernetFabric och påverkar inte kanonisk topologi, klient-IP, VLAN-dokumentation eller sparade projektbytes.

**Portfel:** Välj en dokumenterad och ursprungligen aktiv *switchport* och klicka **Stäng switchport i sessionen**. Motorn tar bort de två riktade förbindelserna genom porten. **Aktivera switchport i sessionen** återställer bara portavbrottet; en separat kabelfel-injektion på samma länk fortsätter att gälla. MAC-tabeller töms på varje tillståndsändring. Om porten stängs efter mottaget DORA-ACK får klienten behålla den tidigare BOUND-leasen till dess sluttid, men T1/T2-REQUEST når inte servern om den verkliga dokumenterade vägen nu är blockerad.

**VLAN-fel:** Välj en aktiv, hostansluten **accessport med uttryckligen dokumenterat VLAN** och ett annat VLAN-ID som **redan förekommer i projektets switchkonfiguration**. **Isolera port med fel VLAN** ändrar bara sessionens forwardingmedlemskap. Vi skapar aldrig ett odokumenterat VLAN eller trunkkonfiguration. Efter isolering ser DHCP-simulatorn inga server-REQUEST/ACK över VLAN-gränsen om servern ligger kvar i det ursprungliga VLAN:et. **Återställ ursprungligt VLAN** återställer sessionens ursprungliga medlemskap och tömmer inlärda MAC-tabeller. Saknas VLAN-data i dokumentationen visas inga valbara VLAN-fel.

Två strikta API-anrop `POST /api/dhcp/session/port-fault` (`sessionId, project, nodeId, portId, disabled`) och `POST /api/dhcp/session/vlan-fault` (`sessionId, project, nodeId, portId, vlanId`) kräver den låsta projektsnapshoten. `disabled` måste vara boolean; `vlanId` måste vara dokumenterat heltal, medan JSON `null` återställer accessportens ursprungliga VLAN. Felaktig eller redundant operation avvisas utan ändring eller förbrukad sessionsbudget. Giltiga operationer räknas mot den befintliga gränsen på 256, serialiseras och syns i `faultedPorts` respektive `faultedAccessVlans`. **Nollställ** tar bort både kabel-, port- och VLAN-fel och återställer simuleringsklocka/leasetabell, utan Save. Funktionerna avser dokumenterade Layer 2-situationer och påstår inte verklig kommunikation, spanning tree, DHCP-relay eller routad leverans.

## Interaktivt DHCP-felsökningslabb: Process of Elimination (PR #38)

Öppna **Builder → Felsökningslabb** och välj först ett uttryckligen dokumenterat klientgränssnitt, en DHCP-server, en giltig adresspool och leasetid i DHCP-panelen ovanför. Klicka **Starta dolt felsökningsfall**. Backend använder samma kanoniska projekt, `DhcpLabSession`, riktiga DHCPDISCOVER/OFFER/REQUEST/ACK och **en faktisk ACK-bekräftad lease**. Först när baseline-verifieringen lyckas flyttas den **virtuella klockan till T1** och ett enda dolt, simulerat fel injiceras. Misslyckas baseline med att nå servern eller klienten avvisas scenariot; ingen fingerad fungerande nätverkskoppling skapas.

Ett scenario väljs mellan de **fel som just den dokumenterade topologin faktiskt kan stödja**: en frånkopplad deklarerad kabel, en administrativt avstängd dokumenterad switchport eller en hostansluten accessport med annat **redan dokumenterat** VLAN. Om ingen VLAN-konfiguration finns skapas aldrig ett VLAN-fel. Resultatet av scenariostarten visar **inte** feltyp, felpunkt eller intern DHCP-session. Det finns ingen publicerad endpoint som listar de dolda felinjektionerna.

Genomför fem verkligt avgränsade observationstyper efter eget val: (1) BOUND-lease/T1/T2 och kvarvarande tid, (2) **skicka DHCPREQUEST** och observera om det når servern och om ACK återvänder, (3) mät observerad länkstatus på en vald verklig kabel, (4) läs switchportens simulerade administrativstatus och operativa länkstatus, (5) jämför dokumenterat mot faktiskt simulerat access-VLAN på vald switchport. Paketspår och MAC-forwarding kommer från den befintliga Ethernet/DHCP-motorn, inte från förberedda positiva svar. Observationerna är **SIMULATED**, inte mätningar av verkliga nätverksutrustningar. Länk `DOWN` räcker inte ensamt för att avgöra om kabeln eller porten är orsak: kontrollera fler variabler.

Efter ett **faktiskt DHCPREQUEST** och minst två **olika andra typer av kontroller** kan du pröva hypoteserna **kabelavbrott**, **administrativt stängd switchport** eller **VLAN-inkonsekvens**. Fel gissning returnerar endast att diagnosen inte stämmer; själva svaret avslöjas inte och högst tre gissningar tillåts. Efter korrekt diagnos kan användaren uttryckligen klicka **Återställ identifierat fel och testa riktig DHCPACK**. Backend återställer då enbart sitt ursprungliga simuleringsfel, skickar en ny riktig DHCPREQUEST och anser reparationen verifierad **endast** om korrekt ACK faktiskt når klientporten och leasen förlängs. Ingen fil, klient-IP eller dokumenterad kabel/port/VLAN ändras; inga OS-kommandon skickas. Start/probe/diagnose/repair/stop är strikt projektsnapshot-bundna och processlokala; en projektändring eller serveromstart ogiltigförklarar övningen. Se [protokollkontraktet](docs/DHCP_DORA.md).

**Avgränsningar (ursprunglig PR #38):** Den första nivån är fortfarande ett **T1-förnyelsefel med ett dolt Layer 1/2-fel**. PR #39 utökar samma övning med explicita T2- och expiration-steg på högre nivåer; inga automatiska DHCP-retries eller påståenden om fullständig nätverksfelsökning införs. De fristående DHCP-sessionerna stöder fortsatt sina egna T1/T2- och expiration-operationer.

## Felsökningsnivåer: DHCP T1 → T2 → expiration → ny DORA (PR #39)

Felsökningsövningen från PR #38 har nu **tre explicita svårighetsgrader**. Alla startar i ett dokumenterat nät som först måste leverera en **riktig, kodad DHCPACK** till klienten. Den virtuella tiden når T1 innan ett dolt Layer 1/2-fel injiceras. Inga nätfakta eller dolda felkällor skickas till användaren innan verifierad lösning.

- **Grund – T1 (`T1_ONLY`)**: undersök unicast-DHCPREQUEST vid T1, jämför mätresultat, ställ diagnos och verifiera ACK-bekräftad lease-förnyelse. Ingen tidsframflyttning i denna nivå.
- **Medel – T1 till T2 (`T2_REBIND`)**: observera först det **verkligt skickade** T1-REQUEST, flytta därefter explicit den virtuella klockan till exakt T2 och skicka ett nytt **broadcast DHCPREQUEST**. Diagnos kräver faktiskt observerat T2-försök. Inget tillstånd får överskrida T2 i denna nivå. Reparation före expiration kräver ett verkligt DHCPACK och förnyar samma BOUND-lease.
- **Avancerad – T1, T2 och expiration (`EXPIRY_RECOVERY`)**: observera ett riktigt T1-försök, flytta till T2, observera ett riktigt T2-försök och flytta sedan till den **exakta sluttiden**. Där tar befintliga DHCP-motorn bort den utgångna leasen, som visas som **EXPIRED, återstående tid 0**. Efter expiration **avvisas renewal**; användaren behöver identifiera rotorsaken och beställa **ny fyrastegs-DORA**. Endast faktiskt levererad DISCOVER → OFFER → REQUEST → ACK skapar då en ny BOUND-lease. Testet skiljer uttryckligen ny tilldelning från att förlänga en gammal lease.

Använd **Flytta klockan till T2/lease-expiration** för tidsförloppet. Knappen aktiveras först när den relevanta fasens riktiga DHCPREQUEST har skickats och observerats. Att flytta tid skickar **aldrig** DHCP-paket automatiskt, förlänger aldrig en lease och avslöjar inte vilket dolt fel som injicerats. Nätets operativa kabel-, port- och VLAN-tillstånd mäts fortfarande med samma `EthernetFabric`.

API: `POST /api/dhcp/investigation/start` accepterar nu ett **valfritt** uttryckligt `difficulty` med exakt något av `T1_ONLY`, `T2_REBIND`, `EXPIRY_RECOVERY` (uteblivet fält betyder `T1_ONLY`). `POST /api/dhcp/investigation/advance` kräver exakt `sessionId`, ursprungligt `project` och positivt heltal `seconds`. För tidiga hopp, hopp över nivåns sluttid, otillåtna typer och försök att använda renewal efter expiration avvisas utan falsk ACK eller ändring av dokumentationen. `probe lease` kan efter expiration visa ett historiskt, utgånget objekt; det är **inte** en aktiv IP-tilldelning. `repair` anger `verifiedProtocol=RENEWAL` eller `verifiedProtocol=NEW_DORA` och endast verifierat verkligt simulerat ACK resulterar i `RECOVERED`.

Varken den kanoniska modellen, riktiga klient-NIC:ar, virtuellt okontrollerat bakgrundsarbete eller sparade projektbytes påverkas. Avancerad nivå inför inte DHCP-relay, riktiga konkurrerande DHCP-servrar, ICMP/routing-felsökning eller automatisk DHCP-retry; detta är fortsatt ett **avgränsat** praktiskt DHCPv4-labb.

## Dolt routing- och Layer 2-felsökningslabb

Builder har en ny **Process of Elimination**-övning för en redan fungerande, uttryckligen dokumenterad tvåvägs-IPv4-kommunikation. Välj klientgränssnitt med dokumenterad IPv4, mål-IP och TTL. Start kräver att den riktiga befintliga `EchoExchange` faktiskt levererar **ICMP Echo Request och korrekt matchad Echo Reply**, genom den existerande IPv4-routing-, ARP-, Ethernet- och VLAN-motorn. Enbart grafväg, adresslikhet eller route lookup räcker aldrig. Om baslinjen redan är trasig avvisas övningen.

Motorn väljer därefter **ett enda dolt fel som redan har bevisats orsaka ett misslyckat Echo-utbyte och vars återställning ger ett nytt fungerande Echo-utbyte** i den befintliga kontrollmotorn `compare_fault`. Den väljer endast bland verkliga dokumenterade och topologiskt tillämpliga förändringar:

- **Layer 2: kabelavbrott** på en kabel som faktiskt användes vid baslinjens riktiga paketöverföringar.
- **Layer 1/2: administrativt avstängd switchport** på en port som användes av den faktiskt simulerade ICMP-baslinjen, och endast om fel och återställning verifierats.
- **Layer 2: fel access-VLAN** på en använd switchport, och bara till ett annat VLAN-ID som redan finns dokumenterat i nätet.
- **Layer 3: borttagen statisk route** som faktiskt bryter framåt- eller returkommunikationen.
- **Layer 3: fel IPv4-prefix/nätmask** på ett dokumenterat, aktivt gränssnitt i en observerad paketväg. En snävare mask är tillåten bara efter korrekt kontroll av next-hop och verifierad påverkan på ICMP tur och retur.
- **Layer 3: fel statisk next-hop** på en route som faktiskt användes i den fungerande ICMP-baslinjen. Ett annat, on-link, odokumenterat gränssnittsvärde injiceras avsiktligt; det godkänns som fel först när motorn visar `ARP_FAILED`/`NO_REPLY` och verkligt simulerad återhämtning efter återställning. Adressen är inte påstådd riktig utrustning.

Användaren får **inte** veta feltyp, nod, port eller route vid start. I Builder finns explicita mätningar: dokumenterad IPv4 och DHCP-bevisläge; enhetsbaserad routingtabell med longest-prefix match och dokumenterad/simulerad statisk next-hop (inklusive val av returväg); verklig ICMP Echo med sändningsstatus, ARP-status och faktiskt använda kablar/VLAN-droppar; original mot aktuellt simulerat kabeltillstånd; dokumenterad kontra simulerad administrativ portstatus och IPv4/CIDR; original mot aktuellt simulerat VLAN. Inga råa muterbara projektobjekt eller dolda sessionsfel lämnas via start eller mätning. Observationer är markerade **SIMULATED** eller **SIMULATED_CONFIG**, inte verklig hårdvarutelemetri.

**Viktig kunskapsgräns:** Nuvarande kanoniska modell dokumenterar en IPv4/CIDR men **inte adressens tilldelningsursprung**. En konfigurerad adress kan alltså inte påstås vara *statisk* eller *från DHCP* enbart utifrån värdet. IP-kontrollen rapporterar därför `dhcpAddressOrigin=UNKNOWN` och `dhcpCheck=NOT_VERIFIED`. Detta routing- och Layer 2-labb är inte ett sammanvävt DHCP-felcase; använd det separata riktiga DHCP-labbet för att testa DHCP-lease och DORA. Inga felaktiga uteslutningar eller falska success-svar förekommer.

Före diagnos krävs minst **ett faktiskt misslyckat ICMP Echo**, en **routingtabellsfråga** och minst en tredje oberoende kontroll (IP, kabel, port eller VLAN). Felaktiga hypoteser får ingen facitinformation; högst tre försök. Efter korrekt hypotes kan användaren uttryckligen begära **Återställ och verifiera**. Motorn gör då två oberoende nya paketsimuleringar: fortfarande misslyckat Echo med felet och en **verklig matchad ICMP Echo Reply** efter återställning till ursprunglig dokumentation. Först då visas `RECOVERED`, korrekt felkategori och den specifika simulerade reparationspunkten. Utan framgång visas `NOT_VERIFIED`.

Fem nya, strikta, sessionsbundna API-operationer finns under `/api/icmp/investigation/`: `start`, `probe`, `diagnose`, `repair`, `stop`. Samtliga data finns enbart i serverminnet och är bundna till oförändrad, validerad projektsnapshot; max 16 samtidiga sessioner, 48 mätningar och 3 hypoteser. Inget ändrar arbetsytan, sparade projektbytes, riktig NIC-konfiguration eller andra sessioner. Webbgränssnittet stoppar övningen och avvisar sena svar vid ändring av kanonisk dokumentation. Se [protokollkontrakt och avgränsningar](docs/ICMP_INVESTIGATION.md).

**Ej modellerat:** DHCP-ursprungsbevis utifrån statisk IPv4-dokumentation, automatisk klientkonfiguration, NAT, dynamiska routingprotokoll, verkliga brandväggsbeslut, DNS, RTT och live-paketmätningar. De åtgärderna kräver särskild verifierbar motormodell och får inte presenteras som implementerade.

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
