# ARCH-001 — en ny sammanhängande simuleringsarkitektur

**APP-ID-001, normativ namnseparation:** [BRAND-IDENTITY-001](BRAND_IDENTITY_CONTRACT.md) kräver ett enda `APP_DISPLAY_NAME` i `core/identity.py`, dynamisk läsning via `core/metadata.py`, framöver `/api/meta`, och brandneutrala klass-/funktions-/namespace-/schema-/package-ID. UI/desktop visar bara det hämtade namnet; native Linux launchern genererar användarsynligt `Name` från samma deklaration vid byggtid. **Cisco och andra korrekta tillverkarnamn får finnas i device-/CLI-specifika adaptrar och användargränssnitt.**


Status 2026-11-26: DESIGN_DECISION; NOT_IMPLEMENTED. Ingen tidigare YadiLab-motor kopieras.

## Tre skilda sanningsdomäner
1. SOURCE/PROJECT: original dokumentbytes, stable provenance, immutable ProjectRevision med explicita device/port/link/config facts och ett atomic explicit Save.
2. SIMULATION: en ScenarioRuntime per scenario och revision med en VirtualClock/EventKernel, seedad PRNG, DeviceRuntime, PortRuntime, LinkRuntime, protocol registry och immutable event log.
3. PRESENTATION: TypeScript GUI/SVG/ELK och CLI-adapter som enbart frågar samma kanoniska runtime/config och inte beräknar paket- eller routingfacit.

Endast validated project configuration används som startinput till simulation. Canvasposition, ELK-rutt, rubrik och dokument-tabell är inte kablar.

## Normativa framtida interfaces (ännu EJ kod)
| Contract | Input | Output, ägare |
|---|---|---|
| ConfigSnapshot.validate | raw source/schema/version/provenance | immutable explicit project or errors |
| DeviceProfile | versioned model, ports, modules, power and CLI capabilities | immutable hardware/features; no anonymous defaults |
| ScenarioRuntime.create | validated config, revision, seed | sole actor registry, Kernel, time=0, scenario generation |
| EventKernel.schedule | actor, typed event, time_ns or checked delay, parent_id | stable unique event_id or reject; no backwards time |
| EventKernel.step/pause/cancel/reset | bounded event/time quotas, cancel tokens | monotonic deterministic trace; no callback leak |
| LinkRuntime.transmit | port, frame bytes, link state, queue config | TX_START/TX_END/PROPAGATE/RX or explicit drop |
| DeviceRuntime.receive | parsed real bytes, ingress port, causal parent | protocol state mutation, RX/DROP or scheduled TX |
| ProtocolRegistry.dispatch | typed input, device capabilities, owned state view | checked effects and timers, no cross-state mutation |
| CLI.execute | command AST, mode, privilege, expected project revision | typed mutation/error and accurate show/debug |
| Inspector.snapshot | scenario, revision, event range | immutable byte/state/queue/RIB/FIB/timer/drop explanation |
| ScenarioGateway | authenticated action, expected revision, generation | one runtime owner and explicit stale/unknown error |

State owners: L2 device owns FDB; L3 device owns RIB and FIB distinctly; interface owns ARP/ND; DHCP actor owns leases; TCP actor owns connection/retry/window; port/link actors own queues and in-flight frames; kernel owns clock and event ordering. Crossprotokoll-kommunikation sker genom händelser och read-only views, ALDRIG globals eller en ny separat thread-/time-simulator.

## Riktig packet/casuality semantics
Hela vägen ska vara packet bytes och händelser: app -> transport -> IPv4/6 -> neighbor -> link TX queue -> serialization -> propagation -> RX/FCS/parser -> VLAN/FDB/route/ACL/queue decision -> next TX/drop -> endpoint app -> eventdriven response. En FIB-match eller kabelikonen är aldrig end-to-end delivery.

Event ordering = integer (time_ns,event_id) och monotont event_id per scenario, seedad versionslåst PRNG. Check overflow/negative time, cancelled events, zero-delay livelock, unknown target/protocol/frame, resource budget, linkdown mitt i TX och scenario replacement. Two separate process starts with identical bytes/seed must yield byte-identical event trace and statehash. UI animation och wall clock får aldrig avgöra nätverkets semantik.

## Teknisk kandidat, ännu ej prestandabevisad
Python 3.12+ typed dataclass/heapq-core, dedicated adapters och external frontend i TypeScript + SVG/elkjs. Ändra inte motorns semantik vid performance-optimering. Om oberoende R1-benchmark faktiskt bevisar flaskhals, pröva Rust internt bakom samma interface, men aldrig en parallell motor. Linux desktop-shell väljs först efter faktisk Qt/PySide6/Tauri/launcher och licens-/packaging-spike; lokalt loopback UI är möjligt preliminärt. Användaren ska få en faktiskt installerbar Linux-applikation, inte bara ett källkodsskript.

## Modulgränser
Project storage and validation → typed config. Importers → source evidence + manual mapping → project. Engine kernel → device, link, protocol actor. Session gateway → engine. GUI and CLI → gateway. ELK → layout projector; no engine import. Tests → independent oracle, fake network traces forbidden.

## Anti-disposable-POC
POC0 definierar DeviceProfile, PortProfile, LinkProfile, ConfigSnapshot och CLI error/transaction redan samtidigt med kernel, även om initial CLI stub ENBART returnerar tydligt unsupported utan falsk framgång. POC1 visar host-switch-host unicast/broadcast och verklig ARP, mellanliggande link/port-fel och VLAN mismatch; no hard-coded ping. Full CLI/device/physical builds görs vertikalt innan S10, inte som en jättelik sen efterhandsrefaktor.

Go/no-go kräver oberoende orakel, negativa scenario, determinism, source behavior preservation och real Chromium UI regression; ingen formell garanti om att framtida alla integrationer blir regressionsfria.
