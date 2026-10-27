# Phase 80 — Living Packet Journey (v1.1.0-dev.1)

Status: DEVELOPMENT CHECKPOINT CANDIDATE — not a verified release.

This phase begins implementation of the authoritative Living Topology & Visual Simulation Specification.

Implemented vertical slice:

- Active modeled probes become a deterministic `VisualJourneyModel` derived from the existing Engine-backed `ActiveProbeTranscript`.
- Scenario hash/revision binding prevents stale evidence from being animated against a different scenario.
- Every animated hop must map to an enabled declared network/management connection; unmapped motion fails closed.
- Blocking points truncate the reached path so later nodes are never shown as reached.
- TRUE terminates as arrival, FALSE as drop/no-path, UNKNOWN as uncertain; the renderer never turns UNKNOWN into a success animation.
- React Flow semantic edges render directional journey arrows.
- Three presentation-only renderers share identical semantics: PDU/envelope, particles, flow pulse.
- Completed path, active segment, source/current/destination and arrival/drop/unknown device states are visibly distinct.
- Journey Player includes Replay, Play/Pause, Step Back, Step Forward, scrubber and 0.25x/0.5x/1x/2x/4x speeds.
- Journey UI exposes provenance as MODELED, runtime revision and evidence count.
- Reduced-motion users retain path/state semantics without continuous motion.

Truth boundary:

No packet, socket, guest command or real network request is executed by this visualization. It renders the same deterministic modeled active-probe truth already produced by YadiLab. React components do not choose the path, blocking point or verdict.

Local development verification:

- visual journey pure TypeScript compile PASS
- functional journey tests PASS
- adversarial truth-binding tests PASS
- UI static contract PASS
- `node --check ui/app/main.mjs` PASS

Still required before any verified v1.1.0 claim:

- exact pinned TypeScript/esbuild/browser toolchain replay
- real Chromium rendering and animation acceptance
- real Firefox rendering acceptance
- screenshot/DOM checks for healthy route, blocking-point drop and no-path
- complete Foundation regression suite
- strict-offline Parrot acceptance
- deterministic product build/reproducibility gates
