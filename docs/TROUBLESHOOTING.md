# Controlled troubleshooting: link failure, symptom and recovery (PR #20)

## Contract

This phase introduces **one narrow reproducible fault type**: disable a single explicit, currently enabled physical link by its canonical `linkId`. It does not create or infer links, alter switch learning rules, or inspect graph connectivity as a substitute for real ICMP. The `compare_link_fault` function validates the entire source document first and requires a real enabled link, explicit source node/port, destination IPv4, TTL, identifier and sequence.

Three **independent** complete `EchoExchange` trials run over the existing single IPv4 / routing / ARP / Ethernet / VLAN engine:

1. **Baseline:** unchanged validated canonical project; real Echo Request and Reply. This establishes whether the chosen communication actually worked before the fault.
2. **Fault:** deep copy of the same canonical project with exactly the explicitly selected link's `enabled` changed from `true` to `false`. All nodes, ports, VLANs, routes, addresses, IDs and other links remain untouched. A new engine (empty ARP/MAC cache) performs the same Echo exchange.
3. **Restoration:** copy of the faulty project with that *same* link re-enabled; its resulting canonical document is checked for equality against the original. A third independent engine executes the identical Echo query.

The response includes **all three real Echo traces**, `request` and `reply` statuses, actual ARP/Ethernet transmissions, ICMP router errors when applicable, and separate lists of observed link IDs derived **only from the actual packet traces**. It never reports physical packet delivery from a graph path alone.

## Classification and repair

- `FAULT_CONFIRMED`: baseline is `REPLIED`, faulted exchange is **not** `REPLIED`, and restored exchange is `REPLIED`. This is the **only** classification where the controlled link change is verified to break that specific modeled communication, and the restoration is verified to recover it.
- `BASELINE_NOT_REPLIED`: the baseline already fails. A later fault cannot be proven to be its cause, regardless of how the faulty trial behaves.
- `NO_OBSERVED_IMPACT`: the baseline and faulted trial both reply successfully. Even if ARP or forwarding used the selected cable in the original experiment, the disabled link is not proven to break communication in this trial.
- `RESTORATION_NOT_VERIFIED`: baseline worked and faulted trial failed, but the independent restored trial did not succeed. Never advertise a successful repair in this case.

The explicit `repair` suggestion is `{"action":"RE_ENABLE_LINK","linkId":"...","expectedEnabled":true,"scope":"PREVIEW_ONLY"}`. It describes only the deliberate rollback of the injected fault, not arbitrary inferred changes to the user's actual documented network. `verifiedFault` and `verifiedRecovery` are true only for `FAULT_CONFIRMED`. The caller's in-memory project object, saved project files, snapshot identifiers and schema remain unchanged. Nothing is saved or applied to the Builder's working model.

## HTTP and Builder

`POST /api/troubleshoot/link` accepts **exactly**:

```json
{
  "project": {"schemaVersion":"1.3","name":"...", "zones":[],"nodes":[],"links":[]},
  "sourceNode":"a","sourcePort":"eth0","destinationIpv4":"203.0.113.20",
  "ttl":5,"identifier":1,"sequence":1,"linkId":"declared-cable-id"
}
```

Invalid links, already disabled links, absent sources, wrong fields or invalid protocol parameters are rejected with HTTP 422. No background work, stateful operation or disk write occurs. Builder provides an explicit source-port selector, destination IP, enabled link selector and TTL. The UI uses fixed ICMP identifier/sequence 1 for this controlled comparison. It shows baseline/fault/restoration results, true observed ARP/IP cable IDs, the precise proposed rollback, and explicit **not applied** notice. Changing the working project invalidates existing comparison results. Stale in-flight HTTP results are discarded if inputs/project differ on return.

## What this proves and does not prove

This phase tests **one simulated controlled fault**, not the root cause of an arbitrary already-broken real-world network. A missing reverse route or a failed reference Echo is explicitly **not** attributed to the selected cable. A disconnected, unrelated cable that does not change the observed Echo success is **not** diagnosed as a failed network. ARP learning is isolated between trials so cached MAC data do not hide a failure.

There is no measured RTT, real packet capture, physical electrical-layer check, automated user-file repair, persistent exercise format, VLAN/route/port fault comparisons, or arbitrary causal discovery yet. Those are separate later stages.

## Verification

`tests/test_troubleshooting.py` covers proven failure and restoration on multiple physical links, an unrelated link with no observed impact, an already failing reference network, disabled/unknown link rejection, invalid source/IP/TTL, actual wire evidence, legacy schema nonmigration, real loopback HTTP and saved bytes/SHA-256 across repeated calls. `tests/browser_smoke.py` covers the actual Builder panel over local HTTP, strict baseline/fault/restore outcomes, a baseline already failing, no silent changes to the live working link and unchanged saved file after comparison.
