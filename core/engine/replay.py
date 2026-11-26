"""Canonical trace and modeled-state evidence for deterministic replay."""

import json
from dataclasses import asdict
from hashlib import sha256

from .events import TraceEntry
from .runtime import RuntimeSnapshot

REPLAY_VERSION = 1


def _encode_bytes(value: object) -> dict[str, str]:
    if type(value) is bytes:
        return {"hex": value.hex()}
    raise TypeError(f"Unsupported replay value: {type(value).__name__}")


def _canonical(kind: str, data: object) -> bytes:
    return json.dumps(
        {"version": REPLAY_VERSION, "kind": kind, "data": data},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=_encode_bytes,
    ).encode("ascii")


def trace_bytes(trace: tuple[TraceEntry, ...]) -> bytes:
    return _canonical("trace", [asdict(entry) for entry in trace])


def trace_hash(trace: tuple[TraceEntry, ...]) -> str:
    return sha256(trace_bytes(trace)).hexdigest()


def state_hash(snapshot: RuntimeSnapshot) -> str:
    return sha256(_canonical("state", asdict(snapshot))).hexdigest()
