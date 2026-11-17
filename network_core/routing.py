"""Read-only IPv4 connected-route tables and longest-prefix lookup.

A route is derived ONLY from an explicitly configured, administratively enabled
IPv4/CIDR interface on the selected canonical node. No links, MACs, ARP or device
position are used to infer routes. A matching route is NOT packet reachability.
"""
from __future__ import annotations

import ipaddress
from typing import Any

from .model import ProjectValidationError, validate_project


class ConnectedRoutingTable:
    """Per-device connected IPv4 RIB: no static routes, gateway or forwarding."""

    def __init__(self, project: dict, node_id: str):
        canonical = validate_project(project)
        if not isinstance(node_id, str):
            raise ProjectValidationError("routing: nodeId must be a declared node ID")
        node = next((n for n in canonical["nodes"] if n["id"] == node_id), None)
        if node is None:
            raise ProjectValidationError("routing: undeclared source node")
        if node["kind"] == "switch":
            raise ProjectValidationError(
                "routing: layer-2 switch has no modeled IPv4 routing table"
            )
        self.node_id = node_id
        self._entries: list[tuple[ipaddress.IPv4Network, dict]] = []
        for port in node["ports"]:
            if not port["enabled"] or port["ipv4"] is None:
                continue
            configured = ipaddress.IPv4Interface(port["ipv4"])
            network = configured.network
            record = {
                "destination": str(network),
                "type": "CONNECTED",
                "outInterface": {"node": node_id, "port": port["id"]},
                "sourceIpv4": str(configured.ip),
                "nextHop": None,
            }
            self._entries.append((network, record))
        self._entries.sort(key=lambda item: (
            -item[0].prefixlen, int(item[0].network_address),
            item[1]["outInterface"]["port"],
        ))

    def routes(self) -> list[dict]:
        """Return detached records; never expose or mutate a project document."""
        return [
            {**record, "outInterface": dict(record["outInterface"])}
            for _, record in self._entries
        ]

    def lookup(self, destination_ipv4: Any) -> dict:
        if not isinstance(destination_ipv4, str) or "/" in destination_ipv4:
            raise ProjectValidationError(
                "routing: destinationIpv4 must be one IPv4 address (not CIDR)"
            )
        try:
            dest = ipaddress.IPv4Address(destination_ipv4)
        except ipaddress.AddressValueError:
            raise ProjectValidationError(
                "routing: destinationIpv4 must be a valid IPv4 address"
            ) from None
        matches = [(net, row) for net, row in self._entries if dest in net]
        candidates: list[dict] = []
        if matches:
            longest = matches[0][0].prefixlen
            candidates = [
                {**row, "outInterface": dict(row["outInterface"])}
                for network, row in matches if network.prefixlen == longest
            ]
        status = "NO_ROUTE" if not candidates else (
            "MATCH" if len(candidates) == 1 else "AMBIGUOUS"
        )
        return {
            "status": status,
            "sourceNode": self.node_id,
            "destinationIpv4": str(dest),
            "routes": self.routes(),
            "selectedRoute": candidates[0] if status == "MATCH" else None,
            "candidates": candidates,
            "meaning": {
                "MATCH": "Most specific configured connected prefix selected. No packet, ARP, Ethernet or IP reachability simulated.",
                "NO_ROUTE": "No configured enabled IPv4 interface has a connected prefix matching this destination.",
                "AMBIGUOUS": "Multiple equally specific connected routes match; no interface or metric is assumed.",
            }[status],
        }
