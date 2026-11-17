# DHCPv4 DORA – avgränsad, tillfällig simuleringssession

## Funktionskontrakt

Den tidigare DHCPDISCOVER/DHCPOFFER-diagnostiken och dess endpoint
`POST /api/dhcp/discover-offer` finns kvar oförändrade i beteende.
Separat kan klient och server genomföra fyra kodade DHCP-meddelanden:
DISCOVER → OFFER → REQUEST → ACK enligt DHCP **SELECTING** i RFC 2131.

En användare väljer **uttryckligen** en hostport utan IPv4, en host-
eller routerport med explicit MAC + IPv4/CIDR, en sammanhängande pool
av 1–256 användbara IPv4-adresser i serverportens subnät,
ett transaktions-ID (1..4294967295) samt en föreslagen leasetid
(60..604800 sekunder). Inga DHCP-roller, nätverk, portar eller
adresspooler gissas från topologin.

Poolen väljs deterministiskt, lägsta tillgängliga IP först, och
serverns IP, alla dokumenterade interface-IP:n och redan simulerat
BOUND-leasade IP:n i **samma** session kan aldrig väljas igen.
Vid tom pool avvisas körningen – inget erbjudande hittas på.

## HTTP-gränssnitt

`POST /api/dhcp/dora` kräver exakt detta JSON-objekt (där
`project` är själva kanoniska projektobjektet):

```json
{
  "project": {"schemaVersion":"1.3","name":"Example","zones":[],"nodes":[],"links":[]},
  "clientNode": "client",
  "clientPort": "eth0",
  "serverNode": "server",
  "serverPort": "eth0",
  "poolStart": "192.0.2.70",
  "poolEnd": "192.0.2.90",
  "transactionId": 305419896,
  "leaseSeconds": 3600
}
```

**Exemplet ovan är endast strukturellt.** Noderna och länkarna
måste finnas i `project` och konfigureras uttryckligen för att
en verklig modellkörning ska lyckas.

Varje HTTP-anrop gör en **ny isolerad simuleringssession**. API:et
skriver inte på disk, och återanrop skapar ingen delad lease-databas.
Den interna klassen `DhcpSession` kan däremot återanvändas för
flera deklarerade klienter i **en och samma** minnessession för att
verifiera tilldelning utan dubblerade adresser.

## Protokoll och status

DHCPREQUEST (typ 3) sänds från klientens MAC/IP 0.0.0.0
till broadcast, UDP 68→67, och har obligatoriska optioner
50 (requested address = erbjuden `yiaddr`) samt 54
(server identifier = erbjudande server). Klienten väntar på
att just den valda serverporten tar emot förfrågan via deklarerade
kablar och VLAN.

DHCPACK (typ 5) sänds från serverns explicit dokumenterade
IPv4-adress till broadcast, UDP 67→68, med `yiaddr`, subnet mask
(option 1), lease duration (option 51) och server ID (option 54).
Alla fyra meddelanden är kodade BOOTP/DHCP med IPv4- och
UDP-checksummor; samma befintliga `EthernetFabric` lär MAC,
floodar broadcast och filtrerar VLAN. Endast ett mottaget,
matchande ACK på originalporten ger:

- `status="ACK_RECEIVED"` och `leaseCommitted=true`.
- Ett tillfälligt `lease`-objekt med `state="BOUND"`, IPv4,
  mask, server-ID, klientens riktiga nod-/port-/MAC-identitet,
  transaction-ID och föreslagen leasetid.
- Spår av observerade länkar, VLAN-droppar och inlärda MAC-tabeller.

Vid `NO_ACTIVE_LINK`, `DISCOVER_NOT_RECEIVED`,
`OFFER_NOT_RECEIVED`, `REQUEST_NOT_RECEIVED` eller
`ACK_NOT_RECEIVED` är `leaseCommitted=false` och
`lease=null`. Felaktiga pooler, dubbleringar och ogiltiga
fakta avvisas med HTTP 422.

## Avsiktliga begränsningar

- Den simulerade leasen existerar endast i minnet. **Klientportens
  kanoniska IPv4-fält är fortfarande `null` och sparas inte.**
  Detta ändrar inte IP-sändning/ARP/routing i befintliga labbar.
- Ingen beständig lease-databas, lease-klocka, förnyelse,
  expiration, release, DECLINE, NAK, återförsök eller DHCP-relay.
- Ingen ARP-probe eller observation från ett riktigt nät.
  Att ingen dokumenterad enhet använder en adress **bevisar inte**
  att den är ledig i ett verkligt nät.
- Bara DHCP selecting-state broadcast med en vald server och
  en enda klient per `run`; inga konkurrerande servrar,
  relay-agenter, unicast ACK eller BOOTP-alternativ.
- Inget nytt Builder-UI för DORA i denna etapp; tidigare
  Discover/Offer-UI är kvar och ska inte påstå att det gör ACK.
- Poolgränsen 256 adresser gäller denna uttryckligt begränsade
  modell och är ingen påstådd DHCP-protokollgräns.

Referens: [RFC 2131 – Dynamic Host Configuration Protocol](https://www.rfc-editor.org/rfc/rfc2131.html).
