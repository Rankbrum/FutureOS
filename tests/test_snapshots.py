"""Continuation, integrity and isolated branches from complete snapshots."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from futureos.branches import BranchConfiguration, compare_branches, create_branch
from futureos.engine import create_simulation, run_ticks, schedule_event
from futureos.models import Event, Memory, World
from futureos.population import create_population
from futureos.randomness import SeededRandom
from futureos.snapshots import (
    Snapshot,
    create_snapshot,
    load_snapshot,
    restore_snapshot,
    save_snapshot,
)


def source_simulation():
    rng = SeededRandom(73)
    agents = create_population(12, rng)
    agents[0].metadata["nested"] = {"items": ["source"]}
    agents[0].memory.append(Memory(0, "fixture", {"nested": {"items": ["source"]}}))
    world = World(
        "snapshot-world",
        agents=agents,
        events=[
            Event("past-news", "NEWS", 2, {"sentiment_delta": 0.25}, reach=0.6),
            Event("future-shock", "TRUST_SHOCK", 8, {"trust_delta": -0.2}, reach=0.7,
                  metadata={"nested": {"items": ["source"]}}),
            Event("future-price", "PRICE_CHANGE", 12, {"price": 75.0}),
        ],
        metadata={"synthetic": True, "nested": {"items": ["source"]}},
    )
    simulation = create_simulation("snapshot-source", 73, world, rng_state=rng.state)
    simulation.metadata["nested"] = {"items": ["source"]}
    return run_ticks(simulation, 6)


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def changed_snapshot_json(snapshot, change):
    """Build a checksum-valid envelope to exercise semantic schema rejection."""
    envelope = json.loads(snapshot.to_json())
    change(envelope["simulation"])
    integrity = {name: envelope[name]
                 for name in ("schema_version", "engine_version", "simulation")}
    checksum = sha256(canonical_json(integrity).encode("utf-8")).hexdigest()
    envelope["checksum"] = checksum
    state = envelope["simulation"]
    envelope["id"] = f"{state['id']}:tick-{state['world']['current_tick']}:{checksum[:16]}"
    return canonical_json(envelope)


class SnapshotTests(unittest.TestCase):
    def test_snapshot_restoration_preserves_complete_state_and_continuation(self):
        original = source_simulation()
        original_before = deepcopy(original)
        snapshot = create_snapshot(original)
        restored = restore_snapshot(snapshot)
        self.assertEqual(restored, original)
        self.assertEqual(original, original_before)
        self.assertGreater(restored.rng_state.draws, 0)
        self.assertTrue(restored.world.agents[0].memory)
        self.assertTrue(restored.world.agents[0].relationships)
        self.assertEqual(restored.metrics.event_count, 1)
        self.assertEqual(
            [event.id for event in restored.world.events
             if event.tick >= restored.world.current_tick],
            ["future-shock", "future-price"],
        )
        uninterrupted = run_ticks(original, 14)
        continued = run_ticks(restored, 14)
        self.assertEqual(continued, uninterrupted)
        self.assertEqual(continued.metrics.event_count, 3)
        self.assertEqual(len(continued.world.event_log), 3)
        self.assertEqual(original, original_before)

    def test_json_roundtrip_preserves_state_rng_metrics_and_future_events(self):
        original = source_simulation()
        snapshot = create_snapshot(original)
        loaded = Snapshot.from_json(snapshot.to_json())
        self.assertEqual(loaded, snapshot)
        self.assertEqual(restore_snapshot(loaded), original)
        self.assertEqual(run_ticks(restore_snapshot(loaded), 14), run_ticks(original, 14))
        self.assertEqual(Snapshot.from_json(loaded.to_json()), loaded)

    def test_persistence_uses_a_fresh_directory_and_restores_continuation(self):
        original = source_simulation()
        snapshot = create_snapshot(original)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "nested" / "society.snapshot.json"
            save_snapshot(snapshot, destination)
            self.assertTrue(destination.is_file())
            loaded = load_snapshot(destination)
            self.assertEqual(loaded, snapshot)
            self.assertEqual(run_ticks(restore_snapshot(loaded), 14), run_ticks(original, 14))
            # Replacing one full snapshot leaves no partially published files.
            updated = create_snapshot(run_ticks(original, 1))
            save_snapshot(updated, destination)
            self.assertEqual(load_snapshot(destination), updated)
            self.assertEqual(list(destination.parent.iterdir()), [destination])

    def test_snapshot_is_immutable_and_detached_from_original(self):
        original = source_simulation()
        snapshot = create_snapshot(original)
        before = snapshot.to_json()
        with self.assertRaises(FrozenInstanceError):
            snapshot.id = "changed"
        original.world.metadata["nested"]["items"].append("changed")
        original.world.agents[0].memory[0].payload["nested"]["items"].append("changed")
        original.world.agents[0].relationships[0].trust = 0.0
        self.assertEqual(snapshot.to_json(), before)
        self.assertEqual(restore_snapshot(snapshot).world.metadata["nested"]["items"], ["source"])

    def test_each_restoration_gets_independent_nested_objects(self):
        snapshot = create_snapshot(source_simulation())
        first = restore_snapshot(snapshot)
        second = restore_snapshot(snapshot)
        before = deepcopy(second)
        first.world.agents[0].metadata["nested"]["items"].append("first")
        first.world.agents[0].memory[0].payload["nested"]["items"].append("first")
        first.world.agents[0].relationships[0].trust = 0.0
        first.world.events[1].payload["trust_delta"] = -0.9
        first.world.events[1].metadata["nested"]["items"].append("first")
        first.world.event_log[0].target_ids.clear()
        first.world.metadata["nested"]["items"].append("first")
        first.configuration.noise = 0.3
        first.metadata["nested"]["items"].append("first")
        self.assertEqual(second, before)
        self.assertEqual(restore_snapshot(snapshot), before)

    def test_invalid_json_and_unknown_envelope_fields_fail_explicitly(self):
        snapshot = create_snapshot(source_simulation())
        valid = json.loads(snapshot.to_json())
        invalid_texts = ["", "{", "null", "[]", "NaN", "Infinity", '{"id":1,"id":2}']
        unknown = deepcopy(valid)
        unknown["unexpected"] = "must not be ignored"
        invalid_texts.append(canonical_json(unknown))
        missing = deepcopy(valid)
        del missing["simulation"]
        invalid_texts.append(canonical_json(missing))
        for text in invalid_texts:
            with self.subTest(text=text[:70]):
                with self.assertRaises(ValueError):
                    Snapshot.from_json(text)

    def test_schema_engine_identity_and_checksum_corruption_are_rejected(self):
        snapshot = create_snapshot(source_simulation())
        mutations = (
            {"schema_version": 999}, {"schema_version": True},
            {"engine_version": "futureos-incompatible"},
            {"checksum": "0" * 64}, {"id": "different-snapshot"},
            {"simulation_json": snapshot.simulation_json.replace('"price":99.9', '"price":1.0')},
        )
        for changes in mutations:
            with self.subTest(changes=tuple(changes)):
                with self.assertRaises(ValueError):
                    restore_snapshot(replace(snapshot, **changes))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.snapshot.json"
            path.write_text('{"schema_version":999}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_snapshot(path)

    def test_valid_integrity_cannot_hide_incomplete_or_invalid_simulation(self):
        snapshot = create_snapshot(source_simulation())

        def missing_rng(data):
            del data["rng_state"]

        def unknown_field(data):
            data["world"]["agents"][0]["state"]["unexpected"] = True

        def invalid_boolean(data):
            data["world"]["agents"][0]["state"]["adopted"] = "false"

        def invalid_relationship(data):
            data["world"]["agents"][0]["relationships"][0]["target_agent_id"] = "missing"

        def inconsistent_events(data):
            data["world"]["event_log"] = []
            data["metrics"]["event_count"] = 0

        def invalid_rng(data):
            data["rng_state"]["draws"] += 1

        for mutation in (missing_rng, unknown_field, invalid_boolean, invalid_relationship,
                         inconsistent_events, invalid_rng):
            with self.subTest(mutation=mutation.__name__):
                with self.assertRaises(ValueError):
                    Snapshot.from_json(changed_snapshot_json(snapshot, mutation))


class BranchRealityTests(unittest.TestCase):
    def test_all_branches_begin_at_exact_same_snapshot_with_distinct_identity(self):
        original = source_simulation()
        original_before = deepcopy(original)
        snapshot = create_snapshot(original)
        before = snapshot.to_json()
        branches = [create_branch(snapshot, BranchConfiguration(name)) for name in "ABC"]
        self.assertEqual({branch.id for branch in branches}, {"A", "B", "C"})
        self.assertEqual(len({branch.simulation.id for branch in branches}), 3)
        for branch in branches:
            self.assertEqual(branch.parent_simulation_id, original.id)
            self.assertEqual(branch.parent_snapshot_id, snapshot.id)
            self.assertEqual(branch.branch_point, original.world.current_tick)
            self.assertEqual(branch.simulation.world, original.world)
            self.assertEqual(branch.simulation.configuration, original.configuration)
            self.assertEqual(branch.simulation.metrics, original.metrics)
            self.assertEqual(branch.simulation.rng_state, original.rng_state)
            self.assertEqual(branch.simulation.seed, original.seed)
            self.assertEqual(branch.simulation.status, original.status)
        self.assertEqual(original, original_before)
        self.assertEqual(snapshot.to_json(), before)

    def test_mutating_one_branch_does_not_change_parent_snapshot_or_siblings(self):
        original = source_simulation()
        original_before = deepcopy(original)
        snapshot = create_snapshot(original)
        snapshot_before = snapshot.to_json()
        configuration = BranchConfiguration("A", metadata={"nested": {"items": ["A"]}})
        first = create_branch(snapshot, configuration)
        siblings = [create_branch(snapshot, BranchConfiguration(name)) for name in "BC"]
        siblings_before = deepcopy(siblings)
        configuration.metadata["nested"]["items"].append("configuration-change")
        self.assertEqual(first.metadata["nested"]["items"], ["A"])
        world = first.simulation.world
        world.metadata["nested"]["items"].append("A")
        world.agents[0].metadata["nested"]["items"].append("A")
        world.agents[0].memory[0].payload["nested"]["items"].append("A")
        world.agents[0].relationships[0].strength = 0.0
        world.events[1].payload["trust_delta"] = -0.9
        world.events[1].metadata["nested"]["items"].append("A")
        world.event_log[0].target_ids.clear()
        world.global_state.price = 42.0
        first.simulation.configuration.noise = 0.2
        first.simulation.metrics.average_trust = 0.7
        first.simulation.metadata["nested"]["items"].append("A")
        first.metadata["nested"]["items"].append("A")
        stream = SeededRandom.from_state(first.simulation.rng_state)
        stream.random()
        first.simulation.rng_state = stream.state
        self.assertEqual(siblings, siblings_before)
        self.assertEqual(original, original_before)
        self.assertEqual(snapshot.to_json(), snapshot_before)
        self.assertEqual(restore_snapshot(snapshot), original_before)

    def test_branch_execution_is_independent_of_execution_order(self):
        original = source_simulation()
        original_before = deepcopy(original)
        snapshot = create_snapshot(original)
        snapshot_before = snapshot.to_json()

        def execute(order):
            branches = {name: create_branch(snapshot, BranchConfiguration(name)) for name in "ABC"}
            interventions = {
                "A": Event("offer-A", "PRICE_CHANGE", 6, {"price": 70.0}),
                "B": Event("offer-B", "PRICE_CHANGE", 6, {"price": 99.9}),
                "C": Event("offer-C", "INCENTIVE", 6, {"amount": 20.0}),
            }
            for name in order:
                branch = branches[name]
                sibling_before = {other: deepcopy(branches[other]) for other in "ABC" if other != name}
                branch.simulation = run_ticks(schedule_event(branch.simulation, interventions[name]), 20)
                for other, before in sibling_before.items():
                    self.assertEqual(branches[other], before)
            return branches

        forward = execute("ABC")
        reverse = execute("CAB")
        self.assertEqual(forward, reverse)
        self.assertEqual(original, original_before)
        self.assertEqual(snapshot.to_json(), snapshot_before)

    def test_branch_intervention_begins_after_origin_boundary(self):
        original = source_simulation()
        snapshot = create_snapshot(original)
        branch = create_branch(snapshot, BranchConfiguration("intervened"))
        intervention = Event("new-price", "PRICE_CHANGE", original.world.current_tick, {"price": 25.0})
        branch.simulation = schedule_event(branch.simulation, intervention)
        self.assertEqual(branch.simulation.world.global_state, original.world.global_state)
        self.assertEqual(branch.simulation.world.agents, original.world.agents)
        self.assertEqual(branch.simulation.metrics, original.metrics)
        branch.simulation = run_ticks(branch.simulation, 1)
        self.assertEqual(branch.simulation.world.global_state.price, 25.0)
        self.assertEqual(branch.simulation.world.event_log[-1].tick, original.world.current_tick)
        self.assertEqual(restore_snapshot(snapshot), original)

    def test_comparison_exposes_lineage_horizon_and_all_numeric_metrics(self):
        snapshot = create_snapshot(source_simulation())
        branches = [create_branch(snapshot, BranchConfiguration(name)) for name in "ABC"]
        for branch in branches:
            branch.simulation = run_ticks(branch.simulation, 4)
        before = deepcopy(branches)
        report = compare_branches(branches)
        self.assertEqual(branches, before)
        self.assertEqual([row["id"] for row in report], ["A", "B", "C"])
        for row, branch in zip(report, branches):
            self.assertEqual(row["simulation_id"], branch.simulation.id)
            self.assertEqual(row["parent_simulation_id"], branch.parent_simulation_id)
            self.assertEqual(row["parent_snapshot_id"], snapshot.id)
            self.assertEqual(row["branch_point"], 6)
            self.assertEqual(row["current_tick"], 10)
            for name, value in asdict(branch.simulation.metrics).items():
                self.assertEqual(row[name], value)

    def test_comparison_rejects_mismatched_origin_horizon_model_population_and_ids(self):
        snapshot = create_snapshot(source_simulation())
        first = create_branch(snapshot, BranchConfiguration("A"))
        second = create_branch(snapshot, BranchConfiguration("B"))

        def origin(branch):
            branch.parent_snapshot_id = "another-origin"

        def horizon(branch):
            branch.simulation = run_ticks(branch.simulation, 1)

        def model(branch):
            branch.simulation.configuration.noise = 0.2

        def population(branch):
            # Rename one population identity and every reference consistently.
            world = branch.simulation.world
            old_id = world.agents[0].id
            new_id = "replacement-agent"
            world.agents[0].id = new_id
            for agent in world.agents:
                for relation in agent.relationships:
                    if relation.target_agent_id == old_id:
                        relation.target_agent_id = new_id
            for record in world.event_log:
                record.target_ids = [new_id if name == old_id else name for name in record.target_ids]

        def duplicate(branch):
            branch.id = "A"

        for mutation in (origin, horizon, model, population, duplicate):
            with self.subTest(mismatch=mutation.__name__):
                changed = deepcopy(second)
                mutation(changed)
                with self.assertRaises(ValueError):
                    compare_branches([first, changed])
        with self.assertRaises(ValueError):
            compare_branches([])

    def test_invalid_branch_configuration_is_rejected(self):
        snapshot = create_snapshot(source_simulation())
        for configuration in (
            BranchConfiguration(""), BranchConfiguration("snapshot-source"),
            BranchConfiguration("A", metadata={"not-json": {"set"}}),
        ):
            with self.subTest(configuration=configuration.id):
                with self.assertRaises(ValueError):
                    create_branch(snapshot, configuration)


if __name__ == "__main__":
    unittest.main()
