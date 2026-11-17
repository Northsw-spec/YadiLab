# Begränsad DHCPv4 DISCOVER/OFFER-diagnostik

## Faktisk funktion

En **engångssimulering** av DHCPDISCOVER → DHCPOFFER (RFC 2131) via den
befintliga, kanoniska `EthernetFabric`. Klienten (`host`) och DHCP-servern
(`host` eller `router`) väljs **uttryckligen** med befintliga nod-/port-ID:n.
Klientens IPv4 måste vara `null`; både klient och server behöver deklarerad
MAC. Serverporten behöver ett explicit IPv4/CIDR och det föreslagna
IPv4-numret väljs uttryckligen av användaren. Vald adress måste vara
en ledig användbar hostadress i serverportens subnet, inte någon redan
dokumenterad gränssnitts-IP. Ingen DHCP-roll härleds från nodtypen.

`POST /api/dhcp/discover-offer` accepterar **exakt** följande fält:

- `project`: kanoniskt projektobjekt (inte en sträng)
- `clientNode`, `clientPort`: klientens faktiska ID:n
- `serverNode`, `serverPort`: serverns faktiska ID:n
- `proposedIpv4`: föreslagen adress, t.ex. `192.0.2.70`
- `transactionId`: 32-bitars heltal (1..4294967295)
- `leaseSeconds`: föreslagen varaktighet (60..604800)

Skrivning sker aldrig i `.yadilab`, serverns lagring eller projektmodellen.

## Vad som faktiskt sker

1. Kodar en BOOTP/DHCPDISCOVER med Ethernet `chaddr`, transaktions-ID,
   magic cookie och DHCP option 53 (Discover); BROADCAST-flaggan är satt.
2. Bygger IPv4 `0.0.0.0 → 255.255.255.255`, UDP `68 → 67`,
   riktiga IPv4- och UDP-checksummor och en Ethernet II-broadcastram.
3. Avkodar och validerar de skapade bytesen, och injicerar ramen i
   **samma faktiska Ethernet-/VLAN-forwardingmodell** som ARP använder.
4. Enbart om den uttryckligen valda serverporten finns i observerade
   `endpointArrivals` byggs ett DHCPOFFER med erbjuden IP i `yiaddr`,
   serveridentifierare (option 54), nätmask (option 1) och föreslagen
   leasetid (option 51). UDP är `67 → 68`, IPv4-källan är serverportens
   IPv4, och svaret broadcastas enligt klientens BROADCAST-flagga.
5. Status `OFFER_RECEIVED` ges enbart om DHCPOFFER genom den faktiska
   L2-motorn når exakt den ursprungliga klientporten och bytes/identitet
   validerats. Resultatet visar verkligt genomgångna länk-ID:n,
   VLAN-droppar, tillfälligt inlärda MAC-tabeller samt `leaseCommitted=false`.

`NO_ACTIVE_LINK` innebär att klientens utgående länk saknas.
`DISCOVER_NOT_RECEIVED` innebär att vald server inte nåddes.
`OFFER_NOT_RECEIVED` innebär att svaret inte nådde klienten.
Saknade/ogiltiga fakta ger HTTP 422, inte ett falskt DHCP-erbjudande.

## Gränser

- Detta är **inte komplett DHCP/DORA**. DHCPREQUEST/ACK/NAK, återförsök,
  adressallokering, adresspooler, reservationslistor, lease-expiration,
  förnyelse och kollisionstester på nätet stöds inte.
- En föreslagen IP **konfigureras aldrig** på klienten; endast redan
  deklarerade IP-uppgifter kontrolleras för kollision. Att en adress
  inte finns i dokumentationen bevisar inte att den är ledig i verkligheten.
- Ingen DHCP-relay, option overload, dynamisk serverupptäckt, routing
  av broadcast eller annan UDP-tjänst. Vanlig `IPv4Trace` lämnas oförändrad;
  dess strikta unicastkrav kan inte återanvändas för DHCP bootstrap.
- Ingen uppmätt RTT, faktisk Ethernet-NIC eller yttre nätverkstrafik.
  MAC-/ARP-lärande är inte beständigt; varje API-anrop är isolerat.
- Både IPv4 och UDP har riktiga checksummor och en avsiktligt begränsad
  avkodare; inga allmänna IPv4/UDP-funktioner utlovas.

Referenser: [RFC 2131](https://www.rfc-editor.org/rfc/rfc2131),
[RFC 768](https://www.rfc-editor.org/rfc/rfc768).
