# dev22 — Canonical Packet Journey v2

Version: `1.1.0-dev.22`
Baseline: sealed `1.1.0-dev.21`

## Purpose

dev22 establishes the canonical event/playback contract required by the next Living Visualization phases. It does not replace Engine truth and does not introduce a second network simulator in the UI.

A Journey is an ordered projection of Engine-owned Active Probe evidence. The UI may control presentation time (`Play`, `Pause`, `Step`, `Replay`, speed) but may not change event order, invent hops, fabricate return traffic or infer an unproven terminal state.

## Canonical playback contract

Each built Journey publishes a `VisualJourneyPlaybackContract` with:

- schema version `1.0.0`;
- source `ENGINE_EVENT_PROJECTION`;
- `STRICT_SEQUENCE` ordering;
- deterministic replay;
- exact event count;
- first and terminal event identity;
- the Engine-derived terminal outcome.

All events in one Journey must have contiguous sequence numbers and the same flow identity.

## Packet outcome contract

The packet outcome is intentionally separate from the overall probe verdict.

### `destination_reached`

A green `✓` may be anchored to the destination only when Engine evidence proves the modeled request path reached that destination. The transient marker lifetime is exactly `4000 ms`.

The marker means **packet/request path reached modeled destination**. It does not by itself claim application success, TCP response, healthy service or return-path success.

Destination-side listener/service failures such as a modeled no-listener or disabled-service condition may therefore still have a packet-arrival outcome when Engine evidence proves the request reached the destination host.

### `dropped`

A red `✕` may be anchored only when an exact Engine-owned `blockingPoint` exists. The marker lifetime is exactly `4000 ms`.

If the probe failed but Engine does not prove the exact drop resource, the Journey may report failure in its status text but must use marker `none`. A red marker is never guessed from the last visually convenient node.

Playback stops at the proven blocking point. No later topology hop may be animated as reached.

### `unknown`

UNKNOWN, UNMODELED or incomplete truth never receives a green success marker or a red drop marker. If a last-known resource is proven, a neutral `?` may identify that last-known position without claiming it is the failure location.

## Fail-closed guards

The adapter rejects:

- an unknown destination resource;
- an unknown blocking-point resource;
- a blocking point not present in the Engine path;
- a `TRUE` transcript that simultaneously claims a blocking point;
- path hops that cannot map to one enabled modeled connection;
- existing manipulated routing/L2/policy/NAT/conntrack/host-stack traces rejected by earlier phases.

A `TRUE` transcript whose path stops before the requested destination is not rendered as success. It becomes an UNKNOWN terminal outcome and retains the diagnostic that the path terminal differs from the requested destination.

## UI behavior

The Journey Player exposes a Swedish result row. Before the terminal event it reports that the Journey is in progress. At the terminal event it reports reached, dropped/blocked, or UNKNOWN.

Transient `✓` and `✕` overlays:

- are anchored only from the outcome contract;
- do not resize or relayout React Flow nodes;
- are cleared by Replay, manual stepping/scrubbing, Journey replacement and component cleanup;
- disappear after 4000 ms;
- remain presentation state only.

The neutral UNKNOWN marker is not treated as a timed success/failure effect.

## Regression acceptance

Functional tests include a five-node modeled path:

`client -> access -> core -> firewall -> server`

The success case must traverse all four modeled connections and terminate at `server` with outcome `destination_reached`.

The drop case uses `firewall` as the explicit blocking point. It must traverse only the first three connections, must not animate `firewall -> server`, and must terminate with a red drop outcome anchored to `firewall`.

Additional tests verify unlocated failure and UNKNOWN behavior, deterministic playback metadata, contiguous event order and fail-closed destination/blocking-point validation.

## Scope boundary

This checkpoint is the first part of the larger post-dev21 program. Fully synchronized all-event X-Ray is the next planned checkpoint, followed by the 30+ node enterprise scenario framework and the living routing/ARP/ND/FDB/STP/VLAN/broadcast views.
