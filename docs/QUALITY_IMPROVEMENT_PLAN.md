# Kvalitetslyft: etappordning och verifieringsläge

Utgångspunkt: `main` vid `92f43c978e1f862f8a5ab196eeb426258c8838d4`.
En etapp räknas som verifierad först när dess funktionella och negativa
tester har körts. Detta dokument ger inte någon produktbetygsättning.

| Etapp | Område | Läge |
|---|---|---|
| 1 | Lokal HTTP-gräns | Implementerad; lokalt verifierad med sockettester, full Python-svit och Chromium i denna PR |
| 2 | Samtidighetssäker Save/Open | Planerad |
| 3 | Frontendmoduler med tydliga ansvar | Planerad |
| 4 | Källtrogen, användarstyrd dokumentationsimport | Planerad |
| 5 | Oberoende protokollreferenser | Planerad |
| 6 | Pedagogiskt felsökningsflöde | Planerad |
| 7 | Prestanda, tillgänglighet och distribution | Planerad |
| 8 | Oberoende slutgranskning och omvärdering | Planerad |

Nästa etapp påbörjas först när denna PR har granskats och landat i `main`.

## Etapp 1: hotmodell och HTTP-kontrakt

Servern lyssnar bara på `127.0.0.1`, men en webbsida på en annan domän
kan försöka nå den via användarens webbläsare. DNS-rebinding kan styra
ett främmande namn till loopback. Därför måste varje `GET` och `POST`
ha exakt en `Host` med serverns faktiska bindningsadress **och port**.
Endast `http://127.0.0.1:<faktisk port>` tillåts som `Origin` när fältet
finns. `Sec-Fetch-Site` får bara vara `same-origin` eller `none` när det
finns; främmande och samma-site-anrop från en annan origin avvisas.
Absoluta HTTP-mål och mål som börjar med `//` avvisas. Ingen CORS-header
ges och `OPTIONS`-preflight avvisas.

Det egna gränssnittet använder samma origin och JSON. Dokumenterade
lokala skript får anropa API:t utan `Origin` eller Fetch Metadata, men
`POST` måste ha `Content-Type: application/json` (valfri charset).
Den medietypen kräver preflight i en annan origins webbläsarskript;
vanliga cross-site-formulär kan inte skriva JSON via denna API-gräns.
En nekad förfrågan når varken projektlagring eller simuleringssessioner.

Detta är en **webbläsargräns, inte autentisering**. En annan process med
användarens lokala åtkomst kan förfalska HTTP-fält eller läsa filer med
samma filbehörighet. Ingen skyddsgaranti mot sådan lokal kod påstås.

Före ändringen gav en riktig socketförfrågan med `Host: evil.example`
`200` och projektdata, och främmande `Origin` fick också `200`.
`tests/test_http_boundary.py` reproducerade dessa fel före rättningen.
Efter rättningen måste testet visa 403 före läsning/skrivning, 415 för
form-liknande POST, nekad preflight samt fortsatt legitima anrop.
