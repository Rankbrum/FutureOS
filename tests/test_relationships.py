"""Graph policies, input isolation and deterministic ordering."""

from copy import deepcopy
from dataclasses import asdict
import unittest

from futureos.models import Agent, Relationship, Traits
from futureos.population_generator import generate_population_with_relationships
from futureos.population_spec import Archetype, PopulationSpec
from futureos.relationship_generator import generate_relationships, validate_relationship_policy


def graph_spec(policy, size=10):
    return PopulationSpec(size, [Archetype("a", 0.5, Traits(influence=0.9)),
                                 Archetype("b", 0.5, Traits(influence=0.2))],
                          relationship_policy=policy)


class RelationshipGeneratorTests(unittest.TestCase):
    def assert_valid_graph(self, agents):
        ids = {agent.id for agent in agents}
        for agent in agents:
            targets = [relation.target_agent_id for relation in agent.relationships]
            self.assertNotIn(agent.id, targets)
            self.assertEqual(len(targets), len(set(targets)))
            self.assertTrue(set(targets).issubset(ids))
            for relation in agent.relationships:
                for field in ("trust", "influence", "strength"):
                    self.assertTrue(0 <= getattr(relation, field) <= 1)

    def test_all_policies_produce_valid_deterministic_graphs(self):
        for policy in ("random_sparse", "clustered", "influencer_centered"):
            with self.subTest(policy=policy):
                first = generate_population_with_relationships(graph_spec(policy), 2026)
                second = generate_population_with_relationships(graph_spec(policy), 2026)
                self.assertEqual(first, second)
                self.assert_valid_graph(first)
                self.assertTrue(all(agent.relationships for agent in first))

    def test_sparse_degree_is_clipped_to_available_peers(self):
        agents = generate_population_with_relationships(
            graph_spec({"type": "random_sparse", "average_degree": 100}, size=4), 1)
        self.assertTrue(all(len(agent.relationships) == 3 for agent in agents))
        self.assert_valid_graph(agents)

    def test_extreme_finite_influencer_degree_is_clipped_without_overflow(self):
        agents = generate_population_with_relationships(graph_spec({
            "type": "influencer_centered", "average_degree": 1.79e308,
        }, size=4), 2026)
        self.assertTrue(all(len(agent.relationships) == 3 for agent in agents))
        self.assert_valid_graph(agents)

    def test_zero_degree_has_no_edges_for_all_policies(self):
        for policy in ("random_sparse", "clustered", "influencer_centered"):
            agents = generate_population_with_relationships(
                graph_spec({"type": policy, "average_degree": 0}), 2)
            self.assertTrue(all(not agent.relationships for agent in agents))

    def test_single_agent_has_no_edges(self):
        for policy in ("random_sparse", "clustered", "influencer_centered"):
            agents = generate_population_with_relationships(graph_spec(policy, size=1), 3)
            self.assertEqual(len(agents), 1)
            self.assertEqual(agents[0].relationships, [])

    def test_cluster_probability_one_prefers_same_archetype(self):
        agents = generate_population_with_relationships(graph_spec({
            "type": "clustered", "average_degree": 3, "within_cluster_probability": 1,
        }), 4)
        clusters = {agent.id: agent.metadata["archetype_id"] for agent in agents}
        self.assertTrue(all(clusters[relation.target_agent_id] == clusters[agent.id]
                            for agent in agents for relation in agent.relationships))

    def test_cluster_probability_zero_prefers_other_archetypes(self):
        agents = generate_population_with_relationships(graph_spec({
            "type": "clustered", "average_degree": 3, "within_cluster_probability": 0,
        }), 5)
        clusters = {agent.id: agent.metadata["archetype_id"] for agent in agents}
        self.assertTrue(all(clusters[relation.target_agent_id] != clusters[agent.id]
                            for agent in agents for relation in agent.relationships))

    def test_cluster_shortage_fills_degree_from_remaining_peers(self):
        agents = generate_population_with_relationships(graph_spec({
            "type": "clustered", "average_degree": 7, "within_cluster_probability": 1,
        }), 6)
        self.assertTrue(all(len(agent.relationships) == 7 for agent in agents))
        self.assert_valid_graph(agents)

    def test_influencer_centered_adds_incoming_links_with_capacity(self):
        policy = {"type": "influencer_centered", "average_degree": 3, "influencer_fraction": 0.1}
        agents = generate_population_with_relationships(graph_spec(policy, size=20), 2026)
        self.assert_valid_graph(agents)
        self.assertTrue(all(3 <= len(agent.relationships) <= 4 for agent in agents))
        influencers = {"agent-001", "agent-002"}
        incoming = sum(relation.target_agent_id in influencers
                       for agent in agents for relation in agent.relationships)
        self.assertGreater(incoming, 12)

    def test_input_order_does_not_change_relationships(self):
        spec = graph_spec("clustered")
        agents = generate_population_with_relationships(spec, 7)
        forward = generate_relationships(agents, spec, seed=8)
        backward = generate_relationships(list(reversed(agents)), spec, seed=8)
        self.assertEqual({agent.id: asdict(agent) for agent in forward},
                         {agent.id: asdict(agent) for agent in backward})

    def test_return_does_not_share_nested_mutable_state(self):
        spec = graph_spec("random_sparse", size=2)
        agents = [Agent("a", metadata={"nested": [1]}), Agent("b")]
        original = deepcopy(agents)
        generated = generate_relationships(agents, spec, seed=9)
        generated[0].traits.openness = 0
        generated[0].state.trust = 0
        generated[0].metadata["nested"].append(2)
        self.assertEqual(agents, original)

    def test_uniform_preserves_existing_ties_as_independent_copy(self):
        agents = [Agent("a", relationships=[Relationship("b")]), Agent("b")]
        copied = generate_relationships(agents, graph_spec("uniform", size=2), seed=10)
        self.assertEqual(copied, agents)
        copied[0].relationships[0].trust = 0
        self.assertEqual(agents[0].relationships[0].trust, 0.5)

    def test_uniform_pipeline_starts_without_fixture_ring(self):
        agents = generate_population_with_relationships(graph_spec("uniform"), 11)
        self.assertTrue(all(not agent.relationships for agent in agents))

    def test_invalid_policy_is_checked_even_for_empty_input(self):
        spec = graph_spec("invented")
        with self.assertRaisesRegex(ValueError, "unknown relationship_policy"):
            generate_relationships([], spec, seed=12)

    def test_invalid_parameters_raise_clear_errors(self):
        invalid = [
            {}, {"type": "random_sparse", "average_degree": -1},
            {"type": "random_sparse", "average_degree": True},
            {"type": "random_sparse", "average_degree": float("nan")},
            {"type": "clustered", "within_cluster_probability": 1.1},
            {"type": "influencer_centered", "influencer_fraction": "high"},
            {"type": "random_sparse", "invented": 1},
            {"type": "uniform", "policy": "clustered"},
        ]
        for policy in invalid:
            with self.subTest(policy=policy):
                with self.assertRaises(ValueError):
                    validate_relationship_policy(graph_spec(policy))

    def test_duplicate_agent_ids_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate agent id"):
            generate_relationships([Agent("a"), Agent("a")], graph_spec("random_sparse"), seed=13)


if __name__ == "__main__":
    unittest.main()
