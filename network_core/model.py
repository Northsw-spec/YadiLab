"""Canonical, intentionally narrow source model for the application.

Every network object must be declared. There is no inference from IP, position,
name, kind or geographic zone. No packet reachability is claimed by topology_trace.
"""
from __future__ import annotations

import ipaddress
import math
import re
from collections import deque
from typing import Any

SCHEMA_VERSION = "1.3"
EVIDENCE_SCHEMA_VERSION = "1.4"
LEGACY_SCHEMA_VERSION = "1.0"
MAC_SCHEMA_VERSION = "1.1"
VLAN_SCHEMA_VERSION = "1.2"
MAC_RE = re.compile(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$")
NODE_KINDS = frozenset({"host", "switch", "router", "firewall"})
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")


class ProjectValidationError(ValueError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _fail(location: str, problem: str) -> None:
    raise ProjectValidationError(f"{location}: {problem}")


def _object(value: Any, where: str, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        _fail(where, "expected an object")
    absent = required - value.keys()
    if absent:
        _fail(where, f"missing fields: {', '.join(sorted(absent))}")
    extras = value.keys() - required - optional
    if extras:
        _fail(where, f"unsupported fields (not silently discarded): {', '.join(sorted(extras))}")
    return value


def _array(value: Any, where: str, max_items: int = 2000) -> list:
    if not isinstance(value, list):
        _fail(where, "expected an array")
    if len(value) > max_items:
        _fail(where, f"too many items (maximum {max_items})")
    return value


def _name(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        _fail(where, "expected a nonempty string of at most 120 characters")
    return value.strip()


def _id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        _fail(where, "invalid identifier (start with a letter; use letters, digits, . _ : -; max 64)")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        _fail(where, "expected true or false")
    return value


def _number(value: Any, where: str) -> float | int:
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 100000:
        _fail(where, "expected a finite coordinate between -100000 and 100000")
    return value


def _vlan_config(value: Any, where: str) -> dict:
    """Strict access/trunk contract: no implicit VLAN or ignored fields."""
    obj = _object(value, where, {"mode"}, {"vlan", "allowedVlans"})
    mode = obj["mode"]
    if mode == "access":
        _object(obj, where, {"mode", "vlan"})
        vlan = obj["vlan"]
        if type(vlan) is not int or not 1 <= vlan <= 4094:
            _fail(where + ".vlan", "VLAN ID must be an integer 1..4094")
        return {"mode": "access", "vlan": vlan}
    if mode == "trunk":
        _object(obj, where, {"mode", "allowedVlans"})
        allowed = obj["allowedVlans"]
        if not isinstance(allowed, list) or not 1 <= len(allowed) <= 4094:
            _fail(where + ".allowedVlans", "expected 1..4094 explicit VLAN IDs")
        seen: set[int] = set()
        result = []
        for index, item in enumerate(allowed):
            if type(item) is not int or not 1 <= item <= 4094:
                _fail(f"{where}.allowedVlans[{index}]", "VLAN ID must be an integer 1..4094")
            if item in seen:
                _fail(where + ".allowedVlans", "duplicate VLAN ID")
            seen.add(item)
            result.append(item)
        return {"mode": "trunk", "allowedVlans": result}
    _fail(where + ".mode", "expected access or trunk")


def _usable_ipv4_host(address: ipaddress.IPv4Address,
                      network: ipaddress.IPv4Network) -> bool:
    """/31 has two endpoint addresses; /32 is one host, not a subnet pair."""
    return network.prefixlen >= 31 or address not in (
        network.network_address, network.broadcast_address)


def _static_route(value: Any, where: str, ports: dict[str, dict]) -> dict:
    """Validate explicit on-link next-hop against its declared output port.

    A disabled interface can retain documentation; route installation is
    handled separately in the read-only routing table.
    """
    obj = _object(value, where, {"id", "destination", "nextHop", "outPort"})
    rid = _id(obj["id"], where + ".id")
    destination = obj["destination"]
    if not isinstance(destination, str):
        _fail(where + ".destination", "expected a canonical IPv4 network/prefix")
    try:
        prefix = ipaddress.ip_network(destination, strict=True)
    except ValueError:
        _fail(where + ".destination", "expected a canonical IPv4 network/prefix (no host bits)")
    if not isinstance(prefix, ipaddress.IPv4Network) or destination != str(prefix):
        _fail(where + ".destination", "expected a canonical IPv4 network/prefix")
    out_port = _id(obj["outPort"], where + ".outPort")
    if out_port not in ports:
        _fail(where + ".outPort", "undeclared output interface")
    port = ports[out_port]
    if port["ipv4"] is None:
        _fail(where + ".outPort", "output interface needs explicit IPv4/CIDR")
    next_hop = obj["nextHop"]
    if not isinstance(next_hop, str):
        _fail(where + ".nextHop", "expected an explicit unicast IPv4 address")
    try:
        gateway = ipaddress.IPv4Address(next_hop)
    except ipaddress.AddressValueError:
        _fail(where + ".nextHop", "expected an explicit unicast IPv4 address")
    if (next_hop != str(gateway) or gateway.is_multicast or gateway.is_unspecified
            or gateway.is_reserved):
        _fail(where + ".nextHop", "next-hop must be a canonical unicast IPv4 address")
    iface = ipaddress.IPv4Interface(port["ipv4"])
    if gateway not in iface.network:
        _fail(where + ".nextHop", "next-hop is not on the configured output interface's subnet")
    if gateway == iface.ip:
        _fail(where + ".nextHop", "next-hop cannot equal output interface's own IPv4")
    if not _usable_ipv4_host(gateway, iface.network):
        _fail(where + ".nextHop", "next-hop cannot be a subnet network or broadcast address")
    return {"id": rid, "destination": str(prefix),
            "nextHop": str(gateway), "outPort": out_port}


def blank_project(name: str = "Nytt nätverkslabb") -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "name": name, "zones": [], "nodes": [], "links": []}


def validate_project(value: Any) -> dict:
    """Reject incompatible/lossy documents; normalize only explicitly declared data."""
    if not isinstance(value, dict):
        _fail("project", "expected an object")
    is_evidence = value.get("schemaVersion") == EVIDENCE_SCHEMA_VERSION
    required = {"schemaVersion", "name", "zones", "nodes", "links"}
    p = _object(value, "project", required | ({"importEvidence"} if is_evidence else set()))
    version = p["schemaVersion"]
    if type(version) is not str or version not in (
            LEGACY_SCHEMA_VERSION, MAC_SCHEMA_VERSION, VLAN_SCHEMA_VERSION,
            SCHEMA_VERSION, EVIDENCE_SCHEMA_VERSION):
        _fail("project.schemaVersion", "only '1.0', '1.1', '1.2', '1.3' and '1.4' are supported")
    project = blank_project(_name(p["name"], "project.name"))
    # Never silently upgrade or rewrite a legacy document during validation.
    project["schemaVersion"] = version

    zone_ids: set[str] = set()
    for i, original in enumerate(_array(p["zones"], "project.zones", 1000)):
        loc = f"project.zones[{i}]"
        z = _object(original, loc, {"id", "label"})
        zid = _id(z["id"], loc + ".id")
        if zid in zone_ids:
            _fail(loc, f"duplicate zone ID {zid!r}")
        zone_ids.add(zid)
        project["zones"].append({"id": zid, "label": _name(z["label"], loc + ".label")})

    nodes_by_id: dict[str, dict] = {}
    port_ids_by_node: dict[str, set[str]] = {}
    configured_macs: set[str] = set()
    for i, original in enumerate(_array(p["nodes"], "project.nodes")):
        loc = f"project.nodes[{i}]"
        n = _object(original, loc, {"id", "label", "kind", "x", "y", "zoneId", "ports"},
                    {"staticRoutes"} if version in (SCHEMA_VERSION, EVIDENCE_SCHEMA_VERSION) else frozenset())
        nid = _id(n["id"], loc + ".id")
        if nid in nodes_by_id:
            _fail(loc, f"duplicate node ID {nid!r}")
        kind = n["kind"]
        if not isinstance(kind, str) or kind not in NODE_KINDS:
            _fail(loc + ".kind", f"expected one of {', '.join(sorted(NODE_KINDS))}")
        zone_id = n["zoneId"]
        if zone_id is not None and (not isinstance(zone_id, str) or zone_id not in zone_ids):
            _fail(loc + ".zoneId", f"unknown zone ID {zone_id!r}")
        node = {"id": nid, "label": _name(n["label"], loc + ".label"), "kind": kind,
                "x": _number(n["x"], loc + ".x"), "y": _number(n["y"], loc + ".y"),
                "zoneId": zone_id, "ports": []}
        seen_ports: set[str] = set()
        for pi, po in enumerate(_array(n["ports"], loc + ".ports", 128)):
            ploc = f"{loc}.ports[{pi}]"
            optional = {"mac"} if version in (MAC_SCHEMA_VERSION, VLAN_SCHEMA_VERSION,
                                               SCHEMA_VERSION, EVIDENCE_SCHEMA_VERSION) else set()
            if version in (VLAN_SCHEMA_VERSION, SCHEMA_VERSION, EVIDENCE_SCHEMA_VERSION):
                optional.add("vlan")
            port = _object(po, ploc, {"id", "name", "enabled", "ipv4"}, optional)
            pid = _id(port["id"], ploc + ".id")
            if pid in seen_ports:
                _fail(ploc, f"duplicate port ID {pid!r} on {nid!r}")
            seen_ports.add(pid)
            ipv4 = port["ipv4"]
            if ipv4 is not None:
                if not isinstance(ipv4, str) or "/" not in ipv4:
                    _fail(ploc + ".ipv4", "expected an explicit IPv4 address/prefix or null")
                try:
                    addr = ipaddress.ip_interface(ipv4)
                except ValueError:
                    _fail(ploc + ".ipv4", "invalid IPv4 interface/prefix")
                if not isinstance(addr, ipaddress.IPv4Interface):
                    _fail(ploc + ".ipv4", "IPv6 is not modeled in v1")
                if not _usable_ipv4_host(addr.ip, addr.network):
                    _fail(ploc + ".ipv4", "interface IPv4 cannot be the subnet network or broadcast address")
                ipv4 = str(addr)
            parsed_port = {"id": pid, "name": _name(port["name"], ploc + ".name"),
                           "enabled": _bool(port["enabled"], ploc + ".enabled"),
                           "ipv4": ipv4}
            if "mac" in port:
                mac = port["mac"]
                if mac is not None:
                    if kind == "switch":
                        _fail(ploc + ".mac", "switch ports cannot have endpoint MAC bindings")
                    if not isinstance(mac, str) or not MAC_RE.fullmatch(mac):
                        _fail(ploc + ".mac", "expected six colon-separated hex octets or null")
                    mac = mac.upper()
                    if (int(mac[:2], 16) & 1) or mac == "00:00:00:00:00:00":
                        _fail(ploc + ".mac", "endpoint MAC must be nonzero unicast")
                    if mac in configured_macs:
                        _fail(ploc + ".mac", "duplicate endpoint MAC binding")
                    configured_macs.add(mac)
                parsed_port["mac"] = mac
            if "vlan" in port:
                if kind != "switch":
                    _fail(ploc + ".vlan", "VLAN port configuration requires a switch")
                vlan = port["vlan"]
                parsed_port["vlan"] = None if vlan is None else _vlan_config(vlan, ploc + ".vlan")
            node["ports"].append(parsed_port)
        if "staticRoutes" in n:
            if kind == "switch":
                _fail(loc + ".staticRoutes", "a layer-2 switch cannot own static IPv4 routes")
            port_by_id = {port["id"]: port for port in node["ports"]}
            route_ids: set[str] = set()
            route_facts: set[tuple[str, str, str]] = set()
            node["staticRoutes"] = []
            for ri, raw in enumerate(_array(n["staticRoutes"], loc + ".staticRoutes", 128)):
                rloc = f"{loc}.staticRoutes[{ri}]"
                route = _static_route(raw, rloc, port_by_id)
                if route["id"] in route_ids:
                    _fail(rloc + ".id", "duplicate static route ID")
                route_ids.add(route["id"])
                facts = (route["destination"], route["nextHop"], route["outPort"])
                if facts in route_facts:
                    _fail(rloc, "duplicate identical static route")
                route_facts.add(facts)
                node["staticRoutes"].append(route)
        nodes_by_id[nid] = node
        port_ids_by_node[nid] = seen_ports
        project["nodes"].append(node)

    link_ids: set[str] = set()
    occupied: set[tuple[str, str]] = set()
    for i, original in enumerate(_array(p["links"], "project.links", 5000)):
        loc = f"project.links[{i}]"
        link = _object(original, loc, {"id", "a", "b", "enabled"})
        lid = _id(link["id"], loc + ".id")
        if lid in link_ids:
            _fail(loc, f"duplicate link ID {lid!r}")
        link_ids.add(lid)
        ends = []
        for side in ("a", "b"):
            end = _object(link[side], loc + "." + side, {"node", "port"})
            nid = _id(end["node"], loc + "." + side + ".node")
            pid = _id(end["port"], loc + "." + side + ".port")
            if nid not in nodes_by_id or pid not in port_ids_by_node[nid]:
                _fail(loc + "." + side, f"undeclared endpoint {nid}/{pid}")
            if (nid, pid) in occupied:
                _fail(loc + "." + side, f"port already connected: {nid}/{pid}")
            ends.append({"node": nid, "port": pid})
        if ends[0]["node"] == ends[1]["node"]:
            _fail(loc, "connections within one device are not supported in this version")
        occupied.update((e["node"], e["port"]) for e in ends)
        project["links"].append({"id": lid, "a": ends[0], "b": ends[1],
                                 "enabled": _bool(link["enabled"], loc + ".enabled")})
    if is_evidence:
        from .import_evidence import validate_evidence
        try:
            project["importEvidence"] = validate_evidence(p["importEvidence"])
        except ProjectValidationError:
            raise
        except (TypeError, ValueError, KeyError, AttributeError) as error:
            raise ProjectValidationError("importEvidence: malformed historical receipt") from error
    return project


def canonical_network_view(value: Any) -> dict:
    """Deep, separately validated 1.3 transport/baseline projection."""
    from copy import deepcopy
    project = validate_project(value)
    if project["schemaVersion"] not in (SCHEMA_VERSION, EVIDENCE_SCHEMA_VERSION):
        _fail("project.schemaVersion", "network projection requires schema 1.3 or 1.4")
    projection = {key: deepcopy(project[key]) for key in
                  ("schemaVersion", "name", "zones", "nodes", "links")}
    projection["schemaVersion"] = SCHEMA_VERSION
    for node in projection["nodes"]:
        for axis in ("x", "y"):
            number = node[axis]
            if type(number) is float and number.is_integer():
                node[axis] = int(number)
    return validate_project(projection)


def topology_trace(value: Any, start: str, target: str) -> dict:
    """Graph path ONLY. No Layer-2 or Layer-3 packet reachability inference.

    Traversal across a device means connected *documentation graph*, not
    switching, routing, electrical continuity, firewall reachability or ping.
    """
    project = validate_project(value)
    nodes = {n["id"]: n for n in project["nodes"]}
    if start not in nodes or target not in nodes:
        raise ProjectValidationError("trace: source and destination must be declared node IDs")
    if start == target:
        return {"status": "SAME_NODE", "hops": [], "meaning": "Same documented node; packet reachability was not evaluated."}
    enabled_ports = {(n["id"], p["id"]) for n in project["nodes"] for p in n["ports"] if p["enabled"]}
    graph: dict[str, list[tuple[str, dict]]] = {key: [] for key in nodes}
    for link in project["links"]:
        a, b = link["a"], link["b"]
        if not link["enabled"] or (a["node"], a["port"]) not in enabled_ports or (b["node"], b["port"]) not in enabled_ports:
            continue
        graph[a["node"]].append((b["node"], {"linkId": link["id"], "fromNode": a["node"], "fromPort": a["port"], "toNode": b["node"], "toPort": b["port"]}))
        graph[b["node"]].append((a["node"], {"linkId": link["id"], "fromNode": b["node"], "fromPort": b["port"], "toNode": a["node"], "toPort": a["port"]}))
    visited = {start}
    queue = deque([(start, [])])
    while queue:
        current, hops = queue.popleft()
        for neighbor, hop in graph[current]:
            if neighbor in visited:
                continue
            extended = hops + [hop]
            if neighbor == target:
                return {"status": "PATH_PRESENT", "hops": extended,
                        "meaning": "A documented graph path exists over enabled links and ports. IP connectivity and routing were NOT simulated."}
            visited.add(neighbor)
            queue.append((neighbor, extended))
    return {"status": "NO_PATH", "hops": [],
            "meaning": "No documented graph path exists over currently enabled links and ports. This does not diagnose actual IP connectivity."}
