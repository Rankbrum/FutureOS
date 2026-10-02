"""Deterministic directed social ties using the existing engine contracts."""

from __future__ import annotations

from copy import deepcopy
import math

from .models import Agent, Relationship
from .randomness import SeededRandom

VALID_POLICIES = {"random_sparse", "clustered", "influencer_centered"}


def validate_relationship_policy(spec) -> str:
    """Reject malformed policies before any generation, including empty lists."""
    raw = spec.relationship_policy
    if type(raw) is str:
        policy = raw
        config = {}
    elif type(raw) is dict:
        policy = raw.get("type", raw.get("policy"))
        if "type" in raw and "policy" in raw and raw["type"] != raw["policy"]:
            raise ValueError("relationship_policy type and policy disagree")
        config = raw
    else:
        raise ValueError("relationship_policy must be a policy name or object")
    if type(policy) is not str or policy not in VALID_POLICIES | {"uniform"}:
        raise ValueError(f"unknown relationship_policy: {policy!r}")
    allowed = {"type", "policy"}
    if policy in VALID_POLICIES:
        allowed.add("average_degree")
    if policy == "clustered":
        allowed.add("within_cluster_probability")
    if policy == "influencer_centered":
        allowed.add("influencer_fraction")
    unknown = set(config) - allowed
    if unknown:
        raise ValueError(f"unsupported relationship_policy fields: {sorted(unknown)!r}")
    for field in ("average_degree", "within_cluster_probability", "influencer_fraction"):
        if field not in config:
            continue
        value = config[field]
        try:
            finite = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite or value < 0 or (field != "average_degree" and value > 1):
            limit = ">= 0" if field == "average_degree" else "in [0, 1]"
            raise ValueError(f"relationship_policy {field} must be finite numeric {limit}")
    return policy


def _append_relationship(agent: Agent, target: str, rng: SeededRandom) -> None:
    agent.relationships.append(Relationship(
        target_agent_id=target,
        trust=0.3 + 0.4 * rng.random(),
        influence=0.3 + 0.4 * rng.random(),
        strength=0.3 + 0.4 * rng.random(),
    ))


def generate_relationships(agents: list[Agent], spec,
                           seed: int | None = None) -> list[Agent]:
    """Return an independent population; input order does not change ties.

    uniform is the legacy no-generation policy and preserves supplied ties.
    Other policies replace ties with a fresh graph without changing traits.
    """
    policy = validate_relationship_policy(spec)
    rng = SeededRandom(0 if seed is None else seed)
    if type(agents) is not list or any(not isinstance(agent, Agent) for agent in agents):
        raise ValueError("agents must be a list of Agent")
    if len({agent.id for agent in agents}) != len(agents):
        raise ValueError("duplicate agent id in relationship population")
    result = deepcopy(agents)
    if policy == "uniform" or not result:
        return result
    for agent in result:
        agent.relationships = []
    sorted_agents = sorted(result, key=lambda item: item.id)
    by_id = {agent.id: agent for agent in sorted_agents}
    ids = list(by_id)
    config = spec.relationship_policy if type(spec.relationship_policy) is dict else {}
    default_degree = 4 if policy == "clustered" else 3
    average_degree = config.get("average_degree", default_degree)
    degree = min(len(ids) - 1, round(average_degree))

    for agent in sorted_agents:
        others = [target for target in ids if target != agent.id]
        if degree == 0:
            continue
        if policy == "clustered":
            cluster = agent.metadata.get("archetype_id", "default")
            intra = rng.shuffle([target for target in others
                                 if by_id[target].metadata.get("archetype_id", "default") == cluster])
            inter = rng.shuffle([target for target in others
                                 if by_id[target].metadata.get("archetype_id", "default") != cluster])
            within = config.get("within_cluster_probability", 0.8)
            intra_count = min(len(intra), round(degree * within))
            picked = intra[:intra_count] + inter[:degree - intra_count]
            # If a preferred cluster is too small, use remaining candidates.
            selected = set(picked)
            picked.extend(target for target in intra + inter if target not in selected)
            picked = picked[:degree]
        else:
            picked = rng.shuffle(others)[:degree]
        for target in picked:
            _append_relationship(agent, target, rng)

    if policy == "influencer_centered" and degree:
        fraction = config.get("influencer_fraction", 0.1)
        count = min(len(ids), max(1, round(len(ids) * fraction))) if fraction else 0
        influencers = sorted(sorted_agents, key=lambda agent: (-agent.traits.influence, agent.id))[:count]
        capacity = min(len(ids) - 1,
                       max(degree, round(min(average_degree, len(ids) - 1) * 1.2)))
        for influencer in sorted(influencers, key=lambda agent: agent.id):
            for agent in sorted_agents:
                targets = {relation.target_agent_id for relation in agent.relationships}
                if (agent.id != influencer.id and influencer.id not in targets
                        and len(targets) < capacity):
                    _append_relationship(agent, influencer.id, rng)
    return result
