# Dev31 MTU/PMTUD truth contract

The dev30 audit found no existing MTU, packet-size, DF, fragmentation, ICMP Fragmentation Needed, IPv6 Packet Too Big, or PMTUD state/event model in the Engine. Dev31 therefore adds only a minimal Engine-owned MTU evaluation: an explicit packet size is supplied by the modeled request, interface/link MTU is read from canonical scenario state, and the Engine reports the comparison with provenance. It is not an IP-stack or timer emulator.

Canonical authority is `interface.mtu` for an egress interface and `connection.properties.mtu`/`linkMtu` for a modeled link. Path MTU is the minimum of fully known interface/link MTUs on an Engine-proven ordered path; incomplete paths are `UNKNOWN`. Packet size is never inferred from protocol. IPv4 DF, fragmentation, ICMP Fragmentation Needed, IPv6 PTB and PMTUD adaptation remain `NOT_MODELED` unless an explicit source/Engine fact exists; this phase does not fabricate those events or timeouts.

The UI may project only the Engine MTU evaluation, packet size, egress/path MTU, comparison, and provenance. It must stop the visual journey at an Engine-reported MTU conflict and must not show a red drop marker unless the existing Engine outcome contract says `FALSE`/blocked. Missing, invalid, conflicting, ambiguous, or stale state is `UNKNOWN`/`UNMODELED`.
