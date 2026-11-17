# Applikationsarkitektur 0.1 — medvetet liten

## Varför en ny implementation?

Applikationen är ett nytt kodträd med en tydlig, begränsad kedja:

```
Användarens explicita fakta
        │
        ▼
network_core/model.py  ← schema och genomskinlig validering
        │
        ├── network_core/storage.py → verklig .yadilab på disk
        ├── network_core/server.py  → loopback HTTP och explicit Save/Open
        └── web/model.js, web/canvas.js, web/app.js
             └── SVG av EXAKT samma nod-/port-/länk-ID:n
```

Visningsnamnet deklareras endast i **`network_core/config.py`** som `APP_NAME`. Runtime-paketet `network_core` är avsiktligt generiskt och behåller sitt tekniska namn vid omprofilering. Inga externa runtimemoduler krävs.

## Modulgränser

| Modul | Ansvar | Gör inte |
|---|---|---|
| `model.py` | Schema, referenser, explicit grafspårning | Routing, ping, fysisk sanning |
| `storage.py` | Verkliga filer, SHA-256, förväntad föregående version | Autosave, tyst overwrite |
| `csv_import.py` | Explicit fyrtabells-CSV till verifierad kanonisk modell | Implicita kablar, heuristisk kolumnmappning, filskrivning |
| `arp.py` | Explicit Ethernet/IPv4 ARP-request/reply över `EthernetFabric` med sparade 1.2-VLAN eller sessions-VLAN, flyktig cache och enskild HTTP/UI-diagnostik | Ingen IP-routing, ping, proxy-ARP eller varaktig ARP-session i UI |
| `ethernet.py` | Flyktig MAC-inlärning, explicit v1.1-port-MAC samt VLAN-forwarding på deklarerade kablar med 1.2-konfiguration eller sessionstillägg | ARP-protokoll, ping, IP, STP, NIC-acceptans eller lagring av inlärda tabeller |
| `server.py` | Lokal UI, API, validering, separat temporär ARP-diagnostik per POST | Tolka källdata som topologi, spara diagnostik eller simulera IP-paket |
| `web/model.js` | Explicit UI-modell, enhets- och portkommandon | Adressbaserad länkförutsägelse |
| `web/canvas.js` | SVG-geometri och direktträff på portpunkter | Ändra noders eller länkars identitet |
| `web/app.js` | Användarinteraktion, fel, Save/Open | Simulering av nätverksprotokoll |

## Testkontrakt

- **31 enhetstester:** schema, negativ input, 47/46/15-identiteter, grafspårning, felinjicering, riktiga filbytes, hash, atomär uppdatering, konflikter och HTTP.
- **Chromiumacceptans:** skapa enheter och portar, skapa exakt en deklarerad kabel, verifiera SVG-portändpunkter, inaktivera kabel, spara, stäng programprocess och browser, öppna igen, kontrollera SHA-256 och exakt projektinnehåll. Direkt webbläsarnätverk eller uttryckligt märkt testbro enligt miljön.
- Tester får inte påstå att simuleringsprotokoll fungerar när den funktionen inte finns.

## Nästa steg (inte implementerade)

Inför verklig IP-simulering först när routingtabell, L2-beteende, nätmask, TTL och avvisningsvillkor definierats och verifierats separat. Integrera inte äldre projekts motorkod per automatik. Det definierade fyrtabells-CSV-formatet har en separat strikt importör. XLSX/ODS och godtyckliga CSV-scheman kräver egna kontrakt och verifierbara avvisningsfall.
