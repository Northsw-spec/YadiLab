"""Synthetic device fixture. Run in a clean process to collect replay evidence."""

import json
import sys

from core.engine.config import ConfigSnapshot, DeviceConfig, DeviceKind, DeviceProfile, PowerState, ProfileRef
from core.engine.events import EventTarget, EventType, TargetKind
from core.engine.kernel import EventKernel, KernelLimits, RunBudget
from core.engine.replay import state_hash, trace_bytes, trace_hash

DEVICE = EventTarget(TargetKind.DEVICE, "counter")
START = EventType("counter/start")
MARK = EventType("counter/mark")
FINISH = EventType("counter/finish")


def run_case(seed, mode, initial):
    profile = DeviceProfile(ProfileRef("counter", "1"), DeviceKind.OTHER, "Fixture", "Counter", ())
    config = ConfigSnapshot("fixture-r1", (DeviceConfig("counter", profile, (), PowerState.ON),), ())

    def start(event, context):
        value = int(event.payload)
        if mode == "random":
            value += context.random_u64()
        context.replace_state(str(value).encode("ascii"))
        context.schedule_after(FINISH, DEVICE, 4, context.state)

    def mark(event, context):
        context.replace_state(context.state + b";mark")

    def finish(event, context):
        if context.state != event.payload + b";mark":
            raise ValueError("Equal-time marker must run before its already queued peer")
        context.replace_state(context.state + b";finish")

    kernel = EventKernel(
        config, "replay", revision_id=config.revision_id, seed=seed,
        limits=KernelLimits(16, 16, 64, 256),
        actors={DEVICE: {START: start, MARK: mark, FINISH: finish}},
    )
    kernel.schedule(kernel.scenario, START, DEVICE, time_ns=3, payload=str(initial).encode("ascii"))
    kernel.schedule(kernel.scenario, MARK, DEVICE, time_ns=7)
    cancelled = kernel.schedule(kernel.scenario, MARK, DEVICE, time_ns=100)
    kernel.cancel(cancelled)
    result = kernel.run(RunBudget(20, 20))
    snapshot = kernel.snapshot()
    return {
        "result": result.reason.value,
        "processed": result.processed,
        "time_ns": result.time_ns,
        "trace_hash": trace_hash(kernel.trace),
        "trace": trace_bytes(kernel.trace).decode("ascii"),
        "state_hash": state_hash(snapshot),
        "state": snapshot.actor_states[0][1].decode("ascii") if snapshot.actor_states else "",
    }


if __name__ == "__main__":
    seed, mode, initial = sys.argv[1:]
    print(json.dumps(run_case(int(seed), mode, int(initial)), sort_keys=True))
