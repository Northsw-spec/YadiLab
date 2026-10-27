# Dev30 host/protocol living-visualization truth contract

Dev30 keeps DHCP/DORA, DNS resolution, TCP state, UDP failure and ICMP failure projections bounded by the existing Engine contracts. These events describe modeled state and evidence; they are not guest execution, packet-timer emulation, or fabricated retries/timeouts. Missing listener, resolver, lease, socket, or ICMP evidence remains `UNKNOWN`/`NOT_MODELED` as declared by the Engine trace.
