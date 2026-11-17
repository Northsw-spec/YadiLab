"""Evidence-first DHCP troubleshooting exercises using the existing packet engine.

The canonical project never changes. A genuinely ACK-confirmed lease precedes
one hidden, session-local physical, port or VLAN fault. The learner must
observe network facts and submit a diagnosis before a verified repair.
No public response contains the hidden injected fault or an underlying lab ID.
"""
from __future__ import annotations

import secrets
from threading import RLock

from .dhcp_registry import DhcpLabSession
from .model import ProjectValidationError
from .simulation import MAX_SESSIONS

MAX_PROBES = 48
DIAGNOSES = ("CABLE_DOWN", "PORT_SHUTDOWN", "VLAN_MISMATCH")
PROBES = ("lease", "renew", "link", "port", "vlan")


def _fault_candidates(project: dict, fabric, client_node: str, client_port: str,
                      server_node: str, server_port: str) -> list[dict]:
    """Choose only interventions supported by the *real declared topology*."""
    def touching(node_id: str, port_id: str) -> tuple[dict, tuple[str, str]] | None:
        for link in project["links"]:
            if not link["enabled"]:
                continue
            for a, b in ((link["a"], link["b"]), (link["b"], link["a"])):
                if (a["node"], a["port"]) == (node_id, port_id):
                    if (node_id, port_id) in fabric._original_wires:
                        return link, (b["node"], b["port"])
        return None

    server_link = touching(server_node, server_port)
    client_link = touching(client_node, client_port)
    if server_link is None or client_link is None:
        raise ProjectValidationError(
            "investigation: selected client/server require documented active cables")
    candidates = [{"kind": "CABLE_DOWN", "linkId": server_link[0]["id"]}]
    server_neighbor = server_link[1]
    if fabric.nodes[server_neighbor[0]]["kind"] == "switch":
        candidates.append({
            "kind": "PORT_SHUTDOWN", "nodeId": server_neighbor[0],
            "portId": server_neighbor[1],
        })
    client_neighbor = client_link[1]
    original = fabric._original_vlan_ports.get(client_neighbor)
    if (fabric.nodes[client_neighbor[0]]["kind"] == "switch"
            and original is not None and original[0] == "access"):
        alternatives = sorted(
            vlan for vlan in fabric._documented_vlan_ids
            if vlan != original[1])
        if alternatives:
            candidates.append({
                "kind": "VLAN_MISMATCH",
                "nodeId": client_neighbor[0],
                "portId": client_neighbor[1],
                "vlanId": alternatives[0],
            })
    return candidates


class InvestigationSession:
    """One hidden fault, one immutable document, and real L2/DHCP observations."""

    def __init__(self, project: object, client_node: str, client_port: str,
                 server_node: str, server_port: str,
                 pool_start: str, pool_end: str, lease_seconds: int,
                 *, _test_choice: str | None = None):
        self.lab = DhcpLabSession(project, server_node, server_port, pool_start, pool_end)
        if type(lease_seconds) is not int or not 60 <= lease_seconds <= 604800:
            raise ProjectValidationError("investigation: leaseSeconds must be integer 60..604800")
        candidates = _fault_candidates(
            self.lab.project, self.lab.dhcp.fabric,
            client_node, client_port, server_node, server_port)
        if _test_choice is None:
            selected = candidates[secrets.randbelow(len(candidates))]
        else:
            # Internal test injection only; never exposed by the HTTP contract.
            selected = next((c for c in candidates if c["kind"] == _test_choice), None)
            if selected is None:
                raise ProjectValidationError("investigation: scenario unsupported by documented topology")
        self._fault = selected
        self.client_node, self.client_port = client_node, client_port
        first = self.lab.run(client_node, client_port, 101, lease_seconds)
        if first["result"]["status"] != "ACK_RECEIVED" or not first["result"]["leaseCommitted"]:
            raise ProjectValidationError(
                "investigation: baseline DORA did not deliver ACK; correct source network first")
        self.lease_ipv4 = first["result"]["lease"]["ipv4"]
        self.original_deadline = first["result"]["lease"]["expiresAtSeconds"]
        self.lab.advance(first["result"]["lease"]["t1AtSeconds"])
        self._inject(True)
        self._probes: list[dict] = []
        self._attempts = 0
        self._diagnosed = False
        self._repaired = False
        self._last_transaction_id = 101

    def _inject(self, enabled: bool) -> None:
        fault = self._fault
        kind = fault["kind"]
        if kind == "CABLE_DOWN":
            self.lab.set_link_fault(fault["linkId"], enabled)
        elif kind == "PORT_SHUTDOWN":
            self.lab.set_port_fault(fault["nodeId"], fault["portId"], enabled)
        else:
            self.lab.set_access_vlan_fault(
                fault["nodeId"], fault["portId"], fault["vlanId"] if enabled else None)

    def public_state(self) -> dict:
        lease = self.lab.dhcp.bound_lease(self.client_node, self.client_port)
        return {
            "clientNode": self.client_node,
            "clientPort": self.client_port,
            "serverNode": self.lab.server_node,
            "serverPort": self.lab.server_port,
            "clockSeconds": self.lab.clock_seconds,
            "leaseIpv4": self.lease_ipv4,
            "expiresAtSeconds": lease["expiresAtSeconds"],
            "remainingSeconds": lease["expiresAtSeconds"] - self.lab.clock_seconds,
            "phase": "RENEWING",
            "observations": len(self._probes),
            "probesPerformed": [p["probe"] for p in self._probes],
            "diagnosisAttempts": self._attempts,
            "diagnosed": self._diagnosed,
            "repaired": self._repaired,
            "maxProbes": MAX_PROBES,
            "ephemeral": True,
        }

    def check_project(self, project: object) -> None:
        self.lab.check_project(project)

    def probe(self, kind: str, target: object) -> dict:
        if self._repaired:
            raise ProjectValidationError("investigation: exercise already repaired")
        if type(kind) is not str or kind not in PROBES or type(target) is not dict:
            raise ProjectValidationError("investigation: unknown probe or invalid target")
        if len(self._probes) >= MAX_PROBES:
            raise ProjectValidationError("investigation: observation limit reached")
        fabric = self.lab.dhcp.fabric
        if kind in ("lease", "renew"):
            if target:
                raise ProjectValidationError("investigation: lease/renew target must be empty")
            if kind == "lease":
                lease = self.lab.dhcp.bound_lease(self.client_node, self.client_port)
                observation = {
                    "status": lease["state"],
                    "ipv4": lease["ipv4"],
                    "clockSeconds": self.lab.clock_seconds,
                    "t1AtSeconds": lease["t1AtSeconds"],
                    "t2AtSeconds": lease["t2AtSeconds"],
                    "expiresAtSeconds": lease["expiresAtSeconds"],
                    "remainingSeconds": lease["expiresAtSeconds"] - self.lab.clock_seconds,
                    "source": "SIMULATED",
                }
            else:
                result = self.lab.renew(
                    self.client_node, self.client_port, self._next_transaction())
                renewal = result["result"]
                observation = {
                    "status": renewal["status"],
                    "phase": renewal["phase"],
                    "requestReachedServer": renewal["request"]["receivedAtServer"],
                    "ackReachedClient": renewal["ack"]["receivedAtClient"],
                    "transmissions": renewal["request"]["transmissions"],
                    "vlanDrops": renewal["request"].get("vlanDrops", []),
                    "leaseRenewed": renewal["leaseRenewed"],
                    "source": "SIMULATED",
                }
        elif kind == "link":
            if set(target) != {"linkId"}:
                raise ProjectValidationError("investigation: link requires only linkId")
            observation = fabric.inspect_link(target["linkId"])
        elif kind in ("port", "vlan"):
            if set(target) != {"nodeId", "portId"}:
                raise ProjectValidationError("investigation: port/VLAN requires nodeId and portId")
            if kind == "port":
                observation = fabric.inspect_switch_port(target["nodeId"], target["portId"])
            else:
                observation = fabric.inspect_access_vlan(target["nodeId"], target["portId"])
        else:
            raise ProjectValidationError("investigation: unsupported probe")
        self._probes.append({"probe": kind, "target": dict(target), "result": observation})
        return {"probe": kind, "observation": observation, **self.public_state()}

    def _next_transaction(self) -> int:
        if self._last_transaction_id >= 0xFFFFFFFF:
            raise ProjectValidationError("investigation: transaction limit reached")
        self._last_transaction_id += 1
        return self._last_transaction_id

    def diagnose(self, diagnosis: object) -> dict:
        if self._repaired:
            raise ProjectValidationError("investigation: exercise already repaired")
        if type(diagnosis) is not str or diagnosis not in DIAGNOSES:
            raise ProjectValidationError("investigation: choose a defined diagnosis")
        observed = {p["probe"] for p in self._probes}
        if "renew" not in observed or len(observed - {"renew"}) < 2:
            raise ProjectValidationError(
                "investigation: observe real renewal and at least two other distinct checks before diagnosis")
        if self._attempts >= 3:
            raise ProjectValidationError("investigation: maximum three diagnostic attempts")
        self._attempts += 1
        correct = diagnosis == self._fault["kind"]
        if correct:
            self._diagnosed = True
        return {
            "correct": correct, "repairAvailable": self._diagnosed,
            "feedback": "Observationerna stöder diagnosen." if correct
            else "Hypotesen stämmer inte med det dolda simulerade felet. Jämför mätningarna.",
            **self.public_state(),
        }

    def repair(self) -> dict:
        if self._repaired:
            raise ProjectValidationError("investigation: exercise already repaired")
        if not self._diagnosed:
            raise ProjectValidationError("investigation: correct diagnosis required before repair")
        self._inject(False)
        result = self.lab.renew(
            self.client_node, self.client_port, self._next_transaction())["result"]
        recovered = result["status"] == "ACK_RECEIVED" and result["leaseRenewed"]
        self._repaired = recovered
        return {
            "status": "RECOVERED" if recovered else "NOT_VERIFIED",
            "requestReachedServer": result["request"]["receivedAtServer"],
            "ackReachedClient": result["ack"]["receivedAtClient"],
            "cause": self._fault["kind"] if recovered else None,
            "repair": {k: v for k, v in self._fault.items() if k != "kind"} if recovered else None,
            **self.public_state(),
        }


class InvestigationRegistry:
    def __init__(self):
        self._sessions: dict[str, InvestigationSession] = {}
        self._lock = RLock()

    def _get(self, session_id: object) -> InvestigationSession:
        if type(session_id) is not str or session_id not in self._sessions:
            raise ProjectValidationError("investigation: unknown or expired session")
        return self._sessions[session_id]

    def start(self, project: object, client_node: str, client_port: str,
              server_node: str, server_port: str, pool_start: str,
              pool_end: str, lease_seconds: int) -> dict:
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                raise ProjectValidationError("investigation: active session limit reached")
            session = InvestigationSession(
                project, client_node, client_port, server_node, server_port,
                pool_start, pool_end, lease_seconds)
            session_id = secrets.token_urlsafe(24)
            self._sessions[session_id] = session
            return {"sessionId": session_id, **session.public_state()}

    def probe(self, session_id: object, project: object,
              kind: str, target: object) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.check_project(project)
            return {"sessionId": session_id, **session.probe(kind, target)}

    def diagnose(self, session_id: object, project: object, diagnosis: object) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.check_project(project)
            return {"sessionId": session_id, **session.diagnose(diagnosis)}

    def repair(self, session_id: object, project: object) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.check_project(project)
            return {"sessionId": session_id, **session.repair()}

    def stop(self, session_id: object) -> dict:
        with self._lock:
            self._get(session_id)
            del self._sessions[session_id]
            return {"status": "STOPPED"}
