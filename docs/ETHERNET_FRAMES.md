# Ethernet II: explicita MAC-identiteter och bytebaserade ramar

**Status:** Implementerat och testat som isolerat Python-API, inte integrerat med GUI. Ingen IP-, ARP- eller VLAN-simulering.

## Kontrakt

- `EthernetFrame(destination, source, ether_type, payload)` är en immutabel Ethernet II-ram, utan FCS, preamble eller VLAN-taggar.
- MAC-format är exakt sex kolonseparerade hexadecimala oktetter. Källa måste vara icke-noll unicast. Destination får vara unicast eller broadcast. Multicast avvisas som ej stödd.
- `ether_type` är heltal `0x0600..0xFFFF`, utom 802.1Q/802.1ad-taggar (`0x8100`, `0x88A8`, `0x9100`). 802.3-längdfält och odefinierade gränsvärden avvisas. Detta är **endast EtherType-fältet**; payload avkodas inte.
- `payload` måste vara `bytes`, 0–1500 oktetter. `serialize()` returnerar destination(6), källa(6), EtherType(2) och payload, med nollpadding upp till 46 payloadoktetter. Resultatets storlek är 60–1514 oktetter, **exklusive FCS**.
- `parse(raw)` tar exakt Ethernet II-byteformat i denna begränsade längd. Eventuell padding kan **inte särskiljas från protokollpayload** utan protokollavkodning, så de inlästa byten bevaras opakt.
- `EthernetFabric(project, interface_macs=...)` kräver en mappning från deklarerade `(node_id, port_id)` till MAC, exempelvis `{('pc-a', 'eth0'): '02:00:00:00:00:0A'}`. Saknade, påhittade, duplicerade, multicast- och switchport-bindningar avvisas. Ingen standardadress hittas på.
- `inject_frame(node_id, port_id, frame)` validerar att källportens MAC är uttryckligt bunden och exakt matchar ramens käll-MAC. Den återanvänder den befintliga deterministic MAC-forwardingmodellen.
- Returnerade `transmissions` och `endpointArrivals` är **ramväg/portankomst**, inte mottagande NIC-acceptans, ARP, IP, ICMP eller ping. `frame` innehåller endast källa, destination, EtherType och serialiserad längd exklusive FCS.
- `EthernetFabric` skriver aldrig projektfiler. Explicita MAC-bindningar från portfältet `mac` i schema 1.1 kan sparas via separat Save/Open, medan sessionsbindningar och inlärda MAC-tabeller inte sparas. Se [MAC_CONFIG.md](MAC_CONFIG.md).

## Exempel

```python
from network_core.ethernet import EthernetFabric
from network_core.ethernet_frame import EthernetFrame

# project måste deklarera pc-a/eth0 och dess faktiska länk i förväg.
fabric = EthernetFabric(project, interface_macs={
    ('pc-a', 'eth0'): '02:00:00:00:00:0A',
})
frame = EthernetFrame(
    destination='02:00:00:00:00:0B',
    source='02:00:00:00:00:0A',
    ether_type=0x88B5,
    payload=b'demo',
)
result = fabric.inject_frame('pc-a', 'eth0', frame)
print(result['transmissions'])
```

Detta är en **API-illustration med platshållar-ID:n**, inte ett bevis på att dessa enheter finns i ett särskilt nät.

## Avsiktliga begränsningar

Ingen FCS-beräkning, VLAN, multicast, MAC-aging, STP, ARP-protokoll, IP-stack eller NIC-filtrering. EtherType `0x0800` eller `0x0806` innebär inte att IPv4 eller ARP avkodas. En importerad fil med okänd MAC tilldelas aldrig en adress.

## Tester

`tests/test_ethernet_frame.py` innehåller oberoende bytevektorer och negativa tester för felaktiga format, överstora ramar, otillåtna EtherType-värden, obundna eller felaktigt bundna källportar och oförändrad projektmodell. Den tidigare `tests/test_ethernet.py` fortsätter verifiera forwarding och MAC-inlärning.
