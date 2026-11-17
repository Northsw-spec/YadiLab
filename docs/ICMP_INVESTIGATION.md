# ICMP/IPv4: dolt fel och evidensstyrd felsökningsövning (PR #40)

## Funktionellt kontrakt

Övningen genomför *inte* en generisk grafbaserad reachability-kontroll.
`EchoExchange` skickar ett riktigt serialiserat ICMP Echo Request
genom den dokumenterade `IPv4Trace`, `ConnectedRoutingTable`,
`ARPResolver` och `EthernetFabric`. För en giltig **baslinje**
krävs också ett korrekt matchat Echo Reply på ursprunglig klientport.
Utan en sådan faktiskt verifierad referens avvisas övningen med HTTP 422.

Endast fel från existerande dokumenterad konfigurering erbjuds:
`LINK_DISABLED`, `ACCESS_VLAN_CHANGED` och
`STATIC_ROUTE_REMOVED`. Motorn bygger kandidater utifrån baslinjens
faktiskt använda kablar och dokumenterade switch-VLAN/statiska routes.
En kandidat accepteras bara om den existerande `compare_fault`
bekräftar en lyckad baslinje, misslyckad paketleverans med just det
felet och återställd verklig Echo-kommunikation i en **oberoende
paketinstans**. Orelaterade, ogiltiga eller redundant konfigurerade
förändringar kan inte bli övningar. Slumpningen väljer endast bland
redan verifierade kandidater och exponerar inte felvalet.

Ingen projektdokumentation ändras av simuleringen. Det dolda felet
injekteras bara på en validerad privat kopia av den ursprungliga
kanoniska modellen. Klientens privata felnamn och målpunkt är
oåtkomliga via publika start-/probe-/diagnose-svar.

## Begäran och observerbara svar

`POST /api/icmp/investigation/start` kräver exakt:

```json
{
  "project": {},
  "sourceNode": "a",
  "sourcePort": "eth0",
  "destinationIpv4": "203.0.113.20",
  "ttl": 5
}
```

Projektobjektet måste valideras mot den kanoniska modellen.
`sourceNode` och `sourcePort` måste identifiera ett verkligt
dokumenterat, aktivt och MAC/IP-konfigurerat gränssnitt.
`ttl` måste vara ett *äkta* heltal 2..255, inte bool/string.
Måladressen måste vara en giltig och av motorn faktiskt nåbar
IPv4-destination innan felinjektion. En lyckad start ger ett opakt
`sessionId`, käll-/mål-ID:n, mätantal, hypotesstatus, DHCP-bevisläge,
samt `ephemeral=true`. **Ingen** intern feltyp, reparationsoperation
eller simulerad felpunkt exponeras.

`POST /api/icmp/investigation/probe` kräver exakt
`sessionId`, ursprungligt `project`, `probe` och `target`.

| `probe` | `target` | Resultat |
|---|---|---|
| `address` | `{}` | Dokumenterad IPv4 och portstatus; adressursprung `UNKNOWN` och DHCP-kontroll `NOT_VERIFIED` |
| `ping` | `{}` | Riktigt ICMP Echo: Request/Reply-status, riktiga route- och ARP-steg, VLAN-drops och faktiskt använda kablar |
| `route` | `{"nodeId":"a","destinationIpv4":"203.0.113.20"}` | Aktuell route lookup på vald explicit host/router, längsta prefix och eventuellt `NO_ROUTE` |
| `link` | `{"linkId":"la"}` | Dokumenterat jämfört med simulerat länktillstånd och deklarerade ändpunkter |
| `vlan` | `{"nodeId":"sw-left","portId":"a"}` | Dokumenterad kontra simulerad explicit VLAN-konfiguration |

`route` får endast slå upp **källans eller destinationens egen IP**
inom samma övning och på faktiskt existerande host/router. Detta
möjliggör att särskilt granska returvägen från destinationen mot
ursprungsklienten. Inga generiska rutter eller graf-baserade hop
påstås vara verifierade. Alla observationer kommer från den
faktiskt felinjicerade simulerade nätverkskopian och anges
`SIMULATED` eller `SIMULATED_CONFIG`.

### DHCP är inte automatiskt uteslutet

Projektets dokumenterade IPv4/CIDR-fält anger **inte** om adressen
har lagts in statiskt eller kommit via DHCP. Det är därför otillåtet
att härleda att DHCP är friskt eller felaktigt bara från en redan
konfigurerad adress. Övningen redovisar alltid
`dhcpAddressOrigin=UNKNOWN` och `dhcpCheck=NOT_VERIFIED`.
Separata DHCP-sessioner kan användas för att diagnostisera ett
DHCP-lease/DORA-problem, men de skapar inte nya routade länkar och
kopplas inte implicit in i detta ICMP-felsökningsfall.

## Diagnos och verifierad reparation

`POST /api/icmp/investigation/diagnose` kräver exakt
`sessionId`, `project`, `diagnosis`, där en enda av
`CABLE_DOWN`, `VLAN_MISMATCH`, `STATIC_ROUTE_MISSING`
är tillåten. Före diagnos krävs riktiga mätningar av **ping**,
**route** och minst en tredje kontrolltyp (**address**, **link**
eller **vlan**). Fel gissning returnerar enbart `correct=false`
och avslöjar inte feltypen. Högst 3 hypotesförsök accepteras.
Inga dolda feluppgifter skickas till webbläsaren förrän efter en
verkligt verifierad reparation.

`POST /api/icmp/investigation/repair` kräver exakt
`sessionId` och `project`, och endast en korrekt diagnos
tillåter åtgärden. Den injicerade felkopian måste fortfarande
misslyckas i ett färskt faktiskt Echo-utbyte. Den ursprungliga
kanoniska kopian måste sedan ge `REPLIED` och
`replyMatched=true` i en annan färsk paketinstans. Först då
får resultatet `status=RECOVERED` och den bekräftade feltypen
samt simulerade reparationspunkten med
`scope=PREVIEW_ONLY`. Om återhämtningen inte är bevisad visas
`NOT_VERIFIED`, inte en konstruerad lyckad ping.

`POST /api/icmp/investigation/stop` kräver bara `sessionId`
och kastar den processlokala övningen. Backend begränsar antalet
till **16 samtidiga övningar**, **48 mätningar per övning**,
**3 gissningar**. Snapshoten kontrolleras före varje åtgärd och
serveromstart utplånar sessionerna. Ett ogiltigt ID, fel nycklar,
ogiltig IPv4/TTL, överskriden budget eller förändrat projekt
avvisas med HTTP 422 utan positiva slutsatser och utan skrivning
till projektfil. Builder ogiltigförklarar alla sena webbsvar
efter projektändring.

## Vad övningen INTE bevisar

- Den kontrollerar inte verkliga switchar, routrar, kablar eller NIC.
- Den är begränsad till befintlig statisk IPv4-routing och dokumenterat VLAN.
- Den simulerar ingen DHCP-tilldelning för den dokumenterade
  IPv4-källan och vet inte varifrån dess adress kommer.
- Den ger ingen DNS-analys, TCP-test, NAT, dynamisk routing,
  brandväggspolicy, RTT, automatiska felläkningar eller internetstatus.
- En ensam route lookup är aldrig liktydig med paketrechability,
  och en framgångsrik Request utan Reply är inte en godkänd ping.

Den existerande `compare_fault`-funktionen ger tre
oberoende paketutbyten: baseline, fel, återställning.
Det nya övnings-API:t återanvänder detta bevis vid scenario-urval
och gör därpå användarstyrda, fristående observerbara
paket-/konfigurationsmätningar för en pedagogisk diagnos.
