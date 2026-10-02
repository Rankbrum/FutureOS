"""Behavioral guarantees for M3 trace, indexed shocks and state provenance."""

from copy import deepcopy
from dataclasses import asdict
import unittest

from futureos.audit import agent_trajectory, final_state_hash, verify_audit
from futureos.codec import canonical_json, parse_json, simulation_to_dict
from futureos.engine import create_simulation, run_ticks, schedule_event, tick
from futureos.models import Agent, AgentState, Configuration, Event, Relationship, World
from futureos.randomness import RandomStreams
from futureos.validation import validate_simulation


def fixture(mode="trace"):
    a = Agent("a", state=AgentState(trust=.6, sentiment=.1, adopted=False),
              relationships=[Relationship("b", .7, .8, .9)])
    b = Agent("b", state=AgentState(trust=.8, sentiment=.3, adopted=True),
              relationships=[Relationship("a", .8, .8, .9)])
    config = Configuration(interaction_probability=1, adoption_threshold=.12, noise=.1)
    simulation = create_simulation("audit-fixture", 42, World("world", agents=[a, b]),
                                   config, audit_mode=mode)
    return schedule_event(simulation, Event("news", "NEWS", 0,
                          {"trust_delta": .1, "sentiment_delta": .2}, reach=.5))


class AuditTests(unittest.TestCase):
    def test_modes_have_identical_society_and_three_hashes(self):
        summary, trace = (run_ticks(fixture(mode), 4) for mode in ("summary", "trace"))
        self.assertEqual(summary.world, trace.world)
        self.assertEqual(summary.metrics, trace.metrics)
        self.assertEqual(summary.audit.frames, trace.audit.frames)
        self.assertEqual(summary.audit.trajectory_hash, trace.audit.trajectory_hash)
        self.assertEqual(summary.audit.event_trace_hash, trace.audit.event_trace_hash)
        self.assertEqual(final_state_hash(summary), final_state_hash(trace))
        self.assertEqual(summary.audit.records, [])
        self.assertGreater(summary.audit.trace_count, 0)
        self.assertEqual(trace.audit.trace_count, len(trace.audit.records))
        verify_audit(summary)
        verify_audit(trace)

    def test_trace_contains_all_required_types_in_execution_order(self):
        s = fixture()
        s.world.events[0].reach = 1
        result = run_ticks(s, 2)
        types = {item.kind for item in result.audit.records}
        self.assertTrue({"tick_started", "tick_completed", "event_applied", "interaction_created",
                         "influence_applied", "state_changed", "adoption_decision",
                         "relationship_changed"} <= types)
        for t in (0, 1):
            rows = [r for r in result.audit.records if r.tick == t]
            self.assertEqual(rows[0].kind, "tick_started")
            self.assertEqual(rows[-1].kind, "tick_completed")
            self.assertEqual(rows[-1].payload["state_tick"], t + 1)

    def test_repeat_trace_and_json_are_exact(self):
        one, two = (run_ticks(fixture(), 3) for _ in range(2))
        self.assertEqual(one, two)
        encoded = canonical_json(simulation_to_dict(one))
        self.assertEqual(parse_json(encoded), simulation_to_dict(two))
        self.assertNotIn("NaN", encoded)

    def test_collection_order_cannot_change_trace_or_hashes(self):
        one = fixture()
        two = deepcopy(one)
        two.world.agents.reverse()
        for a in two.world.agents:
            a.relationships.reverse()
        one, two = run_ticks(one, 3), run_ticks(two, 3)
        self.assertEqual(one.audit, two.audit)
        self.assertEqual(final_state_hash(one), final_state_hash(two))

    def test_reach_and_extra_event_do_not_change_other_mechanism_draws(self):
        original = fixture()
        original.configuration.interaction_probability = .5
        alternatives = []
        for reach in (0, .4, 1):
            sim = deepcopy(original)
            sim.world.events[0].reach = reach
            sim = schedule_event(sim, Event("unrelated", "TRUST_SHOCK", 1, {"trust_delta": 0}, reach=.6))
            alternatives.append(run_ticks(sim, 4))
        def noises(s):
            return [(r.tick, r.entity, r.payload["components"]["noise"])
                    for r in s.audit.records if r.kind == "adoption_decision"]
        def interactions(s):
            return [(r.tick, r.entity, r.payload["target_agent_id"])
                    for r in s.audit.records if r.kind == "interaction_created"]
        for s in alternatives[1:]:
            self.assertEqual(noises(alternatives[0]), noises(s))
            self.assertEqual(interactions(alternatives[0]), interactions(s))
        # An event's draws do not affect another event, including reach endpoints.
        targets = [[r.payload["target_ids"] for r in s.audit.records
                    if r.kind == "event_applied" and r.payload["event_id"] == "unrelated"]
                   for s in alternatives]
        self.assertTrue(all(t == targets[0] for t in targets))

    def test_active_change_does_not_shift_other_agent_noise_or_future_tick(self):
        one, two = fixture(), fixture()
        two.world.agents[0].state.active = False
        one, two = run_ticks(one, 3), run_ticks(two, 3)
        noises = lambda s: [(r.tick, r.payload["components"]["noise"]) for r in s.audit.records
                            if r.entity == "agent:b" and r.kind == "adoption_decision"]
        self.assertEqual(noises(one), noises(two))

    def test_state_deltas_reconstruct_all_agent_state_and_relationship_changes(self):
        before = fixture()
        after = tick(before)
        reconstructed = {f"agent:{a.id}": asdict(a.state) for a in before.world.agents}
        relations = {f"relationship:{a.id}->{r.target_agent_id}": asdict(r)
                     for a in before.world.agents for r in a.relationships}
        for row in after.audit.records:
            if row.kind == "state_changed" and row.entity in reconstructed and not row.payload["field"].startswith("memory"):
                state = reconstructed[row.entity]
                self.assertEqual(state[row.payload["field"]], row.payload["before"])
                state[row.payload["field"]] = row.payload["after"]
            if row.kind == "relationship_changed":
                state = relations[row.entity]
                self.assertEqual(state[row.payload["field"]], row.payload["before"])
                state[row.payload["field"]] = row.payload["after"]
        for a in after.world.agents:
            self.assertEqual(reconstructed[f"agent:{a.id}"], asdict(a.state))
            for r in a.relationships:
                self.assertEqual(relations[f"relationship:{a.id}->{r.target_agent_id}"], asdict(r))

    def test_global_and_override_event_deltas_are_recorded(self):
        s = fixture()
        s.world.agents[0].state.price_override = 20
        s = schedule_event(s, Event("price", "PRICE_CHANGE", 0, {"price": 70}))
        result = tick(s)
        rows = [r for r in result.audit.records if r.kind == "state_changed" and r.mechanism == "event:price"]
        self.assertTrue(any(r.entity == "world" and r.payload == {"field": "price", "before": 99.9, "after": 70} for r in rows))
        self.assertTrue(any(r.entity == "agent:a" and r.payload["field"] == "price_override" and r.payload["after"] is None for r in rows))

    def test_universal_override_clearing_trace_ignores_collection_order(self):
        s = fixture()
        s.world.agents[0].state.price_override = 20
        s.world.agents[1].state.price_override = 30
        s = schedule_event(s, Event("price", "PRICE_CHANGE", 0, {"price": 70}))
        reversed_order = deepcopy(s)
        reversed_order.world.agents.reverse()
        one, two = tick(s), tick(reversed_order)
        self.assertEqual(one.audit, two.audit)

    def test_contributions_and_decision_inputs_explain_internal_algorithm(self):
        s = tick(fixture())
        decision = next(r for r in s.audit.records if r.kind == "adoption_decision" and r.entity == "agent:a")
        self.assertIn("social", decision.payload["components"])
        self.assertEqual(decision.payload["peers"][0]["source_agent_id"], "b")
        expected_noise = (2 * RandomStreams(s.seed).stream("decisions", 0, "a").random() - 1) * s.configuration.noise
        self.assertEqual(expected_noise, decision.payload["components"]["noise"])
        influence = next(r for r in s.audit.records if r.kind == "influence_applied" and r.entity == "agent:a")
        self.assertEqual(influence.payload["source_agent_id"], "b")
        delta = next(r for r in s.audit.records if r.entity == "agent:a" and r.kind == "state_changed" and r.payload["field"] == "trust" and r.mechanism == "social_interaction")
        self.assertEqual(delta.payload["contributions"][0]["source_agent_id"], "b")

    def test_trajectory_answers_events_interactions_influences_adoption_changes(self):
        s = fixture()
        s.world.events[0].reach = 1
        s = run_ticks(s, 2)
        rows = agent_trajectory(s, "a")
        self.assertEqual(rows, agent_trajectory(s, "a"))
        self.assertTrue(any(r["kind"] == "event_applied" and "a" in r["payload"]["target_ids"] for r in rows))
        self.assertTrue(any(r["kind"] == "interaction_created" for r in rows))
        self.assertTrue(any(r["kind"] == "influence_applied" and r["payload"]["source_agent_id"] == "b" for r in rows))
        self.assertTrue(any(r["kind"] == "influence_applied" and r["entity"] == "agent:a"
                            for r in agent_trajectory(s, "b")))
        self.assertTrue(any(r["kind"] == "state_changed" and r["payload"]["field"] == "adopted" for r in rows))
        with self.assertRaises(ValueError):
            agent_trajectory(s, "unknown")
        with self.assertRaises(ValueError):
            agent_trajectory(run_ticks(fixture("summary"), 1), "a")

    def test_full_trace_never_enters_simulated_memory(self):
        s = run_ticks(fixture(), 2)
        self.assertTrue(all(m.kind in {"adoption", "interaction", "event"} for a in s.world.agents for m in a.memory))
        self.assertFalse(any(m.kind in {"state_changed", "tick_started"} for a in s.world.agents for m in a.memory))

    def test_summary_full_trace_or_wrong_versions_are_rejected(self):
        s = run_ticks(fixture("summary"), 1)
        s.audit.records = run_ticks(fixture(), 1).audit.records
        with self.assertRaises(ValueError):
            validate_simulation(s)
        s = fixture()
        s.audit.rng_version = "unknown"
        with self.assertRaises(ValueError):
            tick(s)

    def test_hash_chain_detects_tampering(self):
        s = run_ticks(fixture(), 2)
        s.audit.records[1].payload["reach"] = .7
        with self.assertRaisesRegex(ValueError, "trace hash"):
            verify_audit(s)
        s = run_ticks(fixture(), 2)
        s.audit.frames[0].state_hash = "a" * 64
        with self.assertRaisesRegex(ValueError, "trajectory hash"):
            verify_audit(s)

    def test_zero_ticks_and_invalid_audit_creation(self):
        s = fixture()
        self.assertEqual(run_ticks(s, 0), s)
        self.assertEqual(s.audit.records, [])
        with self.assertRaises(ValueError):
            create_simulation("s", 42, World("w"), audit_mode="unknown")

    def test_endpoint_changes_cannot_hide_behind_a_retained_chain(self):
        s = run_ticks(fixture(), 2)
        s.world.agents[0].state.trust = .123
        with self.assertRaisesRegex(ValueError, "endpoint"):
            verify_audit(s)

    def test_agent_ids_with_separators_do_not_alias_trajectory_ownership(self):
        agents = [Agent("a"), Agent("a->b", relationships=[Relationship("c")]), Agent("c")]
        s = create_simulation("s", 42, World("w", agents=agents),
                              Configuration(interaction_probability=1), audit_mode="trace")
        s = tick(s)
        self.assertFalse(any(r["kind"] == "relationship_changed" for r in agent_trajectory(s, "a")))
        self.assertTrue(any(r["kind"] == "relationship_changed" for r in agent_trajectory(s, "a->b")))

    def test_final_hash_includes_operational_status(self):
        s = tick(fixture())
        completed = deepcopy(s)
        completed.status = "completed"
        self.assertNotEqual(final_state_hash(s), final_state_hash(completed))
        self.assertEqual(s.audit.trajectory_hash, completed.audit.trajectory_hash)


if __name__ == "__main__":
    unittest.main()
