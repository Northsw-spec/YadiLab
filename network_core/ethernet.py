"""Deterministic, MAC-only Ethernet forwarding over the canonical project graph.

This is a deliberately narrow Layer-2 model. A caller supplies source and
unicast/broadcast destination MACs, or a validated Ethernet II frame with an
explicit source interface MAC binding from project v1.1 or this session.
Only switches learn and forward, over explicitly enabled links and ports.
Endpoint arrival means a frame reached a port, NOT that a host accepted it.
No IP, STP, MAC aging, FCS or host NIC acceptance is implemented.
Explicit session-only access/trunk VLAN forwarding is supported when configured.
Ethernet II serialization lives in ethernet_frame.py and is payload-opaque.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping

from .model import ProjectValidationError, validate_project
from .ethernet_frame import BROADCAST, EthernetFrame, normalize_mac, validate_vlan_id


class EthernetFabric:
    """One isolated, explicitly configured simulation session.

    Learned MAC tables live only in this object, never in the project.
    Create a new session after changes to ports, links or topology. Networks
    with active switch-to-switch loops are rejected rather than pretending STP.
    """

    def __init__(self, project: dict, *,
                 interface_macs: Mapping[tuple[str, str], str] | None = None,
                 vlan_ports: Mapping[tuple[str, str], dict] | None = None):
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
        # An explicit VLAN session has no implicit access VLAN 1 or native VLAN.
        # All active wired switch ports must have a declared access/trunk mode.
        # This configuration is NEVER persisted to the project by the engine.
        self._vlan_enabled = vlan_ports is not None
        self._vlan_ports: dict[tuple[str, str], tuple[str, int | frozenset[int]]] = {}
        if vlan_ports is not None:
            if not isinstance(vlan_ports, Mapping):
                raise ProjectValidationError("vlan: vlan_ports must be a mapping")
            for endpoint, config in vlan_ports.items():
                if (not isinstance(endpoint, tuple) or len(endpoint) != 2
                        or not all(isinstance(value, str) for value in endpoint)):
                    raise ProjectValidationError("vlan: port key must be (switch ID, port ID)")
                node_id, port_id = endpoint
                if (node_id not in self.nodes or port_id not in self.ports[node_id]
                        or self.nodes[node_id]["kind"] != "switch"):
                    raise ProjectValidationError("vlan: configuration requires declared switch port")
                if not isinstance(config, dict):
                    raise ProjectValidationError("vlan: port configuration must be an object")
                mode = config.get("mode")
                if mode == "access" and set(config) == {"mode", "vlan"}:
                    self._vlan_ports[endpoint] = ("access", validate_vlan_id(config["vlan"]))
                elif mode == "trunk" and set(config) == {"mode", "allowedVlans"}:
                    allowed = config["allowedVlans"]
                    if (not isinstance(allowed, list) or not 1 <= len(allowed) <= 4094):
                        raise ProjectValidationError("vlan: trunk needs a nonempty allowedVlans list")
                    values = [validate_vlan_id(item) for item in allowed]
                    if len(set(values)) != len(values):
                        raise ProjectValidationError("vlan: duplicate allowed VLAN")
                    self._vlan_ports[endpoint] = ("trunk", frozenset(values))
                else:
                    raise ProjectValidationError("vlan: expected access/vlan or trunk/allowedVlans")
            for endpoint in self.wires:
                if self.nodes[endpoint[0]]["kind"] == "switch" and endpoint not in self._vlan_ports:
                    raise ProjectValidationError("vlan: missing configuration for active switch port")
            for link in self.project["links"]:
                a, b = link["a"], link["b"]
                left, right = (a["node"], a["port"]), (b["node"], b["port"])
                if left not in self.wires:
                    continue
                la, lb = self._vlan_ports.get(left), self._vlan_ports.get(right)
                if la and lb:
                    if la[0] != lb[0] or (la[0] == "access" and la[1] != lb[1]):
                        raise ProjectValidationError("vlan: switch link has incompatible access/trunk configuration")
                elif la or lb:
                    if (la or lb)[0] != "access":
                        raise ProjectValidationError("vlan: endpoint links require untagged access ports")
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

    def mac_table(self, switch_id: str, vlan_id: int | None = None) -> dict[str, str]:
        """Read an isolated VLAN MAC table (or legacy unsegmented table)."""
        if not isinstance(switch_id, str) or switch_id not in self._tables:
            raise ProjectValidationError("ethernet: undeclared switch ID")
        if self._vlan_enabled:
            validate_vlan_id(vlan_id)
            return dict(sorted((mac, port) for (vlan, mac), port in self._tables[switch_id].items()
                               if vlan == vlan_id))
        if vlan_id is not None:
            raise ProjectValidationError("vlan: no VLAN session configured")
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
        if frame.vlan_id is not None:
            raise ProjectValidationError("vlan: endpoint frame injection must be untagged")
        result = self.inject(node_id, port_id, frame.source, frame.destination)
        return {
            **result,
            "frame": {"source": frame.source, "destination": frame.destination,
                      "etherType": frame.ether_type,
                      "lengthWithoutFcs": len(frame.serialize())},
        }

    def inject(self, node_id: str, port_id: str, source_mac: str,
               destination_mac: str) -> dict:
        """Forward one abstract frame along real enabled wires.

        In VLAN sessions each switch learns (VLAN, MAC) -> ingress; 802.1Q tags
        appear on trunk wires only. This traces forwarding, not NIC acceptance,
        IPv4 packets, ARP generation or actual bytes on each link.
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
        vlan_drops: list[dict] = []
        queue: deque[tuple[str, str, int | None]] = deque()

        def transmit(nid: str, pid: str, vlan: int | None = None) -> None:
            neighbor, peer_port, link_id = self.wires[(nid, pid)]
            tagged = (self._vlan_enabled and self.nodes[nid]["kind"] == "switch"
                      and self._vlan_ports[(nid, pid)][0] == "trunk")
            on_wire = vlan if tagged else None
            trace = {
                "linkId": link_id,
                "from": {"node": nid, "port": pid},
                "to": {"node": neighbor, "port": peer_port},
            }
            if self._vlan_enabled:
                trace["vlanId"] = vlan
                trace["tagged"] = tagged
            transmissions.append(trace)
            queue.append((neighbor, peer_port, on_wire))

        transmit(node_id, port_id)
        while queue:
            nid, ingress, wire_vlan = queue.popleft()
            if self.nodes[nid]["kind"] != "switch":
                if wire_vlan is not None:
                    raise ProjectValidationError("vlan: unexpected tagged frame at endpoint")
                arrivals.append({"node": nid, "port": ingress})
                continue

            current_vlan: int | None = None
            if self._vlan_enabled:
                mode, member = self._vlan_ports[(nid, ingress)]
                if mode == "access":
                    if wire_vlan is not None:
                        vlan_drops.append({"switch": nid, "port": ingress,
                                           "reason": "TAGGED_ON_ACCESS", "vlanId": wire_vlan})
                        continue
                    current_vlan = member
                else:
                    if wire_vlan is None or wire_vlan not in member:
                        vlan_drops.append({"switch": nid, "port": ingress,
                                           "reason": "TRUNK_NOT_ALLOWED", "vlanId": wire_vlan})
                        continue
                    current_vlan = wire_vlan

            table = self._tables[nid]
            source_key = (current_vlan, source) if self._vlan_enabled else source
            destination_key = (current_vlan, destination) if self._vlan_enabled else destination
            # Only an actually received, VLAN-admitted frame can teach a switch.
            table[source_key] = ingress
            candidates = [
                port["id"] for port in self.nodes[nid]["ports"]
                if port["id"] != ingress and (nid, port["id"]) in self.wires
            ]
            if self._vlan_enabled:
                candidates = [
                    pid for pid in candidates
                    if (self._vlan_ports[(nid, pid)][1] == current_vlan
                        if self._vlan_ports[(nid, pid)][0] == "access"
                        else current_vlan in self._vlan_ports[(nid, pid)][1])
                ]
            learned = table.get(destination_key)
            if destination == BROADCAST or learned is None:
                action, outgoing = "FLOOD", candidates
            elif learned == ingress:
                action, outgoing = "FILTER_SAME_PORT", []
            else:
                if learned not in candidates:
                    raise ProjectValidationError("ethernet: inconsistent MAC state; start a new session")
                action, outgoing = "FORWARD_UNICAST", [learned]
            decision = {"switch": nid, "ingressPort": ingress,
                        "action": action, "egressPorts": list(outgoing)}
            if self._vlan_enabled:
                decision["vlanId"] = current_vlan
            decisions.append(decision)
            for pid in outgoing:
                transmit(nid, pid, current_vlan)

        result = {
            "status": "SIMULATED", "transmissions": transmissions,
            "endpointArrivals": arrivals, "switchDecisions": decisions,
            "meaning": ("VLAN-aware simulated MAC forwarding over explicit links; no IP reachability or NIC acceptance."
                        if self._vlan_enabled else
                        "MAC-only forwarding. Endpoint arrival does not prove NIC acceptance, ping, ARP, VLAN or IP connectivity.")
        }
        if self._vlan_enabled:
            result["vlanDrops"] = vlan_drops
        return result
