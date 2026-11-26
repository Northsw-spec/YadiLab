# DECISIONS — normativ arkitekturlogg

D009 USER_DECISION_2026-11-26: **Ingen riktig Packet Tracer-binär krävs för utveckling eller release**. Krav på binärversion/hash, PT_RUN_PASS, och obligatorisk head-to-head borttagna från G0–G6, PT-scope-registret och governance-test. Ciscos publicerade funktionsspecifikationer och oberoende körda standard-/YadiLab-tester krävs fortfarande. Fullständiga empiriska jämförelsepåståenden som saknar jämförbar mätning förblir NOT_VERIFIED. Se [PT-DOC-BASELINE-001](PT_DOCUMENTATION_BASELINE_POLICY.md).


D008 AUDIT_2026-11-26: [REPO-READINESS-001](REPO_READINESS_AUDIT.md) fastställer att **main-ruleset numera är aktivt** (`main`-ruleset 28193830 har `enforcement=active` och `governance-contracts` som Required check enligt senare GitHub-kontroll; inget dokumenterat direktpush-/röd-PR-blockeringstest), publik repo saknar beslutad/LICENSE-fil, och den faktiska Packet Tracer-/Legacy Chromium-/motor-/import-/Linux-release-evidensen saknas. R0 äger dessa blockerare; ingen scope-reduktion eller falsk readiness/COMPLETE. Första motor-POC kan utvecklas isolerat enligt R1 och riktade standardtester.


D007 ACCEPTED: Ett enda deklarerat appvisningsnamn i `core/identity.py::APP_DISPLAY_NAME`; neutral paketering, moduler, funktions-/klass-/namespace-ID, JSON/API och projektfiländelse. [BRAND-IDENTITY-001](BRAND_IDENTITY_CONTRACT.md) styr. Tillverkarnamn som Cisco är korrekt domändata och får uttryckligen förekomma i adapters, klasser, profilspecifikationer och UI. Nytt projektextensionsförslag `.netlab`, gammalt `.yadilab` endast legacy-import efter strikt schema.


2026-11-26. Detta är ingen alternativ roadmap.

D001 ACCEPTED: NY Linux-nätverksmotor och produktimplementation, men Legacy-gränssnittets utseende och beteende **MÅSTE** bibehållas enligt [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) på [Northsw-spec/YadiLab_legacy commit aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80). Den gamla nätverkssimulatorn återanvänds inte; dess UI-källkod är en revisionsbar referens.
D002 ACCEPTED: Målet är ALL dokumenterad Cisco Packet Tracer-funktionalitet i publicerat versionssatt och källgranskat PT-scope, samt mätbara förbättringar; [PT-DOC-BASELINE-001](PT_DOCUMENTATION_BASELINE_POLICY.md) tar bort installation/checksum/upprepade PT-binärkörningar som krav. En direkt runtimejämförelse är frivillig; inga påståenden om empiriskt observerad PT-ekvivalens utan sådan evidens. Linux-only och ingen ny keyboard-only/accessibility-paritet är enda scopeundantagen.
D003 ACCEPTED: EN deterministisk in-process DES, EN gemensam virtual-time och runtime-state, bytes och kausala händelser. Ingen extern GNS3/EVE-NG/FRRouting/ns-3/IOS-emulator runtime.
D004 ACCEPTED: projektdata/proveniens, simulation och UI/ELK är olika ägare; canvas får inte härleda kablar, routes eller lyckade packet deliveries.
D005 ACCEPTED: en aktiv roadmap och högst en PR; verkliga standardtest/CLI/UI/projektresultat före VERIFIED-native.
D006 ACCEPTED: proprietära format utan legal/spec evidence blir BLOCKED_LEGAL_OR_SPEC; inget falskt FULL_PARITY.

P001 PROVISIONAL: Python 3.12+ typed DES kernel, Rust-hotpath enbart efter riktig benchmark, aldrig andra motor.
P002 PROVISIONAL: TypeScript frontend med SVG/elkjs och React/Vite utifrån UI spike.
P003 PROVISIONAL: Linux window shell via PySide6 QtWebEngine, Tauri eller browser + native launcher, efter licens/Wayland/X11/packaging tests.
P004 PROVISIONAL: brandneutralt .netlab JSON-projektformat och strikt schema, bekräftas av golden data fixtures.
P005 PROVISIONAL: python-calamine/openpyxl/ODS och andra läsare, faktiska XLS/XLSB/ODS-tester saknas.
P006 SOURCE_AVAILABLE_RENDER_BASELINE_PENDING: äldre UI-källan och koden är granskade/pinnade på Legacy commit aac82926ced3dbf4cac09242530762ac3da1fe80. Verklig Chromium reference, screenshot-/DOM-goldens och nyskapad exakt UI-paritet saknas ännu. Inga påståenden om pixelidentisk ny UI före real comparison.
P007 DOCUMENTATION_BASELINE: Ciscos 9.0-hjälp är en källstart, exakt installerad PT-binär behövs inte. Okända device-/CLI-/filformatvarianter stannar SOURCE_UNCERTAIN tills källorna och funktionerna kan verifieras enligt [PT-DOC-BASELINE-001](PT_DOCUMENTATION_BASELINE_POLICY.md).

Inget P-beslut får uppgraderas till faktapåstående utan separat R0/R1 acceptans.
