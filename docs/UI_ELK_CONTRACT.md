# UI-ELK-001 — tidigare YadiLab-upplevelse, ny kod
Status DESIGN_ONLY, UI_REFERENCE_MISSING. Utan tidigare källkods-ZIP eller referensbilder kan pixelidentitet INTE verifieras. Använd endast gammalt material som visuellt/importreferens efter licensgranskning, aldrig som framtida nätverksmotor.

Linux desktop-app med lokal UI: node palette, network canvas, Builder/inspector för devices/ports/config, kablar, importkällor/proveniens, Save/Open, ELK arrange, Simulation Run/Pause/Step/Reset, OSI/PDU/header, drop reason och causal trace. Canvas med zoom/pan och grupper. Enheten som visas har exakt device_id/port_id i projektet; ingen UI-konstruerad packet-success.

Officiell ELK-källa: https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html ; elkjs: https://github.com/kieler/elkjs . ELK layered stöder portconstraints och orthogonal/straight/spline-edges, men är en LAYOUTMOTOR – inte nätverkssimulator.

## Kabelgeometrins icke-förhandlingsbara invariants
- Kabel har explicita original-endpoints, device_id och port_id; ELK genererar aldrig kablar, gateways eller topologi.
- Stable node/port IDs skickas med till elkjs och tillbaka med validerat layout revision ID; SVG edge start/end mäts mot verkligt renderat port-/handle-center med koordinattransform och zoom/pan. Testa riktiga pixlar/DOM, inte gissade x/y.
- Under ELK PENDING visas inte gamla korta kabelstumpar som godkänd fullständig kabel; sena layoutresponser kastas om workspace generation har ändrats.
- Manual drag, zoom, group collapse, reset, Save/Open och node resize får inte flytta cable endpoint ifrån anslutningspunkten eller ändra ProjectRevision links.
- Simulatorns händelser är read-only source för packettrace, FDB/ARP/RIB/FIB och timeline. UI-animationens hastighet kan ändras utan att nätverksbeslut ändras.

R0 kräver konkret ZIP eller screenshots av tidigare YadiLab för golden reference. R3 kör verklig Chromium/Playwright vid 1366x768 och 1920x1080 för canvas, imported docs, explicit cable endpoint, layout stale handling, save/open, simulation event UI. Förrän golden reference finns: endast FUNCTIONAL_UI, ej SAME_UI_VERIFIED.

Linux window shell (PySide6 QtWebEngine, Tauri eller lokal browser med launcher) väljs efter liten licensing/Wayland/X11/dependency/packaging-spike; frontend TypeScript + SVG/elkjs separeras från desktop shell. Ingen Windows/macOS-build och ingen särskild keyboard-only accessibility-prioritet.
