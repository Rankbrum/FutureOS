"""Behavioral guarantees for the synthetic, provider-free tick engine."""

from copy import deepcopy
import math
import unittest

from futureos.engine import create_simulation, run_ticks, schedule_event, tick
from futureos.models import (
    Agent,
    AgentState,
    Configuration,
    Event,
    EventTarget,
    GlobalState,
    Memory,
    Relationship,
    Traits,
    World,
)
from futureos.population import create_population
from futureos.randomness import SeededRandom


def scenario(seed: int = 41):
    """Synthetic fixture with both stochastic behavior and pending events."""
    rng = SeededRandom(seed)
    world = World(
        id="synthetic-world",
        agents=create_population(16, rng),
        events=[
            Event("news", "NEWS", 2, {"sentiment_delta": 0.4}, reach=0.55),
            Event("price", "PRICE_CHANGE", 5, {"price": 70.0}),
            Event("shock", "TRUST_SHOCK", 9, {"trust_delta": -0.2}, reach=0.7),
        ],
        metadata={"synthetic": True, "nested": {"labels": ["baseline"]}},
    )
    return create_simulation("synthetic-run", seed, world, rng_state=rng.state)


def quiet_configuration(**overrides):
    values = {
        "noise": 0.0,
        "interaction_probability": 0.0,
        "sentiment_decay": 1.0,
        "trust_learning_rate": 0.0,
    }
    values.update(overrides)
    return Configuration(**values)


def event_fixture(*, active: bool = False, count: int = 4):
    agents = [
        Agent(
            id=f"agent-{index}",
            state=AgentState(active=active),
            metadata={"group": "selected" if index % 2 == 0 else "other"},
        )
        for index in range(count)
    ]
    return create_simulation(
        "event-run", 17, World("event-world", agents=agents), quiet_configuration()
    )


class DeterminismAndTicksTests(unittest.TestCase):
    def test_same_seed_and_scenario_reproduce_complete_state(self):
        first = run_ticks(scenario(41), 14)
        second = run_ticks(scenario(41), 14)
        self.assertEqual(first, second)
        self.assertGreater(first.rng_state.draws, 0)
        self.assertTrue(first.world.event_log)
        self.assertTrue(any(agent.memory for agent in first.world.agents))

    def test_distinct_seeds_can_change_population_and_outcomes(self):
        first = run_ticks(scenario(41), 14)
        second = run_ticks(scenario(42), 14)
        self.assertNotEqual(first.world.agents, second.world.agents)
        self.assertNotEqual(first.metrics, second.metrics)

    def test_tick_and_run_ticks_advance_exactly_and_preserve_inputs(self):
        original = scenario()
        before = deepcopy(original)
        first = tick(original)
        self.assertEqual(original, before)
        self.assertEqual(first.world.current_tick, 1)
        batched = run_ticks(original, 7)
        stepped = original
        for _ in range(7):
            stepped = tick(stepped)
        self.assertEqual(batched, stepped)
        self.assertEqual(batched.world.current_tick, 7)
        self.assertEqual(original, before)
        unchanged = run_ticks(original, 0)
        self.assertEqual(unchanged, original)

    def test_creation_schedule_and_tick_do_not_share_mutable_inputs(self):
        source = World(
            "source-world",
            agents=[
                Agent(
                    "a",
                    memory=[Memory(0, "fixture", {"values": [1]})],
                    relationships=[Relationship("b")],
                    metadata={"nested": {"values": [1]}},
                ),
                Agent("b"),
            ],
            metadata={"nested": {"values": [1]}},
        )
        before_world = deepcopy(source)
        configuration = quiet_configuration()
        original = create_simulation("pure-run", 17, source, configuration)
        self.assertEqual(source, before_world)
        source.agents[0].memory[0].payload["values"].append(2)
        source.metadata["nested"]["values"].append(2)
        configuration.noise = 0.2
        self.assertEqual(original.world, before_world)
        self.assertEqual(original.configuration.noise, 0.0)
        before = deepcopy(original)
        event = Event("future", "NEWS", 3, {"trust_delta": 0.1}, metadata={"tags": [1]})
        scheduled = schedule_event(original, event)
        event.metadata["tags"].append(2)
        self.assertEqual(original, before)
        self.assertEqual(scheduled.world.events[0].metadata["tags"], [1])
        updated = tick(scheduled)
        updated.world.agents[0].memory[0].payload["values"].append(3)
        updated.world.agents[0].relationships[0].strength = 0.9
        updated.world.metadata["nested"]["values"].append(3)
        updated.world.events[0].metadata["tags"].append(3)
        self.assertEqual(original, before)
        self.assertEqual(scheduled.world.events[0].metadata["tags"], [1])
        self.assertEqual(scheduled.world.agents[0].memory[0].payload["values"], [1])
        self.assertEqual(scheduled.world.agents[0].relationships[0].strength, 0.5)

    def test_relationship_to_adopted_peer_changes_intent(self):
        observer = Agent("observer", traits=Traits(conformity=1.0))
        peer = Agent("peer", state=AgentState(adopted=True, adoption_intent=1.0))
        plain = create_simulation(
            "social", 13, World("social-world", agents=[observer, peer]),
            quiet_configuration(),
        )
        linked_world = deepcopy(plain.world)
        linked_world.agents[0].relationships = [
            Relationship("peer", trust=1.0, influence=1.0, strength=1.0)
        ]
        linked = create_simulation("social", 13, linked_world, quiet_configuration())
        self.assertGreater(
            tick(linked).world.agents[0].state.adoption_intent,
            tick(plain).world.agents[0].state.adoption_intent,
        )
        self.assertFalse(plain.world.agents[0].relationships)

    def test_agent_and_relationship_collection_order_cannot_change_tick_results(self):
        original = scenario()
        reordered = deepcopy(original)
        reordered.world.agents.reverse()
        for agent in reordered.world.agents:
            agent.relationships.reverse()
        first = run_ticks(original, 14)
        second = run_ticks(reordered, 14)
        self.assertEqual(first.rng_state, second.rng_state)
        self.assertEqual(first.metrics, second.metrics)
        self.assertEqual(first.world.event_log, second.world.event_log)
        first_agents = {agent.id: agent for agent in first.world.agents}
        second_agents = {agent.id: agent for agent in second.world.agents}
        for identifier, agent in first_agents.items():
            other = second_agents[identifier]
            self.assertEqual(agent.state, other.state)
            self.assertEqual(agent.memory, other.memory)
            self.assertEqual({relation.target_agent_id: relation for relation in agent.relationships},
                             {relation.target_agent_id: relation for relation in other.relationships})


class EventEngineTests(unittest.TestCase):
    def test_event_occurs_at_its_tick_once_and_retains_future_queue(self):
        original = event_fixture()
        event = Event("at-two", "TRUST_SHOCK", 2, {"trust_delta": -0.2})
        original = schedule_event(original, event)
        before_due = run_ticks(original, 2)
        self.assertEqual(before_due.world.current_tick, 2)
        self.assertEqual(before_due.metrics.event_count, 0)
        self.assertEqual(before_due.world.agents[0].state.trust, 0.5)
        self.assertEqual([item.id for item in before_due.world.events], ["at-two"])
        applied = tick(before_due)
        self.assertAlmostEqual(applied.world.agents[0].state.trust, 0.3)
        self.assertEqual(applied.metrics.event_count, 1)
        self.assertEqual(applied.world.event_log[0].tick, 2)
        self.assertEqual(applied.world.event_log[0].event_id, "at-two")
        continued = run_ticks(applied, 4)
        self.assertAlmostEqual(continued.world.agents[0].state.trust, 0.3)
        self.assertEqual(continued.metrics.event_count, 1)
        self.assertEqual(len(continued.world.event_log), 1)
        self.assertFalse([event for event in continued.world.events
                          if event.tick >= continued.world.current_tick])

    def test_simultaneous_events_follow_id_order_independent_of_insertion(self):
        initial = event_fixture()
        # Clamping makes event order observable: -0.9 then +0.3 gives 0.3.
        first = Event("a-negative", "TRUST_SHOCK", 0, {"trust_delta": -0.9})
        second = Event("z-positive", "TRUST_SHOCK", 0, {"trust_delta": 0.3})
        reverse = schedule_event(schedule_event(initial, second), first)
        forward = schedule_event(schedule_event(initial, first), second)
        reverse_result = tick(reverse)
        forward_result = tick(forward)
        self.assertEqual(reverse_result, forward_result)
        self.assertEqual(
            [record.event_id for record in reverse_result.world.event_log],
            ["a-negative", "z-positive"],
        )
        self.assertAlmostEqual(reverse_result.world.agents[0].state.trust, 0.3)

    def test_reach_zero_and_one_have_exact_recipient_semantics(self):
        initial = event_fixture()
        unreachable = tick(schedule_event(
            initial, Event("none", "NEWS", 0, {"sentiment_delta": 0.4}, reach=0.0)
        ))
        everyone = tick(schedule_event(
            initial, Event("all", "NEWS", 0, {"sentiment_delta": 0.4}, reach=1.0)
        ))
        self.assertEqual(unreachable.world.event_log[0].target_ids, [])
        self.assertEqual([a.state.sentiment for a in unreachable.world.agents], [0.0] * 4)
        self.assertEqual(everyone.world.event_log[0].target_ids,
                         ["agent-0", "agent-1", "agent-2", "agent-3"])
        self.assertEqual([a.state.sentiment for a in everyone.world.agents], [0.4] * 4)
        self.assertEqual(unreachable.metrics.event_count, 1)
        self.assertEqual(everyone.metrics.event_count, 1)

    def test_probabilistic_reach_is_reproducible_and_partial(self):
        initial = event_fixture(count=40)
        event = Event("partial", "NEWS", 0, {"sentiment_delta": 0.4}, reach=0.5)
        first = tick(schedule_event(initial, event))
        second = tick(schedule_event(initial, event))
        self.assertEqual(first, second)
        recipients = first.world.event_log[0].target_ids
        self.assertGreater(len(recipients), 0)
        self.assertLess(len(recipients), 40)
        self.assertEqual(
            {a.id for a in first.world.agents if a.state.sentiment == 0.4},
            set(recipients),
        )

    def test_group_and_specific_targets_only_change_selected_agents(self):
        for target, expected in (
            (EventTarget(kind="group", group="selected"), {"agent-0", "agent-2"}),
            (EventTarget(kind="agents", agent_ids=["agent-3", "agent-1"]),
             {"agent-1", "agent-3"}),
        ):
            with self.subTest(target=target.kind):
                initial = event_fixture()
                result = tick(schedule_event(initial, Event(
                    "targeted", "TRUST_SHOCK", 0, {"trust_delta": -0.2}, target=target
                )))
                self.assertEqual(set(result.world.event_log[0].target_ids), expected)
                for agent in result.world.agents:
                    expected_trust = 0.3 if agent.id in expected else 0.5
                    self.assertAlmostEqual(agent.state.trust, expected_trust)

    def test_news_and_trust_shock_apply_deltas_and_bound_state(self):
        initial = event_fixture()
        news = tick(schedule_event(initial, Event(
            "news", "NEWS", 0, {"sentiment_delta": 0.3, "trust_delta": 0.2}
        )))
        self.assertAlmostEqual(news.world.agents[0].state.sentiment, 0.3)
        self.assertAlmostEqual(news.world.agents[0].state.trust, 0.7)
        shocked = tick(schedule_event(news, Event(
            "shock", "TRUST_SHOCK", 1, {"trust_delta": -1.0}
        )))
        self.assertEqual(shocked.world.agents[0].state.trust, 0.0)
        bounded = tick(schedule_event(shocked, Event(
            "extreme-news", "NEWS", 2, {"sentiment_delta": -1.0, "trust_delta": 1.0}
        )))
        self.assertEqual(bounded.world.agents[0].state.trust, 1.0)
        self.assertGreaterEqual(bounded.world.agents[0].state.sentiment, -1.0)
        self.assertLessEqual(bounded.world.agents[0].state.sentiment, 1.0)

    def test_all_economic_event_types_affect_intent_in_expected_direction(self):
        cases = (
            ("PRICE_CHANGE", {"price": 20.0}, "price", 20.0, "increase"),
            ("INCENTIVE", {"amount": 30.0}, "incentive", 30.0, "increase"),
            ("COMPETITOR_ENTRY", {"pressure": 0.8}, "competitor_pressure", 0.8,
             "decrease"),
        )
        initial = event_fixture(active=True)
        baseline = tick(initial)
        for event_type, payload, field, value, direction in cases:
            with self.subTest(event=event_type):
                changed = tick(schedule_event(initial, Event("economic", event_type, 0, payload)))
                self.assertEqual(getattr(changed.world.global_state, field), value)
                for before, after in zip(baseline.world.agents, changed.world.agents):
                    if direction == "increase":
                        self.assertGreater(after.state.adoption_intent, before.state.adoption_intent)
                    else:
                        self.assertLess(after.state.adoption_intent, before.state.adoption_intent)

    def test_targeted_economic_events_preserve_untargeted_agent_behavior(self):
        cases = (
            ("PRICE_CHANGE", {"price": 20.0}, "price_override", 20.0),
            ("INCENTIVE", {"amount": 30.0}, "incentive_override", 30.0),
            ("COMPETITOR_ENTRY", {"pressure": 0.8}, "competitor_pressure_override", 0.8),
        )
        initial = event_fixture(active=True)
        baseline = run_ticks(initial, 3)
        for event_type, payload, field, value in cases:
            with self.subTest(event=event_type):
                changed = run_ticks(schedule_event(initial, Event(
                    "targeted-economic", event_type, 0, payload,
                    target=EventTarget(kind="agents", agent_ids=["agent-0"]),
                )), 3)
                self.assertEqual(changed.world.global_state, initial.world.global_state)
                self.assertEqual(getattr(changed.world.agents[0].state, field), value)
                self.assertNotEqual(changed.world.agents[0].state.adoption_intent,
                                    baseline.world.agents[0].state.adoption_intent)
                for expected, actual in zip(baseline.world.agents[1:], changed.world.agents[1:]):
                    self.assertEqual(actual.state, expected.state)
                    self.assertEqual(actual.relationships, expected.relationships)
                    self.assertEqual(actual.memory, expected.memory)

    def test_probabilistic_economic_events_only_affect_actual_recipients(self):
        cases = (
            ("PRICE_CHANGE", {"price": 20.0}, "price_override", 20.0),
            ("INCENTIVE", {"amount": 30.0}, "incentive_override", 30.0),
            ("COMPETITOR_ENTRY", {"pressure": 0.8}, "competitor_pressure_override", 0.8),
        )
        initial = event_fixture(active=True, count=40)
        baseline = tick(initial)
        for event_type, payload, field, value in cases:
            with self.subTest(event=event_type):
                changed = tick(schedule_event(initial, Event(
                    "partial-economic", event_type, 0, payload, reach=0.5,
                )))
                recipients = set(changed.world.event_log[0].target_ids)
                self.assertGreater(len(recipients), 0)
                self.assertLess(len(recipients), 40)
                self.assertEqual(changed.world.global_state, initial.world.global_state)
                for expected, actual in zip(baseline.world.agents, changed.world.agents):
                    if actual.id in recipients:
                        self.assertEqual(getattr(actual.state, field), value)
                        self.assertNotEqual(actual.state.adoption_intent, expected.state.adoption_intent)
                    else:
                        self.assertEqual(actual.state, expected.state)

    def test_universal_economic_event_supersedes_prior_local_override(self):
        cases = (
            ("PRICE_CHANGE", "price", "price_override", 20.0, 80.0),
            ("INCENTIVE", "amount", "incentive_override", 30.0, 5.0),
            ("COMPETITOR_ENTRY", "pressure", "competitor_pressure_override", 0.8, 0.1),
        )
        for event_type, payload_field, override_field, local, universal in cases:
            with self.subTest(event=event_type):
                initial = event_fixture()
                partial = tick(schedule_event(initial, Event(
                    "local", event_type, 0, {payload_field: local},
                    target=EventTarget(kind="agents", agent_ids=["agent-0"]),
                )))
                self.assertEqual(getattr(partial.world.agents[0].state, override_field), local)
                global_result = tick(schedule_event(partial, Event(
                    "universal", event_type, 1, {payload_field: universal},
                )))
                self.assertTrue(all(getattr(agent.state, override_field) is None
                                    for agent in global_result.world.agents))
                self.assertEqual(global_result.metrics.event_count, 2)


class MetricsTests(unittest.TestCase):
    def test_active_agent_denominators_and_empty_population(self):
        agents = [
            Agent("a", state=AgentState(trust=0.2, sentiment=-0.5, adoption_intent=0.2)),
            Agent("b", state=AgentState(trust=0.8, sentiment=0.5,
                                        adoption_intent=0.6, adopted=True)),
            Agent("inactive", state=AgentState(trust=1.0, sentiment=1.0,
                                               adoption_intent=1.0, adopted=True, active=False)),
        ]
        simulation = create_simulation("metrics", 3, World("metrics-world", agents=agents))
        self.assertAlmostEqual(simulation.metrics.adoption_rate, 0.5)
        self.assertAlmostEqual(simulation.metrics.average_trust, 0.5)
        self.assertAlmostEqual(simulation.metrics.average_sentiment, 0.0)
        self.assertAlmostEqual(simulation.metrics.average_intent, 0.4)
        for empty_agents in ([], [agents[2]]):
            with self.subTest(population=len(empty_agents)):
                empty = run_ticks(create_simulation("empty", 3, World("empty", agents=empty_agents)), 3)
                self.assertEqual(empty.metrics.adoption_rate, 0.0)
                self.assertEqual(empty.metrics.average_trust, 0.0)
                self.assertEqual(empty.metrics.average_sentiment, 0.0)
                self.assertEqual(empty.metrics.average_intent, 0.0)
                self.assertEqual(empty.metrics.interaction_count, 0)

    def test_metrics_match_current_states_and_accumulate_occurrences(self):
        simulation = run_ticks(scenario(), 14)
        active = [a for a in simulation.world.agents if a.state.active]
        self.assertAlmostEqual(simulation.metrics.adoption_rate,
                               sum(a.state.adopted for a in active) / len(active))
        self.assertAlmostEqual(simulation.metrics.average_trust,
                               sum(a.state.trust for a in active) / len(active))
        self.assertAlmostEqual(simulation.metrics.average_sentiment,
                               sum(a.state.sentiment for a in active) / len(active))
        self.assertAlmostEqual(simulation.metrics.average_intent,
                               sum(a.state.adoption_intent for a in active) / len(active))
        self.assertEqual(simulation.metrics.event_count, len(simulation.world.event_log))
        self.assertEqual(simulation.metrics.event_count, 3)
        self.assertGreater(simulation.metrics.interaction_count, 0)
        potential_interactions = sum(len(a.relationships) for a in active) * 14
        self.assertLessEqual(simulation.metrics.interaction_count, potential_interactions)
        self.assertEqual(simulation.metrics.interaction_count,
                         sum(memory.kind == "interaction"
                             for agent in simulation.world.agents for memory in agent.memory))
        for agent in simulation.world.agents:
            self.assertTrue(math.isfinite(agent.state.trust))
            self.assertGreaterEqual(agent.state.trust, 0.0)
            self.assertLessEqual(agent.state.trust, 1.0)
            self.assertGreaterEqual(agent.state.sentiment, -1.0)
            self.assertLessEqual(agent.state.sentiment, 1.0)
            self.assertGreaterEqual(agent.state.adoption_intent, 0.0)
            self.assertLessEqual(agent.state.adoption_intent, 1.0)

    def test_interaction_count_is_cumulative_and_relationships_evolve(self):
        first = Agent("a", relationships=[Relationship("b")])
        second = Agent("b", relationships=[Relationship("a")])
        initial = create_simulation(
            "interaction", 1, World("interaction", agents=[first, second]),
            quiet_configuration(interaction_probability=1.0, trust_learning_rate=0.2),
        )
        one = tick(initial)
        three = run_ticks(one, 2)
        self.assertEqual(one.metrics.interaction_count, 2)
        self.assertEqual(three.metrics.interaction_count, 6)
        self.assertNotEqual(three.world.agents[0].relationships, initial.world.agents[0].relationships)
        self.assertGreater(len(three.world.agents[0].memory), len(initial.world.agents[0].memory))


class ValidationTests(unittest.TestCase):
    def test_invalid_configuration_is_rejected_before_transition(self):
        cases = (
            {"noise": -0.1}, {"noise": float("nan")}, {"noise": True},
            {"adoption_threshold": 1.1}, {"peer_weight": -1.0},
            {"price_scale": 0.0}, {"interaction_probability": 1.1},
            {"trust_learning_rate": -0.1}, {"sentiment_decay": 1.1},
            {"tick_unit": ""}, {"model_version": "unknown-model"},
        )
        for values in cases:
            with self.subTest(configuration=values):
                with self.assertRaises(ValueError):
                    create_simulation("bad", 3, World("world"), Configuration(**values))
        for count in (-1, 1.5, True, "2"):
            with self.subTest(ticks=count):
                with self.assertRaises(ValueError):
                    run_ticks(event_fixture(), count)

    def test_invalid_events_unknown_targets_and_duplicate_ids_are_rejected(self):
        cases = (
            Event("unknown-type", "UNKNOWN", 0, {}),
            Event("missing-price", "PRICE_CHANGE", 0, {}),
            Event("negative-price", "PRICE_CHANGE", 0, {"price": -1.0}),
            Event("bad-price-type", "PRICE_CHANGE", 0, {"price": True}),
            Event("nonfinite", "INCENTIVE", 0, {"amount": float("inf")}),
            Event("bad-pressure", "COMPETITOR_ENTRY", 0, {"pressure": 1.1}),
            Event("empty-news", "NEWS", 0, {}),
            Event("bad-trust", "TRUST_SHOCK", 0, {"trust_delta": "bad"}),
            Event("bad-reach", "NEWS", 0, {"trust_delta": 0.1}, reach=-0.1),
            Event("bad-tick", "NEWS", True, {"trust_delta": 0.1}),
            Event("unknown-agent", "NEWS", 0, {"trust_delta": 0.1},
                  target=EventTarget(kind="agents", agent_ids=["missing"])),
            Event("unknown-group", "NEWS", 0, {"trust_delta": 0.1},
                  target=EventTarget(kind="group", group="missing")),
            Event("unknown-target", "NEWS", 0, {"trust_delta": 0.1},
                  target=EventTarget(kind="unknown")),
        )
        for event in cases:
            with self.subTest(event=event.id):
                with self.assertRaises(ValueError):
                    schedule_event(event_fixture(), event)
        once = schedule_event(event_fixture(), Event("unique", "NEWS", 0, {"trust_delta": 0.1}))
        with self.assertRaises(ValueError):
            schedule_event(once, Event("unique", "NEWS", 1, {"trust_delta": 0.1}))
        applied = tick(once)
        with self.assertRaises(ValueError):
            schedule_event(applied, Event("unique", "NEWS", 1, {"trust_delta": 0.1}))
        with self.assertRaises(ValueError):
            schedule_event(applied, Event("past", "NEWS", 0, {"trust_delta": 0.1}))

    def test_invalid_world_state_does_not_enter_kernel(self):
        cases = (
            World("duplicate", agents=[Agent("same"), Agent("same")]),
            World("unknown-link", agents=[Agent("a", relationships=[Relationship("missing")])]),
            World("out-of-range", agents=[Agent("a", state=AgentState(trust=1.1))]),
            World("wrong-trait-type", agents=[Agent("a", traits=Traits(openness="high"))]),
            World("invalid-tick", current_tick=-1),
            World("invalid-global", global_state=GlobalState(price=-1.0)),
            World("unsafe-metadata", metadata={"non-json": {1, 2}}),
        )
        for world in cases:
            with self.subTest(world=world.id):
                with self.assertRaises(ValueError):
                    create_simulation("invalid", 1, world)


if __name__ == "__main__":
    unittest.main()
