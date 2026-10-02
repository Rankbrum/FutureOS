"""Deterministic algorithm provenance, separate from simulated agent memory.

Summary keeps tick commitments and metrics, never the complete record stream.
Hashes use canonical JSON and exclude run identity, branch labels and audit mode.
They detect differences; they do not authenticate authors or imply real causality.
"""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import re

from .codec import canonical_json
from .models import (
    AuditState, M3_ENGINE_VERSION, Simulation, TickFrame, TRACE_VERSION, TraceRecord,
)
from .randomness import RNG_POLICY
from .validation import validate_json


RECORD_KINDS = frozenset({
    "tick_started", "tick_completed", "event_applied", "interaction_created",
    "influence_applied", "state_changed", "adoption_decision", "relationship_changed",
})


def content_hash(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _chain(previous: str, value: object) -> str:
    return sha256(bytes.fromhex(previous) + canonical_json(value).encode("utf-8")).hexdigest()


def _agent_data(agent: object) -> dict:
    data = asdict(agent)
    data["relationships"].sort(key=lambda relationship: relationship["target_agent_id"])
    return data


def _state_data(simulation: Simulation, *, include_definitions: bool) -> dict:
    world = simulation.world
    data = {
        "seed": simulation.seed,
        "configuration": asdict(simulation.configuration),
        "current_tick": world.current_tick,
        "global_state": asdict(world.global_state),
        "agents": [_agent_data(agent) for agent in sorted(world.agents, key=lambda a: a.id)],
        "event_log": [asdict(record) for record in world.event_log],
        "metrics": asdict(simulation.metrics),
    }
    if include_definitions:
        data["status"] = simulation.status
        data["events"] = [asdict(event) for event in sorted(world.events, key=lambda e: (e.tick, e.id))]
        data["rng_state"] = asdict(simulation.rng_state)
        data["world_metadata"] = deepcopy(world.metadata)
        data["versions"] = {
            "engine": M3_ENGINE_VERSION if simulation.audit else "futureos-kernel-v1",
            "rng": RNG_POLICY if simulation.audit else simulation.rng_state.algorithm,
        }
    return data


def final_state_hash(simulation: Simulation) -> str:
    """Hash state needed for continuation, excluding run identity and audit data."""
    return content_hash(_state_data(simulation, include_definitions=True))


def initialize_audit(simulation: Simulation, mode: str) -> None:
    if mode not in ("summary", "trace"):
        raise ValueError("audit mode must be summary or trace")
    # The initial commitment includes realized state; future interventions are
    # definitions in the run protocol, not a realized trajectory divergence.
    initial = content_hash(_state_data(simulation, include_definitions=False))
    header = {"initialStateHash": initial, "engineVersion": M3_ENGINE_VERSION,
              "rngVersion": RNG_POLICY, "traceVersion": TRACE_VERSION}
    simulation.audit = AuditState(
        mode=mode, start_tick=simulation.world.current_tick, initial_state_hash=initial,
        trajectory_hash=content_hash({"trajectory": header}),
        event_trace_hash=content_hash({"trace": header}),
        engine_version=M3_ENGINE_VERSION, rng_version=RNG_POLICY, trace_version=TRACE_VERSION,
    )


def record(simulation: Simulation, kind: str, entity: str,
           mechanism: str, payload: dict, *, tick: int | None = None) -> None:
    audit = simulation.audit
    if audit is None:
        return
    item = TraceRecord(simulation.world.current_tick if tick is None else tick,
                       kind, entity, mechanism, deepcopy(payload))
    audit.event_trace_hash = _chain(audit.event_trace_hash, asdict(item))
    audit.trace_count += 1
    if audit.mode == "trace":
        audit.records.append(item)


def state_delta(simulation: Simulation, entity: str, field: str,
                before: object, after: object, mechanism: str,
                *, contributions: list[dict] | None = None, kind: str = "state_changed",
                source_agent_id: str | None = None, target_agent_id: str | None = None) -> None:
    if simulation.audit is None or before == after:
        return
    payload = {"field": field, "before": before, "after": after}
    if contributions is not None:
        payload["contributions"] = contributions
    if source_agent_id is not None:
        payload["source_agent_id"] = source_agent_id
    if target_agent_id is not None:
        payload["target_agent_id"] = target_agent_id
    record(simulation, kind, entity, mechanism, payload)


def commit_frame(simulation: Simulation, executed_tick: int) -> None:
    audit = simulation.audit
    if audit is None:
        return
    frame = TickFrame(
        tick=executed_tick,
        state_hash=content_hash(_state_data(simulation, include_definitions=False)),
        agent_hashes={agent.id: content_hash(_agent_data(agent))
                      for agent in sorted(simulation.world.agents, key=lambda a: a.id)},
        metrics=asdict(simulation.metrics),
        active_count=sum(agent.state.active for agent in simulation.world.agents),
        tick_unit=simulation.configuration.tick_unit,
    )
    audit.trajectory_hash = _chain(audit.trajectory_hash, asdict(frame))
    audit.frames.append(frame)


def agent_trajectory(simulation: Simulation, agent_id: str) -> list[dict]:
    """Read owned changes, received events and incoming/outgoing interactions."""
    if simulation.audit is None or simulation.audit.mode != "trace":
        raise ValueError("agent trajectory requires trace mode")
    if agent_id not in {agent.id for agent in simulation.world.agents}:
        raise ValueError("unknown agent ID")
    entity = f"agent:{agent_id}"
    rows = []
    for item in simulation.audit.records:
        payload = item.payload
        if (item.entity == entity or payload.get("source_agent_id") == agent_id
                or payload.get("target_agent_id") == agent_id
                or agent_id in payload.get("target_ids", [])):
            rows.append(asdict(item))
    return rows


def _digest(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_audit(simulation: Simulation) -> None:
    """Validate tick boundaries and audit schema without replaying the engine."""
    audit = simulation.audit
    if audit is None:
        return
    if not isinstance(audit, AuditState) or audit.mode not in ("summary", "trace"):
        raise ValueError("invalid audit state or mode")
    if (audit.engine_version != M3_ENGINE_VERSION or audit.rng_version != RNG_POLICY
            or audit.trace_version != TRACE_VERSION):
        raise ValueError("unsupported audit engine/RNG/trace version")
    if simulation.rng_state.draws != 0:
        raise ValueError("indexed RNG requires an unconsumed root state")
    if type(audit.start_tick) is not int or not 0 <= audit.start_tick <= simulation.world.current_tick:
        raise ValueError("invalid audit start tick")
    for digest in (audit.initial_state_hash, audit.trajectory_hash, audit.event_trace_hash):
        if not _digest(digest):
            raise ValueError("invalid audit hash")
    if type(audit.trace_count) is not int or audit.trace_count < 0:
        raise ValueError("invalid trace count")
    if type(audit.frames) is not list or len(audit.frames) != simulation.world.current_tick - audit.start_tick:
        raise ValueError("audit frames must cover every committed tick")
    ids = {agent.id for agent in simulation.world.agents}
    metric_fields = set(asdict(simulation.metrics))
    for expected_tick, frame in enumerate(audit.frames, audit.start_tick):
        if not isinstance(frame, TickFrame) or type(frame.tick) is not int or frame.tick != expected_tick:
            raise ValueError("unordered or invalid audit frame tick")
        if not _digest(frame.state_hash) or type(frame.agent_hashes) is not dict:
            raise ValueError("invalid audit frame hashes")
        if (type(frame.active_count) is not int or not 0 <= frame.active_count <= len(ids)
                or frame.tick_unit != simulation.configuration.tick_unit):
            raise ValueError("invalid audit frame denominator/unit")
        if set(frame.agent_hashes) != ids or not all(_digest(value) for value in frame.agent_hashes.values()):
            raise ValueError("audit frame population differs from world")
        if type(frame.metrics) is not dict or set(frame.metrics) != metric_fields:
            raise ValueError("invalid audit frame metrics")
        validate_json(frame.metrics, "audit.frame.metrics")
    if audit.frames and audit.frames[-1].metrics != asdict(simulation.metrics):
        raise ValueError("last audit frame metrics differ from current metrics")
    if audit.frames and audit.frames[-1].active_count != sum(agent.state.active for agent in simulation.world.agents):
        raise ValueError("last audit frame denominator differs from world")
    if type(audit.records) is not list:
        raise ValueError("audit records must be a list")
    if audit.mode == "summary" and audit.records:
        raise ValueError("summary must not retain full trace")
    if audit.mode == "trace" and len(audit.records) != audit.trace_count:
        raise ValueError("trace count differs from retained records")
    last_tick = audit.start_tick
    for item in audit.records:
        if (not isinstance(item, TraceRecord) or type(item.tick) is not int
                or not last_tick <= item.tick < simulation.world.current_tick):
            raise ValueError("invalid trace record tick")
        last_tick = item.tick
        if item.kind not in RECORD_KINDS or type(item.entity) is not str or not item.entity:
            raise ValueError("invalid trace record kind/entity")
        if type(item.mechanism) is not str or not item.mechanism or type(item.payload) is not dict:
            raise ValueError("invalid trace mechanism/payload")
        validate_json(item.payload, "audit.record.payload")
        if item.kind in ("state_changed", "relationship_changed"):
            if not {"field", "before", "after"} <= set(item.payload):
                raise ValueError("state delta requires field/before/after")
        if item.kind == "relationship_changed" and not {"source_agent_id", "target_agent_id"} <= set(item.payload):
            raise ValueError("relationship delta requires structured participant IDs")


def verify_audit(simulation: Simulation) -> None:
    """Check retained chain commitments at a persistence/read boundary."""
    validate_audit(simulation)
    audit = simulation.audit
    if audit is None:
        return
    header = {"initialStateHash": audit.initial_state_hash, "engineVersion": audit.engine_version,
              "rngVersion": audit.rng_version, "traceVersion": audit.trace_version}
    trajectory = content_hash({"trajectory": header})
    for frame in audit.frames:
        trajectory = _chain(trajectory, asdict(frame))
    if trajectory != audit.trajectory_hash:
        raise ValueError("audit trajectory hash mismatch")
    if audit.frames:
        last = audit.frames[-1]
        if last.state_hash != content_hash(_state_data(simulation, include_definitions=False)):
            raise ValueError("audit endpoint state hash mismatch")
        if last.agent_hashes != {agent.id: content_hash(_agent_data(agent)) for agent in simulation.world.agents}:
            raise ValueError("audit endpoint agent hashes mismatch")
    if audit.mode == "trace":
        trace_hash = content_hash({"trace": header})
        for item in audit.records:
            trace_hash = _chain(trace_hash, asdict(item))
        if trace_hash != audit.event_trace_hash:
            raise ValueError("audit trace hash mismatch")
