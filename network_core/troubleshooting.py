"""Read-only comparison of a declared link fault with verified restoration.

All three ICMP Echo trials execute independently on validated canonical project
copies via the one existing EchoExchange / IPv4 / ARP / Ethernet engine.
No diagnosis is claimed from topology alone or from a pre-existing failure.
"""
from __future__ import annotations

from copy import deepcopy

from .icmp_ping import EchoExchange
from .model import ProjectValidationError, validate_project


def _observed_wires(exchange: dict) -> list[str]:
    """Actual request/reply/error ARP and IPv4 link IDs, not graph adjacency."""
    visited: set[str] = set()
    traces = [exchange["request"], exchange["reply"]]
    if exchange["icmpError"]:
        traces.append(exchange["icmpError"]["trace"])
    for trace in traces:
        if trace is None:
            continue
        for hop in trace["steps"]:
            for transmit in hop["ipv4Transmissions"]:
                visited.add(transmit["linkId"])
            for field in ("requestTransmissions", "replyTransmissions"):
                for transmit in hop["arp"].get(field, []):
                    visited.add(transmit["linkId"])
    return sorted(visited)


def compare_link_fault(project: dict, source_node: str, source_port: str,
                       destination_ipv4: str, ttl: int, identifier: int,
                       sequence: int, link_id: str) -> dict:
    """Explicitly disconnect ONE enabled link, retest, reconnect, retest.

    Only FAULT_CONFIRMED means a controlled failure was observed *and*
    communication was restored. All outcomes are ephemeral, nonpersistent.
    """
    canonical = validate_project(project)
    if not isinstance(link_id, str):
        raise ProjectValidationError("troubleshoot: linkId must be a declared link ID")
    original_link = next((l for l in canonical["links"] if l["id"] == link_id), None)
    if original_link is None:
        raise ProjectValidationError("troubleshoot: unknown declared linkId")
    if not original_link["enabled"]:
        raise ProjectValidationError("troubleshoot: selected link is already disabled")

    def trial(doc: dict) -> dict:
        return EchoExchange(doc).ping(
            source_node, source_port, destination_ipv4, ttl, identifier, sequence)

    # Run original first: invalid source/target/TTL fails closed without
    # constructing a misleading diagnosis. No ARP or switch learning is
    # shared between trials.
    baseline = trial(canonical)
    faulty_project = deepcopy(canonical)
    next(l for l in faulty_project["links"] if l["id"] == link_id)["enabled"] = False
    faulted = trial(faulty_project)
    restored_project = deepcopy(faulty_project)
    next(l for l in restored_project["links"] if l["id"] == link_id)["enabled"] = True
    if restored_project != canonical:
        raise ProjectValidationError("troubleshoot: restoration changed unrelated project facts")
    restored = trial(restored_project)

    if baseline["status"] != "REPLIED":
        status = "BASELINE_NOT_REPLIED"
        explanation = ("The original ICMP Echo exchange already fails; a new "
                       "cable fault cannot be proven as its cause.")
    elif faulted["status"] == "REPLIED":
        status = "NO_OBSERVED_IMPACT"
        explanation = ("The same bidirectional Echo exchange still succeeds with "
                       "the selected cable disabled; it is not a proven failure.")
    elif restored["status"] != "REPLIED":
        status = "RESTORATION_NOT_VERIFIED"
        explanation = ("Communication did not recover in the independent restoration "
                       "trial; no successful repair is claimed.")
    else:
        status = "FAULT_CONFIRMED"
        explanation = ("One explicitly selected cable was disabled; a previously "
                       "successful Echo exchange failed and succeeded again after "
                       "restoring that exact cable in an isolated copy.")

    return {
        "status": status,
        "meaning": explanation,
        "fault": {
            "type": "LINK_DISABLED",
            "linkId": link_id,
            "fromEnabled": True,
            "toEnabled": False,
        },
        "repair": {
            "action": "RE_ENABLE_LINK",
            "linkId": link_id,
            "expectedEnabled": True,
            "scope": "PREVIEW_ONLY",
        },
        "baseline": baseline,
        "faulted": faulted,
        "restored": restored,
        "observedLinkIds": {
            "baseline": _observed_wires(baseline),
            "faulted": _observed_wires(faulted),
            "restored": _observed_wires(restored),
        },
        "verifiedFault": status == "FAULT_CONFIRMED",
        "verifiedRecovery": status == "FAULT_CONFIRMED",
        "ephemeral": True,
        "projectChanged": False,
    }
