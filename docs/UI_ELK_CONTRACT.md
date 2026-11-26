# UI-ELK-001 — tidigare YadiLab-upplevelse, ny kod

**Aktuell referens för samtliga UI-fakta:** [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) + [55 UI-case seeds](requirements/legacy_ui_manifest.json). Låt inte generic dashboard-förslag eller felaktig gammal trekolumnsregel styra: aktuell Legacy CSS vid >=951px visar en full-width topologiruta ovanför två verktygskolumner med collapse/expand. Kodfilen `web/features/layout/elk.js` har `elk.aspectRatio: '3'` medan äldre legacy-layoutdocs nämner 1.6; exakt låst kod och browserobservation har företräde.

Status DESIGN_ONLY, **UI_REFERENCE_SOURCE_AVAILABLE** på [låst YadiLab_legacy commit aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80). [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) är bindande för exakt känt utseende, same-flow, färgtema, fullbreddscanvas ovanför utfällbara nedre panelsamlingar och korrekta ELK-/importflöden. Renderad screenshot-baslinje är fortfarande **NOT_CAPTURED**; ingen implementerad ny UI eller PIXEL_PARITY hävdas. Gammal nätverksruntime är förbjuden som implementationsgrund.

Linux desktop-app med lokal UI: node palette, network canvas, Builder/inspector för devices/ports/config, kablar, importkällor/proveniens, Save/Open, ELK arrange, Simulation Run/Pause/Step/Reset, OSI/PDU/header, drop reason och causal trace. Canvas med zoom/pan och grupper. Enheten som visas har exakt device_id/port_id i projektet; ingen UI-konstruerad packet-success.

Officiell ELK-källa: https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html ; elkjs: https://github.com/kieler/elkjs . ELK layered stöder portconstraints och orthogonal/straight/spline-edges, men är en LAYOUTMOTOR – inte nätverkssimulator.

## Kabelgeometrins icke-förhandlingsbara invariants
- Kabel har explicita original-endpoints, device_id och port_id; ELK genererar aldrig kablar, gateways eller topologi.
- Stable node/port IDs skickas med till elkjs och tillbaka med validerat layout revision ID; SVG edge start/end mäts mot verkligt renderat port-/handle-center med koordinattransform och zoom/pan. Testa riktiga pixlar/DOM, inte gissade x/y.
- Under ELK PENDING visas inte gamla korta kabelstumpar som godkänd fullständig kabel; sena layoutresponser kastas om workspace generation har ändrats.
- Manual drag, zoom, group collapse, reset, Save/Open och node resize får inte flytta cable endpoint ifrån anslutningspunkten eller ändra ProjectRevision links.
- Simulatorns händelser är read-only source för packettrace, FDB/ARP/RIB/FIB och timeline. UI-animationens hastighet kan ändras utan att nätverksbeslut ändras.

R0 använder redan det faktiskt tillgängliga och SHA-låsta Legacy-repot och ska **köra en verklig Legacy-Chromium-referens** och frysa screenshots/DOM vid 1366x768, 1920x1080 och smala viewports. R3 kör samma scenarier i den nya UI:n och jämför visuella/vardagliga användarresor (inklusive originalets 4-stegs importdialog, paneler, ELK auto+Preview/Apply/Cancel, Save/Open och diagnostik). En zip kan vara praktisk offline men är inte längre ett krav för att veta hur källans UI är designad. Inga screenshots är ännu verifierade.

Linux window shell (PySide6 QtWebEngine, Tauri eller lokal browser med launcher) väljs efter liten licensing/Wayland/X11/dependency/packaging-spike; frontend TypeScript + SVG/elkjs separeras från desktop shell. Ingen Windows/macOS-build och ingen särskild keyboard-only accessibility-prioritet.
