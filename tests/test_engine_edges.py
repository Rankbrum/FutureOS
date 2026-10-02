"""Boundary guarantees not exercised by the main behavioral scenarios."""

from copy import deepcopy
from threading import Lock
import unittest

from futureos.engine import create_simulation, run_ticks, schedule_event, tick
from futureos.models import Configuration, Event, World
from futureos.population import create_population
from futureos.randomness import SeededRandom


def fixture(configuration=None):
    rng = SeededRandom(123)
    world = World("edge-world", agents=create_population(8, rng))
    return create_simulation(
        "edge-run", 123, world, configuration, rng_state=rng.state
    )


def economic_and_social_events(reach):
    return [
        Event("price", "PRICE_CHANGE", 0, {"price": 1.0}, reach=reach),
        Event("incentive", "INCENTIVE", 0, {"amount": 70.0}, reach=reach),
        Event("competitor", "COMPETITOR_ENTRY", 0, {"pressure": 0.7}, reach=reach),
        Event("news", "NEWS", 0, {"sentiment_delta": 0.5}, reach=reach),
        Event("shock", "TRUST_SHOCK", 0, {"trust_delta": -0.4}, reach=reach),
    ]


class EngineBoundaryTests(unittest.TestCase):
    def test_invalid_uncopyable_metadata_fails_with_validation_message(self):
        invalid = World("bad-world", metadata={"invalid": Lock()})
        with self.assertRaisesRegex(ValueError, "not a JSON value"):
            create_simulation("bad-run", 1, invalid)
        self.assertEqual(invalid.current_tick, 0)
        self.assertIn("invalid", invalid.metadata)

    def test_excessive_metadata_depth_is_rejected_before_copying(self):
        metadata = {}
        for _ in range(1200):
            metadata = {"nested": metadata}
        with self.assertRaisesRegex(ValueError, "maximum JSON depth"):
            create_simulation("bad-run", 1, World("bad-world", metadata=metadata))

    def test_agent_and_relationship_collection_order_does_not_change_outcomes(self):
        original = fixture()
        reordered = deepcopy(original)
        reordered.world.agents.reverse()
        for agent in reordered.world.agents:
            agent.relationships.reverse()
        first = run_ticks(original, 9)
        second = run_ticks(reordered, 9)
        self.assertEqual(first.rng_state, second.rng_state)
        self.assertEqual(first.metrics, second.metrics)
        self.assertEqual(first.world.event_log, second.world.event_log)
        first_agents = {agent.id: agent for agent in first.world.agents}
        for agent in second.world.agents:
            expected = first_agents[agent.id]
            self.assertEqual(agent.state, expected.state)
            self.assertEqual(agent.memory, expected.memory)
            self.assertEqual(
                {edge.target_agent_id: edge for edge in agent.relationships},
                {edge.target_agent_id: edge for edge in expected.relationships},
            )

    def test_all_event_types_with_zero_reach_preserve_behavior_and_rng(self):
        original = fixture(Configuration(noise=0, interaction_probability=0))
        baseline = tick(original)
        scheduled = original
        for event in economic_and_social_events(0):
            scheduled = schedule_event(scheduled, event)
        result = tick(scheduled)
        self.assertEqual(result.world.global_state, baseline.world.global_state)
        self.assertEqual(result.world.agents, baseline.world.agents)
        self.assertEqual(result.rng_state, baseline.rng_state)
        self.assertEqual(result.metrics.event_count, 5)
        self.assertTrue(all(not record.target_ids for record in result.world.event_log))

    def test_negative_reach_for_each_event_fails_without_mutating_input(self):
        original = fixture()
        before = deepcopy(original)
        for event in economic_and_social_events(-0.01):
            with self.subTest(event=event.type):
                with self.assertRaises(ValueError):
                    schedule_event(original, event)
                self.assertEqual(original, before)

    def test_completed_simulation_is_terminal_but_can_be_copied(self):
        original = fixture()
        original.status = "completed"
        before = deepcopy(original)
        with self.assertRaisesRegex(ValueError, "completed"):
            tick(original)
        with self.assertRaisesRegex(ValueError, "completed"):
            run_ticks(original, 1)
        with self.assertRaisesRegex(ValueError, "completed"):
            schedule_event(original, Event("future", "NEWS", 1, {"trust_delta": 0.1}))
        self.assertEqual(original, before)
        copied = run_ticks(original, 0)
        self.assertEqual(copied, original)
        self.assertIsNot(copied.world, original.world)

    def test_invalid_population_size_rejects_without_consuming_rng(self):
        rng = SeededRandom(2)
        before = rng.state
        for count in (0, -1, True, 2.5, "3"):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    create_population(count, rng)
                self.assertEqual(rng.state, before)


if __name__ == "__main__":
    unittest.main()
