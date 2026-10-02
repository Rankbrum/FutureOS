"""Small data contracts for the local, synthetic FutureOS kernel.

Mutable execution data is copied by engine transitions and snapshot restoration.
Simulation is the M1 execution aggregate; model definition is its configuration.
"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from .randomness import RandomState


ENGINE_VERSION = "futureos-kernel-v1"
SNAPSHOT_VERSION = 1
M3_ENGINE_VERSION = "futureos-kernel-v2"
M3_SNAPSHOT_VERSION = 2
TRACE_VERSION = "futureos-trace-v1"
JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)
EventType: TypeAlias = Literal[
    "PRICE_CHANGE", "INCENTIVE", "NEWS", "TRUST_SHOCK", "COMPETITOR_ENTRY"
]
SimulationStatus: TypeAlias = Literal["ready", "running", "paused", "completed"]


@dataclass(slots=True)
class Traits:
    openness: float = 0.5
    risk_tolerance: float = 0.5
    price_sensitivity: float = 0.5
    influence: float = 0.5
    conformity: float = 0.5


@dataclass(slots=True)
class AgentState:
    trust: float = 0.5
    sentiment: float = 0.0
    adoption_intent: float = 0.0
    adopted: bool = False
    active: bool = True
    price_override: float | None = None
    incentive_override: float | None = None
    competitor_pressure_override: float | None = None


@dataclass(slots=True)
class Memory:
    tick: int
    kind: str
    payload: dict[str, JsonValue]


@dataclass(slots=True)
class Relationship:
    target_agent_id: str
    trust: float = 0.5
    influence: float = 0.5
    strength: float = 0.5


@dataclass(slots=True)
class Agent:
    id: str
    traits: Traits = field(default_factory=Traits)
    state: AgentState = field(default_factory=AgentState)
    memory: list[Memory] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True)
class EventTarget:
    kind: Literal["all", "agents", "group"] = "all"
    agent_ids: list[str] = field(default_factory=list)
    group: str | None = None


@dataclass(slots=True)
class Event:
    id: str
    type: EventType
    tick: int
    payload: dict[str, JsonValue]
    target: EventTarget = field(default_factory=EventTarget)
    reach: float = 1.0
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True)
class GlobalState:
    price: float = 99.9
    incentive: float = 0.0
    competitor_pressure: float = 0.0


@dataclass(slots=True)
class EventRecord:
    tick: int
    event_id: str
    target_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class World:
    id: str
    current_tick: int = 0
    agents: list[Agent] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    global_state: GlobalState = field(default_factory=GlobalState)
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    event_log: list[EventRecord] = field(default_factory=list)


@dataclass(slots=True)
class Configuration:
    tick_unit: str = "synthetic_step"
    model_version: str = "synthetic-adoption-v1"
    noise: float = 0.1
    adoption_threshold: float = 0.60
    peer_weight: float = 0.35
    price_scale: float = 100.0
    interaction_probability: float = 0.3
    trust_learning_rate: float = 0.03
    sentiment_decay: float = 0.95


@dataclass(slots=True)
class Metrics:
    adoption_rate: float = 0.0
    average_trust: float = 0.0
    average_sentiment: float = 0.0
    average_intent: float = 0.0
    interaction_count: int = 0
    event_count: int = 0


@dataclass(slots=True)
class TraceRecord:
    tick: int
    kind: str
    entity: str
    mechanism: str
    payload: dict[str, JsonValue]


@dataclass(slots=True)
class TickFrame:
    tick: int
    state_hash: str
    agent_hashes: dict[str, str]
    metrics: dict[str, int | float]
    active_count: int
    tick_unit: str


@dataclass(slots=True)
class AuditState:
    mode: Literal["summary", "trace"]
    start_tick: int
    initial_state_hash: str
    trajectory_hash: str
    event_trace_hash: str
    engine_version: str
    rng_version: str
    trace_version: str
    trace_count: int = 0
    records: list[TraceRecord] = field(default_factory=list)
    frames: list[TickFrame] = field(default_factory=list)


@dataclass(slots=True)
class Simulation:
    id: str
    seed: int
    world: World
    rng_state: RandomState
    configuration: Configuration = field(default_factory=Configuration)
    metrics: Metrics = field(default_factory=Metrics)
    status: SimulationStatus = "ready"
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    audit: AuditState | None = None
