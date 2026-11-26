# RELEASE-GATES — full paritet, därefter verifierat bättre

Alla gates NOT_RUN per 2026-11-26.

G0: lagligt installerad exakt PT-binär med build/version/checksum, samtliga enheter/moduler/medier/CLI/UI/protokoll/IoT/OT/Multiuser/ExApps/format och underfall inventerade, oberoende granskning av fullständighet. Machine scope-registry inventory_complete=true endast med bevis.

G1: teknisk standardkorrekthet; varje deklarerad protokollfunktion har versionerad RFC/IEEE/IEC + errata, bytes/state/timers, oberoende positiva/negativa/motsägande orakel, inga kända allvarliga falska packet successes.

G2: integrerad produkt; EN motor, EN simulerad tid, device/port/link/CLI och korrekt TX/RX, riktiga header-/packet-/drop-traces, config projekt+UI+Simulation-Mode utan andra sanningar.

G3: funktionell PT-paritet i samtliga inventerade underfall: deviceprofiler, CLI, logical/physical, power, real-time/simulation/PDU, Activity Wizard/scoring, IoT/OT/programmering, Multiuser, extension och laglig PKT/PKA/PKZ-interoperabilitet. Inga OPEN/NOT_VERIFIED/NOT_RUN/BLOCKED där slutparitet krävs.

G4: säkerhet, produktjuridik och format; scripts sandboxed, no live PLC/NIC, opt-in multiuser auth, ingen olovlig Cisco-kod eller kringgående av proprietary rights, safe import, genuine Save/Open/SHA, rollback.

G5: installerbar Linux-release med **obligatorisk sann Same-UI-paritet mot Legacy commit aac82926ced3dbf4cac09242530762ac3da1fe80 enligt [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) och [UI-registret](requirements/legacy_ui_manifest.json)**. Kräver låsta och jämförda Chromium/DOM/screenshot/E2E-fall för alla UI-case (visuell identitet och interaktionsflöde, tillåtna standardiserade renderingstoleranser). Plus verkliga ELK/UI/import/DES/säkerhetsregressioner, Required CI SUCCESS på exakt HEAD, oberoende code/protocol/security audit, noll blockerande P0/P1, data migration/recovery och återspelbar build.

G6: i förväg registrerad oberoende Cisco-jämförelse med samma/topologiska labb och hårdvara, upprepade trials, faktisk standardskorrekthet, kausal precision, diagnostiskt felutfall, latency/resource/scale/stability, feature breadth och pedagogisk uppgiftsförmåga. För påstående om bättre inlärning behövs frivillig kontrollerad mänsklig studie. Enbart PT-modelling limitations bevisar inte YadiLabs bättre beteende utan korrekta egenprov.

Tillåtna slutetiketter:
IN_PROGRESS = minst en gate saknar evidens.
PARTIAL_PARITY_VERIFIED = exakt deklarerade underfall har verifierats, men totalparitet ännu saknas.
FULL_PARITY_VERIFIED = endast G0–G5 PASS, inga luckor utom Linux-port/ny keyboard-only/accessibility.
EXCEEDS_PT_VERIFIED = FULL_PARITY_VERIFIED + G6 PASS på de dimensioner som påstås. "Bättre i ALLT" kräver faktiskt oberoende bättre resultat i varje relevant domän, inga okända eller mätbart sämre resultat.

Ett juridiskt blockerat PT-format låser FULL_PARITY = EJ UPPNÅTT, det blir inte ett nytt scope-undantag. En grön dokument-PR kan aldrig uppfylla G0–G6. Vid ny PT-release inventeras delta; full paritet mot den nya versionen är inte automatiskt uppnådd.
