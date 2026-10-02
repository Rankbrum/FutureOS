"""Materialize a validated PopulationSpec without using an LLM or the fixture.

Archetype traits provide numeric defaults; global distributions override them.
Population and relationship draws use separate, derived SplitMix64 streams.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import math

from .engine import create_simulation
from .models import Agent, Simulation, Traits, World
from .population_spec import Archetype, PopulationSpec, VALID_TRAIT_KEYS
from .population_validation import validate_population_spec
from .randomness import SeededRandom, derive_seed
from .relationship_generator import generate_relationships, validate_relationship_policy


def _sample_distribution(dist: dict, rng: SeededRandom) -> float:
    kind = dist["type"]
    if kind == "fixed":
        return dist["value"]
    lower, upper = dist.get("min", 0.0), dist.get("max", 1.0)
    if lower == upper:
        return lower
    if kind == "uniform":
        return lower + (upper - lower) * rng.random()
    if kind == "bounded_normal":
        mean = dist["mean"]
        spread = dist["spread"]
        if spread == 0:
            return mean
        # Box-Muller uses exactly two draws. Clipping makes bounds explicit
        # and avoids an unbounded rejection loop for narrow intervals.
        radius = math.sqrt(-2.0 * math.log(1.0 - rng.random()))
        sample = mean + spread * radius * math.cos(2.0 * math.pi * rng.random())
        return max(lower, min(upper, sample))
    raise ValueError(f"unsupported trait distribution: {kind!r}")


def generate_traits(traits: Traits, distributions: dict[str, dict],
                    rng: SeededRandom) -> Traits:
    """Copy numeric defaults and sample global overrides in supported-key order.

    The population boundary validates the distribution contract. Fixed and
    degenerate distributions consume no RNG draws.
    """
    values = asdict(traits)
    for name in VALID_TRAIT_KEYS:
        if name in distributions:
            values[name] = _sample_distribution(distributions[name], rng)
    return Traits(**values)


def _allocate_archetypes(spec: PopulationSpec) -> list[tuple[Archetype, int]]:
    archetypes = sorted(spec.archetypes, key=lambda item: item.id)
    total_weight = math.fsum(archetype.weight for archetype in archetypes)
    quotas = [spec.size * archetype.weight / total_weight for archetype in archetypes]
    counts = [math.floor(quota) for quota in quotas]
    remainder = spec.size - sum(counts)
    ranking = sorted(range(len(archetypes)),
                     key=lambda i: (-(quotas[i] - counts[i]), archetypes[i].id))
    for index in ranking[:remainder]:
        counts[index] += 1
    return list(zip(archetypes, counts))


def generate_population(spec: PopulationSpec, seed: int) -> list[Agent]:
    """Generate exactly size agents with stable IDs and independent traits.

    Weights accepted within validation epsilon are normalized only for integer
    allocation; the caller's spec remains unchanged. Largest-remainder ties
    use archetype IDs. No synthetic fixture influencer or ring is introduced.
    """
    validate_population_spec(spec)
    rng = SeededRandom(derive_seed(seed, "agents"))
    agents: list[Agent] = []
    for archetype, count in _allocate_archetypes(spec):
        for _ in range(count):
            metadata = deepcopy(archetype.metadata)
            metadata.update({"archetype_id": archetype.id, "source": spec.source})
            agents.append(Agent(
                id=f"agent-{len(agents) + 1:03d}",
                traits=generate_traits(archetype.traits, spec.trait_distributions, rng),
                metadata=metadata,
            ))
    return agents


def generate_population_with_relationships(spec: PopulationSpec,
                                           seed: int) -> list[Agent]:
    """Generate traits and relationships with isolated, deterministic streams."""
    agents = generate_population(spec, seed)
    policy = validate_relationship_policy(spec)
    return generate_relationships(agents, spec,
                                  seed=derive_seed(seed, "relationships", policy))


def create_simulation_from_population_spec(
    spec: PopulationSpec,
    seed: int,
    simulation_id: str = "population-simulation",
    world_id: str = "population-world",
    audit_mode: str | None = "summary",
) -> Simulation:
    """Pass a generated world to the existing, validated engine constructor.

    The complete reviewed spec is retained as JSON provenance in world metadata.
    Engine RNG starts from the root seed and is independent of generation draws.
    """
    world = World(
        id=world_id,
        agents=generate_population_with_relationships(spec, seed),
        metadata={"population_spec": spec.to_json()},
    )
    return create_simulation(simulation_id=simulation_id, seed=seed, world=world,
                             audit_mode=audit_mode)
