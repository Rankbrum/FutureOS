"""Validate committed kernel state before execution or snapshot restoration."""

import math

from .models import (
    Agent, AgentState, Configuration, Event, EventRecord, EventTarget,
    GlobalState, Memory, Metrics, Relationship, Simulation, Traits, World,
)
from .randomness import SeededRandom, validate_seed


def _instance(value: object, expected: type, path: str) -> None:
    if not isinstance(value, expected):
        raise ValueError(f"{path} must be a {expected.__name__}")


def _text(value: object, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a nonempty string")
    _unicode(value, path)


def _unicode(value: str, path: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{path} must contain valid Unicode scalar values") from error


def _integer(value: object, path: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{path} must be a nonnegative integer")


def _number(value: object, path: str, lower: float | None = None,
            upper: float | None = None, *, positive: bool = False) -> None:
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{path} must be a finite number")
    if lower is not None and value < lower:
        raise ValueError(f"{path} must be >= {lower}")
    if upper is not None and value > upper:
        raise ValueError(f"{path} must be <= {upper}")
    if positive and value <= 0:
        raise ValueError(f"{path} must be > 0")


def _list(value: object, path: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")


def validate_json(value: object, path: str = "value") -> None:
    """Reject non-JSON values, cycles, and nonfinite floats without mutating data."""
    ancestors: set[int] = set()

    def visit(item: object, location: str, depth: int) -> None:
        if depth > 100:
            raise ValueError(f"{location} exceeds the maximum JSON depth (100)")
        if type(item) is str:
            _unicode(item, location)
            return
        if item is None or type(item) in (int, bool):
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError(f"{location} must contain only finite JSON numbers")
            return
        if type(item) not in (list, dict):
            raise ValueError(f"{location} is not a JSON value")
        if id(item) in ancestors:
            raise ValueError(f"{location} contains a JSON cycle")
        ancestors.add(id(item))
        if isinstance(item, dict):
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError(f"{location} must contain string keys")
                _unicode(key, f"{location} key")
                visit(child, f"{location}.{key}", depth + 1)
        else:
            for index, child in enumerate(item):
                visit(child, f"{location}[{index}]", depth + 1)
        ancestors.remove(id(item))

    visit(value, path, 0)


def _mapping(value: object, path: str) -> None:
    if type(value) is not dict:
        raise ValueError(f"{path} must be a JSON object")
    validate_json(value, path)


def _ids(value: object, path: str) -> set[str]:
    _list(value, path)
    seen: set[str] = set()
    for index, identifier in enumerate(value):
        _text(identifier, f"{path}[{index}]")
        if identifier in seen:
            raise ValueError(f"{path} contains duplicate ID {identifier!r}")
        seen.add(identifier)
    return seen


def _population_ids(world: World) -> set[str]:
    _instance(world, World, "world")
    _list(world.agents, "world.agents")
    ids: list[str] = []
    for index, agent in enumerate(world.agents):
        _instance(agent, Agent, f"world.agents[{index}]")
        ids.append(agent.id)
    return _ids(ids, "world.agents IDs")


def validate_event(event: Event, world: World) -> None:
    """Validate one scheduled event; past events remain legal history in a world."""
    _instance(event, Event, "event")
    _text(event.id, "event.id")
    _integer(event.tick, "event.tick")
    _number(event.reach, "event.reach", 0, 1)
    _mapping(event.payload, "event.payload")
    _mapping(event.metadata, "event.metadata")
    specifications = {
        "PRICE_CHANGE": {"price": (0, None)},
        "INCENTIVE": {"amount": (0, None)},
        "NEWS": {"sentiment_delta": (-1, 1), "trust_delta": (-1, 1)},
        "TRUST_SHOCK": {"trust_delta": (-1, 1)},
        "COMPETITOR_ENTRY": {"pressure": (0, 1)},
    }
    _text(event.type, "event.type")
    if event.type not in specifications:
        raise ValueError(f"unsupported event type: {event.type!r}")
    specification = specifications[event.type]
    unknown = set(event.payload) - set(specification)
    if unknown:
        raise ValueError(f"event.payload contains unknown keys: {sorted(unknown)}")
    if event.type == "NEWS":
        if not event.payload:
            raise ValueError("NEWS payload requires sentiment_delta or trust_delta")
    elif set(event.payload) != set(specification):
        raise ValueError(f"{event.type} payload requires {', '.join(specification)}")
    for key, value in event.payload.items():
        lower, upper = specification[key]
        _number(value, f"event.payload.{key}", lower, upper)

    population_ids = _population_ids(world)
    _instance(event.target, EventTarget, "event.target")
    target = event.target
    selected = _ids(target.agent_ids, "event.target.agent_ids")
    if target.kind == "all":
        if selected or target.group is not None:
            raise ValueError("target 'all' cannot contain agent_ids or group")
    elif target.kind == "agents":
        if target.group is not None or not selected:
            raise ValueError("target 'agents' requires agent_ids and no group")
        unknown_ids = selected - population_ids
        if unknown_ids:
            raise ValueError(f"event target has unknown agent IDs: {sorted(unknown_ids)}")
    elif target.kind == "group":
        _text(target.group, "event.target.group")
        if selected:
            raise ValueError("target 'group' cannot contain agent_ids")
        for agent in world.agents:
            _mapping(agent.metadata, f"agent {agent.id}.metadata")
        if not any(agent.metadata.get("group") == target.group for agent in world.agents):
            raise ValueError(f"event target has unknown group: {target.group!r}")
    else:
        raise ValueError(f"unsupported event target kind: {target.kind!r}")


def _validate_agent(agent: Agent, world: World, ids: set[str]) -> None:
    path = f"agent {agent.id}"
    _instance(agent.traits, Traits, f"{path}.traits")
    for field in ("openness", "risk_tolerance", "price_sensitivity", "influence", "conformity"):
        _number(getattr(agent.traits, field), f"{path}.traits.{field}", 0, 1)
    _instance(agent.state, AgentState, f"{path}.state")
    for field in ("trust", "adoption_intent"):
        _number(getattr(agent.state, field), f"{path}.state.{field}", 0, 1)
    _number(agent.state.sentiment, f"{path}.state.sentiment", -1, 1)
    for field in ("adopted", "active"):
        if type(getattr(agent.state, field)) is not bool:
            raise ValueError(f"{path}.state.{field} must be a boolean")
    for field in ("price_override", "incentive_override", "competitor_pressure_override"):
        value = getattr(agent.state, field)
        if value is not None:
            upper = 1 if field == "competitor_pressure_override" else None
            _number(value, f"{path}.state.{field}", 0, upper)
    _mapping(agent.metadata, f"{path}.metadata")
    _list(agent.memory, f"{path}.memory")
    for memory in agent.memory:
        _instance(memory, Memory, f"{path}.memory entry")
        _integer(memory.tick, f"{path}.memory.tick")
        if memory.tick > world.current_tick:
            raise ValueError(f"{path}.memory.tick cannot be in the future")
        _text(memory.kind, f"{path}.memory.kind")
        _mapping(memory.payload, f"{path}.memory.payload")
    _list(agent.relationships, f"{path}.relationships")
    targets: set[str] = set()
    for relationship in agent.relationships:
        _instance(relationship, Relationship, f"{path}.relationship")
        _text(relationship.target_agent_id, f"{path}.relationship.target_agent_id")
        target = relationship.target_agent_id
        if target not in ids:
            raise ValueError(f"{path} has relationship to unknown agent {target!r}")
        if target == agent.id or target in targets:
            raise ValueError(f"{path} has self or duplicate relationship to {target!r}")
        targets.add(target)
        for field in ("trust", "influence", "strength"):
            _number(getattr(relationship, field), f"{path}.relationship.{field}", 0, 1)


def _validate_configuration(configuration: Configuration) -> None:
    _instance(configuration, Configuration, "configuration")
    if configuration.tick_unit != "synthetic_step":
        raise ValueError("unsupported tick_unit; expected 'synthetic_step'")
    if configuration.model_version != "synthetic-adoption-v1":
        raise ValueError("unsupported behavioral model version")
    for field in ("noise", "adoption_threshold", "peer_weight", "interaction_probability",
                  "trust_learning_rate", "sentiment_decay"):
        _number(getattr(configuration, field), f"configuration.{field}", 0, 1)
    _number(configuration.price_scale, "configuration.price_scale", positive=True)


def _validate_behavioral_aliases(world: World) -> None:
    # deepcopy deliberately preserves aliases. Shared mutable behavior data would
    # therefore make changing one agent silently change another in the same world.
    owners: dict[int, str] = {}

    def claim(value: object, owner: str) -> None:
        previous = owners.get(id(value))
        if previous is not None and previous != owner:
            raise ValueError(f"agents {previous!r} and {owner!r} share mutable behavior state")
        owners[id(value)] = owner

    for agent in world.agents:
        for value in (agent.state, agent.memory, agent.relationships,
                      *agent.memory, *agent.relationships):
            claim(value, agent.id)


def validate_simulation(simulation: Simulation) -> None:
    """Validate complete state at a committed tick boundary, including history.

    Completed simulations can be saved and inspected. Engine execution functions
    separately reject them, since completion is a terminal runtime status.
    """
    _instance(simulation, Simulation, "simulation")
    _text(simulation.id, "simulation.id")
    validate_seed(simulation.seed)
    generator = SeededRandom.from_state(simulation.rng_state)
    if generator.state.seed != simulation.seed:
        raise ValueError("simulation seed differs from RNG seed")
    if simulation.status not in ("ready", "running", "paused", "completed"):
        raise ValueError(f"unsupported simulation status: {simulation.status!r}")
    _mapping(simulation.metadata, "simulation.metadata")
    _validate_configuration(simulation.configuration)

    world = simulation.world
    ids = _population_ids(world)
    _text(world.id, "world.id")
    _integer(world.current_tick, "world.current_tick")
    _mapping(world.metadata, "world.metadata")
    _instance(world.global_state, GlobalState, "world.global_state")
    _number(world.global_state.price, "world.global_state.price", 0)
    _number(world.global_state.incentive, "world.global_state.incentive", 0)
    _number(world.global_state.competitor_pressure, "world.global_state.competitor_pressure", 0, 1)
    for agent in world.agents:
        _validate_agent(agent, world, ids)
    _validate_behavioral_aliases(world)

    _list(world.events, "world.events")
    events: dict[str, Event] = {}
    for event in world.events:
        validate_event(event, world)
        if event.id in events:
            raise ValueError(f"world.events contains duplicate ID {event.id!r}")
        events[event.id] = event
    _list(world.event_log, "world.event_log")
    recorded: set[str] = set()
    last_key: tuple[int, str] | None = None
    for record in world.event_log:
        _instance(record, EventRecord, "world.event_log entry")
        _integer(record.tick, "event_log.tick")
        _text(record.event_id, "event_log.event_id")
        targets = _ids(record.target_ids, "event_log.target_ids")
        if targets - ids:
            raise ValueError("event_log contains unknown target agent IDs")
        if record.event_id not in events or record.event_id in recorded:
            raise ValueError("event_log contains an unknown or duplicate event ID")
        if record.tick != events[record.event_id].tick or record.tick >= world.current_tick:
            raise ValueError("event_log must refer to an event in a committed past tick")
        key = (record.tick, record.event_id)
        if last_key is not None and key < last_key:
            raise ValueError("event_log must be ordered by (tick, event ID)")
        last_key = key
        recorded.add(record.event_id)
    expected_records = {event.id for event in world.events if event.tick < world.current_tick}
    if recorded != expected_records:
        raise ValueError("event_log is missing committed past events")

    _instance(simulation.metrics, Metrics, "metrics")
    for field in ("adoption_rate", "average_trust", "average_intent"):
        _number(getattr(simulation.metrics, field), f"metrics.{field}", 0, 1)
    _number(simulation.metrics.average_sentiment, "metrics.average_sentiment", -1, 1)
    _integer(simulation.metrics.interaction_count, "metrics.interaction_count")
    _integer(simulation.metrics.event_count, "metrics.event_count")
    if simulation.metrics.event_count != len(world.event_log):
        raise ValueError("metrics.event_count must equal the event log length")
    # Imported at the committed boundary to avoid a codec/validation/audit
    # import cycle. The audit module owns its versioned state invariants.
    from .audit import validate_audit
    validate_audit(simulation)


def validate_transition(simulation: Simulation, previous: Simulation) -> None:
    """Minimal incremental validation: only what changed from previous tick."""
    _instance(simulation, Simulation, "simulation")
    _instance(previous, Simulation, "previous")
    if simulation.id != previous.id:
        raise ValueError("transition id changed")
    if simulation.seed != previous.seed:
        raise ValueError("transition seed changed")
    world = simulation.world
    if world.current_tick != previous.world.current_tick + 1:
        raise ValueError("tick must advance by exactly 1")
    for event in world.events:
        if event.tick > world.current_tick:
            raise ValueError("future event tick exceeds current")
    if simulation.metrics.event_count < previous.metrics.event_count:
        raise ValueError("event_count must not decrease")
