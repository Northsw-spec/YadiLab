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
DIFFICULTIES = ("T1_ONLY", "T2_REBIND", "EXPIRY_RECOVERY")


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
                 *, difficulty: str = "T1_ONLY",
                 _test_choice: str | None = None):
        self.lab = DhcpLabSession(project, server_node, server_port, pool_start, pool_end)
        if type(lease_seconds) is not int or not 60 <= lease_seconds <= 604800:
            raise ProjectValidationError("investigation: leaseSeconds must be integer 60..604800")
        if type(difficulty) is not str or difficulty not in DIFFICULTIES:
            raise ProjectValidationError("investigation: unsupported difficulty")
        self.difficulty = difficulty
        self.lease_seconds = lease_seconds
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
        self._last_lease = dict(first["result"]["lease"])
        self.original_deadline = first["result"]["lease"]["expiresAtSeconds"]
        self.lab.advance(first["result"]["lease"]["t1AtSeconds"])
        self._inject(True)
        self._probes: list[dict] = []
        self._attempts = 0
        self._diagnosed = False
        self._repaired = False
        self._fault_active = True
        self._renewed_phases: set[str] = set()
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

    def _active_lease(self) -> dict | None:
        """The actual ACK-confirmed lease, not an inferred historical lease."""
        return next(
            (lease for lease in self.lab.dhcp.leases()
             if lease["clientNode"] == self.client_node
             and lease["clientPort"] == self.client_port),
            None,
        )

    def _phase(self, lease: dict | None) -> str:
        if lease is None:
            return "EXPIRED"
        clock = self.lab.clock_seconds
        return ("BOUND" if clock < lease["t1AtSeconds"]
                else "RENEWING" if clock < lease["t2AtSeconds"]
                else "REBINDING")

    def _next_clock_target(self, lease: dict | None) -> int | None:
        if lease is None or self._repaired or self.difficulty == "T1_ONLY":
            return None
        clock = self.lab.clock_seconds
        if clock < lease["t2AtSeconds"]:
            return lease["t2AtSeconds"]
        if self.difficulty == "EXPIRY_RECOVERY" and clock < lease["expiresAtSeconds"]:
            return lease["expiresAtSeconds"]
        return None

    def _can_diagnose(self, phase: str) -> bool:
        observed = {p["probe"] for p in self._probes}
        if "renew" not in observed or len(observed - {"renew"}) < 2:
            return False
        if self.difficulty == "T2_REBIND":
            return "REBINDING" in self._renewed_phases
        if self.difficulty == "EXPIRY_RECOVERY":
            return phase == "EXPIRED" and "REBINDING" in self._renewed_phases
        return True

    def public_state(self) -> dict:
        lease = self._active_lease()
        historical = lease if lease is not None else self._last_lease
        phase = self._phase(lease)
        target = self._next_clock_target(lease)
        can_advance = (
            target is not None
            and not self._diagnosed
            and not self._repaired
            and ("RENEWING" if phase == "RENEWING" else "REBINDING")
                in self._renewed_phases
        )
        return {
            "clientNode": self.client_node,
            "clientPort": self.client_port,
            "serverNode": self.lab.server_node,
            "serverPort": self.lab.server_port,
            "difficulty": self.difficulty,
            "clockSeconds": self.lab.clock_seconds,
            "leaseIpv4": self.lease_ipv4,
            "leaseActive": lease is not None,
            "expiresAtSeconds": historical["expiresAtSeconds"],
            "t1AtSeconds": historical["t1AtSeconds"],
            "t2AtSeconds": historical["t2AtSeconds"],
            "remainingSeconds": max(0, historical["expiresAtSeconds"] - self.lab.clock_seconds),
            "phase": phase,
            "requiredRecovery": ("COMPLETED" if self._repaired else
                                 "NEW_DORA" if lease is None else "RENEWAL"),
            "nextClockTargetSeconds": target,
            "canAdvance": can_advance,
            "canDiagnose": self._can_diagnose(phase),
            "renewedPhases": sorted(self._renewed_phases),
            "observations": len(self._probes),
            "probesPerformed": [p["probe"] for p in self._probes],
            "diagnosisAttempts": self._attempts,
            "diagnosed": self._diagnosed,
            "repaired": self._repaired,
            "maxProbes": MAX_PROBES,
            "ephemeral": True,
        }

    def advance(self, seconds: int) -> dict:
        """Only explicit learner-triggered virtual time, with staged evidence.

        Moving the clock NEVER issues DHCPREQUEST or extends the lease.
        Advanced scenario can expire the last bound lease exactly once.
        """
        if self._repaired or self._diagnosed:
            raise ProjectValidationError("investigation: clock is locked after diagnosis")
        if self.difficulty == "T1_ONLY":
            raise ProjectValidationError("investigation: T1-only difficulty has no clock advance")
        if type(seconds) is not int or not 1 <= seconds <= 604800:
            raise ProjectValidationError("investigation: seconds must be integer 1..604800")
        lease = self._active_lease()
        if lease is None:
            raise ProjectValidationError("investigation: lease already expired")
        target_clock = self.lab.clock_seconds + seconds
        limit = (lease["t2AtSeconds"] if self.difficulty == "T2_REBIND"
                 else lease["expiresAtSeconds"])
        if target_clock > limit:
            raise ProjectValidationError("investigation: advance exceeds this difficulty's deadline")
        if target_clock >= lease["t2AtSeconds"] and "RENEWING" not in self._renewed_phases:
            raise ProjectValidationError(
                "investigation: observe real T1 DHCPREQUEST before reaching T2")
        if target_clock >= lease["expiresAtSeconds"] and "REBINDING" not in self._renewed_phases:
            raise ProjectValidationError(
                "investigation: observe real T2 DHCPREQUEST before expiration")
        result = self.lab.advance(seconds)
        expired = [
            {"ipv4": l["ipv4"], "state": l["state"],
             "expiresAtSeconds": l["expiresAtSeconds"]}
            for l in result["expiredLeases"]
        ]
        # No privileged fabric fault/state is returned to the student.
        return {"advancedSeconds": seconds, "expiredLeases": expired, **self.public_state()}

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
                lease = self._active_lease()
                historical = lease if lease is not None else self._last_lease
                observation = {
                    "status": "BOUND" if lease is not None else "EXPIRED",
                    "ipv4": historical["ipv4"],
                    "clockSeconds": self.lab.clock_seconds,
                    "t1AtSeconds": historical["t1AtSeconds"],
                    "t2AtSeconds": historical["t2AtSeconds"],
                    "expiresAtSeconds": historical["expiresAtSeconds"],
                    "remainingSeconds": max(
                        0, historical["expiresAtSeconds"] - self.lab.clock_seconds),
                    "source": "SIMULATED",
                }
            else:
                if self._active_lease() is None:
                    raise ProjectValidationError(
                        "investigation: lease expired; DHCP renewal impossible, use new DORA")
                result = self.lab.renew(
                    self.client_node, self.client_port, self._next_transaction())
                renewal = result["result"]
                self._renewed_phases.add(renewal["phase"])
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
        if self.difficulty == "T2_REBIND" and "REBINDING" not in self._renewed_phases:
            raise ProjectValidationError(
                "investigation: T2 scenario requires a real rebinding DHCPREQUEST")
        if self.difficulty == "EXPIRY_RECOVERY" and (
                self._active_lease() is not None
                or "REBINDING" not in self._renewed_phases):
            raise ProjectValidationError(
                "investigation: advanced scenario requires observed T2 and expired lease")
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
        # Only one original scenario fault is repaired, never the actual project.
        if self._fault_active:
            self._inject(False)
            self._fault_active = False
        expired = self._active_lease() is None
        if expired:
            # RFC2131: an expired lease cannot use RENEWING/REBINDING.
            # Only a NEW real four-message DORA can allocate an address.
            proof = self.lab.run(
                self.client_node, self.client_port,
                self._next_transaction(), self.lease_seconds)["result"]
            recovered = proof["status"] == "ACK_RECEIVED" and proof["leaseCommitted"]
            method = "NEW_DORA"
            request_received = proof["request"]["receivedAtServer"]
            ack_received = proof["ack"]["receivedAtClient"]
            discover_received = proof["discover"]["receivedAtServer"]
            offer_received = proof["offer"]["receivedAtClient"]
        else:
            proof = self.lab.renew(
                self.client_node, self.client_port,
                self._next_transaction())["result"]
            recovered = proof["status"] == "ACK_RECEIVED" and proof["leaseRenewed"]
            method = "RENEWAL"
            request_received = proof["request"]["receivedAtServer"]
            ack_received = proof["ack"]["receivedAtClient"]
            discover_received = None
            offer_received = None
        self._repaired = recovered
        if recovered:
            self.lease_ipv4 = proof["lease"]["ipv4"]
            self._last_lease = dict(proof["lease"])
        return {
            **self.public_state(),
            "status": "RECOVERED" if recovered else "NOT_VERIFIED",
            "verifiedProtocol": method,
            "packetStatus": proof["status"],
            "discoverReachedServer": discover_received,
            "offerReachedClient": offer_received,
            "requestReachedServer": request_received,
            "ackReachedClient": ack_received,
            "cause": self._fault["kind"] if recovered else None,
            "repair": ({k: v for k, v in self._fault.items() if k != "kind"}
                       if recovered else None),
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
              pool_end: str, lease_seconds: int,
              difficulty: str = "T1_ONLY") -> dict:
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                raise ProjectValidationError("investigation: active session limit reached")
            session = InvestigationSession(
                project, client_node, client_port, server_node, server_port,
                pool_start, pool_end, lease_seconds, difficulty=difficulty)
            session_id = secrets.token_urlsafe(24)
            self._sessions[session_id] = session
            return {"sessionId": session_id, **session.public_state()}

    def advance(self, session_id: object, project: object, seconds: int) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.check_project(project)
            return {"sessionId": session_id, **session.advance(seconds)}

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
