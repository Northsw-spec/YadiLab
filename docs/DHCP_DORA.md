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

## DORA i Builder (PR #32)

Den separata panelen **DHCP – Discover / Offer / Request / ACK**
finns i högra laboratoriepanelen. Användaren väljer uttryckligen
klientgränssnitt (host utan IPv4), servergränssnitt (host/router med
dokumenterad IPv4), poolstart och poolslut, transaktions-ID och
simulerad leasetid. Båda porternas MAC måste fortfarande vara
uttryckligen dokumenterade; saknade identiteter avvisas.

Engångsknappen **Simulera full DHCP DORA** anropar det existerande
`POST /api/dhcp/dora` utan extra nätverkslogik i JavaScript.
Resultatet visar separata överföringsspår för DISCOVER, OFFER,
REQUEST och ACK, observerade VLAN-droppar, inlärda MAC-tabeller,
servermottagning av DISCOVER/REQUEST och klientmottagning av ACK.
En **SIMULERAD BOUND-lease** visas endast när HTTP-motorn
returnerar `ACK_RECEIVED` och `leaseCommitted=true`.

Ändring av projekt, topologi, portval, pool eller tid ogiltigförklarar
tidigare resultat. Även en redan avslutad HTTP-körnings fördröjda
svar ignoreras om underlaget har ändrats. Inga UI-värden appliceras
automatiskt på dokumenterade klientportar, ingen autosave sker, och
ett nytt knapptryck startar en ny tom simuleringssession. Den
befintliga Discover/Offer-panelen kvarstår separat och visar
fortfarande bara två meddelanden.

## Processlokal sessionshantering för flera klienter (PR #33)

Den befintliga `DhcpSession`-motorn och samma `EthernetFabric` används;
en serverprocess håller högst **16** separata, slump-ID-skyddade
`DhcpLabSession`-instanser. Varje session kan utföra högst **256**
DORA-operationer mellan nollställningar. Alla operationer och uppdateringar
för en viss serverprocess serialiseras via ett lås. En session binds
vid starten till ett validerat projekts SHA-256-signatur, en
uttryckligen vald serverport och en sammanhängande adresspool.
Den serverporten och poolen kan inte ändras under sessionen.

Nya endpoints (HTTP POST, exakt JSON-nyckeluppsättning):

- `/api/dhcp/session/start`: `project`, `serverNode`,
  `serverPort`, `poolStart`, `poolEnd`.
  Ger `sessionId`, pool/server, `operationCount=0`, `leases=[]`.
- `/api/dhcp/session/run`: `sessionId`, `project`,
  `clientNode`, `clientPort`, `transactionId`, `leaseSeconds`.
  Ger `result` från **samma existerande DORA-motor** och
  aktuell `leases`, `leaseCount`, `operationCount` och MAC-tabeller.
  Klienten måste vara en deklarerad hostport utan IPv4.
- `/api/dhcp/session/reset`: `sessionId`, `project`.
  Behåller server och pool men nollställer lease-tabell, MAC-inlärning
  och operationsräknare.
- `/api/dhcp/session/stop`: endast `sessionId`.
  Tar bort den processlokala sessionen.

Alla endpunkter avvisar oväntade/saknade nycklar (422). `run` och
`reset` vägrar om projektets signatur ändrats sedan sessionens start;
`stop` tillåts alltid för att frigöra den gamla sessionen.
Dubblerad tilldelning till samma klient och uttömd pool ger 422
**utan att tidigare BOUND-leases raderas**. L2-fel räknas som en
genomförd simuleringsoperation men ger ingen lease; invalida
indata räknas inte som genomförd operation.

Builder använder nu de fyra livscykelknapparna ovan. Den gemensamma
DORA-panelens server och pool låses när sessionen är aktiv,
medan användaren uttryckligen kan välja nästa klient och transaktions-ID.
Observerade spår för DISCOVER/OFFER/REQUEST/ACK och den aktuella
simulerade lease-tabellen visas var för sig. Projektändringar ogiltigförklarar
sessionen och gör ett best-effort-anrop till `stop`; ett fördröjt
HTTP-svar får aldrig återställa gammal UI-status. Separata
engångsanrop till `/api/dhcp/dora` påverkar inte någon session.

**Ingen session sparas** till projektfilen. Leases gäller bara den
aktuella serverprocessens simulerade arbetsminne; de försvinner
vid omstart, och inget faktiskt nät verifieras. En uttryckligt framflyttad
virtuell klocka hanterar nu expiration, men ingen verklig
tidsbaserad nedräkning eller RFC-förnyelsemekanism finns.

## Virtuell DHCP-sessionstid och expiration (PR #34)

`POST /api/dhcp/session/advance` kräver **exakt** dessa nycklar:

```json
{"sessionId":"<opaque ID från start>","project":{},"seconds":60}
```

`project` måste vara exakt samma kanoniska projektsnapshot som
sessionen startades med. `seconds` måste vara ett äkta heltal mellan
**1 och 604800**, aldrig bool, sträng, 0 eller negativt. Det finns
även ett totalgränsvärde `clockSeconds <= 315360000`.
En godkänd framflyttning räknas som en av de 256 operationerna.
Felaktig indata, förbrukad operationsbudget, överskriden tidsgräns,
okänd session eller ändrat projekt avvisas med HTTP 422 och lämnar
klocka/leases orörda.

Sessionens klocka börjar på **0** och kan endast öka uttryckligen.
En `ACK_RECEIVED` får en tidsstämpel först efter att ACK är verifierad
på den valda klientporten:

- `startedAtSeconds = clockSeconds`
- `expiresAtSeconds = startedAtSeconds + leaseSeconds`
- `remainingSeconds = expiresAtSeconds - clockSeconds`

När `clockSeconds < expiresAtSeconds` förblir leasen BOUND. På det
exakta gränsvärdet, och därefter, försvinner den ur aktiva leases och
returneras enbart som en **EXPIRED-händelse** i `expiredLeases`
för det tidssteg då den upphörde. Responsen inkluderar även det
uppdaterade virtuella klockvärdet, aktuell BOUND-tabell och oförändrade
kanoniska projektfakta. Frigjorda adresser väljs på nytt först efter
en separat faktisk DORA-simulering. Den nya leasen får sin egen
ACK-tidpunkt; det är inte T1/T2-renewal.

Builder visar simuleringstid, kvarvarande tid för varje aktiv lease,
exakt expiration och återanvändning. Knappen
**Flytta fram DHCP-klockan** är inaktiv när ingen session finns.
Nollställning tömmer tabeller och sätter klockan till 0.
Ingen synk mot OS-klocka, sömn, timer, schemalagt jobb eller bakgrundsarbetare
får förändra sessionen. Engångs-DORA har fortfarande ingen
beständig klocka eller expiration; endast den uttryckliga sessionen har det.

## Avsiktliga begränsningar

- Den simulerade leasen existerar endast i minnet. **Klientportens
  kanoniska IPv4-fält är fortfarande `null` och sparas inte.**
  Detta ändrar inte IP-sändning/ARP/routing i befintliga labbar.
- Ingen beständig lease-databas, förnyelse (T1/T2),
  release, DECLINE, NAK, återförsök eller DHCP-relay.
  Expiration stöds **endast** via uttrycklig virtuell tidsframflyttning.
- Ingen ARP-probe eller observation från ett riktigt nät.
  Att ingen dokumenterad enhet använder en adress **bevisar inte**
  att den är ledig i ett verkligt nät.
- Bara DHCP selecting-state broadcast med en vald server och
  en enda klient per `run`; inga konkurrerande servrar,
  relay-agenter, unicast ACK eller BOOTP-alternativ.
- Builder har en separat DORA-panel. Engångsknappen delar aldrig
  lease-databas med senare engångskörningar. De explicita
  DHCP-sessionsknapparna delar däremot tillfällig lease-tabell
  mellan klienter inom en och samma startade session.
  Den tidigare Discover/Offer-panelen är oförändrad och påstår inte ACK.
- Poolgränsen 256 adresser gäller denna uttryckligt begränsade
  modell och är ingen påstådd DHCP-protokollgräns.

Referens: [RFC 2131 – Dynamic Host Configuration Protocol](https://www.rfc-editor.org/rfc/rfc2131.html).
