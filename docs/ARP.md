# Avgränsad ARP-simulering över deklarerad Ethernet-topologi

**Status:** Fristående Python-funktion, inte kopplad till GUI, IPv4-paket eller ping. Ingen automatisk konfiguration eller migrering av projektformat.

`network_core.arp.ArpMessage` modellerar och kodar ett 28-byte ARP-meddelande enligt Ethernet/IPv4-varianten i RFC 826 (EtherType `0x0806`, hardware type 1, protocol type `0x0800`, hardware length 6, protocol length 4, opcode 1 eller 2). `serialize` och `parse` bevarar de deklarerade ARP-fälten exakt. Om ett meddelande kapslas i `EthernetFrame` används korrekt broadcast för request, unicast för reply och Ethernet-minimipadding. Avkodning accepterar endast kanonisk nollpadding och avvisar avvikande Ethernet- och ARP-adresser. Detta är en **avsiktligt strikt modell**, inte ett fullständigt stöd för varje ARP-variant.

`ArpSession(project, interface_macs=..., vlan_ports=...)` använder den **redan implementerade** `EthernetFabric`, utan en parallell topologi eller forwardingmotor. Om `vlan_ports` anges måste varje aktiv switchport konfigureras enligt [VLAN-kontraktet](VLAN.md); samma regler tillämpas på både request och reply. Utan `vlan_ports` används tidigare otaggad ARP-simulering utan VLAN-separering. Käll-IP hämtas från den **uttryckligen konfigurerade** IPv4/CIDR-adressen i projektets port. MAC-bindningen måste vara explicit: antingen det sparade `mac`-fältet i projektformat 1.1 eller `interface_macs={(node_id, port_id): "02:..."}` vid skapandet av sessionen. Förfrågan skickas som Ethernet-broadcast över aktiva, uttryckligt dokumenterade länkar. En icke-switchport som faktiskt nås, har exakt den efterfrågade IPv4-adressen och har en explicit MAC-bindning skickar ett ARP-reply. Den avsedda källporten måste verkligen nås av svaret för att MAC-adressen ska hamna i källportens ARP-cache. En senare fråga i samma session kan ge `CACHE_HIT` utan ny trafik.

### Sanningsgränser och negativa beteenden

- `RESOLVED` betyder att denna **begränsade simulerade ARP-utväxling** fick ett svar över deklarerade Ethernetlänkar, inte att IP-paket eller ping kan nå destinationen.
- `NO_ACTIVE_LINK` betyder att källportens deklarerade länk saknas eller är avstängd; ingen förfrågan sändes.
- `NO_REPLY` betyder att ingen i den **konfigurerade, nådda** broadcast-domänen svarade; det är inte ett påstående om ett verkligt nätverk.
- `UNKNOWN` betyder att matchande IP-port nåddes men saknar explicit MAC-bindning; inget svar får hittas på.
- Off-link IP, egen IP, odeklarerade källportar, saknad käll-IP/MAC och dubblerade deklarerade IP-adresser avvisas. Proxy ARP stöds inte.
- IPv4 ARP probes med `0.0.0.0`, multicast, **taggade slutvärds-NIC**, native VLAN, QinQ, IPv6 NDP, virtuella MAC-adresser, STP, IP-forwarding, ICMP, DHCP, ARP-aging, gratuitous ARP och riktiga NIC-paketfilter är **inte implementerade**. VLAN-trunkar representeras av Ethernetmotorns per-länk-metadata; ARP-dekodern accepterar fortfarande bara otaggade NIC-ramar.
- En switchloop avvisas av befintlig `EthernetFabric` tills korrekt loopkontroll finns. En router vidarebefordrar inte ARP-broadcast mellan sina gränssnitt.
- ARP-cachen, inlärda MAC-tabeller, VLAN-inställningar och sessionsspecifika MAC-bindningar sparas **inte**. Endast explicit dokumenterad port-MAC i schema 1.1 sparas efter användarens uttryckliga Save.
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

`tests/test_vlan_arp.py` verifierar VLAN 10/20-isolering, ARP över två switchar med trunk, svarsväg, tillståndsisolering, allowlist-drop, felaktig VLAN-konfiguration, avstängda portar, verklig Save/Open utan VLAN-lagring och att legacy ARP fungerar utan ny parameter. `tests/test_arp.py` prövar explicita RFC 826-headerbytes, request/reply-framekontrakt, verklig switchportsspridning, inlärning och källa-till-svar-väg, cache, avstängda länkar, saknad konfiguration, felaktiga payloads, duplicate IP och att ingen kommunikation uppfinns via router eller frånkopplad topologi. Samtliga övriga Python- och Chromium-regressioner ska fortsätta passera.
