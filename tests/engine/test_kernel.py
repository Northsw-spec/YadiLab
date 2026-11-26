import json
import os
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path

from core.engine.config import ConfigError, ConfigSnapshot, Endpoint, PowerState
from core.engine.events import (
    MAX_TIME_NS, ErrorCode, EventTarget, EventType, KernelError, StopReason, TargetKind, TraceAction,
)
from core.engine.kernel import EventKernel, KernelLimits, RunBudget
from test_contracts import topology

DEVICE = EventTarget(TargetKind.DEVICE, "a")
PORT = EventTarget(TargetKind.PORT, "a", "eth0")
LINK = EventTarget(TargetKind.LINK, "link-1")
SCENARIO = EventTarget(TargetKind.SCENARIO, "simulation")
TICK = EventType("actor/tick")
LIMITS = KernelLimits(12, 8, 64, 64)
ROOT = Path(__file__).resolve().parents[2]


def append_payload(event, context):
    context.replace_state(context.state + event.payload)


def new_kernel(handler=append_payload, *, scenario_id="simulation", limits=LIMITS, actors=None):
    config = topology()
    return EventKernel(
        config, scenario_id, revision_id=config.revision_id, seed=7, limits=limits,
        actors={DEVICE: {TICK: handler}} if actors is None else actors,
    )


class KernelTests(unittest.TestCase):
    def assert_error(self, code, function, *args, **kwargs):
        with self.assertRaises(KernelError) as raised:
            function(*args, **kwargs)
        self.assertIs(raised.exception.code, code)

    def test_order_is_chronological_then_fifo_at_equal_times(self):
        kernel = new_kernel()
        for deadline, payload in ((12, b"d"), (3, b"a"), (7, b"b"), (7, b"c")):
            kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=deadline, payload=payload)
        result = kernel.run(RunBudget(8, 12))
        self.assertEqual((result.reason, result.processed, result.time_ns), (StopReason.IDLE, 4, 12))
        self.assertEqual(
            [(entry.at_ns, entry.event.ref.event_id) for entry in kernel.trace],
            [(3, 2), (7, 3), (7, 4), (12, 1)],
        )
        self.assertEqual(kernel.snapshot().actor_states, ((DEVICE, b"abcd"),))

    def test_actor_can_read_topology_and_send_causal_event_to_another_owner(self):
        def dispatch(event, context):
            self.assertEqual(context.config.revision_id, "rev-1")
            self.assertIs(context.device("a").power, PowerState.ON)
            self.assertEqual(context.port(Endpoint("a", "eth0")).endpoint, Endpoint("a", "eth0"))
            self.assertEqual(context.link("link-1").link_id, "link-1")
            context.replace_state(b"source")
            context.schedule_after(TICK, LINK, 10, b"link")

        def on_link(event, context):
            context.replace_state(event.payload)
            context.schedule_after(TICK, PORT, 2, b"port")

        kernel = new_kernel(actors={
            DEVICE: {TICK: dispatch}, LINK: {TICK: on_link}, PORT: {TICK: append_payload},
            SCENARIO: {TICK: append_payload},
        })
        kernel.schedule_after(kernel.scenario, TICK, DEVICE, delay_ns=2)
        self.assertIs(kernel.step().reason, StopReason.STEPPED)
        self.assertEqual(kernel.now_ns, 2)
        self.assertIs(kernel.run(RunBudget(5, 12)).reason, StopReason.IDLE)
        self.assertEqual(
            [(line.event.target, line.at_ns, line.event.parent_id) for line in kernel.trace],
            [(DEVICE, 2, None), (LINK, 12, 1), (PORT, 14, 2)],
        )
        self.assertEqual(kernel.snapshot().actor_states, (
            (DEVICE, b"source"), (LINK, b"link"), (PORT, b"port"),
        ))
        self.assertEqual(kernel.config, topology())

    def test_cancel_never_dispatches_or_advances_time(self):
        kernel = new_kernel()
        delayed = kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=20, payload=b"bad")
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=5, payload=b"good")
        kernel.cancel(delayed)
        self.assert_error(ErrorCode.UNKNOWN_EVENT, kernel.cancel, delayed)
        result = kernel.run(RunBudget(2, 100))
        self.assertEqual((result.reason, result.processed, result.time_ns), (StopReason.IDLE, 1, 5))
        self.assertEqual(
            [(line.action, line.at_ns) for line in kernel.trace],
            [(TraceAction.CANCELLED, 0), (TraceAction.EXECUTED, 5)],
        )
        self.assertEqual(kernel.snapshot().actor_states, ((DEVICE, b"good"),))

    def test_repeated_future_cancellation_releases_queue_slots(self):
        kernel = new_kernel(limits=KernelLimits(2, 2, 32, 64))
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=5, payload=b"survives")
        for time_ns in range(10, 30):
            kernel.cancel(kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=time_ns))
        self.assertEqual(len(kernel.trace), 20)
        self.assertEqual(kernel.run(RunBudget(3, 100)).processed, 1)
        self.assertEqual(kernel.snapshot().actor_states, ((DEVICE, b"survives"),))

    def test_pause_allows_manual_step_and_resume_preserves_queue(self):
        kernel = new_kernel()
        for time_ns in (3, 5):
            kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=time_ns, payload=b"x")
        kernel.pause()
        self.assertIs(kernel.run(RunBudget(5, 10)).reason, StopReason.PAUSED)
        self.assertEqual(kernel.now_ns, 0)
        self.assertEqual(kernel.step().time_ns, 3)
        self.assertIs(kernel.run(RunBudget(5, 10)).reason, StopReason.PAUSED)
        kernel.resume()
        self.assertEqual(kernel.run(RunBudget(5, 10)).time_ns, 5)
        self.assertEqual(kernel.snapshot().actor_states, ((DEVICE, b"xx"),))

    def test_reset_rejects_old_tokens_and_keeps_ids_monotonic(self):
        kernel = new_kernel()
        old = kernel.scenario
        first = kernel.schedule(old, TICK, DEVICE, time_ns=3, payload=b"old")
        pending = kernel.schedule(old, TICK, DEVICE, time_ns=4, payload=b"old")
        kernel.step()
        new = kernel.reset(old)
        self.assertEqual(new.generation, 1)
        self.assertEqual(kernel.now_ns, 0)
        self.assertEqual(kernel.trace, ())
        self.assertEqual(kernel.snapshot().actor_states, ())
        self.assertIs(kernel.step().reason, StopReason.IDLE)
        self.assert_error(ErrorCode.STALE_SCENARIO, kernel.schedule, old, TICK, DEVICE, time_ns=1)
        self.assert_error(ErrorCode.STALE_SCENARIO, kernel.cancel, pending)
        self.assert_error(ErrorCode.STALE_SCENARIO, kernel.reset, old)
        self.assert_error(
            ErrorCode.REVISION_MISMATCH, kernel.schedule, replace(new, revision_id="prior"),
            TICK, DEVICE, time_ns=1,
        )
        third = kernel.schedule(new, TICK, DEVICE, time_ns=1)
        self.assertEqual((first.event_id, pending.event_id, third.event_id), (1, 2, 3))

    def test_scenarios_with_the_same_revision_have_independent_runtime(self):
        first = new_kernel()
        second = new_kernel(scenario_id="other")
        reference = first.schedule(first.scenario, TICK, DEVICE, time_ns=2, payload=b"first")
        second.schedule(second.scenario, TICK, DEVICE, time_ns=6, payload=b"second")
        self.assert_error(ErrorCode.STALE_SCENARIO, second.cancel, reference)
        first.step()
        self.assertEqual(second.now_ns, 0)
        self.assertEqual(second.trace, ())
        second.step()
        first.reset(first.scenario)
        self.assertEqual(second.snapshot().actor_states, ((DEVICE, b"second"),))
        self.assertEqual(second.now_ns, 6)

    def test_negative_fractional_boolean_and_past_times_are_rejected(self):
        kernel = new_kernel()
        for bad in (-1, 0.5, True):
            with self.subTest(bad=bad):
                self.assert_error(
                    ErrorCode.INVALID_TIME, kernel.schedule, kernel.scenario, TICK, DEVICE, time_ns=bad,
                )
                self.assert_error(
                    ErrorCode.INVALID_TIME, kernel.schedule_after, kernel.scenario, TICK, DEVICE,
                    delay_ns=bad,
                )
        first = kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=4)
        self.assertEqual(first.event_id, 1)
        kernel.step()
        self.assert_error(
            ErrorCode.INVALID_TIME, kernel.schedule, kernel.scenario, TICK, DEVICE, time_ns=3,
        )

    def test_clock_limit_rejects_absolute_and_relative_overflow(self):
        kernel = new_kernel()
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=MAX_TIME_NS)
        self.assertEqual(kernel.step().time_ns, MAX_TIME_NS)
        self.assert_error(
            ErrorCode.TIME_OVERFLOW, kernel.schedule_after, kernel.scenario, TICK, DEVICE, delay_ns=1,
        )
        self.assert_error(
            ErrorCode.TIME_OVERFLOW, kernel.schedule, kernel.scenario, TICK, DEVICE, time_ns=MAX_TIME_NS + 1,
        )
        kernel.schedule_after(kernel.scenario, TICK, DEVICE, delay_ns=0)
        self.assertEqual(kernel.run(RunBudget(1, 1)).time_ns, MAX_TIME_NS)

    def test_event_and_time_budgets_leave_unprocessed_work_pending(self):
        kernel = new_kernel()
        for time_ns in (2, 3, 12):
            kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=time_ns, payload=b"x")
        result = kernel.run(RunBudget(1, 9))
        self.assertEqual((result.reason, result.processed, result.time_ns), (StopReason.EVENT_BUDGET, 1, 2))
        result = kernel.run(RunBudget(5, 1))
        self.assertEqual((result.reason, result.processed, result.time_ns), (StopReason.TIME_BUDGET, 1, 3))
        result = kernel.run(RunBudget(5, 0))
        self.assertEqual((result.reason, result.processed, result.time_ns), (StopReason.TIME_BUDGET, 0, 3))
        result = kernel.run(RunBudget(5, 9))
        self.assertEqual((result.reason, result.processed, result.time_ns), (StopReason.IDLE, 1, 12))
        self.assert_error(ErrorCode.INVALID_BUDGET, RunBudget, 0, 10)
        self.assert_error(ErrorCode.INVALID_TIME, RunBudget, 1, -1)

    def test_queue_payload_and_trace_budgets_fail_closed(self):
        kernel = new_kernel(limits=KernelLimits(2, 8, 1, 4))
        self.assert_error(
            ErrorCode.INVALID_PAYLOAD, kernel.schedule, kernel.scenario, TICK, DEVICE,
            time_ns=1, payload=b"12345",
        )
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=1)
        second = kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=2)
        self.assert_error(ErrorCode.QUEUE_LIMIT, kernel.schedule, kernel.scenario, TICK, DEVICE, time_ns=3)
        self.assertIs(kernel.run(RunBudget(2, 2)).reason, StopReason.TRACE_BUDGET)
        self.assertEqual(kernel.trace[0].event.ref.event_id, 1)
        self.assertEqual(kernel.now_ns, 1)
        self.assert_error(ErrorCode.TRACE_LIMIT, kernel.cancel, second)
        self.assertEqual(len(kernel.trace), 1)

    def test_livelock_guard_spans_step_and_run_slices_and_can_reset(self):
        def loop(event, context):
            context.replace_state(context.state + b"x")
            context.schedule_after(TICK, DEVICE, 0)

        kernel = new_kernel(loop, limits=KernelLimits(4, 3, 20, 20))
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=4)
        self.assertIs(kernel.run(RunBudget(1, 4)).reason, StopReason.EVENT_BUDGET)
        self.assertIs(kernel.step().reason, StopReason.STEPPED)
        result = kernel.run(RunBudget(9, 0))
        self.assertEqual((result.reason, result.error, result.processed, result.time_ns),
                         (StopReason.FAULTED, ErrorCode.LIVELOCK, 1, 4))
        self.assertEqual(result.event.event_id, 4)
        self.assertEqual(kernel.snapshot().actor_states, ((DEVICE, b"xxx"),))
        self.assertIs(kernel.step().error, ErrorCode.LIVELOCK)
        kernel.reset(kernel.scenario)
        self.assertIs(kernel.step().reason, StopReason.IDLE)

    def test_timestamp_guard_resets_at_a_later_virtual_time(self):
        kernel = new_kernel(limits=KernelLimits(8, 1, 8, 20))
        for time_ns in (0, 1, 2):
            kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=time_ns)
        self.assertEqual(kernel.run(RunBudget(8, 8)).processed, 3)

    def test_invalid_event_types_and_targets_fail_without_consuming_an_id(self):
        kernel = new_kernel()
        for event_type, target, code in (
            ("actor/tick", DEVICE, ErrorCode.INVALID_EVENT_TYPE),
            (EventType("unregistered"), DEVICE, ErrorCode.INVALID_EVENT_TYPE),
            (TICK, PORT, ErrorCode.INVALID_EVENT_TYPE),
            (TICK, EventTarget(TargetKind.PORT, "a", "missing"), ErrorCode.INVALID_TARGET),
            (TICK, EventTarget(TargetKind.DEVICE, "gone"), ErrorCode.INVALID_TARGET),
            (TICK, "a", ErrorCode.INVALID_TARGET),
        ):
            with self.subTest(event_type=event_type, target=target):
                self.assert_error(code, kernel.schedule, kernel.scenario, event_type, target, time_ns=1)
        self.assert_error(
            ErrorCode.INVALID_PAYLOAD, kernel.schedule, kernel.scenario, TICK, DEVICE,
            time_ns=1, payload=lambda: None,
        )
        self.assertEqual(kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=1).event_id, 1)
        with self.assertRaises(ConfigError):
            EventType("")
        with self.assertRaises(ConfigError):
            EventTarget(TargetKind.PORT, "a")

    def test_faulting_handler_discards_state_and_followups(self):
        def fail(event, context):
            append_payload(event, context)
            if event.payload == b"bad":
                context.schedule_after(TICK, DEVICE, 0, payload=b"orphan")
                raise RuntimeError("handler failed after staging")

        kernel = new_kernel(fail)
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=1, payload=b"prior")
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=2, payload=b"bad")
        result = kernel.run(RunBudget(5, 5))
        self.assertEqual((result.reason, result.error, result.processed, result.time_ns),
                         (StopReason.FAULTED, ErrorCode.HANDLER_FAILED, 2, 2))
        self.assertEqual(kernel.snapshot().actor_states, ((DEVICE, b"prior"),))
        self.assertEqual([line.action for line in kernel.trace], [TraceAction.EXECUTED, TraceAction.FAILED])
        self.assertIs(kernel.step().error, ErrorCode.HANDLER_FAILED)
        self.assert_error(ErrorCode.FAULTED, kernel.schedule, kernel.scenario, TICK, DEVICE, time_ns=2)
        kernel.reset(kernel.scenario)
        self.assertEqual(kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=1).event_id, 3)

    def test_invalid_followup_and_reentrant_operations_fault_the_handler(self):
        def invalid_followup(event, context):
            context.replace_state(b"staged")
            context.schedule_after(TICK, DEVICE, -1)

        def reentrant(event, context):
            kernel.step()

        for handler in (invalid_followup, reentrant):
            with self.subTest(handler=handler.__name__):
                kernel = new_kernel(handler)
                kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=4)
                self.assertIs(kernel.step().error, ErrorCode.HANDLER_FAILED)
                self.assertEqual(kernel.snapshot().actor_states, ())

    def test_random_algorithm_matches_independently_calculated_vectors(self):
        def take_two_draws(event, context):
            context.replace_state(
                context.random_u64().to_bytes(8, "big") + context.random_u64().to_bytes(8, "big"),
            )

        kernel = new_kernel(take_two_draws)
        kernel.schedule(kernel.scenario, TICK, DEVICE, time_ns=3)
        self.assertIs(kernel.step().reason, StopReason.STEPPED)
        self.assertEqual(kernel.snapshot().actor_states, ((DEVICE, bytes.fromhex(
            "902bc1b4f51ae1ee9eb105cdefbf4b7b",
        )),))

    def test_seed_must_be_unsigned_64_bit_integer(self):
        for seed in (-1, 1 << 64, False, 4.0):
            with self.subTest(seed=seed):
                self.assert_error(
                    ErrorCode.INVALID_SEED, EventKernel, ConfigSnapshot("r", (), ()), "scenario",
                    revision_id="r", seed=seed, limits=LIMITS, actors={},
                )


class ReplayTests(unittest.TestCase):
    def process(self, seed, mode="random", initial=5, hash_seed=1):
        script = "import runpy; runpy.run_path('tests/engine/replay_case.py', run_name='__main__')"
        result = subprocess.run(
            [sys.executable, "-c", script, str(seed), mode, str(initial)], cwd=ROOT,
            env={**os.environ, "PYTHONHASHSEED": str(hash_seed)},
            check=True, capture_output=True, text=True, timeout=15,
        )
        return json.loads(result.stdout)

    def test_two_processes_produce_identical_trace_bytes_and_state_hash(self):
        first = self.process(7)
        second = self.process(7, hash_seed=19)
        self.assertEqual(first, second)
        self.assertEqual((first["result"], first["processed"], first["time_ns"]), ("idle", 3, 7))
        change = int("902bc1b4f51ae1ee", 16) + 5
        self.assertEqual(first["state"], f"{change};mark;finish")
        records = json.loads(first["trace"])["data"]
        self.assertEqual(
            [(record["action"], record["at_ns"], record["event"]["ref"]["event_id"],
              record["event"]["parent_id"]) for record in records],
            [("cancelled", 0, 3, None), ("executed", 3, 1, None),
             ("executed", 7, 2, None), ("executed", 7, 4, 1)],
        )
        self.assertEqual(records[-1]["event"]["payload"], {"hex": str(change).encode("ascii").hex()})

    def test_only_explicit_random_draws_depend_on_seed(self):
        plain = self.process(7, "plain")
        self.assertEqual(plain, self.process(8, "plain"))
        self.assertEqual(plain["state"], "5;mark;finish")
        changed_input = self.process(7, "plain", initial=6)
        self.assertEqual(changed_input["state"], "6;mark;finish")
        self.assertNotEqual(plain["trace_hash"], changed_input["trace_hash"])
        self.assertNotEqual(plain["state_hash"], changed_input["state_hash"])
        random = self.process(7)
        changed_seed = self.process(8)
        self.assertNotEqual(random["trace_hash"], changed_seed["trace_hash"])
        self.assertNotEqual(random["state_hash"], changed_seed["state_hash"])
        a, b = (json.loads(output["trace"])["data"] for output in (random, changed_seed))
        self.assertEqual(a[:-1], b[:-1])
        self.assertNotEqual(a[-1]["event"].pop("payload"), b[-1]["event"].pop("payload"))
        self.assertEqual(a[-1], b[-1])
