# Controlled troubleshooting: link, port, VLAN, IPv4 and route faults (PR #20–22)

## Contract

The first phase introduced disabling an enabled physical link by its canonical `linkId`. PR #21 added port and VLAN fault previews. PR #22 adds changing an enabled non-switch interface IPv4 prefix, temporarily removing one declared static route by its stable ID, or changing only that route's explicit next-hop IPv4. It does not create or infer links, alter switch learning rules, or inspect graph connectivity as a substitute for real ICMP. The `compare_link_fault` function validates the entire source document first and requires a real enabled link, explicit source node/port, destination IPv4, TTL, identifier and sequence.

Three **independent** complete `EchoExchange` trials run over the existing single IPv4 / routing / ARP / Ethernet / VLAN engine:

1. **Baseline:** unchanged validated canonical project; real Echo Request and Reply. This establishes whether the chosen communication actually worked before the fault.
2. **Fault:** deep copy of the same canonical project with exactly one explicitly selected fact changed: `link.enabled`, `port.enabled`, `switchPort.vlan`, one trunk VLAN membership, a port's IPv4 prefix, one static route entry removed, or the next-hop of one static route. All other nodes, ports, VLANs, routes, addresses, IDs and links remain untouched. A new engine (empty ARP/MAC cache) performs the same Echo exchange.
3. **Restoration:** copy of the faulty project with that *same* single value restored; the validated canonical result is checked for exact equality with the original. A third independent engine executes the identical Echo query.

The response includes **all three real Echo traces**, `request` and `reply` statuses, actual ARP/Ethernet transmissions, ICMP router errors when applicable, and separate lists of observed link IDs derived **only from the actual packet traces**. It never reports physical packet delivery from a graph path alone.

## Classification and repair

- `FAULT_CONFIRMED`: baseline is `REPLIED`, faulted exchange is **not** `REPLIED`, and restored exchange is `REPLIED`. This is the **only** classification where the controlled link change is verified to break that specific modeled communication, and the restoration is verified to recover it.
- `BASELINE_NOT_REPLIED`: the baseline already fails. A later fault cannot be proven to be its cause, regardless of how the faulty trial behaves.
- `NO_OBSERVED_IMPACT`: the baseline and faulted trial both reply successfully. Even if ARP or forwarding used the selected cable in the original experiment, the disabled link is not proven to break communication in this trial.
- `RESTORATION_NOT_VERIFIED`: baseline worked and faulted trial failed, but the independent restored trial did not succeed. Never advertise a successful repair in this case.

The explicit `repair` suggestion is one of `RE_ENABLE_LINK`, `RE_ENABLE_PORT`, `RESTORE_VLAN_CONFIG`, `RESTORE_IPV4`, `RESTORE_STATIC_ROUTE`, or `RESTORE_NEXT_HOP`, with the exact original link/port or switch VLAN settings, and always `"scope":"PREVIEW_ONLY"`. It describes only deliberate rollback of the injected fault, not arbitrary inferred changes to the user's actual documented network. `verifiedFault` and `verifiedRecovery` are true only for `FAULT_CONFIRMED`. The caller's in-memory project object, saved project files, snapshot identifiers and schema remain unchanged. Nothing is saved or applied to the Builder's working model.

## HTTP and Builder

The existing `POST /api/troubleshoot/link` remains unchanged and now calls the same comparison engine as the extended endpoint. `POST /api/troubleshoot/link` accepts **exactly**:

```json
{
  "project": {"schemaVersion":"1.3","name":"...", "zones":[],"nodes":[],"links":[]},
  "sourceNode":"a","sourcePort":"eth0","destinationIpv4":"203.0.113.20",
  "ttl":5,"identifier":1,"sequence":1,"linkId":"declared-cable-id"
}
```

New `POST /api/troubleshoot/fault` accepts the same exact top-level fields as the link endpoint, except it requires `fault` rather than `linkId`. Each `fault` object is **one** exact shape:

```json
{"type":"LINK_DISABLED","linkId":"cable-1"}
{"type":"PORT_DISABLED","nodeId":"switch-a","portId":"ge-1"}
{"type":"ACCESS_VLAN_CHANGED","nodeId":"switch-a","portId":"ge-2","newVlan":20}
{"type":"TRUNK_VLAN_BLOCKED","nodeId":"switch-a","portId":"te-1","blockedVlan":10}
{"type":"IPV4_PREFIX_CHANGED","nodeId":"router-a","portId":"lan","newPrefix":30}
{"type":"STATIC_ROUTE_REMOVED","nodeId":"client-a","routeId":"r-1"}
{"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"client-a","routeId":"r-1","newNextHop":"192.0.2.254"}
```

An access fault requires an enabled **switch access port** with an explicit, different target VLAN 1–4094; a trunk fault requires an enabled **switch trunk port**, the chosen VLAN explicitly in its `allowedVlans` and **at least one other allowed VLAN remaining**. Invalid or noncanonical faulted network configurations are rejected, not silently adjusted. Trunk access restrictions must still satisfy the existing Ethernet/VLAN network contract. Port faults require an enabled declared port on any node, but selecting **the very source port of the diagnostic Echo** is rejected with 422: the existing sender cannot originate a packet from a disabled source, and the comparison must not fabricate a third Echo trace. Transit, switch and destination ports are supported. IPv4-prefix faults require an enabled non-switch interface with a declared IPv4/CIDR address. The user changes **only the prefix** to a different integer in 1..32; the host IP must not change. Existing static routes must remain valid under the new prefix, including their on-link next-hop, or the entire comparison is rejected with 422—no silent drop. Static-route faults require schema 1.3 and exact existing node/route IDs. Route removal preserves array ordering upon restoration. Changed next-hop must differ from the original and be canonical IPv4; the **existing canonical validator** checks that it is unicast, on-link, nonself and not subnet network/broadcast. No synthetic gateway, route or cable is created. Invalid links, disabled links/ports, absent sources, unknown fields, wrong field types, invalid protocol parameters or unsupported VLAN configurations return HTTP 422. No background work, stateful operation or disk write occurs. Builder provides source-port, destination IP, TTL, an explicit fault-type selector, and the appropriate enabled link, port or configured switch VLAN port plus numeric VLAN choice. The UI uses fixed ICMP identifier/sequence 1 for this controlled comparison. It shows baseline/fault/restoration results, true observed ARP/IP cable IDs, the precise proposed rollback, and explicit **not applied** notice. Changing the working project invalidates existing comparison results. Stale in-flight HTTP results are discarded if inputs/project differ on return.

## What this proves and does not prove

This phase tests **one simulated controlled fault**, not the root cause of an arbitrary already-broken real-world network. A missing reverse route or a failed reference Echo is explicitly **not** attributed to the selected cable. A disconnected, unrelated cable that does not change the observed Echo success is **not** diagnosed as a failed network. ARP learning is isolated between trials so cached MAC data do not hide a failure.

There is no measured RTT, real packet capture, physical electrical-layer check, automated user-file repair, persistent exercise format, arbitrary IP-address changes, or automatic discovery of unknown root causes. One wrong prefix, removed route or changed next-hop is modeled at a time; an invalid configured state is rejected rather than silently corrected. Those are separate later stages.

## Verification

`tests/test_troubleshooting_ipv4_routes.py` verifies real two-way Echo impact and recovery for router-prefix /30, missing forward and return static routes, incorrect but on-link next-hop with ARP failure, unaffected /25 prefix, baseline already broken, strict invalid IP/prefix/route/gateway inputs, legacy formats, exact route ordering, real loopback HTTP, and unchanged stored bytes/SHA. Chromium drives the IP-prefix preview and validates a real reply-route failure, checks no false fault attribution when the baseline already fails, and validates bad/good explicit next-hop inputs without mutations.

`tests/test_troubleshooting_port_vlan.py` now checks host/router/switch port failures, a mismatched access VLAN, real tagged-switch-trunk VLAN 10 removal, unrelated VLAN 20 with no observed impact, invalid disabled/unknown ports, same/invalid/last trunk VLAN rejection, actual HTTP 422, independent ARP learning and unchanged on-disk SHA. Chromium covers controlled port and access VLAN faults/recoveries, invalid same-VLAN injection and no eligible trunk option. 

`tests/test_troubleshooting.py` covers proven failure and restoration on multiple physical links, an unrelated link with no observed impact, an already failing reference network, disabled/unknown link rejection, invalid source/IP/TTL, actual wire evidence, legacy schema nonmigration, real loopback HTTP and saved bytes/SHA-256 across repeated calls. `tests/browser_smoke.py` covers the actual Builder panel over local HTTP, strict baseline/fault/restore outcomes, a baseline already failing, no silent changes to the live working link and unchanged saved file after comparison.
