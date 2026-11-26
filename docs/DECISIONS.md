# DECISIONS — normativ arkitekturlogg

D007 ACCEPTED: Ett enda deklarerat appvisningsnamn i `core/identity.py::APP_DISPLAY_NAME`; neutral paketering, moduler, funktions-/klass-/namespace-ID, JSON/API och projektfiländelse. [BRAND-IDENTITY-001](BRAND_IDENTITY_CONTRACT.md) styr. Tillverkarnamn som Cisco är korrekt domändata och får uttryckligen förekomma i adapters, klasser, profilspecifikationer och UI. Nytt projektextensionsförslag `.netlab`, gammalt `.yadilab` endast legacy-import efter strikt schema.


2026-11-26. Detta är ingen alternativ roadmap.

D001 ACCEPTED: NY Linux-nätverksmotor och produktimplementation, men Legacy-gränssnittets utseende och beteende **MÅSTE** bibehållas enligt [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) på [Northsw-spec/YadiLab_legacy commit aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80). Den gamla nätverkssimulatorn återanvänds inte; dess UI-källkod är en revisionsbar referens.
D002 ACCEPTED: ALL Cisco Packet Tracer-funktionsparitet i relevant licensierad och exakt versionerad baseline, samt ökad faktisk kvalitet. Endast Linux-port och ny keyboard-only/accessibility är undantagna.
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
P007 NOT_VERIFIED: exakt Cisco Packet Tracer 9.0.1/future binary; bara dokumentation från 9.0 help är granskad.

Inget P-beslut får uppgraderas till faktapåstående utan separat R0/R1 acceptans.
