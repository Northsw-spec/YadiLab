# Avgränsad ARP-simulering över deklarerad Ethernet-topologi

**Status:** Fristående Python-funktion, inte kopplad till GUI, IPv4-paket eller ping. Ingen automatisk konfiguration eller migrering av projektformat.

`network_core.arp.ArpMessage` modellerar och kodar ett 28-byte ARP-meddelande enligt Ethernet/IPv4-varianten i RFC 826 (EtherType `0x0806`, hardware type 1, protocol type `0x0800`, hardware length 6, protocol length 4, opcode 1 eller 2). `serialize` och `parse` bevarar de deklarerade ARP-fälten exakt. Om ett meddelande kapslas i `EthernetFrame` används korrekt broadcast för request, unicast för reply och Ethernet-minimipadding. Avkodning accepterar endast kanonisk nollpadding och avvisar avvikande Ethernet- och ARP-adresser. Detta är en **avsiktligt strikt modell**, inte ett fullständigt stöd för varje ARP-variant.

`ArpSession(project, interface_macs=...)` använder den **redan implementerade** `EthernetFabric`, utan en parallell topologi eller forwardingmotor. Käll-IP hämtas från den **uttryckligen konfigurerade** IPv4/CIDR-adressen i projektets port. MAC-bindningen måste alltid skickas uttryckligen som `{(node_id, port_id): "02:..."}` och är bara sessionstillstånd. Förfrågan skickas som Ethernet-broadcast över aktiva, uttryckligt dokumenterade länkar. En icke-switchport som faktiskt nås, har exakt den efterfrågade IPv4-adressen och har en explicit MAC-bindning skickar ett ARP-reply. Den avsedda källporten måste verkligen nås av svaret för att MAC-adressen ska hamna i källportens ARP-cache. En senare fråga i samma session kan ge `CACHE_HIT` utan ny trafik.

### Sanningsgränser och negativa beteenden

- `RESOLVED` betyder att denna **begränsade simulerade ARP-utväxling** fick ett svar över deklarerade Ethernetlänkar, inte att IP-paket eller ping kan nå destinationen.
- `NO_ACTIVE_LINK` betyder att källportens deklarerade länk saknas eller är avstängd; ingen förfrågan sändes.
- `NO_REPLY` betyder att ingen i den **konfigurerade, nådda** broadcast-domänen svarade; det är inte ett påstående om ett verkligt nätverk.
- `UNKNOWN` betyder att matchande IP-port nåddes men saknar explicit MAC-bindning; inget svar får hittas på.
- Off-link IP, egen IP, odeklarerade källportar, saknad käll-IP/MAC och dubblerade deklarerade IP-adresser avvisas. Proxy ARP stöds inte.
- IPv4 ARP probes med `0.0.0.0`, multicast, VLAN, IPv6 NDP, virtuella MAC-adresser, STP, IP-forwarding, ICMP, DHCP, ARP-aging, gratuitous ARP och riktiga NIC-paketfilter är **inte implementerade**.
- En switchloop avvisas av befintlig `EthernetFabric` tills korrekt loopkontroll finns. En router vidarebefordrar inte ARP-broadcast mellan sina gränssnitt.
- ARP-cachen, MAC-tabeller och explicit tilldelade MAC-adresser finns enbart i denna session och sparas **inte** automatiskt i `.yadilab`-projektet.

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

`tests/test_arp.py` prövar explicita RFC 826-headerbytes, request/reply-framekontrakt, verklig switchportsspridning, inlärning och källa-till-svar-väg, cache, avstängda länkar, saknad konfiguration, felaktiga payloads, duplicate IP och att ingen kommunikation uppfinns via router eller frånkopplad topologi. Samtliga övriga Python- och Chromium-regressioner ska fortsätta passera.
