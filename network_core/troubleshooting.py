"""Read-only fault comparison using the single existing Echo/IPv4/ARP/Ethernet engine.

Link, port and explicit VLAN fault mutations operate only on a canonical copy.
No speculative causal diagnosis, automatic repair, or file/working-state writes.
"""
from __future__ import annotations

from copy import deepcopy
import ipaddress

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


def _exact_fault(value: object, kind: str, required: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != required or value.get("type") != kind:
        raise ProjectValidationError(
            f"troubleshoot: {kind} requires exactly {', '.join(sorted(required))}")
    return value


def _port(project: dict, node_id: object, port_id: object) -> tuple[dict, dict]:
    if not isinstance(node_id, str) or not isinstance(port_id, str):
        raise ProjectValidationError("troubleshoot: nodeId and portId must be strings")
    device = next((n for n in project["nodes"] if n["id"] == node_id), None)
    if device is None:
        raise ProjectValidationError("troubleshoot: unknown nodeId")
    port = next((p for p in device["ports"] if p["id"] == port_id), None)
    if port is None:
        raise ProjectValidationError("troubleshoot: unknown portId on selected node")
    return device, port


def _mutation(project: dict, fault: object) -> tuple[dict, dict, callable, callable]:
    """Validate a single explicit change and return apply/undo operations.

    The closure inputs are independent canonical document copies, not shared
    simulator instances or persisted source documents.
    """
    if not isinstance(fault, dict) or not isinstance(fault.get("type"), str):
        raise ProjectValidationError("troubleshoot: expected explicit fault type")
    kind = fault["type"]
    if kind == "LINK_DISABLED":
        _exact_fault(fault, kind, {"type", "linkId"})
        link_id = fault["linkId"]
        if not isinstance(link_id, str):
            raise ProjectValidationError("troubleshoot: linkId must be a declared link ID")
        link = next((l for l in project["links"] if l["id"] == link_id), None)
        if link is None:
            raise ProjectValidationError("troubleshoot: unknown declared linkId")
        if not link["enabled"]:
            raise ProjectValidationError("troubleshoot: selected link is already disabled")

        def select(doc: dict) -> dict:
            return next(l for l in doc["links"] if l["id"] == link_id)

        def inject(doc: dict) -> None:
            select(doc)["enabled"] = False

        def undo(doc: dict) -> None:
            select(doc)["enabled"] = True

        return (
            {"type": kind, "linkId": link_id, "fromEnabled": True, "toEnabled": False},
            {"action": "RE_ENABLE_LINK", "linkId": link_id,
             "expectedEnabled": True, "scope": "PREVIEW_ONLY"},
            inject, undo,
        )

    if kind in ("IPV4_PREFIX_CHANGED", "IPV4_HOST_ADDRESS_CHANGED",
                "STATIC_ROUTE_REMOVED", "STATIC_NEXT_HOP_CHANGED"):
        if kind == "IPV4_HOST_ADDRESS_CHANGED":
            _exact_fault(fault, kind, {"type", "nodeId", "portId", "newIpv4"})
            node_id, port_id = fault["nodeId"], fault["portId"]
            device, port = _port(project, node_id, port_id)
            if device["kind"] != "host" or not port["enabled"] or port["ipv4"] is None:
                raise ProjectValidationError("troubleshoot: address fault requires an enabled host IPv4 port")
            original = port["ipv4"]
            configured = ipaddress.IPv4Interface(original)
            address = fault["newIpv4"]
            if type(address) is not str:
                raise ProjectValidationError("troubleshoot: newIpv4 must be a canonical host address")
            try:
                changed_ip = ipaddress.IPv4Address(address)
            except ipaddress.AddressValueError:
                raise ProjectValidationError("troubleshoot: newIpv4 must be a canonical host address") from None
            occupied = {ipaddress.IPv4Interface(p["ipv4"]).ip
                        for node in project["nodes"] for p in node["ports"]
                        if p["ipv4"] is not None}
            network = configured.network
            if (str(changed_ip) != address or changed_ip not in network
                    or changed_ip in occupied or changed_ip.is_multicast
                    or changed_ip.is_unspecified or changed_ip.is_reserved
                    or (network.prefixlen <= 30 and changed_ip in
                        (network.network_address, network.broadcast_address))):
                raise ProjectValidationError("troubleshoot: newIpv4 must be an unused host address in the documented subnet")
            changed = str(ipaddress.IPv4Interface(f"{address}/{network.prefixlen}"))

            def select(doc: dict) -> dict:
                return _port(doc, node_id, port_id)[1]

            def inject(doc: dict) -> None:
                select(doc)["ipv4"] = changed

            def undo(doc: dict) -> None:
                select(doc)["ipv4"] = original

            return (
                {"type": kind, "nodeId": node_id, "portId": port_id,
                 "fromIpv4": original, "toIpv4": changed},
                {"action": "RESTORE_IPV4", "nodeId": node_id, "portId": port_id,
                 "expectedIpv4": original, "scope": "PREVIEW_ONLY"},
                inject, undo,
            )
        if kind == "IPV4_PREFIX_CHANGED":
            _exact_fault(fault, kind, {"type", "nodeId", "portId", "newPrefix"})
            node_id, port_id = fault["nodeId"], fault["portId"]
            device, port = _port(project, node_id, port_id)
            if device["kind"] == "switch" or not port["enabled"] or port["ipv4"] is None:
                raise ProjectValidationError(
                    "troubleshoot: IPv4 prefix fault requires an enabled non-switch port with explicit IPv4/CIDR")
            new_prefix = fault["newPrefix"]
            if type(new_prefix) is not int or not 1 <= new_prefix <= 32:
                raise ProjectValidationError("troubleshoot: newPrefix must be an integer 1..32")
            current = ipaddress.IPv4Interface(port["ipv4"])
            if new_prefix == current.network.prefixlen:
                raise ProjectValidationError("troubleshoot: newPrefix must differ from configured prefix")
            original = port["ipv4"]
            changed = str(ipaddress.IPv4Interface(
                f"{current.ip}/{new_prefix}"))

            def select(doc: dict) -> dict:
                return _port(doc, node_id, port_id)[1]

            def inject(doc: dict) -> None:
                select(doc)["ipv4"] = changed

            def undo(doc: dict) -> None:
                select(doc)["ipv4"] = original

            return (
                {"type": kind, "nodeId": node_id, "portId": port_id,
                 "fromIpv4": original, "toIpv4": changed},
                {"action": "RESTORE_IPV4", "nodeId": node_id, "portId": port_id,
                 "expectedIpv4": original, "scope": "PREVIEW_ONLY"},
                inject, undo,
            )

        required = {"type", "nodeId", "routeId"}
        if kind == "STATIC_NEXT_HOP_CHANGED":
            required.add("newNextHop")
        _exact_fault(fault, kind, required)
        node_id, route_id = fault["nodeId"], fault["routeId"]
        if not isinstance(node_id, str) or not isinstance(route_id, str):
            raise ProjectValidationError("troubleshoot: nodeId and routeId must be strings")
        node = next((n for n in project["nodes"] if n["id"] == node_id), None)
        if node is None or node["kind"] == "switch":
            raise ProjectValidationError("troubleshoot: static route fault requires a declared non-switch node")
        routes = node.get("staticRoutes")
        if routes is None:
            raise ProjectValidationError("troubleshoot: node has no schema 1.3 static routes")
        index = next((i for i, r in enumerate(routes) if r["id"] == route_id), None)
        if index is None:
            raise ProjectValidationError("troubleshoot: unknown static routeId")
        original_route = deepcopy(routes[index])

        def route_list(doc: dict) -> list[dict]:
            device = next(n for n in doc["nodes"] if n["id"] == node_id)
            return device["staticRoutes"]

        if kind == "STATIC_ROUTE_REMOVED":
            def inject(doc: dict) -> None:
                route_list(doc).pop(index)

            def undo(doc: dict) -> None:
                route_list(doc).insert(index, deepcopy(original_route))

            return (
                {"type": kind, "nodeId": node_id, "routeId": route_id,
                 "removedRoute": original_route},
                {"action": "RESTORE_STATIC_ROUTE", "nodeId": node_id,
                 "routeId": route_id, "expectedRoute": original_route,
                 "scope": "PREVIEW_ONLY"},
                inject, undo,
            )

        next_hop = fault["newNextHop"]
        if not isinstance(next_hop, str):
            raise ProjectValidationError("troubleshoot: newNextHop must be a canonical IPv4 address")
        try:
            ip = ipaddress.IPv4Address(next_hop)
        except ipaddress.AddressValueError:
            raise ProjectValidationError(
                "troubleshoot: newNextHop must be a canonical IPv4 address") from None
        if str(ip) != next_hop or next_hop == original_route["nextHop"]:
            raise ProjectValidationError("troubleshoot: newNextHop must differ and be canonical")
        # Validation of on-link, non-reserved and non-self IPv4 gateway is
        # performed by the ONE canonical validate_project on the fault copy.
        def inject(doc: dict) -> None:
            route_list(doc)[index]["nextHop"] = next_hop

        def undo(doc: dict) -> None:
            route_list(doc)[index]["nextHop"] = original_route["nextHop"]

        return (
            {"type": kind, "nodeId": node_id, "routeId": route_id,
             "fromNextHop": original_route["nextHop"], "toNextHop": next_hop},
            {"action": "RESTORE_NEXT_HOP", "nodeId": node_id,
             "routeId": route_id, "expectedNextHop": original_route["nextHop"],
             "scope": "PREVIEW_ONLY"},
            inject, undo,
        )

    if kind not in ("PORT_DISABLED", "ACCESS_VLAN_CHANGED", "TRUNK_VLAN_BLOCKED"):
        raise ProjectValidationError("troubleshoot: unsupported fault type")
    required = {"type", "nodeId", "portId"}
    if kind == "ACCESS_VLAN_CHANGED":
        required.add("newVlan")
    elif kind == "TRUNK_VLAN_BLOCKED":
        required.add("blockedVlan")
    _exact_fault(fault, kind, required)
    node_id, port_id = fault["nodeId"], fault["portId"]
    device, port = _port(project, node_id, port_id)
    if not port["enabled"]:
        raise ProjectValidationError("troubleshoot: selected port is already disabled")

    def select(doc: dict) -> dict:
        return _port(doc, node_id, port_id)[1]

    if kind == "PORT_DISABLED":
        def inject(doc: dict) -> None:
            select(doc)["enabled"] = False

        def undo(doc: dict) -> None:
            select(doc)["enabled"] = True

        return (
            {"type": kind, "nodeId": node_id, "portId": port_id,
             "fromEnabled": True, "toEnabled": False},
            {"action": "RE_ENABLE_PORT", "nodeId": node_id, "portId": port_id,
             "expectedEnabled": True, "scope": "PREVIEW_ONLY"},
            inject, undo,
        )

    if device["kind"] != "switch":
        raise ProjectValidationError("troubleshoot: VLAN faults require a declared switch port")
    config = port.get("vlan")
    expected_mode = "access" if kind == "ACCESS_VLAN_CHANGED" else "trunk"
    if config is None or config["mode"] != expected_mode:
        raise ProjectValidationError(
            f"troubleshoot: selected switch port requires explicit {expected_mode} VLAN config")
    old_config = deepcopy(config)
    if kind == "ACCESS_VLAN_CHANGED":
        vlan = fault["newVlan"]
        if type(vlan) is not int or not 1 <= vlan <= 4094:
            raise ProjectValidationError("troubleshoot: newVlan must be an integer 1..4094")
        old = config["vlan"]
        if vlan == old:
            raise ProjectValidationError("troubleshoot: newVlan must differ from configured VLAN")
        new_config = {"mode": "access", "vlan": vlan}
        change = {"type": kind, "nodeId": node_id, "portId": port_id,
                  "fromVlan": old, "toVlan": vlan}
    else:
        vlan = fault["blockedVlan"]
        if type(vlan) is not int or not 1 <= vlan <= 4094:
            raise ProjectValidationError("troubleshoot: blockedVlan must be an integer 1..4094")
        allowed = config["allowedVlans"]
        if vlan not in allowed:
            raise ProjectValidationError("troubleshoot: blockedVlan must be explicitly allowed")
        if len(allowed) == 1:
            raise ProjectValidationError(
                "troubleshoot: cannot remove last allowed trunk VLAN")
        new_config = {"mode": "trunk",
                      "allowedVlans": [v for v in allowed if v != vlan]}
        change = {"type": kind, "nodeId": node_id, "portId": port_id,
                  "blockedVlan": vlan, "remainingAllowedVlans": new_config["allowedVlans"]}

    def inject(doc: dict) -> None:
        select(doc)["vlan"] = deepcopy(new_config)

    def undo(doc: dict) -> None:
        select(doc)["vlan"] = deepcopy(old_config)

    return (
        change,
        {"action": "RESTORE_VLAN_CONFIG", "nodeId": node_id, "portId": port_id,
         "expectedVlan": old_config, "scope": "PREVIEW_ONLY"},
        inject, undo,
    )


def compare_fault(project: dict, source_node: str, source_port: str,
                  destination_ipv4: str, ttl: int, identifier: int,
                  sequence: int, fault: dict) -> dict:
    """Validate, simulate a single explicit fault, independently restore.

    All three trials construct new EchoExchange instances, retaining only
    actual observed network transmissions and never any shared ARP cache.
    """
    canonical = validate_project(project)
    failure, repair, inject, undo = _mutation(canonical, fault)
    # The existing packet sender intentionally rejects a disabled source
    # interface before any traffic. Do not fabricate an Echo trial when
    # source-interface shutdown is selected as the injected fault.
    if (failure["type"] == "PORT_DISABLED" and
            failure["nodeId"] == source_node and failure["portId"] == source_port):
        raise ProjectValidationError(
            "troubleshoot: source-port shutdown cannot run an ICMP Echo trial; "
            "select a transit or destination port")

    def trial(doc: dict) -> dict:
        return EchoExchange(doc).ping(
            source_node, source_port, destination_ipv4, ttl, identifier, sequence)

    baseline = trial(canonical)
    faulty = deepcopy(canonical)
    inject(faulty)
    faulty = validate_project(faulty)
    faulted = trial(faulty)
    restored_project = deepcopy(faulty)
    undo(restored_project)
    restored_project = validate_project(restored_project)
    if restored_project != canonical:
        raise ProjectValidationError("troubleshoot: restoration changed unrelated project facts")
    restored = trial(restored_project)

    if baseline["status"] != "REPLIED":
        status = "BASELINE_NOT_REPLIED"
        explanation = ("The original ICMP Echo exchange already fails; the "
                       "injected change cannot be proven as its cause.")
    elif faulted["status"] == "REPLIED":
        status = "NO_OBSERVED_IMPACT"
        explanation = ("The same bidirectional Echo exchange still succeeds "
                       "with the selected fault; it is not a proven failure.")
    elif restored["status"] != "REPLIED":
        status = "RESTORATION_NOT_VERIFIED"
        explanation = ("Communication did not recover in the independent "
                       "restoration trial; no successful repair is claimed.")
    else:
        status = "FAULT_CONFIRMED"
        explanation = ("One explicit configuration fault caused a previously "
                       "successful Echo exchange to fail; restoring only "
                       "that configuration restored communication in the model.")
    return {
        "status": status,
        "meaning": explanation,
        "fault": failure,
        "repair": repair,
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


def compare_link_fault(project: dict, source_node: str, source_port: str,
                       destination_ipv4: str, ttl: int, identifier: int,
                       sequence: int, link_id: str) -> dict:
    """Backward-compatible link-only entrypoint using the same fault engine."""
    return compare_fault(project, source_node, source_port, destination_ipv4,
                         ttl, identifier, sequence,
                         {"type": "LINK_DISABLED", "linkId": link_id})
