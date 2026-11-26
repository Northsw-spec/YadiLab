# BRAND-IDENTITY-001 — ett enda namnbyte, utan renovering

**Bindande beslut 2026-11-26.** Nuvarande produktvisningsnamn är **YadiLab**, men **det är INTE ett kod-, paket-, klass-, filformats- eller namespace-ID**. Tillåtet i Markdown-styrdokument och externa, historiska referenser. I all faktisk källkod, testkod, CSS, HTML, frontend, backend, desktop- och byggskript får texten **YadiLab** och varumärkesförkortningen **YL** inte hårdkodas — **enda tillåtna förekomsten av hela aktuella appnamnet i källkod är den deklarativa strängvariabeln** `core/identity.py::APP_DISPLAY_NAME`.

## En enda deklaration

```python
# core/identity.py – en enda ändringspunkt
APP_DISPLAY_NAME = "YadiLab"
```

När namnet byts redigeras **enbart värdet** till exempelvis `"Network Laboratory"`. **Ingen sök/ersätt**, ingen omdöpning av klasser/moduler, JSON-nycklar, namespaces, test-fixtures, desktop-paket-ID eller native filändelse. Kod får referera till symbolen `APP_DISPLAY_NAME` utan att duplicera strängvärdet. En ändring kräver vanlig omstart/ny build för att nytt namn ska visas; datamigration ska aldrig behövas.

En mycket liten, verkligt implementerad del finns nu: `core/identity.py` definierar en deklaration och `core/metadata.py::public_metadata()` läser den dynamiskt. **Nätverksmotorn, HTTP-route, frontend, desktop-launcher och förpackningen är fortfarande INTE implementerade.** Namnbytets totala UI-/installerarflöde får inte kallas end-to-end verifierat förrän de existerar och har passerat regressionstester.

## Alla användarsynliga brandingytor är härledda

- Lokal backend exponerar i framtiden `GET /api/meta` → `{"appDisplayName": <det deklarerade värdet>}`. **Den routen är ännu inte byggd.**
- Web/frontend läser samma metadata vid bootstrap och använder den i topbar, `document.title`, tomlägesrubrik, dialogs, About/Help, notification/error-headings och exporterade rapporttitlar. Ingen separat `const APP_NAME = "..."` i JavaScript eller HTML-templates.
- Linux-shell/launcher får visningsnamn och `.desktop`-fältet `Name` från *samma deklaration* vid build/install/launch. Normala programid:n, binary names och installpaths är stabila och neutrala. Rebranding kräver rebuild/reinstall för installerad launcher, men **ingen källkodsrefaktor eller användardatamigration**.
- Introducera inte namnet i projektserialisering, permanent storage key, API-route, websocket path, event typ, CSS-klass, DOM-ID, importprofil, CLI-kommando, environment-variable prefix, artifact basename eller loggers. Namn neutralt: `core`, `engine`, `devices`, `protocols`, `projects`, `importers`, `ui`, `cli`, `simulator`, `network-lab`.
- Nytt native projektformat använder brandneutral `.netlab` som första kandidat, inte tidigare varumärkesbaserad `.yadilab`. Historiska projekt kan identifieras av *validerat innehåll/schema* och importeras, även när de har en gammal filändelse. Aldrig avled legacy-extension från det nya `APP_DISPLAY_NAME`: det skulle gå sönder vid namnbyte.
- Legacy-UI:t får **behålla layout, färger, paneler, importflöde och utseende** enligt [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md), men dess gamla hårdkodade text/plats­hållare ska ersättas med centralt hämtat `appDisplayName`. Visuell branding ska inte kräva byte av kodstruktur.

## Särskilj TILLVERKARE från appens varumärke

**Det finns INGET förbud mot tillverkarnamn** såsom **Cisco**, Juniper, Arista, MikroTik, HPE, Fortinet, Nokia eller Huawei. Namnen ska uttryckligen användas när utrustning, CLI-dialekt, protokollvariant, nätverksmodell eller GUI kräver det. Exempel: `vendor="Cisco"`, `model="Catalyst 9300"`, `CiscoCliProfile`, `JuniperJunosProfile`, `VendorDeviceProfile`. De är fackligt korrekta och får vara *tillverkarspecifika*, medan appens egna generiska funktioner/klasser/namnrymder förblir oberoende av appens nuvarande visningsnamn. Det är fel att tvinga bort tillverkarnamn ur en korrekt simulator.

Tillverkarnamn i UI/kommandon är dataprecision, inte YadiLabs egen branding. Cisco-proprietära rättigheter, licenser och beviskrav enligt [SECURITY_LEGAL](SECURITY_LEGAL.md) fortsätter gälla.

## Stoppregler och tester

[Maskinläsbar policy](requirements/branding_policy.json) definierar den enda deklarationen, förbjudna varumärkestoken och granskade källfiltyper. `tests/test_brand_identity.py` ska:
1. AST-validera **exakt en deklarativ strängtilldelning** i `core/identity.py`, ingen ytterligare appnamnsliteral i den filen.
2. Scanna alla första parts källfiler, tester, scripts, HTML/CSS/JSON/UI assets och deras namn; tillåt brandsträngen endast på den enda raden. Docs är undantagna. Avvisa även `YL`, `yl-`, `YL_Engine`, `YLDevice` i egna symboler.
3. Mutera det deklarerade värdet i minnet och bevisa att `public_metadata()` följer det utan modifiering av en annan kodfil.
4. Avvisa falskt två deklarationer, brandade namespaces, frontendliteral, klasser och paths. **Tillåt korrekta manufacturer-specific profiler/kommandon**, inklusive Cisco, Juniper och andra faktiska tillverkare.
5. När frontend och Linux-shell byggs: verkliga Chromium/desktop E2E testar namnbyte genom **endast deklarationsvärdet**, resulterande fönstertitel/menyer/export och stabila projektbytes/API/IDs före och efter. Denna framtida E2E-grind är ännu NOT_IMPLEMENTED.

**Sanning:** En grön governance-PR verifierar bara namnkontraktet och nuvarande kod; den verifierar inte en ännu obefintlig desktop-/webbapp. Samma externa identiteter i projektfiler ska vara kompatibla vid namnbyte.
