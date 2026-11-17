# Avgränsad ARP-simulering över deklarerad Ethernet-topologi

**Status:** Pythonbaserad ARP-funktion med en avgränsad HTTP-/GUI-diagnostik. Ingen IP-paketforwarding eller ping. Ingen automatisk konfiguration eller migrering av projektformat.

`network_core.arp.ArpMessage` modellerar och kodar ett 28-byte ARP-meddelande enligt Ethernet/IPv4-varianten i RFC 826 (EtherType `0x0806`, hardware type 1, protocol type `0x0800`, hardware length 6, protocol length 4, opcode 1 eller 2). `serialize` och `parse` bevarar de deklarerade ARP-fälten exakt. Om ett meddelande kapslas i `EthernetFrame` används korrekt broadcast för request, unicast för reply och Ethernet-minimipadding. Avkodning accepterar endast kanonisk nollpadding och avvisar avvikande Ethernet- och ARP-adresser. Detta är en **avsiktligt strikt modell**, inte ett fullständigt stöd för varje ARP-variant.

`ArpSession(project, interface_macs=..., vlan_ports=...)` använder den **redan implementerade** `EthernetFabric`, utan en parallell topologi eller forwardingmotor. Om `vlan_ports` anges, **eller om projektformat 1.2 innehåller sparade VLAN på switchportar**, måste varje aktiv och ansluten switchport konfigureras enligt [VLAN-kontraktet](VLAN.md). Samma regler tillämpas på request och reply. Utan `vlan_ports` används tidigare otaggad ARP-simulering utan VLAN-separering. Käll-IP hämtas från den **uttryckligen konfigurerade** IPv4/CIDR-adressen i projektets port. MAC-bindningen måste vara explicit: antingen det sparade `mac`-fältet i projektformat 1.1 eller `interface_macs={(node_id, port_id): "02:..."}` vid skapandet av sessionen. Förfrågan skickas som Ethernet-broadcast över aktiva, uttryckligt dokumenterade länkar. En icke-switchport som faktiskt nås, har exakt den efterfrågade IPv4-adressen och har en explicit MAC-bindning skickar ett ARP-reply. Den avsedda källporten måste verkligen nås av svaret för att MAC-adressen ska hamna i källportens ARP-cache. En senare fråga i samma session kan ge `CACHE_HIT` utan ny trafik.

### GUI/HTTP – en isolerad ARP-körning

Användaren väljer ett uttryckligen deklarerat icke-switchgränssnitt och fyller i mål-IPv4. `POST /api/diagnostics/arp` kräver exakt `{"project", "sourceNode", "sourcePort", "targetIpv4"}` och skapar en helt **ny** `ArpSession(project)` för detta enda anrop. Ingen källfil läses eller skrivs och inga cacheträffar från tidigare anrop finns. Svaret innehåller `result` från `ArpSession.resolve`, verklig `arpTable` från avsändaren, `macTables` med **enbart MAC-adresser som denna session lärt på inkommande switchportar**, samt `ephemeral: true`.

Builder visar status (`RESOLVED`, `NO_REPLY`, `UNKNOWN`, `NO_ACTIVE_LINK`), faktiska request-/reply-transmissioner, VLAN-droppar och inlärda switch-MAC-/ARP-tabeller. Endast faktiskt traverserade länkar markeras. Vid invalid projekt, felaktig IPv4 eller saknad explicit MAC/IP visas ett avvisningsfel, aldrig ett fabricerat svar. Ändrad dokumentation rensar tidigare diagnostik. Ett `RESOLVED`-resultat visar en lyckad simulerad ARP-utväxling, **inte** ping, IP-routing eller NIC-acceptans. Det finns fortfarande ingen beständig ARP-session eller interaktiv flerpaketssimulering.

### Fortsatta sessioner med bevarad inlärning

Den tidigare `/api/diagnostics/arp` fortsätter avsiktligt att skapa en ny, isolerad session per anrop. För **stegvis felsökning** tillhandahåller `/api/simulation/start`, `/api/simulation/run`, `/api/simulation/reset` och `/api/simulation/stop` en uttryckligen startad, tillfällig session som delar exakt samma `ArpSession` och `EthernetFabric` under flera ARP-/Ethernetoperationer. Detta möjliggör observerbara cacheträffar och switch-MAC-inlärning utan dubbla forwardingmotorer. HTTP-servern avvisar ändrat projekt, okända sessioner och ogiltiga operationer; klienten avslutar sessionen när dokumentationen redigeras. Se [SIMULATION_SESSION.md](SIMULATION_SESSION.md) för kontrakt, begränsningar och felutfall.

### Sanningsgränser och negativa beteenden

- `RESOLVED` betyder att denna **begränsade simulerade ARP-utväxling** fick ett svar över deklarerade Ethernetlänkar, inte att IP-paket eller ping kan nå destinationen.
- `NO_ACTIVE_LINK` betyder att källportens deklarerade länk saknas eller är avstängd; ingen förfrågan sändes.
- `NO_REPLY` betyder att ingen i den **konfigurerade, nådda** broadcast-domänen svarade; det är inte ett påstående om ett verkligt nätverk.
- `UNKNOWN` betyder att matchande IP-port nåddes men saknar explicit MAC-bindning; inget svar får hittas på.
- Off-link IP, egen IP, odeklarerade källportar, saknad käll-IP/MAC och dubblerade deklarerade IP-adresser avvisas. Proxy ARP stöds inte.
- IPv4 ARP probes med `0.0.0.0`, multicast, **taggade slutvärds-NIC**, native VLAN, QinQ, IPv6 NDP, virtuella MAC-adresser, STP, IP-forwarding, ICMP, DHCP, ARP-aging, gratuitous ARP och riktiga NIC-paketfilter är **inte implementerade**. VLAN-trunkar representeras av Ethernetmotorns per-länk-metadata; ARP-dekodern accepterar fortfarande bara otaggade NIC-ramar.
- En switchloop avvisas av befintlig `EthernetFabric` tills korrekt loopkontroll finns. En router vidarebefordrar inte ARP-broadcast mellan sina gränssnitt.
- ARP-cachen, inlärda MAC-tabeller och sessionsspecifika VLAN-/MAC-bindningar sparas **inte**. Däremot kan användaren spara explicit VLAN-konfiguration på switchportar i schema 1.2. Endast explicit dokumenterad port-MAC i schema 1.1 sparas efter användarens uttryckliga Save.
- Om VLAN-trunkens ingress förbjuder en VLAN-tagg rapporteras `NO_REPLY` (om inget giltigt svar nås), med `requestVlanDrops`/`replyVlanDrops` som faktiskt observerade Ethernet-droporsaker. MAC-cache uppdateras endast när ARP-svaret når tillbaka till deklarerad källport. En separat session behövs efter topologi-/konfigurationsändring.
- Dubblerade deklarerade IPv4-adresser avvisas fortfarande globalt även om adresserna skulle ligga i skilda VLAN. Dubblerade IP per VLAN är ännu inte definierat i denna begränsade modell.

### Exempel (Python-API)

```python
from network_core.arp import ArpSession

session = ArpSession(
    documented_project,
    interface_macs={
        ("pc-1", "eth0"): "02:00:00:00:00:01",
        ("pc-2", "eth0"): "02:00:00:00:00:02",
    },
)
result = session.resolve("pc-1", "eth0", "192.0.2.20")
print(result["status"], session.arp_table("pc-1", "eth0"))
```

Exemplet förutsätter att projektet **redan** deklarerar båda porter, deras IPv4-adresser och en fungerande fysisk L2-väg. Det skapar inga enheter, kablar eller IP-adresser.

### Verifiering

`tests/test_arp_diagnostics_http.py` verifierar verklig loopback-HTTP, VLAN-trunk, förlorade svar, negativ indata, att en ny session startas per begäran, faktiska switchtabeller och ingen filmutation. `tests/browser_smoke.py` verifierar GUI-inmatning, positiv ARP över access-VLAN 10, negativt ARP efter ändring av switchporten till VLAN 20 och oförändrad sparad fil. `tests/test_vlan_arp.py` verifierar VLAN 10/20-isolering, ARP över två switchar med trunk, svarsväg, tillståndsisolering, allowlist-drop, felaktig VLAN-konfiguration, avstängda portar, verklig Save/Open utan VLAN-lagring och att legacy ARP fungerar utan ny parameter. `tests/test_arp.py` prövar explicita RFC 826-headerbytes, request/reply-framekontrakt, verklig switchportsspridning, inlärning och källa-till-svar-väg, cache, avstängda länkar, saknad konfiguration, felaktiga payloads, duplicate IP och att ingen kommunikation uppfinns via router eller frånkopplad topologi. Samtliga övriga Python- och Chromium-regressioner ska fortsätta passera.
