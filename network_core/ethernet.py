"""Deterministic, MAC-only Ethernet forwarding over the canonical project graph.

This is a deliberately narrow Layer-2 model. A caller supplies source and
unicast/broadcast destination MACs, or a validated Ethernet II frame with an
explicit source interface MAC binding from project v1.1 or this session.
Only switches learn and forward, over explicitly enabled links and ports.
Endpoint arrival means a frame reached a port, NOT that a host accepted it.
No IP, ARP, VLAN, STP, aging, FCS, or host NIC acceptance is implemented.
Ethernet II serialization lives in ethernet_frame.py and is payload-opaque.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping

from .model import ProjectValidationError, validate_project
from .ethernet_frame import BROADCAST, EthernetFrame, normalize_mac


class EthernetFabric:
    """One isolated, explicitly configured simulation session.

    Learned MAC tables live only in this object, never in the project.
    Create a new session after changes to ports, links or topology. Networks
    with active switch-to-switch loops are rejected rather than pretending STP.
    """

    def __init__(self, project: dict, *, interface_macs: Mapping[tuple[str, str], str] | None = None):
        self.project = validate_project(project)
        self.nodes = {node["id"]: node for node in self.project["nodes"]}
        self.ports = {
            node["id"]: {port["id"]: port for port in node["ports"]}
            for node in self.project["nodes"]
        }
        # Bidirectional map: each enabled physical endpoint has at most one link
        # (already guaranteed by the canonical project validator).
        self.wires: dict[tuple[str, str], tuple[str, str, str]] = {}
        for link in self.project["links"]:
            a, b = link["a"], link["b"]
            if not link["enabled"] or not self.ports[a["node"]][a["port"]]["enabled"] \
                    or not self.ports[b["node"]][b["port"]]["enabled"]:
                continue
            self.wires[(a["node"], a["port"])] = (b["node"], b["port"], link["id"])
            self.wires[(b["node"], b["port"])] = (a["node"], a["port"], link["id"])
        self._reject_switch_loops()
        # Explicit NIC identities from validated v1.1 ports or session bindings.
        # Neither session nor switch learning ever mutates the saved project.
        persisted = {
            (node["id"], port["id"]): port["mac"]
            for node in self.project["nodes"] if node["kind"] != "switch"
            for port in node["ports"] if port.get("mac") is not None
        }
        if interface_macs is None:
            interface_macs = {}
        if not isinstance(interface_macs, Mapping):
            raise ProjectValidationError("ethernet: interface_macs must be a mapping")
        bindings = dict(persisted)
        for endpoint, address in interface_macs.items():
            if endpoint in persisted and normalize_mac(address, source=True) != persisted[endpoint]:
                raise ProjectValidationError("ethernet: session MAC conflicts with persisted interface MAC")
            bindings[endpoint] = address
        self._interface_macs: dict[tuple[str, str], str] = {}
        seen_macs: set[str] = set()
        for endpoint, address in bindings.items():
            if not isinstance(endpoint, tuple) or len(endpoint) != 2 or \
                    not all(isinstance(part, str) for part in endpoint):
                raise ProjectValidationError("ethernet: MAC binding requires (node ID, port ID)")
            node_id, port_id = endpoint
            if node_id not in self.nodes or port_id not in self.ports[node_id]:
                raise ProjectValidationError("ethernet: MAC binding has undeclared endpoint")
            if self.nodes[node_id]["kind"] == "switch":
                raise ProjectValidationError("ethernet: switch interfaces cannot have host NIC bindings")
            mac = normalize_mac(address, source=True)
            if mac in seen_macs:
                raise ProjectValidationError("ethernet: duplicate interface MAC binding")
            seen_macs.add(mac)
            self._interface_macs[endpoint] = mac
        self._tables: dict[str, dict[str, str]] = {
            node_id: {} for node_id, node in self.nodes.items()
            if node["kind"] == "switch"
        }

    def _reject_switch_loops(self) -> None:
        adjacent: dict[str, list[tuple[str, str]]] = {
            node_id: [] for node_id, node in self.nodes.items()
            if node["kind"] == "switch"
        }
        for link in self.project["links"]:
            a, b = link["a"], link["b"]
            if (a["node"], a["port"]) not in self.wires:
                continue
            if a["node"] in adjacent and b["node"] in adjacent:
                adjacent[a["node"]].append((b["node"], link["id"]))
                adjacent[b["node"]].append((a["node"], link["id"]))

        visited: set[str] = set()
        for root in adjacent:
            if root in visited:
                continue
            visited.add(root)
            queue = deque([(root, None)])
            while queue:
                node, incoming_link = queue.popleft()
                for neighbor, link_id in adjacent[node]:
                    if link_id == incoming_link:
                        continue
                    if neighbor in visited:
                        raise ProjectValidationError(
                            "ethernet: switch loop unsupported (no STP implemented)"
                        )
                    visited.add(neighbor)
                    queue.append((neighbor, link_id))

    def mac_table(self, switch_id: str) -> dict[str, str]:
        """Return a copy of learned entries, never a reference to internal state."""
        if switch_id not in self._tables:
            raise ProjectValidationError("ethernet: undeclared switch ID")
        return dict(sorted(self._tables[switch_id].items()))

    def bound_macs(self) -> dict[tuple[str, str], str]:
        """Return a detached snapshot of explicit session NIC identity bindings."""
        return dict(self._interface_macs)

    def inject_frame(self, node_id: str, port_id: str, frame: EthernetFrame) -> dict:
        """Forward a validated Ethernet II frame from an explicitly bound NIC.

        The result reports wire transmissions and switch state, not whether
        an endpoint accepted or decoded the payload. No ARP or IP simulation.
        """
        if not isinstance(frame, EthernetFrame):
            raise ProjectValidationError("ethernet: inject_frame requires EthernetFrame")
        if not isinstance(node_id, str) or not isinstance(port_id, str):
            raise ProjectValidationError("ethernet: undeclared source node/port")
        assigned = self._interface_macs.get((node_id, port_id))
        if assigned is None:
            raise ProjectValidationError("ethernet: source port has no explicit MAC binding")
        if frame.source != assigned:
            raise ProjectValidationError("ethernet: source MAC does not match configured interface")
        result = self.inject(node_id, port_id, frame.source, frame.destination)
        return {
            **result,
            "frame": {"source": frame.source, "destination": frame.destination,
                      "etherType": frame.ether_type,
                      "lengthWithoutFcs": len(frame.serialize())},
        }

    def inject(self, node_id: str, port_id: str, source_mac: str,
               destination_mac: str) -> dict:
        """Inject one abstract frame from an explicitly declared non-switch port.

        This traces wire transmissions, switch decisions and port arrivals only.
        It does not simulate endpoint MAC filtering, reply generation or IP.
        """
        source = normalize_mac(source_mac, source=True)
        destination = normalize_mac(destination_mac, source=False)
        if not isinstance(node_id, str) or not isinstance(port_id, str) \
                or node_id not in self.nodes or port_id not in self.ports[node_id]:
            raise ProjectValidationError("ethernet: undeclared source node/port")
        if self.nodes[node_id]["kind"] == "switch":
            raise ProjectValidationError(
                "ethernet: external frame must originate at a non-switch endpoint"
            )
        if (node_id, port_id) not in self.wires:
            return {
                "status": "NO_ACTIVE_LINK", "transmissions": [],
                "endpointArrivals": [], "switchDecisions": [],
                "meaning": "No enabled physical link at source; nothing was transmitted."
            }

        transmissions: list[dict] = []
        arrivals: list[dict] = []
        decisions: list[dict] = []
        queue: deque[tuple[str, str]] = deque()

        def transmit(nid: str, pid: str) -> None:
            neighbor, peer_port, link_id = self.wires[(nid, pid)]
            transmissions.append({
                "linkId": link_id,
                "from": {"node": nid, "port": pid},
                "to": {"node": neighbor, "port": peer_port},
            })
            queue.append((neighbor, peer_port))

        transmit(node_id, port_id)
        while queue:
            nid, ingress = queue.popleft()
            if self.nodes[nid]["kind"] != "switch":
                arrivals.append({"node": nid, "port": ingress})
                continue

            # Learning is driven by a frame that has actually arrived at an
            # active switch port, not by static IP, naming or graph proximity.
            table = self._tables[nid]
            table[source] = ingress
            candidates = [
                port["id"] for port in self.nodes[nid]["ports"]
                if port["id"] != ingress and (nid, port["id"]) in self.wires
            ]
            learned = table.get(destination)
            if destination == BROADCAST or learned is None:
                action, outgoing = "FLOOD", candidates
            elif learned == ingress:
                action, outgoing = "FILTER_SAME_PORT", []
            else:
                # A learned port must be active for the lifetime of this session.
                if learned not in candidates:
                    raise ProjectValidationError("ethernet: inconsistent MAC state; start a new session")
                action, outgoing = "FORWARD_UNICAST", [learned]
            decisions.append({
                "switch": nid, "ingressPort": ingress,
                "action": action, "egressPorts": list(outgoing),
            })
            for pid in outgoing:
                transmit(nid, pid)

        return {
            "status": "SIMULATED", "transmissions": transmissions,
            "endpointArrivals": arrivals, "switchDecisions": decisions,
            "meaning": "MAC-only forwarding. Endpoint arrival does not prove NIC acceptance, ping, ARP, VLAN or IP connectivity."
        }
