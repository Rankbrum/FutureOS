"""Seeded, wholly synthetic fixture population with directed social ties."""

from .models import Agent, AgentState, Relationship, Traits
from .randomness import SeededRandom


def create_population(count: int, rng: SeededRandom) -> list[Agent]:
    """Create count agents; the final agent is the fixture's influencer.

At count=21 this is twenty citizens and one influencer. Draw consumption is
retained by the supplied stream, allowing callers to continue it in a run.
These distributions and the two-neighbor ring are uncalibrated assumptions.
"""
    if type(count) is not int or count < 1:
        raise ValueError("population count must be a positive integer")
    if not isinstance(rng, SeededRandom):
        raise ValueError("population rng must be a SeededRandom")
    agents = []
    for index in range(count):
        traits = Traits(
            openness=0.20 + 0.75 * rng.random(),
            risk_tolerance=0.15 + 0.75 * rng.random(),
            price_sensitivity=0.15 + 0.75 * rng.random(),
            influence=0.20 + 0.55 * rng.random(),
            conformity=0.30 + 0.65 * rng.random(),
        )
        state = AgentState(
            trust=0.35 + 0.50 * rng.random(),
            sentiment=-0.15 + 0.40 * rng.random(),
            adoption_intent=0.10 + 0.30 * rng.random(),
        )
        influencer = index == count - 1
        if influencer:
            traits.openness = 0.90
            traits.influence = 0.95
            traits.price_sensitivity = 0.20
            state.trust = 0.80
        agents.append(Agent(
            id=f"agent-{index + 1:03d}",
            traits=traits,
            state=state,
            metadata={"role": "influencer" if influencer else "citizen",
                      "group": "early" if traits.openness >= 0.6 else "late",
                      "origin": "synthetic-fixture-v1"},
        ))
    for index, agent in enumerate(agents):
        for distance in range(1, min(3, count)):
            peer = agents[(index + distance) % count]
            agent.relationships.append(Relationship(
                target_agent_id=peer.id,
                trust=0.50 + 0.40 * rng.random(),
                influence=0.50 + 0.40 * rng.random(),
                strength=0.50 + 0.40 * rng.random(),
            ))
    return agents
