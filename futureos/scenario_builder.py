"""Scenario Builder M15 — manual mode only. No execution, only spec."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Literal

from .codec import canonical_json, parse_json
from .models import Event, EventTarget, EventType, GlobalState

ScenarioSource = Literal["manual", "llm_generated"]
ScenarioWarning = Literal["SYNTHETIC_SCENARIO", "UNCALIBRATED_SCENARIO"]

SUPPORTED_TYPES: set[str] = set(EventType.__args__ if hasattr(EventType, "__args__") else ("PRICE_CHANGE", "INCENTIVE", "NEWS", "TRUST_SHOCK", "COMPETITOR_ENTRY"))


@dataclass(slots=True)
class InterventionSpec:
    type: str
    tick: int
    payload: dict
    target: str | dict = field(default_factory=lambda: {"kind": "all"})
    reach: float = 1.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in SUPPORTED_TYPES:
            raise ValueError(f"Unsupported intervention type: {self.type}")
        if not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be int >= 0")
        if not isinstance(self.reach, (int, float)) or self.reach < 0 or self.reach > 1:
            raise ValueError("reach must be in [0, 1]")
        if not isinstance(self.payload, dict) or not self.payload:
            raise ValueError("payload must be non-empty dict")


@dataclass(slots=True)
class BranchSpec:
    id: str
    name: str
    interventions: list[InterventionSpec] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise ValueError("BranchSpec.id must be non-empty str")
        for i in self.interventions:
            if not isinstance(i, InterventionSpec):
                raise ValueError("interventions must be InterventionSpec")


@dataclass(slots=True)
class ScenarioSpec:
    id: str
    name: str
    description: str
    initial_state: dict
    duration_ticks: int
    branches: list[BranchSpec]
    assumptions: list[str] = field(default_factory=list)
    warnings: list[ScenarioWarning] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source: ScenarioSource = "manual"

    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise ValueError("ScenarioSpec.id must be non-empty str")
        if self.duration_ticks < 0 or isinstance(self.duration_ticks, float):
            raise ValueError("duration_ticks must be int >= 0")
        branch_ids = [b.id for b in self.branches]
        if len(branch_ids) != len(set(branch_ids)):
            raise ValueError("Duplicate branch ids")
        for w in self.warnings:
            if w not in ("SYNTHETIC_SCENARIO", "UNCALIBRATED_SCENARIO"):
                raise ValueError("Invalid warning")
        if self.source not in ("manual", "llm_generated"):
            raise ValueError("Invalid source")


def validate_scenario_spec(spec: ScenarioSpec) -> None:
    if not isinstance(spec, ScenarioSpec):
        raise ValueError("Expected ScenarioSpec")
    branch_ids = [b.id for b in spec.branches]
    if len(branch_ids) != len(set(branch_ids)):
        raise ValueError("branch IDs must be unique")
    if spec.duration_ticks < 0:
        raise ValueError("duration_ticks must be >= 0")
    for b in spec.branches:
        for inter in b.interventions:
            if inter.tick > spec.duration_ticks:
                raise ValueError(f"intervention tick {inter.tick} > duration {spec.duration_ticks}")
            if inter.reach < 0 or inter.reach > 1:
                raise ValueError("reach must be in [0,1]")
            if inter.type not in SUPPORTED_TYPES:
                raise ValueError(f"unsupported type {inter.type}")
            p = inter.payload
            if inter.type == "PRICE_CHANGE" and ("price" not in p):
                raise ValueError("PRICE_CHANGE requires price in payload")
    allowed_global = {"price", "incentive", "competitor_pressure"}
    for k in spec.initial_state:
        if k not in allowed_global:
            raise ValueError(f"initial_state unknown key: {k}")


def build_branch_events(branch_spec: BranchSpec) -> list[Event]:
    events = []
    for inter in branch_spec.interventions:
        target = EventTarget(kind="all")
        if isinstance(inter.target, dict):
            target = EventTarget(**inter.target)
        events.append(Event(
            id=f"{branch_spec.id}-{inter.tick}-{inter.type}",
            type=inter.type,  # type: ignore[arg-type]
            tick=inter.tick,
            payload=inter.payload,
            target=target,
            reach=inter.reach,
            metadata=inter.metadata,
        ))
    return events


def apply_initial_state(world, initial_state: dict):
    if hasattr(world, "global_state") and world.global_state is not None:
        gs = world.global_state
        for k, v in initial_state.items():
            if hasattr(gs, k):
                setattr(gs, k, v)
    else:
        for agent in getattr(world, "agents", []):
            if "price" in initial_state:
                agent.state.price_override = initial_state.get("price")
            if "incentive" in initial_state:
                agent.state.incentive_override = initial_state.get("incentive")


def scenario_fingerprint(spec: ScenarioSpec) -> str:
    raw = asdict(spec)
    canonical = canonical_json(raw)
    return hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()


def scenario_to_json(spec: ScenarioSpec) -> dict:
    validate_scenario_spec(spec)
    return asdict(spec)


def scenario_from_json(value: str | dict) -> ScenarioSpec:
    if isinstance(value, str):
        value = parse_json(value)
    if not isinstance(value, dict):
        raise ValueError("ScenarioSpec JSON must be object")
    allowed = set(ScenarioSpec.__dataclass_fields__)
    unknown = set(value) - allowed
    if unknown:
        raise ValueError("Unknown ScenarioSpec field(s): " + ", ".join(sorted(unknown)))
    raw_branches = value.get("branches", [])
    if not isinstance(raw_branches, list):
        raise ValueError("branches must be list")
    branches = []
    for idx, rb in enumerate(raw_branches):
        if set(rb) - set(BranchSpec.__dataclass_fields__):
            raise ValueError(f"Unknown branch field at {idx}")
        raw_inter = rb.get("interventions", [])
        interventions = []
        for i_idx, ri in enumerate(raw_inter):
            if set(ri) - set(InterventionSpec.__dataclass_fields__):
                raise ValueError(f"Unknown intervention field at branch {idx} inter {i_idx}")
            interventions.append(InterventionSpec(**ri))
        branches.append(BranchSpec(
            id=rb["id"], name=rb.get("name", rb["id"]),
            interventions=interventions,
            metadata=rb.get("metadata", {}),
        ))
    spec = ScenarioSpec(
        id=value["id"],
        name=value.get("name", value["id"]),
        description=value.get("description", ""),
        initial_state=value.get("initial_state", {}),
        duration_ticks=value.get("duration_ticks", 0),
        branches=branches,
        assumptions=value.get("assumptions", []),
        warnings=value.get("warnings", []),
        metadata=value.get("metadata", {}),
        source=value.get("source", "manual"),
    )
    validate_scenario_spec(spec)
    return spec
