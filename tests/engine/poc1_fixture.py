"""Explicit, synthetic Ethernet topology and independently calculated wire vectors."""

from dataclasses import replace
import json
import sys

from core.engine.config import (
    AdminState, ConfigSnapshot, DeviceConfig, DeviceKind, DeviceProfile, Endpoint, InterfaceKind,
    LinkConfig, LinkProfile, PortConfig, PortProfile, PowerState, ProfileRef,
)
from core.engine.ethernet.config import AccessPort, HostSettings, LinkTiming, SwitchSettings
from core.engine.ethernet.network import EthernetConfig, EthernetScenario
from core.engine.kernel import KernelLimits, RunBudget
from core.engine.replay import state_hash, trace_bytes

A = Endpoint("host-a", "eth0")
B = Endpoint("host-b", "eth0")
S1 = Endpoint("switch-s", "port1")
S2 = Endpoint("switch-s", "port2")
C = Endpoint("host-c", "eth0")
S3 = Endpoint("switch-s", "port3")
A_MAC = bytes.fromhex("02000000000a")
B_MAC = bytes.fromhex("02000000000b")
C_MAC = bytes.fromhex("02000000000c")
A_IP = "192.168.10.10"
B_IP = "192.168.10.20"
# Destination through ARP data, followed by eighteen zero pad bytes and literal FCS.
REQUEST = bytes.fromhex(
    "ffffffffffff02000000000a0806000108000604000102000000000ac0a80a0a000000000000c0a80a14"
    "000000000000000000000000000000000000f341ec0e"
)
REPLY = bytes.fromhex(
    "02000000000a02000000000b0806000108000604000202000000000bc0a80a1402000000000ac0a80a0a"
    "00000000000000000000000000000000000016c3bc33"
)


def scenario(*, vlan=10, queue_limit=8, rate=100_000_000, l1_delay=100, l2_delay=200,
             third_port=False, third_vlan=10, cache_limit=8, pending_limit=8, fdb_limit=16):
    port_profile = PortProfile(ProfileRef("ethernet", "1"), InterfaceKind.PHYSICAL, {"copper"})
    cable = LinkProfile(ProfileRef("cable", "1"), "copper")
    host = DeviceProfile(ProfileRef("host", "1"), DeviceKind.HOST, "Fixture", "End station", (port_profile,))
    switch = DeviceProfile(ProfileRef("switch", "1"), DeviceKind.SWITCH, "Fixture", "Bridge", (port_profile,))

    def make_device(device_id, profile, ports):
        return DeviceConfig(device_id, profile, tuple(
            PortConfig(endpoint.port_id, port_profile, AdminState.UP) for endpoint in ports
        ), PowerState.ON)

    switch_ports = (S1, S2, S3) if third_port else (S1, S2)
    devices = (
        make_device(A.device_id, host, (A,)),
        make_device(S1.device_id, switch, switch_ports),
        make_device(B.device_id, host, (B,)),
    )
    cables = (LinkConfig("l1", cable, A, S1, "fixture/l1"), LinkConfig("l2", cable, S2, B, "fixture/l2"))
    ports = (AccessPort(A, 10, queue_limit), AccessPort(S1, 10, queue_limit),
             AccessPort(S2, vlan, queue_limit), AccessPort(B, vlan, queue_limit))
    links = (LinkTiming("l1", rate, l1_delay), LinkTiming("l2", rate, l2_delay))
    hosts = (HostSettings(A, A_MAC, A_IP + "/24", cache_limit, pending_limit, 100_000),
             HostSettings(B, B_MAC, B_IP + "/24", cache_limit, pending_limit, 100_000))
    if third_port:
        devices += (make_device(C.device_id, host, (C,)),)
        cables += (LinkConfig("l3", cable, S3, C, "fixture/l3"),)
        ports += (AccessPort(S3, third_vlan, queue_limit), AccessPort(C, third_vlan, queue_limit))
        links += (LinkTiming("l3", rate, 300),)
        hosts += (HostSettings(C, C_MAC, "192.168.10.30/24", cache_limit, pending_limit, 100_000),)
    config = EthernetConfig(ConfigSnapshot("poc1", devices, cables), ports, links, hosts,
                            (SwitchSettings(S1.device_id, fdb_limit),))
    return EthernetScenario(config, "ethernet-fixture", seed=7,
                            limits=KernelLimits(256, 256, 4096, 32768))


def run_generations():
    sim = scenario()
    evidence = []
    first_id = 1
    for generation in range(3):
        if generation:
            sim.kernel.reset(sim.kernel.scenario)
        sim.initialize()
        ref = sim.resolve(A.device_id, B_IP, at_ns=0)
        outcome = sim.kernel.run(RunBudget(1000, 200_000))
        entries = json.loads(trace_bytes(sim.kernel.trace))
        for entry in entries["data"]:
            event = entry["event"]
            event["ref"]["scenario"]["generation"] = 0
            event["ref"]["event_id"] -= first_id - 1
            if event["parent_id"] is not None:
                event["parent_id"] -= first_id - 1
            if entry["cause_id"] is not None:
                entry["cause_id"] -= first_id - 1
        snapshot = sim.kernel.snapshot()
        semantic = replace(snapshot, ref=replace(snapshot.ref, generation=0))
        evidence.append({
            "generation": generation,
            "resolve_id": ref.event_id,
            "trace": entries,
            "state_sha256": state_hash(semantic),
            "neighbors": [(item.ip.hex(), item.mac.hex()) for item in sim.host_state(A.device_id).neighbors],
            "fdb": [(item.vlan, item.mac.hex(), item.port) for item in sim.switch_state(S1.device_id).fdb],
            "result": outcome.reason.value,
            "end_ns": outcome.time_ns,
        })
        first_id = max(entry.event.ref.event_id for entry in sim.kernel.trace) + 1
    return evidence


if __name__ == "__main__":
    print(json.dumps(run_generations(), sort_keys=True))
