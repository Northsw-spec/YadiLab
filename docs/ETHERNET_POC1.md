# R1-2 / POC1 — Ethernet II, accessbrygga och ARP

POC1 överför serialiserade Ethernet II-ramar med Ethernet/IPv4-ARP i den befintliga händelsekärnan. En scenariokonfiguration anger uttryckliga projektändpunkter, access-VLAN, länkhastighet, propagationstid, kögränser och värdarnas MAC- och IPv4-adresser. `EthernetScenario` registrerar aktörer, schemalägger användaråtgärder och läser händelseloggen. Klockan, händelsekön och det muterbara tillståndet tillhör `EventKernel` och `ScenarioRuntime`.

## Protokoll och tillstånd

- Otaggade Ethernet II-ramar har 6 byte adress vardera, EtherType i nätverksordning, upp till 1 500 byte data och fyra FCS-byte. Kodaren fyller data till minst 46 byte. Bufferten innehåller hela ramen från destination till FCS och är 64–1 518 byte. FCS beräknas med Ethernet CRC-32 över adressfält, EtherType, data och padding. Reflekterad polynomrepresentation är `0xedb88320`, initialvärde och slutlig XOR är `0xffffffff`, och FCS ligger i little endian i bufferten. Parsning verifierar storlek och FCS före leverans till en enhet. Längdfält, LLC och identifierade VLAN-taggar avvisas uttryckligen. [IEEE 802.3-2022](https://standards.ieee.org/ieee/802.3/10422/) · [RFC 894](https://www.rfc-editor.org/rfc/rfc894.html)
- Accessbryggan klassificerar otaggad ingress enligt portens VLAN. Den lär en individuell käll-MAC per `(VLAN, MAC)` och skickar känd unicast till vald port. Okänd unicast och broadcast sprids till övriga operativt berättigade portar inom samma VLAN. Känd destination på ingress filtreras. En otillgänglig känd utgång orsakar en drop. Multicast utöver broadcast avvisas i POC1. FDB är storleksbegränsad och behåller de senast inlärda eller uppdaterade posterna. [IEEE 802.1Q-2022](https://standards.ieee.org/ieee/802.1Q/10323/)
- ARP-parsern hanterar Ethernet, IPv4, adresslängder 6 och 4, och operationerna Request och Reply. Meddelandet är 28 byte. En mottagen minsta ram kan ha ytterligare 18 paddingbyte. En värd med en konfigurerad fysisk port svarar på en giltig fråga för sin egen IPv4-adress. Endast ett giltigt svar till den egna MAC- och IP-adressen med motsvarande utestående fråga uppdaterar cachen. Ethernet- och ARP-käll-MAC måste stämma och avsändaren måste ha en användbar adress inom det lokala prefixet. En aktiv timeout avslutar frågan och ett godkänt svar avbokar timern i samma transaktion som cacheuppdateringen. Cache med FIFO-utdrivning och utestående frågor har egna gränser. Kontrollerna är lokal mottagningspolicy. ARP saknar autentisering. [RFC 826](https://www.rfc-editor.org/rfc/rfc826.html) · [Verifierat RFC 826-erratum 7909](https://www.rfc-editor.org/eid7909)
- En giltig Ethernet-ram med ett ogiltigt ARP-meddelande kan lära bryggan en L2-källadress. Värdens ARP-parser avvisar meddelandet. En ogiltig Ethernet-ram når aldrig bryggans inlärning.

## Tid och fel

`DEVICE_PROCESS → TX_QUEUED → TX_SERVICE → TX_START → SERIALIZATION_COMPLETE → PROPAGATION_COMPLETE → RX_FRAME → ETHERNET_PARSE → DEVICE_PROCESS` körs i samma diskreta kö. Vid en förlust schemaläggs `DROP` med orsak och kausal förälder. En `FrameObservation` innehåller ursprungsport, ram-ID och EtherType när ramdata finns. Hopp innehåller länken, sändar- och mottagarport och VLAN. Ursprungliga ram-ID:n följer en ram genom bryggan och genom eventuella kopior. En ny ARP Reply får ett eget ram-ID och har det mottagna Request-händelseförloppet som kausal föregångare. Ingress-VLAN fastställs på mottagarporten före enhetens bearbetning.

Modellen använder punkt-till-punkt och full duplex. Varje port äger sin FIFO och sändriktning. För ramstorlek `n` inklusive FCS och hastighet `r` bit/s gäller:

| Gräns | Tid från sändstart |
|---|---|
| Serialisering, inklusive åtta byte preamble/SFD | `ceil((n + 8) × 8 × 10⁹ / r)` ns |
| Tidigaste nästa sändstart för samma port, inklusive 12 byte IFG | `ceil((n + 20) × 8 × 10⁹ / r)` ns |
| Komplett mottagning | Serialiseringstid + länkens propagationstid |

Vid 100 Mbit/s tar en 64-bytesram 5 760 ns att serialisera och reserverar porten i 6 720 ns. Länkens propagationstid fördröjer mottagning utan att förlänga portens FIFO-plats. Bryggan väntar på komplett mottagning och giltig FCS före forwarding.

Varje accepterad köpost bär identiteter för aktuell port-, länk- och strömperiod. En ändring gör gamla köade och pågående hopp inaktuella även om tillståndet återställs före nästa steg. Kärnan hittar avbrottet vid nästa kontrollpunkt och loggar orsaken där. Den återstående reserverade sändplatsen kan fortfarande löpa ut. En avstängd enhet gör sina portar obrukbara för transporten. Administrativ portstatus tillhör oföränderlig projektkonfiguration. Operativa port-, länk- och strömåtgärder schemaläggs som separata händelser med avgränsat ägarskap. Reset rensar runtime och väntande hopp.

`PORT_DOWN`, `LINK_DOWN`, `DEVICE_OFF`, `INVALID_FCS`, `INVALID_FRAME`, `VLAN_BLOCKED`, `NO_EGRESS_PORT`, `QUEUE_FULL`, `UNSUPPORTED_PROTOCOL`, `INVALID_ARP`, `UNEXPECTED_ARP`, `NOT_FOR_INTERFACE`, `STATE_LIMIT`, `TIME_LIMIT` och `ARP_TIMEOUT` representerar förväntade avvisningar. `HANDLER_FAILED` är ett internt körfel och annullerar händelsens staged effekter.

## Resursgränser och återstående arbete

23 640 ns är ett simulerat resultat för testfixturen. Värdhårdvarans prestanda mäts separat. Fixturen har 256 väntande kärnhändelser, högst 256 händelser per tidsstämpel, 4 096 loggposter och en strukturerad värdebudget på 32 768 per payload eller aktörstillstånd. Den använder åtta väntande ramar per port, åtta utestående frågor och cacheposter per värd samt 16 FDB-poster. Varje aktivt fysiskt hopp har högst en väntande fortsättning i kärnkön. Ett fullt protokoll- eller porttillstånd hanteras enligt gränserna ovan. Kärnans egna budgetar begränsar hela scenariot och kan stoppa körningen.

Köer och tabeller använder immutabla tupler. Uppslag och ersättning kostar linjärt i sin konfigurerade storlek. Logg och replaykodning behåller ramdata och kan dominera minnet i stora körningar. Skaltest, diskbaserad logg och snabbare tillståndsstrukturer är framtida arbete. Modellen saknar bryggloopskydd och kräver loopfria topologier för meningsfull trafik.

**NOT_IMPLEMENTED:** Ethernet-varianter med halv duplex, kollisioner, jumbo frames, LLC, VLAN-trunkar, STP, multicast-forwarding, FDB-åldring, ARP-retries och cacheåldring, IPv4-adresskonfliktsdetektion och annonsering enligt RFC 5227, flera gränssnitt per ARP-värd, omstartssemantik för protokolltillstånd, IPv4-forwarding, ICMP, andra nätverksprotokoll och gränssnitt.

Testmatris och oberoende fixturer finns i [VERIFICATION-001](VERIFICATION.md#r1-2--poc1).
