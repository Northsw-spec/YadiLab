# DECISIONS — normativ arkitekturlogg

2026-11-26. Detta är ingen alternativ roadmap.

D001 ACCEPTED: NY Linux-kodbas; ingen tidigare motor återanvänds. Äldre ZIP endast för visuellt UI-/ELK-/importreferens efter källgranskning.
D002 ACCEPTED: ALL Cisco Packet Tracer-funktionsparitet i relevant licensierad och exakt versionerad baseline, samt ökad faktisk kvalitet. Endast Linux-port och ny keyboard-only/accessibility är undantagna.
D003 ACCEPTED: EN deterministisk in-process DES, EN gemensam virtual-time och runtime-state, bytes och kausala händelser. Ingen extern GNS3/EVE-NG/FRRouting/ns-3/IOS-emulator runtime.
D004 ACCEPTED: projektdata/proveniens, simulation och UI/ELK är olika ägare; canvas får inte härleda kablar, routes eller lyckade packet deliveries.
D005 ACCEPTED: en aktiv roadmap och högst en PR; verkliga standardtest/CLI/UI/projektresultat före VERIFIED-native.
D006 ACCEPTED: proprietära format utan legal/spec evidence blir BLOCKED_LEGAL_OR_SPEC; inget falskt FULL_PARITY.

P001 PROVISIONAL: Python 3.12+ typed DES kernel, Rust-hotpath enbart efter riktig benchmark, aldrig andra motor.
P002 PROVISIONAL: TypeScript frontend med SVG/elkjs och React/Vite utifrån UI spike.
P003 PROVISIONAL: Linux window shell via PySide6 QtWebEngine, Tauri eller browser + native launcher, efter licens/Wayland/X11/packaging tests.
P004 PROVISIONAL: canonical .yadilab JSON projektformat och strikt schema, bekräftas av golden data fixtures.
P005 PROVISIONAL: python-calamine/openpyxl/ODS och andra läsare, faktiska XLS/XLSB/ODS-tester saknas.
P006 REFERENCE_MISSING: samma UI som tidigare YadiLab kräver ägarens original-ZIP eller screenshots.
P007 NOT_VERIFIED: exakt Cisco Packet Tracer 9.0.1/future binary; bara dokumentation från 9.0 help är granskad.

Inget P-beslut får uppgraderas till faktapåstående utan separat R0/R1 acceptans.
