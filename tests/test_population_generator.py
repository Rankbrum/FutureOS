"""PopulationSpec materialization, RNG boundaries and engine integration."""

from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

from futureos.audit import final_state_hash
from futureos.engine import run_ticks
from futureos.models import Traits
from futureos.population_generator import (
    create_simulation_from_population_spec,
    generate_population,
    generate_population_with_relationships,
    generate_traits,
)
from futureos.population_spec import Archetype, PopulationSpec
from futureos.population_validation import PopulationSpecValidationError
from futureos.randomness import SeededRandom
from futureos.validation import validate_simulation


def example_spec(size=8, relationship_policy="random_sparse"):
    return PopulationSpec(
        size=size,
        archetypes=[
            Archetype("early", 0.6, Traits(openness=0.8, influence=0.8),
                      metadata={"nested": {"labels": ["synthetic"]}}),
            Archetype("price_sensitive", 0.4, Traits(price_sensitivity=0.8)),
        ],
        relationship_policy=relationship_policy,
        trait_distributions={
            "risk_tolerance": {"type": "uniform", "min": 0.2, "max": 0.7},
            "conformity": {"type": "bounded_normal", "mean": 0.6,
                           "spread": 0.2, "min": 0.1, "max": 0.9},
        },
        assumptions=["Synthetic uncalibrated population."],
        warnings=["SYNTHETIC_POPULATION", "UNCALIBRATED_POPULATION"],
    )


class PopulationGeneratorTests(unittest.TestCase):
    def test_same_spec_and_seed_reproduce_all_agents_and_relationships(self):
        spec = example_spec()
        first = generate_population_with_relationships(spec, 2026)
        second = generate_population_with_relationships(spec, 2026)
        self.assertEqual(first, second)
        self.assertEqual(json.dumps([asdict(agent) for agent in first], sort_keys=True),
                         json.dumps([asdict(agent) for agent in second], sort_keys=True))

    def test_different_seeds_change_stochastic_traits(self):
        self.assertNotEqual(generate_population(example_spec(), 2026),
                            generate_population(example_spec(), 2027))

    def test_largest_remainder_exact_size_and_weights(self):
        agents = generate_population(example_spec(size=8), 2026)
        self.assertEqual(len(agents), 8)
        self.assertEqual(Counter(agent.metadata["archetype_id"] for agent in agents),
                         {"early": 5, "price_sensitive": 3})

    def test_largest_remainder_ties_use_archetype_id(self):
        spec = PopulationSpec(5, [Archetype("b", 0.5), Archetype("a", 0.5)])
        agents = generate_population(spec, 1)
        self.assertEqual([agent.metadata["archetype_id"] for agent in agents],
                         ["a", "a", "a", "b", "b"])
        reversed_spec = deepcopy(spec)
        reversed_spec.archetypes.reverse()
        self.assertEqual(agents, generate_population(reversed_spec, 1))

    def test_weight_sum_within_epsilon_allocates_without_mutating_weights(self):
        spec = PopulationSpec(101, [Archetype("a", 0.495), Archetype("b", 0.5)])
        original = deepcopy(spec)
        agents = generate_population(spec, 2)
        self.assertEqual(len(agents), 101)
        self.assertEqual(spec, original)
        self.assertEqual(Counter(agent.metadata["archetype_id"] for agent in agents),
                         {"a": 50, "b": 51})

    def test_numeric_archetype_defaults_and_global_fixed_override(self):
        spec = PopulationSpec(2, [Archetype("a", 1, Traits(openness=0.83))],
                              trait_distributions={"influence": {"type": "fixed", "value": 0.25}})
        agents = generate_population(spec, 3)
        self.assertTrue(all(agent.traits.openness == 0.83 for agent in agents))
        self.assertTrue(all(agent.traits.risk_tolerance == 0.5 for agent in agents))
        self.assertTrue(all(agent.traits.influence == 0.25 for agent in agents))
        self.assertIsNot(agents[0].traits, agents[1].traits)
        self.assertIsNot(agents[0].traits, spec.archetypes[0].traits)

    def test_uniform_and_bounded_normal_respect_declared_bounds(self):
        agents = generate_population(example_spec(size=300), 4)
        self.assertTrue(all(0.2 <= agent.traits.risk_tolerance <= 0.7 for agent in agents))
        self.assertTrue(all(0.1 <= agent.traits.conformity <= 0.9 for agent in agents))

    def test_fixed_and_degenerate_distributions_consume_zero_draws(self):
        rng = SeededRandom(2026)
        traits = generate_traits(Traits(), {
            "openness": {"type": "fixed", "value": 0.9},
            "risk_tolerance": {"type": "uniform", "min": 0.1, "max": 0.1},
            "influence": {"type": "bounded_normal", "mean": 0.7, "spread": 0},
        }, rng)
        self.assertEqual(rng.state.draws, 0)
        self.assertEqual(traits.openness, 0.9)
        self.assertEqual(traits.risk_tolerance, 0.1)
        self.assertEqual(traits.influence, 0.7)

    def test_fixed_population_makes_no_rng_draws(self):
        spec = PopulationSpec(8, [Archetype("a", 1)])
        with patch.object(SeededRandom, "random", side_effect=AssertionError("unexpected draw")):
            agents = generate_population(spec, 2026)
        self.assertEqual(len(agents), 8)

    def test_metadata_and_ids_are_stable(self):
        agents = generate_population(example_spec(), 5)
        self.assertEqual([agent.id for agent in agents], [f"agent-{i:03d}" for i in range(1, 9)])
        self.assertTrue(all(agent.metadata["source"] == "manual" for agent in agents))
        self.assertEqual(agents[0].metadata["nested"], {"labels": ["synthetic"]})

    def test_generation_does_not_mutate_spec_or_share_nested_metadata(self):
        spec = example_spec()
        original = deepcopy(spec)
        agents = generate_population_with_relationships(spec, 2026)
        self.assertEqual(spec, original)
        agents[0].metadata["nested"]["labels"].append("changed")
        agents[0].traits.openness = 0
        self.assertEqual(spec, original)
        self.assertEqual(agents[1].metadata["nested"]["labels"], ["synthetic"])

    def test_relationship_policy_never_changes_traits(self):
        spec = example_spec()
        baseline = [agent.traits for agent in generate_population(spec, 2026)]
        for policy in ("uniform", "random_sparse", "clustered", "influencer_centered"):
            spec.relationship_policy = policy
            self.assertEqual([agent.traits for agent in generate_population_with_relationships(spec, 2026)],
                             baseline)

    def test_relationship_consumption_isolated_from_trait_generation(self):
        spec = example_spec()
        small = generate_population_with_relationships(spec, 2026)
        spec.relationship_policy = {"type": "random_sparse", "average_degree": 7}
        dense = generate_population_with_relationships(spec, 2026)
        self.assertEqual([agent.traits for agent in small], [agent.traits for agent in dense])
        self.assertNotEqual([agent.relationships for agent in small], [agent.relationships for agent in dense])

    def test_trait_draw_consumption_does_not_change_sparse_relationships(self):
        spec = example_spec()
        stochastic = generate_population_with_relationships(spec, 2026)
        spec.trait_distributions = {"openness": {"type": "fixed", "value": 0.7}}
        fixed = generate_population_with_relationships(spec, 2026)
        self.assertNotEqual([agent.traits for agent in stochastic], [agent.traits for agent in fixed])
        self.assertEqual([agent.relationships for agent in stochastic], [agent.relationships for agent in fixed])

    def test_invalid_spec_fails_before_rng_construction(self):
        spec = example_spec()
        spec.archetypes[0].weight = 0.1
        with patch("futureos.population_generator.SeededRandom") as rng:
            with self.assertRaises(PopulationSpecValidationError):
                generate_population(spec, 2026)
            rng.assert_not_called()

    def test_unknown_relationship_policy_is_not_silently_ignored(self):
        spec = example_spec()
        spec.relationship_policy = "invented"
        with self.assertRaises(PopulationSpecValidationError):
            generate_population_with_relationships(spec, 2026)

    def test_manual_mode_reaches_real_engine_and_five_ticks(self):
        spec = example_spec()
        initial = create_simulation_from_population_spec(spec, 2026,
                                                         simulation_id="manual", world_id="manual-world")
        validate_simulation(initial)
        self.assertEqual(initial.id, "manual")
        self.assertEqual(initial.world.id, "manual-world")
        self.assertEqual(initial.rng_state.draws, 0)
        self.assertEqual(initial.audit.mode, "summary")
        final = run_ticks(initial, 5)
        validate_simulation(final)
        self.assertEqual(initial.world.current_tick, 0)
        self.assertEqual(final.world.current_tick, 5)
        self.assertEqual(len(final.world.agents), 8)
        self.assertEqual(len(final.audit.frames), 5)
        self.assertTrue(0 <= final.metrics.adoption_rate <= 1)
        self.assertEqual(final.world.metadata["population_spec"]["warnings"], spec.warnings)

    def test_same_reviewed_json_and_seed_reproduce_simulation_hashes(self):
        spec = example_spec()
        reviewed = PopulationSpec.from_json(json.dumps(spec.to_json()))
        first = run_ticks(create_simulation_from_population_spec(spec, 2026), 5)
        second = run_ticks(create_simulation_from_population_spec(reviewed, 2026), 5)
        self.assertEqual(final_state_hash(first), final_state_hash(second))
        self.assertEqual(first.audit.trajectory_hash, second.audit.trajectory_hash)
        self.assertEqual(first.audit.event_trace_hash, second.audit.event_trace_hash)

    def test_summary_and_trace_keep_behavior_and_hashes_equal(self):
        spec = example_spec()
        summary = run_ticks(create_simulation_from_population_spec(spec, 2026), 5)
        trace = run_ticks(create_simulation_from_population_spec(spec, 2026, audit_mode="trace"), 5)
        self.assertEqual(summary.world, trace.world)
        self.assertEqual(summary.metrics, trace.metrics)
        self.assertEqual(final_state_hash(summary), final_state_hash(trace))
        self.assertEqual(summary.audit.trajectory_hash, trace.audit.trajectory_hash)
        self.assertEqual(summary.audit.event_trace_hash, trace.audit.event_trace_hash)


if __name__ == "__main__":
    unittest.main()
