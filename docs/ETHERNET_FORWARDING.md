# Isolerad Layer 2-kärna: MAC-forwarding

**Status:** Delvis implementerad, endast Python-API. Ännu ingen anslutning till användargränssnittet eller nätverksprotokollstacken.

Modulen `network_core/ethernet.py` implementerar en *deterministisk MAC-forwardingmodell*, inte ett komplett Ethernet-, ARP-, VLAN-, IP- eller pingprotokoll.

## Indata och sanning

1. `EthernetFabric(project)` validerar det **befintliga kanoniska projektet** med `validate_project`. Inga noder, kablar, portar eller konfigurationer härleds eller skapas.
2. Endast länkar med `enabled: true` och aktiverade portar i **båda ändarna** kan transportera ramen.
3. `inject(node_id, port_id, source_mac, destination_mac)` är det ursprungliga MAC-only-anropet. Den striktare `inject_frame(node_id, port_id, frame)` kräver en faktisk `EthernetFrame` och en uttrycklig källa i `interface_macs` vid sessionens start. **MAC-identiteter finns ännu inte i projektformatet** och tilldelas aldrig automatiskt.
4. Endast sex oktetter hex, separerade med kolon, stöds. Källadressen måste vara icke-noll unicast. Destinationen måste vara unicast eller `FF:FF:FF:FF:FF:FF` (broadcast). Multicast avvisas uttryckligen som ej implementerat.
5. Samtliga portars forwarding-domän antas för denna modell vara **otaggad, utan VLAN-segmentering**. Det är en begränsning, inte ett påstående om verkliga switchkonfigurationer.

## Regler för forwarding

- När en ram **faktiskt anländer** till en aktiv switchport lär switchen `source_mac → ingressport`.
- Om destinations-MAC inte finns i den tillfälliga tabellen, eller om destinations-MAC är broadcast, floodar switchen på sina övriga **aktiva och fysiskt anslutna** portar.
- Om destinations-MAC är känd vidarebefordras ramen endast via den inlärda aktiva porten.
- Om destinations-MAC är inlärd på inkommande port filtreras ramen; den skickas inte tillbaka samma port.
- Noder av typen `host`, `router` och `firewall` är i denna etapp **terminala observationspunkter**. De bryggar eller routar inte automatiskt.
- Aktiva switch-till-switch-loopar, inklusive parallella länkar, avvisas med fel: ingen STP, RSTP eller annan loopkontroll har implementerats.

Sessionens MAC-tabeller är **flyktigt tillstånd**. Återanvänd samma `EthernetFabric` för att observera inlärning mellan flera ramar. Skapa en **ny** instans när den deklarerade topologin, någon länk eller något porttillstånd har ändrats. Tabellen sparas inte i projektet.

## Exempel

```python
from network_core.ethernet import EthernetFabric

fabric = EthernetFabric(project)  # project måste redan deklarera noder, portar och länkar
result = fabric.inject(
    "host-a", "eth0", "02:00:00:00:00:0A", "02:00:00:00:00:0B"
)
assert result["status"] in {"SIMULATED", "NO_ACTIVE_LINK"}
print(result["transmissions"])  # faktiska deklarerade länkar per transmissionssteg
print(result["endpointArrivals"])  # ram nådde port, inte nödvändigtvis accepterad av NIC
print(fabric.mac_table("switch-a"))  # inlärda MAC-adresser i denna session
```

Exemplet är kodfragment med **platshållar-ID:n**, inte ett bevis att dessa nätverksobjekt finns i användarens projekt.

## Icke-implementerat

- L2-ramar kan nu serialiseras/parsas **utan FCS** som Ethernet II i `ethernet_frame.py`. Däremot saknas FCS, preamble, tidsfördröjning, länkförhandling och protokollavkodning av payload.
- Dynamisk MAC-aging, STP/RSTP, multicastgrupper, VLAN och trunkar.
- ARP, IP, ICMP, ping, DHCP, DNS, routing, brandväggslogik.
- MAC-filtrering eller paketacceptans i mottagande host/NIC. `endpointArrivals` betyder **enbart att ramen nådde ett deklarerat gränssnitt**.
- UI, HTTP-endpoint eller beständig lagring av simuleringssessionen.

Den befintliga `topology_trace` är fortfarande en **dokumentationsgraf**, inte denna forwardingmodell. Blanda inte ihop deras resultat och ersätt inte den ena med falska antaganden om den andra.

## Verifiering

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Beteendet provas i `tests/test_ethernet.py`: kända/okända destinationer, broadcast, flyttad MAC, nedstängd port eller länk, två switchar, loopar och ogiltiga MAC-adresser samt oförändrat källdokument. Dessa tester är **funktionella modelltester**, inte test av verklig fysisk nätverkskommunikation.

Nästa välmotiverade etapp: definiera hur MAC-adresser ska sparas som källdata genom en separat versionshanterad projektmodell och verifierad migrering, följt av ARP med oberoende testning. Ingen UI-integrering får antyda IP-reachability innan IP-forwarding finns.

## Utökning: uttryckliga NIC-MAC-bindningar och Ethernet II

Se även [ETHERNET_FRAMES.md](ETHERNET_FRAMES.md). `EthernetFabric(project, interface_macs={('host-id', 'eth0'): '02:00:00:00:00:0A'})` validerar deklarerade icke-switchportar och avvisar ogiltig/duplicerad MAC. Bindningen finns **endast i simuleringens minne**, inte i projektfilen.

`inject_frame` avvisar obundna källportar eller ramar vars käll-MAC inte matchar den explicita bindningen. Ramen är en validerad Ethernet II-header med opak bytes-payload. Det ändrar inte switchens enda befintliga forwardingalgoritm. Tidigare `inject` finns kvar för kompatibilitet och är fortsatt ett explicit MAC-only-anrop utan bindningskontroll.

Inga MAC-adresser, FCS-värden, ARP-svar eller IP-resultat skapas automatiskt.
