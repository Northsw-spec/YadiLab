"""Bounded process-local DHCP DORA sessions using the existing DHCP engine.

Sessions are fixed to one canonical project snapshot, server port and address
pool. They share leases and MAC learning among explicitly selected clients
but never write a canonical interface, a project file or a timer-based lease.
"""
from __future__ import annotations

import secrets
from threading import RLock

from .dhcp import DhcpSession, validate_dora_pool
from .model import ProjectValidationError
from .simulation import MAX_OPERATIONS, MAX_SESSIONS, _signature


class DhcpLabSession:
    """A single immutable project/server/pool contract with volatile state."""

    def __init__(self, project: object, server_node: str, server_port: str,
                 pool_start: str, pool_end: str):
        self.dhcp = DhcpSession(project)
        # Validate all server and pool facts *before* allocating a registry ID.
        validate_dora_pool(self.dhcp.fabric, server_node, server_port,
                           pool_start, pool_end)
        self.signature = _signature(self.dhcp.fabric.project)
        self.project = self.dhcp.fabric.project
        self.server_node = server_node
        self.server_port = server_port
        self.pool_start = pool_start
        self.pool_end = pool_end
        self.operation_count = 0

    def check_project(self, project: object) -> None:
        if _signature(project) != self.signature:
            raise ProjectValidationError(
                "dhcp session: project changed since session start; start a new session")

    def state(self) -> dict:
        leases = self.dhcp.leases()
        return {
            "serverNode": self.server_node,
            "serverPort": self.server_port,
            "poolStart": self.pool_start,
            "poolEnd": self.pool_end,
            "operationCount": self.operation_count,
            "maxOperations": MAX_OPERATIONS,
            "leases": leases,
            "leaseCount": len(leases),
            "macTables": self.dhcp.fabric.learned_mac_tables(),
            "ephemeral": True,
        }

    def run(self, client_node: str, client_port: str,
            transaction_id: int, lease_seconds: int) -> dict:
        if self.operation_count >= MAX_OPERATIONS:
            raise ProjectValidationError(
                "dhcp session: operation limit reached; reset the session")
        result = self.dhcp.run(
            client_node, client_port, self.server_node, self.server_port,
            self.pool_start, self.pool_end, transaction_id, lease_seconds)
        # Even unsuccessful network deliveries are deliberate operations,
        # but malformed requests rejected before completion are not.
        self.operation_count += 1
        return {"result": result, **self.state()}

    def reset(self) -> dict:
        self.dhcp = DhcpSession(self.project)
        self.operation_count = 0
        return self.state()


class DhcpSessionRegistry:
    """Opaque, bounded session IDs; one lock serializes racing requests."""

    def __init__(self):
        self._sessions: dict[str, DhcpLabSession] = {}
        self._lock = RLock()

    def _get(self, session_id: object) -> DhcpLabSession:
        if not isinstance(session_id, str) or session_id not in self._sessions:
            raise ProjectValidationError(
                "dhcp session: unknown or expired session; start a new session")
        return self._sessions[session_id]

    def start(self, project: object, server_node: str, server_port: str,
              pool_start: str, pool_end: str) -> dict:
        session = DhcpLabSession(
            project, server_node, server_port, pool_start, pool_end)
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                raise ProjectValidationError(
                    "dhcp session: too many active sessions; stop an existing session")
            session_id = secrets.token_urlsafe(24)
            self._sessions[session_id] = session
            return {"sessionId": session_id, **session.state()}

    def run(self, session_id: object, project: object, client_node: str,
            client_port: str, transaction_id: int, lease_seconds: int) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.check_project(project)
            return {"sessionId": session_id, **session.run(
                client_node, client_port, transaction_id, lease_seconds)}

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
