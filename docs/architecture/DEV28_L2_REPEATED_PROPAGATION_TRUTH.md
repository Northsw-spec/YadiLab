# Dev28 L2 repeated-propagation truth contract

Dev28 models a broadcast/flooding frame as a deterministic, bounded graph traversal. The Engine is authoritative; the browser only projects Engine events and derived counters.

## Canonical state

`resource.properties.stpPorts` is the sole authoritative per-interface STP state. Every row must reference one declared resource interface, have a unique `interface`, and use the canonical upper-case state vocabulary. Legacy `properties.stp.portState` is not consulted by the propagation Engine. Importers may normalize legacy input before runtime state is created; an unresolved or ambiguous port is `UNKNOWN`, never an invented forwarding state.

## Event and safety semantics

The traversal orders connections and egresses lexicographically by stable IDs. It emits `FRAME_GENERATED`, `FLOOD_FORWARD`, `LOOP_REENTRY`, `SIMULATION_LIMIT`, and `PROPAGATION_COMPLETE`. A loop re-entry is an observed repeated visit to a resource in the current branch; it is not a packet drop. `SIMULATION_LIMIT` is the only cutoff event and records the configured event/depth budget. No wall clock, random value, implicit TTL, or UI-side event is part of the truth model.

Counters are derived exclusively from the emitted Engine events. A visual frame may highlight only the connection ID carried by the corresponding Engine event and must preserve the event provenance. Missing/malformed STP, missing endpoints, and ambiguous interface mappings fail closed to `UNKNOWN`.
