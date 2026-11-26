# PT-DOC-BASELINE-001 — Packet Tracer utan krav på dess binär

**Bindande användarbeslut 2026-11-26:** Det är **INTE NÖDVÄNDIGT** att installera, köra, äga eller benchmarka en riktig Cisco Packet Tracer-binär för att utveckla YadiLab, inventera dess funktionsmål eller passera dess dokument-/protokollacceptansgrindar. Detta upphäver alla tidigare absoluta krav på PT-build, checksum, PT_RUN_PASS och labb på två installerade appar.

## Primära kunskapskällor

1. **Cisco publicerad Packet Tracer-hjälp och versionsuppgifter** för varje relevant funktion, enhetsprofil, modul, konfigurationskommando, UI, Activity Wizard, IoT, OT, Multiuser och export. Registrera dokument-URL, dokumentets versions-/publiceringsstatus och explicit det funktionspåstående källan stödjer. Otydlig, odaterad eller motsägande dokumentation markeras SOURCE_UNCERTAIN, inte verifierad.
2. **Oberoende tekniska specifikationer** (RFC, IEEE, IEC, ODVA, standardernas errata och dokumenterade korrekta implementationer/testvektorer) är facit för paket, timers, state machines och negativa fall. Vendor-särdrag får lagligt implementeras enligt verifierbara Cisco-källor och tydligt versionerade device-/CLI-profiler, utan att påstå att Cisco är RFC-facit.
3. **YadiLabs egna körda integrationstester** ska bevisa faktisk funktion i vår Linux-app: bytes, state, TX/RX, timers, device/CLI/GUI, port/link, projekt/data/import, Legacy-UI/ELK och säkerhet. Ett Cisco-help-omnämnande eller ett registrerat PT-case är inte en implementerad funktion.
4. **Frivilligt PT-kört jämförelsetest** får läggas till senare, efter laglig åtkomst, när ett dokumenterat beteende är tvetydigt eller direktbenchmark är meningsfullt. Det får **aldrig** blockera R0/R1 eller vara en generell prerequisite i G0–G6.

## Evidensnivåer och anspråk

- **DOC_CANDIDATE:** upptäckt kategori/feature, ännu inte granskad mot en konkret officiell funktionsspecifikation.
- **DOC_VERIFIED:** explicit versions-/källbelagt funktions- eller beteendekontrakt med dokumentreferens, enhet/variant och accepterad förväntad semantik; kräver länk och registrerad evidens.
- **SOURCE_UNCERTAIN:** väsentliga subcases saknar bevis, finns motstridiga Cisco-källor eller är proprietära/ej publicerade.
- **VERIFIED_NATIVE:** YadiLab implementerat och oberoende granskat/testat mot konkreta tekniska krav, med exakt commit/CI, positiva, negativa och motsägande fall.
- **DOCUMENTED_PT_SCOPE_VERIFIED:** varje upptäckt relevant Cisco-dokumenterat PT-underfall är källgranskat och har VERIFIED_NATIVE-implementation; R0/G0-inventeringen är källbaserad, oberoende reviderad och komplett inom **publicerat/verifierbart dokumentationsomfång**. Detta betyder **inte** empiriskt bevisad full ekvivalens med en okörd Cisco-binär.
- **EXCEEDS_DOCUMENTED_PT_SCOPE:** bevisat bättre på explicit angivna och objektivt testade domäner, mot publicerade och jämförbara Cisco-data eller oberoende standard-/användartest. Påstå aldrig "snabbare än PT", "bättre i alla avseenden" eller annat direkt jämförelsepåstående om det inte finns jämförbara mätningar.

## Komplett dokumenterat scope utan att reducera produktmålet

- [PT-registret](requirements/pt_scope.json) är ett levande, **append-only i ID-historik**, maskinläsbart index över obligatoriska funktioner. Dess 36 familjer och 108 initiala kandidater är en startpunkt, inte en slutlig full lista.
- Komplettera källa för varje enhet/modul/kommando/protokollvariant/filformat, lägg till fall vid nya Cisco-dokument eller referenslabb. "Allt Cisco Packet Tracer gör" är fortsatt den absoluta **produktriktningen**, men utan exekvering av PT kan endast dokumenterad/faktiskt bevisbar täckning intygas. Resterande okända ska uttryckligen dokumenteras som risk, inte hittas på.
- PKT/PKA/PKZ eller andra proprietära funktioner som saknar laglig verifierbar specifikation är BLOCKED_LEGAL_OR_SPEC. Gör dem inte valfria och påstå inte full paritet med dem.
- Ersätt **alla** tidigare maskinläsbara källomfångsfält pt_binary_result och pt_build_sha256 med source_status, source_evidence och source_revision. Ingen ersättningsfält ska indirekt kräva en PT-binär. Registrera separat frivilliga mätningar endast när de faktiskt har utförts.
- För direkt numerisk överlägsenhet eller universella konkurrensanspråk krävs oberoende jämförbara mätningar (publicerade motsvarande mått kan duga om deras metod/hårdvara är verifierbar). Utan sådana kan appen vara tekniskt korrekt, kapabel och mer funktionell, men universella påståenden är NOT_VERIFIED.

**Detta är en justering av BEVISMETOD, inte av funktionsscope.** En helt ny DES-motor, samma Legacy-UI, dokumentimport, alla PT-protokoll/device/CLI/IoT/OT/Activity/Multiuser, vendor-specifika Cisco-namn, Linux-only och inga nya keyboard-only/accessibilitykrav gäller oförändrat.
