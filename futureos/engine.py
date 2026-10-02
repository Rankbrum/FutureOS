"""Atomic, deterministic transitions for a deliberately synthetic society.

Every public transition returns an independent copy. Agents observe peers after
the event phase and before any decision; iteration order cannot expose a peer's
new decision during the same tick. The formula is an engineering fixture, not a
calibrated model of human behavior.
"""

from copy import deepcopy
from dataclasses import asdict

from .audit import commit_frame, initialize_audit, record, state_delta

from .models import (
    Agent,
    AgentState,
    Configuration,
    Event,
    EventRecord,
    Memory,
    Metrics,
    Relationship,
    Simulation,
    World,
)
from .randomness import RandomState, RandomStreams, SeededRandom
from .validation import validate_event, validate_simulation


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _active_agents(world: World) -> list[Agent]:
    return sorted((agent for agent in world.agents if agent.state.active),
                  key=lambda agent: agent.id)


def _collect_metrics(world: World, interaction_count: int) -> Metrics:
    active = _active_agents(world)
    count = len(active)
    return Metrics(
        adoption_rate=sum(agent.state.adopted for agent in active) / count if count else 0.0,
        average_trust=sum(agent.state.trust for agent in active) / count if count else 0.0,
        average_sentiment=sum(agent.state.sentiment for agent in active) / count if count else 0.0,
        average_intent=sum(agent.state.adoption_intent for agent in active) / count if count else 0.0,
        interaction_count=interaction_count,
        event_count=len(world.event_log),
    )


def create_simulation(
    simulation_id: str,
    seed: int,
    world: World,
    configuration: Configuration | None = None,
    rng_state: RandomState | None = None,
    *,
    audit_mode: str | None = None,
) -> Simulation:
    """Copy a world and retain an optional stream already used by population.

Snapshot restoration is a separate operation. For a supplied world with past
activity, initial interaction counts come from its interaction memories.
"""
    if audit_mode is not None and audit_mode not in ("summary", "trace"):
        raise ValueError("audit mode must be summary or trace")
    if audit_mode is not None and rng_state is not None and rng_state.draws != 0:
        raise ValueError("M3 requires an unconsumed root RNG; population has a separate stream")
    generator = (SeededRandom(seed) if rng_state is None
                 else SeededRandom.from_state(rng_state))
    if not isinstance(world, World):
        raise ValueError("world must be a World")
    simulation = Simulation(
        id=simulation_id,
        seed=seed,
        world=world,
        rng_state=generator.state,
        configuration=configuration if configuration is not None else Configuration(),
        metrics=Metrics(event_count=(len(world.event_log)
                                   if isinstance(world.event_log, list) else 0)),
    )
    # Validate before copying: invalid metadata can contain objects that cannot
    # be deep-copied, and should still fail with the domain validation message.
    validate_simulation(simulation)
    simulation = deepcopy(simulation)
    copied_world = simulation.world
    copied_world.events.sort(key=lambda event: (event.tick, event.id))
    interaction_count = sum(
        memory.kind == "interaction"
        for agent in copied_world.agents
        for memory in agent.memory
    )
    simulation.metrics = _collect_metrics(copied_world, interaction_count)
    if audit_mode is not None:
        initialize_audit(simulation, audit_mode)
    validate_simulation(simulation)
    return simulation


def schedule_event(simulation: Simulation, event: Event) -> Simulation:
    """Return an isolated simulation with a validated current/future event."""
    validate_simulation(simulation)
    if simulation.status == "completed":
        raise ValueError("cannot schedule events on a completed simulation")
    validate_event(event, simulation.world)
    if event.tick < simulation.world.current_tick:
        raise ValueError("cannot schedule an event before the current tick")
    if any(existing.id == event.id for existing in simulation.world.events):
        raise ValueError(f"duplicate event id: {event.id!r}")
    result = deepcopy(simulation)
    result.world.events.append(deepcopy(event))
    result.world.events.sort(key=lambda item: (item.tick, item.id))
    validate_simulation(result)
    return result


def _eligible_agents(event: Event, world: World) -> list[Agent]:
    if event.target.kind == "all":
        eligible = world.agents
    elif event.target.kind == "agents":
        target_ids = set(event.target.agent_ids)
        eligible = [agent for agent in world.agents if agent.id in target_ids]
    else:
        eligible = [agent for agent in world.agents
                    if agent.metadata.get("group") == event.target.group]
    return sorted(eligible, key=lambda agent: agent.id)


def _apply_event(event: Event, world: World, generator: SeededRandom,
                 simulation: Simulation) -> None:
    recipients = [agent for agent in _eligible_agents(event, world)
                  if (RandomStreams(simulation.seed).stream(
                      "events", world.current_tick, event.id, agent.id
                  ) if simulation.audit else generator).probability(event.reach)]
    record(simulation, "event_applied", f"event:{event.id}", f"event:{event.type}",
           {"event_id": event.id, "type": event.type, "target_ids": [a.id for a in recipients],
            "reach": event.reach, "payload": event.payload})
    economic_fields = {
        "PRICE_CHANGE": ("price", "price_override", "price"),
        "INCENTIVE": ("incentive", "incentive_override", "amount"),
        "COMPETITOR_ENTRY": (
            "competitor_pressure", "competitor_pressure_override", "pressure"
        ),
    }
    if event.type in economic_fields:
        global_field, override_field, payload_field = economic_fields[event.type]
        value = event.payload[payload_field]
        if event.target.kind == "all" and event.reach == 1:
            before = getattr(world.global_state, global_field)
            setattr(world.global_state, global_field, value)
            state_delta(simulation, "world", global_field, before, value, f"event:{event.id}")
            # A subsequent universal condition supersedes previous local offers.
            for agent in sorted(world.agents, key=lambda item: item.id):
                before = getattr(agent.state, override_field)
                setattr(agent.state, override_field, None)
                state_delta(simulation, f"agent:{agent.id}", override_field, before, None,
                            f"event:{event.id}")
        else:
            for agent in recipients:
                before = getattr(agent.state, override_field)
                setattr(agent.state, override_field, value)
                state_delta(simulation, f"agent:{agent.id}", override_field, before, value,
                            f"event:{event.id}")
    elif event.type == "NEWS":
        for agent in recipients:
            before_sentiment, before_trust = agent.state.sentiment, agent.state.trust
            agent.state.sentiment = _clamp(
                agent.state.sentiment + event.payload.get("sentiment_delta", 0.0),
                -1.0, 1.0,
            )
            agent.state.trust = _clamp(
                agent.state.trust + event.payload.get("trust_delta", 0.0)
            )
            state_delta(simulation, f"agent:{agent.id}", "sentiment", before_sentiment,
                        agent.state.sentiment, f"event:{event.id}", contributions=[
                            {"mechanism": "news_sentiment", "value": event.payload.get("sentiment_delta", 0.0)}])
            state_delta(simulation, f"agent:{agent.id}", "trust", before_trust,
                        agent.state.trust, f"event:{event.id}", contributions=[
                            {"mechanism": "news_trust", "value": event.payload.get("trust_delta", 0.0)}])
    elif event.type == "TRUST_SHOCK":
        for agent in recipients:
            before = agent.state.trust
            agent.state.trust = _clamp(
                agent.state.trust + event.payload["trust_delta"]
            )
            state_delta(simulation, f"agent:{agent.id}", "trust", before, agent.state.trust,
                        f"event:{event.id}", contributions=[
                            {"mechanism": "trust_shock", "value": event.payload["trust_delta"]}])
    for agent in recipients:
        before_memory = len(agent.memory)
        agent.memory.append(Memory(
            tick=world.current_tick,
            kind="event",
            payload={"event_id": event.id, "type": event.type,
                     "payload": deepcopy(event.payload)},
        ))
        state_delta(simulation, f"agent:{agent.id}", "memory.length", before_memory,
                    len(agent.memory), f"event:{event.id}")
    # Count an occurrence once even when its reach selects no recipients.
    world.event_log.append(EventRecord(
        tick=world.current_tick,
        event_id=event.id,
        target_ids=[agent.id for agent in recipients],
    ))


def _relationship_weight(relationship: Relationship, peer: Agent) -> float:
    return (relationship.trust * relationship.influence * relationship.strength
            * peer.traits.influence)


def _peer_adoption(
    agent: Agent,
    by_id: dict[str, Agent],
    observed: dict[str, AgentState],
) -> float:
    weights = []
    adopted_weights = []
    for relationship in sorted(agent.relationships,
                               key=lambda item: item.target_agent_id):
        peer_id = relationship.target_agent_id
        if not observed[peer_id].active:
            continue
        weight = _relationship_weight(relationship, by_id[peer_id])
        weights.append(weight)
        adopted_weights.append(weight * observed[peer_id].adopted)
    # Retain edge magnitude when total influence is small, while bounding it.
    return sum(adopted_weights) / max(1.0, sum(weights))


def _effective_value(override: float | None, global_value: float) -> float:
    return global_value if override is None else override


def _decide(
    agent: Agent,
    simulation: Simulation,
    by_id: dict[str, Agent],
    observed: dict[str, AgentState],
    generator: SeededRandom,
) -> None:
    configuration = simulation.configuration
    previous = observed[agent.id]
    global_state = simulation.world.global_state
    price = _effective_value(previous.price_override, global_state.price)
    incentive = _effective_value(previous.incentive_override, global_state.incentive)
    competitor = _effective_value(
        previous.competitor_pressure_override, global_state.competitor_pressure
    )
    # One noise sample per active agent, including zero amplitude, fixes draw
    # count across adoption outcomes and offer interventions.
    noise = (2.0 * generator.random() - 1.0) * configuration.noise
    peer_adoption = _peer_adoption(agent, by_id, observed)
    score = _clamp(
        0.20
        + 0.30 * agent.traits.openness
        + 0.10 * agent.traits.risk_tolerance
        + 0.25 * previous.trust
        + 0.10 * previous.sentiment
        + configuration.peer_weight * agent.traits.conformity
        * peer_adoption
        - 0.30 * agent.traits.price_sensitivity
        * max(0.0, price - incentive) / configuration.price_scale
        - 0.15 * competitor
        + noise
    )
    agent.state.adoption_intent = _clamp(
        0.55 * previous.adoption_intent + 0.45 * score
    )
    agent.state.adopted = agent.state.adoption_intent >= configuration.adoption_threshold
    agent.state.sentiment = _clamp(
        previous.sentiment * configuration.sentiment_decay, -1.0, 1.0
    )
    if simulation.audit is not None:
        components = {
            "baseline": 0.20,
            "openness": 0.30 * agent.traits.openness,
            "risk_tolerance": 0.10 * agent.traits.risk_tolerance,
            "trust": 0.25 * previous.trust,
            "sentiment": 0.10 * previous.sentiment,
            "social": configuration.peer_weight * agent.traits.conformity * peer_adoption,
            "price": -0.30 * agent.traits.price_sensitivity * max(0.0, price - incentive) / configuration.price_scale,
            "competitor": -0.15 * competitor,
            "noise": noise,
        }
        peers = [
            {"source_agent_id": relation.target_agent_id,
             "weight": _relationship_weight(relation, by_id[relation.target_agent_id]),
             "observed_adopted": observed[relation.target_agent_id].adopted}
            for relation in sorted(agent.relationships, key=lambda r: r.target_agent_id)
            if observed[relation.target_agent_id].active
        ]
        record(simulation, "adoption_decision", f"agent:{agent.id}", "adoption_model",
               {"before": previous.adopted, "after": agent.state.adopted,
                "intent_before": previous.adoption_intent, "intent_after": agent.state.adoption_intent,
                "score": score, "threshold": configuration.adoption_threshold,
                "components": components, "peers": peers,
                "intent_contributions": {"previous_intent": 0.55 * previous.adoption_intent,
                                         "score": 0.45 * score}})
        state_delta(simulation, f"agent:{agent.id}", "adoption_intent", previous.adoption_intent,
                    agent.state.adoption_intent, "adoption_model", contributions=[
                        {"mechanism": mechanism, "score_value": value}
                        for mechanism, value in components.items()])
        state_delta(simulation, f"agent:{agent.id}", "adopted", previous.adopted,
                    agent.state.adopted, "adoption_threshold")
        state_delta(simulation, f"agent:{agent.id}", "sentiment", previous.sentiment,
                    agent.state.sentiment, "sentiment_decay")
    if agent.state.adopted != previous.adopted:
        before_memory = len(agent.memory)
        agent.memory.append(Memory(
            tick=simulation.world.current_tick,
            kind="adoption",
            payload={"adopted": agent.state.adopted,
                     "intent": agent.state.adoption_intent, "score": score},
        ))
        state_delta(simulation, f"agent:{agent.id}", "memory.length", before_memory,
                    len(agent.memory), "adoption_memory")


def _interact(
    simulation: Simulation,
    active: list[Agent],
    by_id: dict[str, Agent],
    observed: dict[str, AgentState],
    generator: SeededRandom,
) -> int:
    interactions = 0
    configuration = simulation.configuration
    for agent in active:
        trust_delta = 0.0
        sentiment_delta = 0.0
        contributions = []
        for relationship in sorted(agent.relationships,
                                   key=lambda item: item.target_agent_id):
            peer = by_id[relationship.target_agent_id]
            previous_peer = observed[peer.id]
            if not previous_peer.active:
                continue
            interaction_rng = (RandomStreams(simulation.seed).stream(
                "interactions", simulation.world.current_tick, agent.id, peer.id
            ) if simulation.audit else generator)
            if not interaction_rng.probability(configuration.interaction_probability):
                continue
            interactions += 1
            weight = _relationship_weight(relationship, peer)
            sentiment_delta += 0.04 * weight * previous_peer.sentiment
            trust_delta += 0.02 * weight * previous_peer.sentiment
            if simulation.audit is not None:
                contribution = {"mechanism": "social_interaction", "source_agent_id": peer.id,
                                "trust": 0.02 * weight * previous_peer.sentiment,
                                "sentiment": 0.04 * weight * previous_peer.sentiment}
                contributions.append(contribution)
                record(simulation, "interaction_created", f"agent:{agent.id}", "interaction_selection",
                       {"source_agent_id": agent.id, "target_agent_id": peer.id,
                        "observed_adopted": previous_peer.adopted,
                        "observed_sentiment": previous_peer.sentiment})
                record(simulation, "influence_applied", f"agent:{agent.id}", "social_interaction",
                       {**contribution, "weight": weight})
            agreement = 1.0 if agent.state.adopted == peer.state.adopted else -1.0
            before_relationship = relationship.trust
            relationship.trust = _clamp(
                relationship.trust + configuration.trust_learning_rate * agreement
            )
            state_delta(simulation, f"relationship:{agent.id}->{peer.id}", "trust",
                        before_relationship, relationship.trust, "relationship_learning",
                        kind="relationship_changed", source_agent_id=agent.id, target_agent_id=peer.id, contributions=[
                            {"mechanism": "adoption_agreement", "value": configuration.trust_learning_rate * agreement}])
            before_memory = len(agent.memory)
            agent.memory.append(Memory(
                tick=simulation.world.current_tick,
                kind="interaction",
                payload={"target_agent_id": peer.id,
                         "observed_adopted": previous_peer.adopted,
                         "observed_sentiment": previous_peer.sentiment},
            ))
            state_delta(simulation, f"agent:{agent.id}", "memory.length", before_memory,
                        len(agent.memory), "interaction_memory")
        before_trust, before_sentiment = agent.state.trust, agent.state.sentiment
        agent.state.trust = _clamp(agent.state.trust + trust_delta)
        agent.state.sentiment = _clamp(
            agent.state.sentiment + sentiment_delta, -1.0, 1.0
        )
        state_delta(simulation, f"agent:{agent.id}", "trust", before_trust, agent.state.trust,
                    "social_interaction", contributions=contributions)
        state_delta(simulation, f"agent:{agent.id}", "sentiment", before_sentiment, agent.state.sentiment,
                    "social_interaction", contributions=contributions)
    return interactions


def tick(simulation: Simulation) -> Simulation:
    """Commit one tick, or raise without changing the caller's simulation."""
    validate_simulation(simulation)
    if simulation.status == "completed":
        raise ValueError("cannot tick a completed simulation")
    result = deepcopy(simulation)
    generator = SeededRandom.from_state(result.rng_state)
    world = result.world
    executed_tick = world.current_tick
    record(result, "tick_started", "world", "tick", {"active_count": len(_active_agents(world)),
                                                      "tick_unit": result.configuration.tick_unit})
    due_events = sorted(
        (event for event in world.events if event.tick == world.current_tick),
        key=lambda event: event.id,
    )
    for event in due_events:
        validate_event(event, world)
        _apply_event(event, world, generator, result)
    active = _active_agents(world)
    by_id = {agent.id: agent for agent in world.agents}
    observed = {agent.id: deepcopy(agent.state) for agent in world.agents}
    for agent in active:
        decision_rng = (RandomStreams(result.seed).stream("decisions", executed_tick, agent.id)
                        if result.audit else generator)
        _decide(agent, result, by_id, observed, decision_rng)
    interactions = _interact(result, active, by_id, observed, generator)
    result.metrics = _collect_metrics(
        world, result.metrics.interaction_count + interactions
    )
    world.current_tick += 1
    result.rng_state = generator.state
    result.status = "running"
    record(result, "tick_completed", "world", "tick", {"metrics": asdict(result.metrics),
           "active_count": len(active), "state_tick": world.current_tick}, tick=executed_tick)
    commit_frame(result, executed_tick)
    validate_simulation(result)
    return result


def run_ticks(simulation: Simulation, count: int) -> Simulation:
    """Run a nonnegative number of atomic transitions on independent state."""
    if type(count) is not int or count < 0:
        raise ValueError("tick count must be a nonnegative integer")
    validate_simulation(simulation)
    if count and simulation.status == "completed":
        raise ValueError("cannot run ticks on a completed simulation")
    result = deepcopy(simulation)
    for _ in range(count):
        result = tick(result)
    return result
