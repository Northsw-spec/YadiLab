import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError
from ipaddress import IPv4Address

from core.engine.ethernet.actors import ARP_EXPIRE, FDBEntry, Neighbor
from core.engine.ethernet.codec import ARP_TYPE, BROADCAST, ARPMessage, ARPOperation, EthernetFrame
from core.engine.ethernet.config import LinkTiming
from core.engine.ethernet.transport import (
    PARSE, PROCESS, PROPAGATED, RX_FRAME, SERIALIZED, TX_QUEUED, TX_SERVICE, TX_START, DropReason,
)
from core.engine.events import (
    MAX_TIME_NS, ErrorCode, EventRef, EventTarget, EventType, KernelError, StopReason, TargetKind, TraceAction,
)
from core.engine.kernel import EventKernel, KernelLimits, RunBudget
from core.engine.runtime import OperState
from poc1_fixture import A, A_IP, A_MAC, B, B_IP, B_MAC, C, C_MAC, REPLY, REQUEST, S1, S2, scenario

ROOT = Path(__file__).resolve().parents[2]
ARP_NEIGHBOR = Neighbor(IPv4Address(B_IP).packed, B_MAC)


def finish(sim, duration=300_000):
    result = sim.kernel.run(RunBudget(2000, duration))
    if result.reason is not StopReason.IDLE:
        raise AssertionError(result)
    return result.time_ns


def drops(sim, reason):
    return [row for row in sim.observations() if row.reason is reason]


def stages(sim, kind, target):
    return [row for row in sim.observations() if row.stage == kind and row.target.object_id == target]


def complete_arp(sim):
    sim.initialize()
    sim.resolve(A.device_id, B_IP, at_ns=0)
    return finish(sim)


class EthernetIntegrationTests(unittest.TestCase):
    def test_arp_request_reply_are_exact_and_causal_on_both_links(self):
        sim = scenario()
        project = sim.config.project
        self.assertEqual(sim.host_state(A.device_id).neighbors, ())
        sim.initialize()
        resolve = sim.resolve(A.device_id, B_IP, at_ns=0)
        partial = sim.kernel.run(RunBudget(1000, 11_819))
        self.assertEqual(partial.reason, StopReason.TIME_BUDGET)
        self.assertEqual(sim.host_state(A.device_id).neighbors, ())
        self.assertEqual(sim.switch_state(S1.device_id).fdb, (FDBEntry(10, A_MAC, "port1"),))
        self.assertEqual(finish(sim), 23_640)
        self.assertEqual(sim.host_state(A.device_id).neighbors, (ARP_NEIGHBOR,))
        self.assertEqual(sim.host_state(A.device_id).pending, ())
        self.assertEqual(sim.switch_state(S1.device_id).fdb,
                         (FDBEntry(10, A_MAC, "port1"), FDBEntry(10, B_MAC, "port2")))
        rows = sim.observations()
        self.assertEqual([(row.stage, row.target.object_id, row.at_ns) for row in rows[:16]], [
            (TX_QUEUED, A.device_id, 0), (TX_SERVICE, A.device_id, 0), (TX_START, A.device_id, 0),
            (SERIALIZED, "l1", 5760), (PROPAGATED, "l1", 5860),
            (RX_FRAME, S1.device_id, 5860), (PARSE, S1.device_id, 5860), (PROCESS, S1.device_id, 5860),
            (TX_QUEUED, S1.device_id, 5860), (TX_SERVICE, S1.device_id, 5860), (TX_START, S1.device_id, 5860),
            (SERIALIZED, "l2", 11620), (PROPAGATED, "l2", 11820),
            (RX_FRAME, B.device_id, 11820), (PARSE, B.device_id, 11820), (PROCESS, B.device_id, 11820),
        ])
        self.assertEqual([(row.stage, row.target.object_id, row.at_ns) for row in rows[16:]], [
            (TX_QUEUED, B.device_id, 11820), (TX_SERVICE, B.device_id, 11820), (TX_START, B.device_id, 11820),
            (SERIALIZED, "l2", 17580), (PROPAGATED, "l2", 17780),
            (RX_FRAME, S2.device_id, 17780), (PARSE, S2.device_id, 17780), (PROCESS, S2.device_id, 17780),
            (TX_QUEUED, S2.device_id, 17780), (TX_SERVICE, S2.device_id, 17780), (TX_START, S2.device_id, 17780),
            (SERIALIZED, "l1", 23540), (PROPAGATED, "l1", 23640),
            (RX_FRAME, A.device_id, 23640), (PARSE, A.device_id, 23640), (PROCESS, A.device_id, 23640),
        ])
        parent = resolve.event_id
        for row in rows:
            self.assertEqual(row.parent_id, parent)
            self.assertEqual(row.frame.ethertype, ARP_TYPE)
            self.assertEqual(row.frame.wire, REQUEST if row.frame.origin.endpoint() == A else REPLY)
            if row.hop:
                self.assertEqual(row.hop.vlan, 10)
            parent = row.event.event_id
        expiry, = (line for line in sim.kernel.trace if line.event.event_type == ARP_EXPIRE)
        self.assertIs(expiry.action, TraceAction.CANCELLED)
        self.assertEqual(expiry.cause_id, rows[-1].event.event_id)
        self.assertIs(sim.kernel.config, project)
        with self.assertRaises(FrozenInstanceError):
            project.links[0].a = B

    def test_unknown_unicast_floods_learned_unicast_selects_one_port(self):
        sim = scenario(third_port=True)
        sim.initialize()
        wire = EthernetFrame(B_MAC, A_MAC, 0x88B5, b"opaque").encode()
        sim.inject(A, wire, at_ns=0)
        finish(sim)
        self.assertEqual([row.target.port_id for row in stages(sim, TX_START, S1.device_id)],
                         ["port2", "port3"])
        now = sim.kernel.now_ns
        sim.resolve(A.device_id, B_IP, at_ns=now)
        finish(sim)
        self.assertEqual(sim.host_state(A.device_id).neighbors, (ARP_NEIGHBOR,))
        cutoff = sim.kernel.now_ns + 1
        sim.inject(A, wire, at_ns=cutoff)
        finish(sim)
        switched = [row for row in stages(sim, TX_START, S1.device_id) if row.at_ns >= cutoff]
        self.assertEqual([row.target.port_id for row in switched], ["port2"])
        self.assertEqual([row.frame.wire for row in stages(sim, RX_FRAME, B.device_id) if row.at_ns >= cutoff],
                         [wire])
        self.assertEqual([row for row in stages(sim, RX_FRAME, C.device_id) if row.at_ns >= cutoff], [])
        self.assertTrue(any(row.target.object_id == B.device_id for row in drops(sim, DropReason.UNSUPPORTED_PROTOCOL)))

    def test_same_vlan_known_ingress_is_filtered(self):
        sim = scenario(third_port=True)
        sim.initialize()
        sim.inject(A, EthernetFrame(A_MAC, A_MAC, 0x88B5, b"same port").encode(), at_ns=0)
        finish(sim)
        self.assertEqual(stages(sim, TX_START, S1.device_id), [])
        self.assertEqual(len(drops(sim, DropReason.NO_EGRESS_PORT)), 1)

    def test_vlan_isolation_and_same_mac_has_independent_entries(self):
        sim = scenario(vlan=20)
        complete_arp(sim)
        self.assertEqual(stages(sim, RX_FRAME, B.device_id), [])
        self.assertEqual(stages(sim, TX_QUEUED, B.device_id), [])
        self.assertEqual(sim.host_state(A.device_id).neighbors, ())
        blocked, = drops(sim, DropReason.VLAN_BLOCKED)
        self.assertEqual((blocked.hop.destination.endpoint(), blocked.vlan, blocked.frame.wire), (S1, 10, REQUEST))
        self.assertEqual(len(drops(sim, DropReason.ARP_TIMEOUT)), 1)
        sim.inject(B, EthernetFrame(BROADCAST, A_MAC, 0x88B5, b"same MAC in another VLAN").encode(),
                   at_ns=sim.kernel.now_ns)
        finish(sim)
        self.assertEqual(sim.switch_state(S1.device_id).fdb,
                         (FDBEntry(10, A_MAC, "port1"), FDBEntry(20, A_MAC, "port2")))

    def test_bad_fcs_does_not_teach_switch_malformed_arp_does_not_teach_host(self):
        sim = scenario()
        sim.initialize()
        sim.inject(A, REQUEST[:-1] + bytes([REQUEST[-1] ^ 1]), at_ns=0)
        sim.inject(A, REQUEST[:-3], at_ns=10_000)
        finish(sim)
        self.assertEqual(sim.switch_state(S1.device_id).fdb, ())
        self.assertEqual(len(drops(sim, DropReason.INVALID_FCS)), 1)
        self.assertEqual(len(drops(sim, DropReason.INVALID_FRAME)), 1)
        self.assertEqual(stages(sim, RX_FRAME, B.device_id), [])
        payload = bytearray(REQUEST[14:42])
        payload[4] = 5
        frame = EthernetFrame(BROADCAST, A_MAC, ARP_TYPE, bytes(payload)).encode()
        sim.inject(A, frame, at_ns=20_000)
        finish(sim)
        self.assertEqual(len(drops(sim, DropReason.INVALID_ARP)), 1)
        self.assertEqual(stages(sim, TX_QUEUED, B.device_id), [])
        self.assertEqual(sim.host_state(B.device_id).neighbors, ())

    def test_inconsistent_sender_and_unexpected_replies_are_rejected(self):
        sim = scenario()
        sim.initialize()
        mismatched = EthernetFrame(A_MAC, C_MAC, ARP_TYPE, REPLY[14:42]).encode()
        sim.inject(B, mismatched, at_ns=0)
        sim.inject(B, REPLY, at_ns=15_000)
        finish(sim)
        self.assertEqual(sim.host_state(A.device_id).neighbors, ())
        self.assertEqual(len(drops(sim, DropReason.INVALID_ARP)), 1)
        self.assertEqual(len(drops(sim, DropReason.UNEXPECTED_ARP)), 1)

    def test_reply_for_outstanding_ip_still_needs_correct_target_mac(self):
        sim = scenario(vlan=20)
        sim.initialize()
        sim.resolve(A.device_id, B_IP, at_ns=0)
        # Inject at the switch's VLAN-10 egress so that this reply can reach A
        # while the genuine VLAN-10 request remains outstanding.
        reply = ARPMessage(ARPOperation.REPLY, B_MAC, IPv4Address(B_IP).packed,
                           C_MAC, IPv4Address(A_IP).packed)
        sim.inject(S1, EthernetFrame(A_MAC, B_MAC, ARP_TYPE, reply.encode()).encode(), at_ns=15_000)
        finish(sim)
        self.assertEqual(sim.host_state(A.device_id).neighbors, ())
        self.assertEqual(len(drops(sim, DropReason.UNEXPECTED_ARP)), 1)

    def test_rate_length_spacing_and_propagation_are_independent(self):
        sim = scenario(rate=200_000_000, l1_delay=360)
        sim.initialize()
        short = EthernetFrame(BROADCAST, A_MAC, 0x88B5, b"short").encode()
        long = EthernetFrame(BROADCAST, A_MAC, 0x88B5, bytes(182)).encode()
        self.assertEqual(len(long), 200)
        sim.inject(A, short, at_ns=0)
        sim.inject(A, long, at_ns=0)
        finish(sim)
        # 72 and 208 wire octets incl. preamble/SFD. First slot is 84 octets.
        self.assertEqual([row.at_ns for row in stages(sim, TX_START, A.device_id)], [0, 3360])
        self.assertEqual([row.at_ns for row in stages(sim, SERIALIZED, "l1")], [2880, 11680])
        self.assertEqual([row.at_ns for row in stages(sim, PROPAGATED, "l1")], [3240, 12040])
        self.assertEqual([row.at_ns for row in stages(sim, TX_START, S1.device_id)], [3240, 12040])

    def test_full_duplex_egresses_can_serialize_at_the_same_time(self):
        sim = scenario()
        sim.initialize()
        wire = EthernetFrame(BROADCAST, A_MAC, 0x88B5, b"one direction").encode()
        reverse = EthernetFrame(A_MAC, B_MAC, 0x88B5, b"the other direction").encode()
        sim.inject(A, wire, at_ns=0)
        sim.inject(S1, reverse, at_ns=0)
        finish(sim)
        serializations = stages(sim, SERIALIZED, "l1")
        self.assertEqual([(row.at_ns, row.hop.source.endpoint(), row.frame.wire) for row in serializations],
                         [(5760, A, wire), (5760, S1, reverse)])

    def test_reserved_non_broadcast_multicast_is_outside_the_forwarding_subset(self):
        sim = scenario()
        sim.initialize()
        wire = EthernetFrame(bytes.fromhex("0180c2000000"), A_MAC, 0x88B5, b"control").encode()
        sim.inject(A, wire, at_ns=0)
        finish(sim)
        self.assertEqual(stages(sim, RX_FRAME, B.device_id), [])
        self.assertEqual(sim.switch_state(S1.device_id).fdb, ())
        self.assertEqual(len(drops(sim, DropReason.UNSUPPORTED_PROTOCOL)), 1)

    def test_timing_integer_rounding_and_horizon_drop(self):
        model = LinkTiming("l1", 3_000_000_000, 0)
        self.assertEqual(model.serialization_ns(65), 195)
        self.assertEqual(model.slot_ns(65), 227)
        sim = scenario(l1_delay=MAX_TIME_NS)
        sim.initialize()
        sim.inject(A, REQUEST, at_ns=0)
        finish(sim)
        self.assertEqual(len(drops(sim, DropReason.TIME_LIMIT)), 1)
        self.assertEqual(stages(sim, RX_FRAME, S1.device_id), [])

    def test_bounded_queue_reports_loss_and_preserves_first_frame(self):
        sim = scenario(queue_limit=1)
        sim.initialize()
        sim.inject(A, REQUEST, at_ns=0)
        sim.inject(A, REQUEST, at_ns=0)
        finish(sim)
        lost, = drops(sim, DropReason.QUEUE_FULL)
        delivered, = (row for row in stages(sim, RX_FRAME, S1.device_id) if row.frame.wire == REQUEST)
        self.assertNotEqual(lost.frame.frame_id, delivered.frame.frame_id)
        self.assertEqual(delivered.frame.wire, REQUEST)
        self.assertEqual(sim.switch_state(S1.device_id).fdb,
                         (FDBEntry(10, A_MAC, "port1"), FDBEntry(10, B_MAC, "port2")))

    def test_port_down_before_queued_tx_start_and_later_recovers(self):
        sim = scenario()
        sim.initialize()
        sim.inject(A, REQUEST, at_ns=0)
        sim.inject(A, REQUEST, at_ns=20)
        sim.set_port(A, False, at_ns=6200)
        sim.set_port(A, True, at_ns=6800)
        sim.inject(A, REQUEST, at_ns=7000)
        finish(sim)
        frame_hops = [row for row in stages(sim, RX_FRAME, S1.device_id) if row.frame.origin.endpoint() == A]
        self.assertEqual([row.at_ns for row in frame_hops], [5860, 12860])
        [queued_drop] = [row for row in drops(sim, DropReason.PORT_DOWN) if row.hop.source.endpoint() == A]
        self.assertEqual(queued_drop.at_ns, 6720)
        self.assertEqual([row.at_ns for row in stages(sim, TX_START, A.device_id)], [0, 7000])

    def test_queued_frame_is_stale_after_link_reopens_before_its_slot(self):
        sim = scenario()
        sim.initialize()
        wire = EthernetFrame(BROADCAST, A_MAC, 0x88B5, b"opaque").encode()
        sim.inject(A, wire, at_ns=0)
        sim.inject(A, wire, at_ns=20)
        sim.set_link("l1", False, at_ns=6200)
        sim.set_link("l1", True, at_ns=6300)
        sim.inject(A, wire, at_ns=7000)
        finish(sim)
        self.assertEqual([row.at_ns for row in stages(sim, RX_FRAME, S1.device_id)], [5860, 12860])
        stale, = drops(sim, DropReason.LINK_DOWN)
        self.assertEqual(stale.at_ns, 6720)

    def test_port_down_during_serialization_even_after_reopening(self):
        sim = scenario()
        sim.initialize()
        sim.inject(A, REQUEST, at_ns=0)
        sim.set_port(A, False, at_ns=2000)
        sim.set_port(A, True, at_ns=2100)
        finish(sim)
        failure, = drops(sim, DropReason.PORT_DOWN)
        self.assertEqual(failure.at_ns, 5760)
        self.assertEqual(stages(sim, RX_FRAME, S1.device_id), [])

    def test_link_outage_during_propagation_drops_old_frame_new_resolution_succeeds(self):
        sim = scenario()
        sim.initialize()
        sim.resolve(A.device_id, B_IP, at_ns=0)
        sim.set_link("l2", False, at_ns=11700)
        sim.set_link("l2", True, at_ns=11750)
        finish(sim)
        aborted, = drops(sim, DropReason.LINK_DOWN)
        self.assertEqual((aborted.at_ns, aborted.hop.link_id), (11820, "l2"))
        self.assertEqual(stages(sim, RX_FRAME, B.device_id), [])
        self.assertEqual(sim.host_state(A.device_id).neighbors, ())
        sim.resolve(A.device_id, B_IP, at_ns=100_001)
        self.assertEqual(finish(sim), 123_641)
        self.assertEqual(sim.host_state(A.device_id).neighbors, (ARP_NEIGHBOR,))

    def test_device_power_off_before_arrival_and_stale_frames_cleared_by_reset(self):
        sim = scenario()
        sim.initialize()
        sim.resolve(A.device_id, B_IP, at_ns=0)
        sim.set_device_power(B.device_id, False, at_ns=11_700)
        finish(sim)
        power_drop, = drops(sim, DropReason.DEVICE_OFF)
        self.assertEqual(power_drop.at_ns, 11_820)
        self.assertEqual(stages(sim, RX_FRAME, B.device_id), [])
        sim.kernel.reset(sim.kernel.scenario)
        sim.initialize()
        old = sim.resolve(A.device_id, B_IP, at_ns=0)
        self.assertIs(sim.kernel.run(RunBudget(1000, 6000)).reason, StopReason.TIME_BUDGET)
        new = sim.kernel.reset(sim.kernel.scenario)
        self.assertEqual(sim.kernel.trace, ())
        self.assertEqual(sim.host_state(A.device_id).pending, ())
        with self.assertRaises(KernelError) as exc:
            sim.kernel.cancel(old)
        self.assertIs(exc.exception.code, ErrorCode.STALE_SCENARIO)
        self.assertGreater(new.generation, old.scenario.generation)
        self.assertEqual(complete_arp(sim), 23_640)

    def test_learned_fdb_cannot_deliver_across_failed_link(self):
        sim = scenario(third_port=True)
        complete_arp(sim)
        cutoff = sim.kernel.now_ns + 100
        sim.set_link("l2", False, at_ns=cutoff)
        sim.inject(A, EthernetFrame(B_MAC, A_MAC, 0x88B5, b"known unicast").encode(), at_ns=cutoff)
        finish(sim)
        self.assertIn(FDBEntry(10, B_MAC, "port2"), sim.switch_state(S1.device_id).fdb)
        self.assertEqual([row for row in stages(sim, RX_FRAME, B.device_id) if row.at_ns >= cutoff], [])
        self.assertEqual([row for row in stages(sim, RX_FRAME, C.device_id) if row.at_ns >= cutoff], [])
        refused, = drops(sim, DropReason.LINK_DOWN)
        self.assertEqual(refused.hop.source.endpoint(), S2)

    def test_arp_pending_and_fdb_capacity_bound_protocol_state(self):
        sim = scenario(vlan=20, pending_limit=1, fdb_limit=1)
        sim.initialize()
        sim.resolve(A.device_id, B_IP, at_ns=0)
        sim.resolve(A.device_id, "192.168.10.21", at_ns=1)
        finish(sim)
        self.assertEqual(len(drops(sim, DropReason.STATE_LIMIT)), 1)
        self.assertEqual(len(drops(sim, DropReason.ARP_TIMEOUT)), 1)
        sim.inject(B, EthernetFrame(BROADCAST, B_MAC, 0x88B5, b"new MAC").encode(), at_ns=100_001)
        finish(sim)
        self.assertEqual(sim.switch_state(S1.device_id).fdb, (FDBEntry(20, B_MAC, "port2"),))


class TransactionTests(unittest.TestCase):
    def test_network_operational_and_timer_effects_roll_back_together(self):
        config = scenario().config.project
        target = EventTarget(TargetKind.PORT, A.device_id, A.port_id)
        timer = EventType("fixture/timer")
        fail = EventType("fixture/fail")
        setup = EventType("fixture/setup")

        def ignore(event, ctx):
            pass

        def setup_timer(event, ctx):
            ctx.set_oper_state(OperState.UP)
            ctx.replace_state((ctx.schedule_after(timer, target, 10), b"before"))

        def fail_after_changes(event, ctx):
            ctx.set_oper_state(OperState.DOWN)
            ctx.cancel_timer(ctx.state[0])
            ctx.replace_state((b"new queue", b"uncommitted frame"))
            ctx.schedule_after(timer, target, 1)
            raise RuntimeError("injected actor failure")

        kernel = EventKernel(config, "atomic", revision_id=config.revision_id, seed=0,
                             limits=KernelLimits(8, 8, 16, 1024),
                             actors={target: {setup: setup_timer, timer: ignore, fail: fail_after_changes}})
        kernel.schedule(kernel.scenario, setup, target, time_ns=0)
        kernel.schedule(kernel.scenario, fail, target, time_ns=1)
        result = kernel.run(RunBudget(8, 20))
        self.assertEqual((result.reason, result.error), (StopReason.FAULTED, ErrorCode.HANDLER_FAILED))
        snapshot = kernel.snapshot()
        self.assertEqual(snapshot.actor_states, ((target, (3, b"before")),))
        self.assertIs(next(port for port in snapshot.ports if port.endpoint == A).oper_state, OperState.UP)
        with self.assertRaises(KernelError) as err:
            kernel.cancel(EventRef(kernel.scenario, 4))
        self.assertIs(err.exception.code, ErrorCode.UNKNOWN_EVENT)
        kernel.cancel(EventRef(kernel.scenario, 3))
        self.assertIs(kernel.trace[-1].action, TraceAction.CANCELLED)
        self.assertEqual(kernel.trace[-1].event.time_ns, 10)

    def test_value_budget_counts_empty_items_and_rejects_mutable_values(self):
        target = EventTarget(TargetKind.DEVICE, A.device_id)
        config = scenario().config.project
        action = EventType("fixture/model")
        kernel = EventKernel(config, "values", revision_id=config.revision_id, seed=5,
                             limits=KernelLimits(4, 4, 10, 8), actors={target: {action: lambda e, c: None}})
        for payload in ((b"",) * 9, ([],), {"mutable": True}):
            with self.subTest(payload=payload), self.assertRaises(KernelError) as err:
                kernel.schedule(kernel.scenario, action, target, time_ns=0, payload=payload)
            self.assertIs(err.exception.code, ErrorCode.INVALID_PAYLOAD)


class ReplayTests(unittest.TestCase):
    def test_two_processes_and_three_generations_reproduce_observed_network(self):
        script = "import runpy; runpy.run_path('tests/engine/poc1_fixture.py', run_name='__main__')"
        runs = []
        for hash_seed in ("1", "173"):
            result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                                    env={**os.environ, "PYTHONHASHSEED": hash_seed},
                                    text=True, capture_output=True, check=True, timeout=15)
            runs.append(json.loads(result.stdout))
        self.assertEqual(runs[0], runs[1])
        self.assertEqual([item["generation"] for item in runs[0]], [0, 1, 2])
        ids = [item["resolve_id"] for item in runs[0]]
        self.assertEqual(ids, sorted(set(ids)))
        traces = [item["trace"] for item in runs[0]]
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])
        self.assertEqual(len({item["state_sha256"] for item in runs[0]}), 1)
        for item in runs[0]:
            self.assertEqual((item["result"], item["end_ns"]), ("idle", 23_640))
            self.assertEqual(item["neighbors"], [["c0a80a14", "02000000000b"]])
            self.assertEqual(item["fdb"], [[10, "02000000000a", "port1"], [10, "02000000000b", "port2"]])
