"""Synthetic device fixture. Run in a clean process to collect replay evidence."""

import json
import sys
from dataclasses import replace

from core.engine.config import ConfigSnapshot, DeviceConfig, DeviceKind, DeviceProfile, PowerState, ProfileRef
from core.engine.events import EventTarget, EventType, KernelError, TargetKind
from core.engine.kernel import EventKernel, KernelLimits, RunBudget
from core.engine.replay import state_hash, trace_bytes, trace_hash

DEVICE = EventTarget(TargetKind.DEVICE, "counter")
START = EventType("counter/start")
MARK = EventType("counter/mark")
FINISH = EventType("counter/finish")


def run_generations(seed, mode, initial, resets):
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
    generations = []
    prior_ref = None
    for index in range(resets + 1):
        if index:
            kernel.reset(kernel.scenario)
        reference = kernel.schedule(
            kernel.scenario, START, DEVICE, time_ns=3, payload=str(initial).encode("ascii"),
        )
        kernel.schedule(kernel.scenario, MARK, DEVICE, time_ns=7)
        cancelled = kernel.schedule(kernel.scenario, MARK, DEVICE, time_ns=100)
        kernel.cancel(cancelled)
        stale_error = None
        if prior_ref is not None:
            try:
                kernel.cancel(prior_ref)
            except KernelError as exc:
                stale_error = exc.code.value
        prior_ref = reference

        result = kernel.run(RunBudget(20, 20))
        snapshot = kernel.snapshot()
        # Preserve the scenario and revision, dropping only the reset generation.
        semantic_snapshot = replace(snapshot, ref=replace(snapshot.ref, generation=0))
        generations.append({
            "result": result.reason.value,
            "processed": result.processed,
            "time_ns": result.time_ns,
            "trace_hash": trace_hash(kernel.trace),
            "trace": trace_bytes(kernel.trace).decode("ascii"),
            "state_hash": state_hash(snapshot),
            "semantic_state_hash": state_hash(semantic_snapshot),
            "state": snapshot.actor_states[0][1].decode("ascii") if snapshot.actor_states else "",
            "stale_error": stale_error,
        })
    return generations


if __name__ == "__main__":
    seed, mode, initial, *rest = sys.argv[1:]
    output = run_generations(int(seed), mode, int(initial), int(rest[0]) if rest else 0)
    print(json.dumps(output if rest else output[0], sort_keys=True))
