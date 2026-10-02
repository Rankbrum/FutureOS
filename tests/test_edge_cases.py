"""Malformed inputs fail before transitions and never masquerade as snapshots."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from futureos.branches import BranchConfiguration, compare_branches, create_branch
from futureos.codec import canonical_json, parse_json, simulation_from_dict, simulation_to_dict
from futureos.demo import DEFAULT_SCENARIO, run_demo
from futureos.engine import create_simulation
from futureos.models import Agent, AgentState, Memory, Relationship, World
from futureos.randomness import SeededRandom
from futureos.snapshots import Snapshot, create_snapshot, restore_snapshot


def minimal_simulation():
    return create_simulation("edge-run", 1, World("edge-world", agents=[Agent("a")]))


class MalformedDataTests(unittest.TestCase):
    def test_agents_cannot_share_mutable_behavioral_objects(self):
        for field in ("state", "memory-list", "relationships-list", "memory", "relationship"):
            with self.subTest(field=field):
                first, second = Agent("a"), Agent("b")
                if field == "state":
                    first.state = second.state = AgentState()
                elif field == "memory-list":
                    first.memory = second.memory = []
                elif field == "relationships-list":
                    first.relationships = second.relationships = []
                elif field == "memory":
                    memory = Memory(0, "fixture", {})
                    first.memory, second.memory = [memory], [memory]
                else:
                    relationship = Relationship("c")
                    first.relationships, second.relationships = [relationship], [relationship]
                world = World("aliased", agents=[first, second, Agent("c")])
                with self.assertRaisesRegex(ValueError, "share mutable"):
                    create_simulation("aliased", 1, world)

    def test_nonfinite_and_oversized_float_fields_raise_value_error(self):
        for value in (float("nan"), float("inf"), 10 ** 400):
            with self.subTest(value=value):
                data = simulation_to_dict(minimal_simulation())
                data["world"]["global_state"]["price"] = value
                with self.assertRaises(ValueError):
                    simulation_from_dict(data)

    def test_nonstring_keys_cycles_and_deep_metadata_raise_value_error(self):
        cycle = {}
        cycle["cycle"] = cycle
        nested = {}
        for _ in range(110):
            nested = {"nested": nested}
        for metadata in ({1: "not-a-string"}, cycle, nested):
            with self.subTest(metadata_type=type(metadata)):
                data = simulation_to_dict(minimal_simulation())
                data["metadata"] = metadata
                with self.assertRaises(ValueError):
                    simulation_from_dict(data)
        data = simulation_to_dict(minimal_simulation())
        data[1] = None
        with self.assertRaises(ValueError):
            simulation_from_dict(data)

    def test_deep_json_parsing_and_encoding_fail_with_value_error(self):
        deep_json = "[" * 2000 + "0" + "]" * 2000
        with self.assertRaises(ValueError):
            parse_json(deep_json)
        deeply_nested = 0
        for _ in range(2000):
            deeply_nested = [deeply_nested]
        with self.assertRaises(ValueError):
            canonical_json(deeply_nested)

    def test_unpaired_unicode_surrogates_are_rejected_before_snapshot_encoding(self):
        for field in ("metadata", "identity", "key"):
            with self.subTest(field=field):
                simulation = minimal_simulation()
                if field == "metadata":
                    simulation.metadata["invalid"] = "\ud800"
                elif field == "key":
                    simulation.metadata["\ud800"] = "invalid"
                else:
                    simulation.id = "invalid\ud800"
                with self.assertRaisesRegex(ValueError, "Unicode"):
                    create_snapshot(simulation)

    def test_snapshot_checksum_version_identity_and_duplicate_keys_fail(self):
        snapshot = create_snapshot(minimal_simulation())
        for broken in (
            replace(snapshot, checksum="0" * 64),
            replace(snapshot, schema_version=True),
            replace(snapshot, engine_version="different-engine"),
            replace(snapshot, id="different-id"),
            replace(snapshot, simulation_json="[" * 2000 + "0" + "]" * 2000),
        ):
            with self.subTest(snapshot_id=broken.id), self.assertRaises(ValueError):
                restore_snapshot(broken)
        duplicate = snapshot.to_json().replace('"schema_version":1',
                                              '"schema_version":1,"schema_version":1')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            Snapshot.from_json(duplicate)


class BranchProtocolTests(unittest.TestCase):
    def test_branch_metadata_requires_object(self):
        snapshot = create_snapshot(minimal_simulation())
        with self.assertRaises(ValueError):
            create_branch(snapshot, BranchConfiguration("A", metadata=[]))

    def test_comparison_rejects_invalid_objects_and_inconsistent_lineage(self):
        snapshot = create_snapshot(minimal_simulation())
        original = create_branch(snapshot, BranchConfiguration("A"))
        candidates = [None, replace(original, simulation=None), replace(original, id=[]),
                      replace(original, branch_point=1)]
        altered = deepcopy(original)
        altered.simulation.metadata["lineage"]["branch_id"] = "another-branch"
        candidates.append(altered)
        for candidate in candidates:
            with self.subTest(candidate_type=type(candidate)), self.assertRaises(ValueError):
                compare_branches([candidate])

    def test_comparison_rejects_different_seed_continuations(self):
        snapshot = create_snapshot(minimal_simulation())
        first = create_branch(snapshot, BranchConfiguration("A"))
        second = create_branch(snapshot, BranchConfiguration("B"))
        second.simulation.seed = 2
        second.simulation.rng_state = SeededRandom(2).state
        with self.assertRaises(ValueError):
            compare_branches([first, second])

    def test_invalid_scenario_configuration_is_rejected_before_ticks(self):
        scenario = json.loads(DEFAULT_SCENARIO.read_text(encoding="utf-8"))
        for alteration in ("configuration", "branch-price"):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as directory:
                altered = deepcopy(scenario)
                if alteration == "configuration":
                    altered["configuration"]["noise"] = -1
                else:
                    altered["branches"][0]["price"] = -1
                path = Path(directory) / "invalid-scenario.json"
                path.write_text(json.dumps(altered), encoding="utf-8")
                with patch("futureos.demo.run_ticks") as ticks:
                    with self.assertRaises(ValueError):
                        run_demo(scenario_path=path)
                    ticks.assert_not_called()


if __name__ == "__main__":
    unittest.main()
