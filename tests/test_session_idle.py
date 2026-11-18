"""Deterministic real-time expiry, locking and server lifecycle for all registries."""
from __future__ import annotations

import hashlib
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from network_core.dhcp_investigation import InvestigationRegistry
from network_core.dhcp_registry import DhcpSessionRegistry
from network_core.icmp_investigation import IcmpInvestigationRegistry
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.session_idle import IDLE_TIMEOUT_SECONDS
from network_core.simulation import MAX_SESSIONS, SimulationRegistry
from network_core.storage import ProjectStore
from test_dhcp_port_vlan_fault import vlan_clients
from test_dhcp_registry import clients
from test_icmp_echo import routed_reply_lab
from test_vlan_persistence import persisted_topology


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def cases(clock):
    return (
        (SimulationRegistry(clock=clock), persisted_topology(),
         lambda r, p: r.start(p)),
        (DhcpSessionRegistry(clock=clock), clients(),
         lambda r, p: r.start(p, 'server', 'eth0', '192.0.2.70', '192.0.2.71')),
        (InvestigationRegistry(clock=clock), vlan_clients(),
         lambda r, p: r.start(p, 'client', 'eth0', 'server', 'eth0',
                              '192.0.2.70', '192.0.2.71', 60)),
        (IcmpInvestigationRegistry(clock=clock), routed_reply_lab(),
         lambda r, p: r.start(p, 'a', 'eth0', '203.0.113.20', 5)),
    )


class IdleRegistryTests(unittest.TestCase):
    def test_all_four_expire_and_old_ids_never_return(self):
        clock = Clock()
        for registry, project, start in cases(clock):
            with self.subTest(registry=type(registry).__name__):
                old = start(registry, project)['sessionId']
                clock.advance(IDLE_TIMEOUT_SECONDS)
                self.assertEqual(registry.cleanup_expired(), 1)
                self.assertEqual(len(registry._sessions), 0)
                with self.assertRaisesRegex(ProjectValidationError, 'unknown or expired'):
                    registry.stop(old)
                with self.assertRaisesRegex(ProjectValidationError, 'unknown or expired'):
                    if isinstance(registry, (SimulationRegistry, DhcpSessionRegistry)):
                        registry.reset(old, project)
                    elif isinstance(registry, InvestigationRegistry):
                        registry.probe(old, project, 'lease', {})
                    else:
                        registry.probe(old, project, 'address', {})
                new = start(registry, project)['sessionId']
                self.assertNotEqual(new, old)
                with self.assertRaisesRegex(ProjectValidationError, 'unknown or expired'):
                    registry.stop(old)
                self.assertEqual(registry.cleanup_expired(), 0)
                self.assertIn(new, registry._sessions)
                clock.advance(1)

    def test_successful_activity_renews_only_its_id(self):
        clock = Clock()
        registry = SimulationRegistry(clock=clock)
        project = persisted_topology()
        first = registry.start(project)['sessionId']
        other = registry.start(project)['sessionId']
        clock.advance(IDLE_TIMEOUT_SECONDS - 1)
        registry.reset(first, project)
        with self.assertRaises(ProjectValidationError):
            registry.reset('not-a-session', project)
        clock.advance(1)
        self.assertEqual(registry.cleanup_expired(), 1)
        self.assertIn(first, registry._sessions)
        self.assertNotIn(other, registry._sessions)
        clock.advance(IDLE_TIMEOUT_SECONDS - 1)
        self.assertEqual(registry.cleanup_expired(), 1)

    def test_invalid_project_does_not_renew_and_virtual_clock_is_independent(self):
        clock = Clock()
        registry = DhcpSessionRegistry(clock=clock)
        project = clients()
        sid = registry.start(project, 'server', 'eth0',
                             '192.0.2.70', '192.0.2.71')['sessionId']
        registry.advance(sid, project, 3600)
        self.assertEqual(registry._sessions[sid].clock_seconds, 3600)
        self.assertEqual(clock.now, registry._last_activity[sid])
        clock.advance(IDLE_TIMEOUT_SECONDS - 1)
        with self.assertRaises(ProjectValidationError):
            registry.reset(sid, clients(4))
        clock.advance(1)
        self.assertEqual(registry.cleanup_expired(), 1)
        with self.assertRaisesRegex(ProjectValidationError, 'unknown or expired'):
            registry.reset(sid, project)

    def test_expired_capacity_is_reclaimed_atomically_on_start(self):
        clock = Clock()
        registry = SimulationRegistry(clock=clock)
        project = persisted_topology()
        ids = {registry.start(project)['sessionId'] for _ in range(MAX_SESSIONS)}
        self.assertEqual(len(ids), MAX_SESSIONS)
        with self.assertRaisesRegex(ProjectValidationError, 'too many active'):
            registry.start(project)
        clock.advance(IDLE_TIMEOUT_SECONDS)
        new = registry.start(project)['sessionId']
        self.assertEqual(len(registry._sessions), 1)
        self.assertNotIn(new, ids)

    def test_concurrent_cleanup_and_starts_share_capacity_lock(self):
        clock = Clock()
        registry = SimulationRegistry(clock=clock)
        project = persisted_topology()
        for _ in range(MAX_SESSIONS):
            registry.start(project)
        clock.advance(IDLE_TIMEOUT_SECONDS)
        gate = threading.Barrier(3)

        def start():
            gate.wait(timeout=2)
            return registry.start(project)['sessionId']

        def cleanup():
            gate.wait(timeout=2)
            return registry.cleanup_expired()

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(start), pool.submit(start), pool.submit(cleanup)]
            first, second, _ = (future.result(timeout=3) for future in futures)
        self.assertNotEqual(first, second)
        self.assertEqual(set(registry._sessions), {first, second})

    def test_cleanup_waits_for_real_operation_and_refresh(self):
        clock = Clock()
        registry = SimulationRegistry(clock=clock)
        project = persisted_topology()
        sid = registry.start(project)['sessionId']
        entered, finish = threading.Event(), threading.Event()
        session = registry._sessions[sid]
        original = session.reset

        def held():
            entered.set()
            self.assertTrue(finish.wait(2))
            return original()

        session.reset = held
        attempted = threading.Event()

        def cleanup_after_attempt():
            attempted.set()
            return registry.cleanup_expired()

        with ThreadPoolExecutor(max_workers=2) as pool:
            operation = pool.submit(registry.reset, sid, project)
            self.assertTrue(entered.wait(2))
            clock.advance(IDLE_TIMEOUT_SECONDS)
            cleanup = pool.submit(cleanup_after_attempt)
            self.assertTrue(attempted.wait(2))
            self.assertFalse(cleanup.done())
            finish.set()
            self.assertEqual(operation.result(timeout=2)['sessionId'], sid)
            self.assertEqual(cleanup.result(timeout=2), 0)
        self.assertIn(sid, registry._sessions)

    def test_cleanup_and_stop_are_atomic(self):
        clock = Clock()
        registry = SimulationRegistry(clock=clock)
        project = persisted_topology()
        sid = registry.start(project)['sessionId']
        clock.advance(IDLE_TIMEOUT_SECONDS)
        with ThreadPoolExecutor(max_workers=2) as pool:
            cleanup = pool.submit(registry.cleanup_expired)
            stop = pool.submit(registry.stop, sid)
            count = cleanup.result(timeout=2)
            try:
                stopped = stop.result(timeout=2)
            except ProjectValidationError:
                stopped = None
        self.assertIn((count, stopped), ((1, None), (0, {'status': 'STOPPED'})))
        self.assertFalse(registry._sessions)

    def test_server_worker_reaps_without_requests_and_stops_on_close(self):
        clock = Clock()
        with tempfile.TemporaryDirectory() as temp:
            server = LabHTTPServer(('127.0.0.1', 0), ProjectStore(temp),
                                   clock=clock, cleanup_interval=.01)
            try:
                cleaned = threading.Event()
                original = server.icmp_investigations.cleanup_expired

                def observed():
                    count = original()
                    if all(not registry._sessions for registry in
                           (server.simulations, server.dhcp_sessions,
                            server.investigations, server.icmp_investigations)):
                        cleaned.set()
                    return count

                server.icmp_investigations.cleanup_expired = observed
                ids = (
                    server.simulations.start(persisted_topology())['sessionId'],
                    server.dhcp_sessions.start(clients(), 'server', 'eth0',
                                               '192.0.2.70', '192.0.2.71')['sessionId'],
                    server.investigations.start(vlan_clients(), 'client', 'eth0',
                                                'server', 'eth0', '192.0.2.70',
                                                '192.0.2.71', 60)['sessionId'],
                    server.icmp_investigations.start(routed_reply_lab(), 'a', 'eth0',
                                                     '203.0.113.20', 5)['sessionId'],
                )
                cleaned.clear()
                clock.advance(IDLE_TIMEOUT_SECONDS)
                self.assertTrue(cleaned.wait(2), 'scheduler did not reap without HTTP')
                for registry, sid in zip((server.simulations, server.dhcp_sessions,
                                          server.investigations, server.icmp_investigations), ids):
                    self.assertNotIn(sid, registry._sessions)
            finally:
                server.server_close()
            self.assertFalse(server._cleanup_thread.is_alive())

    def test_two_servers_are_isolated_and_files_unchanged(self):
        clock_a, clock_b = Clock(), Clock()
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = LabHTTPServer(('127.0.0.1', 0), ProjectStore(first), clock=clock_a)
            b = LabHTTPServer(('127.0.0.1', 0), ProjectStore(second), clock=clock_b)
            try:
                project = persisted_topology()
                a.store.save('saved', project)
                path = Path(first) / 'saved.yadilab'
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                sid_a = a.simulations.start(project)['sessionId']
                sid_b = b.simulations.start(project)['sessionId']
                clock_a.advance(IDLE_TIMEOUT_SECONDS)
                self.assertEqual(a.simulations.cleanup_expired(), 1)
                self.assertNotIn(sid_a, a.simulations._sessions)
                self.assertIn(sid_b, b.simulations._sessions)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            finally:
                a.server_close()
                b.server_close()
            self.assertFalse(a._cleanup_thread.is_alive())
            self.assertFalse(b._cleanup_thread.is_alive())
