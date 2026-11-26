# VERIFICATION-001 — oberoende evidens i stället för demo

Datum 2026-11-26. Status: normative DESIGN, inga nya motor- eller PT-tester körda.

## Sanningsnivåer
DOC_VERIFIED = faktisk källdokumentation; PLANNED = design; IMPLEMENTED_UNVERIFIED = kod utan fullt orakel; VERIFIED_NATIVE = implementerad packet/state/timer med oberoende standardtest, negativa och motsägande scenarier, exakta CI-bevis; PT_RUN_VERIFIED = samma labb faktiskt kört i lagligt installerad PT med exakt build; BLOCKED_LEGAL_OR_SPEC = saknad laglig väg. PT_HELP ≠ PT_RUN_VERIFIED.

## Konkreta acceptanstester för varje nätverksfunktion
1. Raw bytes: parser, serializer, checksum, MTU, fragment, malformed, unknown protocols, wrong lengths, förvaliderade golden vectors. Orakel får inte vara implementationens egna returvärden.
2. State: timer/retry/lease/neighbor/session/route, boot/power, linkfail, packet reorder, concurrent events, TTL/hoplimit och exception behavior.
3. Positivt, negativt, motsägande: lyckad leverans, förbjuden leverans (VLAN/ACL/linkdown), FIB-route utan fungerande next hop eller returpaket; inget fabricerat ping eller DHCP-ACK.
4. Cross-protocol: samma Runtime och Clock för L2, IP, DHCP, TCP, OSPF, BGP, IoT/OT och appservice; inga parallella sessioners egna timer-facit.
5. Determinism: två separata processstarter får identiska canonical eventbytes+statehash; tie-order, cancel, reset, overflow, zero-delay livelock, untrusted packet och resource budget testas negativt.
6. CLI/GUI/API: samma DeviceRuntime/ConfigSnapshot/Scenario, verkliga show/debug-tabeller, inga hard-coded CLI success, stale workspace generation reject.
7. Browser Linux: verklig Playwright/Chromium i relevanta X11/Wayland-miljöer. ELK port-center geometry, layout pending/stale, drag/cable, Save/Open, import/preview, simulation timelines och packet reasons.
8. Source: verklig CSV/Excel/XLSB/ODS/JSON/YAML/XML-fixture, cellproveniens, formula/cached value handling, duplicate keys, zip/XML bomb, conflicts, explicit atomic Save och SHA.
9. Secure sandbox: importmakro och IoT-script får inte exekvera host commands; säker peer Multiuser, inga reala PLC eller nätverkskortseffekter.
10. Scale: förregistrerade topologier 5/50/500 och 1e5 events som utgångspunkt för R1-performance-spike; ingen påstådd kapacitet före mätning.

Krav för dokumentation: case ID, PT-build+SHA, YadiLab SHA, källstandard/errata, scenario bytes, seed, predicted output och observed output, event/state traces, negativa motbevis och CI/artifacts. Vid olika PT-vs-standardskorrekta resultat: dokumentera båda; PT-output är konkurrensbaseline, inte oberoende orakel.

Fuzz/property/metamorphic och mutationstester ska verifiera att farliga fel upptäcks: försvunnen kabel, omkastad port, VLAN mismatch, stale revision, invalid IPv6, ICMP error suppression, brutna sessions och flera samtidiga timers. Resultat PASS/FAIL/NOT_RUN/BLOCKED med relevant nämnare.

Governance-CI får enbart påstå att planen är sammanhängande, inte att en app eller protokoll fungerar. Se RELEASE_GATES.md.
