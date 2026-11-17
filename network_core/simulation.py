"""Bounded, process-local Layer-2 simulation sessions over one canonical project.

Each session owns exactly one ArpSession and its existing EthernetFabric.
No source project writes, shared protocol cache, IP reachability or background work.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from threading import RLock

from .arp import ArpSession
from .ethernet_frame import EthernetFrame
from .model import ProjectValidationError, validate_project

MAX_SESSIONS = 16
MAX_OPERATIONS = 256


def _signature(project: object) -> str:
    canonical = validate_project(project)
    data = json.dumps(canonical, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class SimulationSession:
    """Live in-memory ARP/MAC learning on a fixed explicit project snapshot."""

    def __init__(self, project: dict):
        self.arp = ArpSession(project)
        self.project = self.arp.fabric.project
        self.signature = _signature(self.project)
        self.operation_count = 0

    def check_project(self, project: object) -> None:
        if _signature(project) != self.signature:
            raise ProjectValidationError(
                "simulation: project changed since session start; start a new session"
            )

    def reset(self) -> dict:
        self.arp = ArpSession(self.project)
        self.operation_count = 0
        return self.state()

    def state(self) -> dict:
        return {
            "operationCount": self.operation_count,
            "macTables": self.arp.fabric.learned_mac_tables(),
            "ephemeral": True,
        }

    def run(self, operation: str, source_node: str, source_port: str,
            target: str) -> dict:
        if self.operation_count >= MAX_OPERATIONS:
            raise ProjectValidationError(
                "simulation: operation limit reached; reset the session"
            )
        if operation == "arp":
            result = self.arp.resolve(source_node, source_port, target)
        elif operation == "ethernet":
            endpoint = (source_node, source_port)
            bound = self.arp.fabric.bound_macs()
            if endpoint not in bound:
                raise ProjectValidationError(
                    "simulation: Ethernet source requires explicit endpoint MAC binding"
                )
            # Only an opaque Ethernet II frame is modeled: it is NOT IP/ARP/ping.
            frame = EthernetFrame(target, bound[endpoint], 0x88B5, b"")
            result = self.arp.fabric.inject_frame(source_node, source_port, frame)
        else:
            raise ProjectValidationError(
                "simulation: operation must be arp or ethernet"
            )
        self.operation_count += 1
        return {
            "operation": operation,
            "result": result,
            "arpTable": self.arp.arp_table(source_node, source_port),
            **self.state(),
        }


class SimulationRegistry:
    """One bounded server-process registry; operations serialized by its lock."""

    def __init__(self):
        self._sessions: dict[str, SimulationSession] = {}
        self._lock = RLock()

    def _get(self, session_id: object) -> SimulationSession:
        if not isinstance(session_id, str) or session_id not in self._sessions:
            raise ProjectValidationError(
                "simulation: unknown or expired session; start a new session"
            )
        return self._sessions[session_id]

    def start(self, project: object) -> dict:
        # Validate completely before allocating a session or consuming capacity.
        session = SimulationSession(project)
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                raise ProjectValidationError(
                    "simulation: too many active sessions; stop an existing session"
                )
            session_id = secrets.token_urlsafe(24)
            self._sessions[session_id] = session
            return {"sessionId": session_id, **session.state()}

    def run(self, session_id: object, project: object, operation: str,
            source_node: str, source_port: str, target: str) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.check_project(project)
            return {"sessionId": session_id,
                    **session.run(operation, source_node, source_port, target)}

    def reset(self, session_id: object, project: object) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.check_project(project)
            return {"sessionId": session_id, **session.reset()}

    def stop(self, session_id: object) -> dict:
        with self._lock:
            self._get(session_id)
            del self._sessions[session_id]
            return {"status": "STOPPED"}
