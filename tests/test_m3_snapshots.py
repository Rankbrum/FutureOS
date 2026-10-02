"""Versioned M3 snapshots preserve the legacy contract and indexed replay."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from futureos.branches import BranchConfiguration, compare_branches, create_branch
from futureos.codec import canonical_json, parse_json, simulation_from_dict, simulation_to_dict
from futureos.engine import create_simulation, run_ticks
from futureos.models import (
    Agent, Configuration, ENGINE_VERSION, Event, M3_ENGINE_VERSION, M3_SNAPSHOT_VERSION,
    Relationship, SNAPSHOT_VERSION, World,
)
from futureos.snapshots import (
    Snapshot, create_snapshot, load_snapshot, restore_snapshot, save_snapshot,
)


# Captured from the unchanged M1 transition for this manual fixture. Keeping
# the JSON and checksum literal detects accidental schema/float/hash drift.
LEGACY_SIMULATION_JSON = (
    '{"configuration":{"adoption_threshold":0.6,"interaction_probability":0.3,'
    '"model_version":"synthetic-adoption-v1","noise":0.1,"peer_weight":0.35,'
    '"price_scale":100.0,"sentiment_decay":0.95,"tick_unit":"synthetic_step",'
    '"trust_learning_rate":0.03},"id":"legacy-run","metadata":{},"metrics":{'
    '"adoption_rate":0.0,"average_intent":0.18343123370823003,"average_sentiment":0.0,'
    '"average_trust":0.5,"event_count":0,"interaction_count":0},"rng_state":{'
    '"algorithm":"splitmix64-v1","draws":3,"seed":73,"state":15755400384260043912},'
    '"seed":73,"status":"running","world":{"agents":[{"id":"a","memory":[],"metadata":{},'
    '"relationships":[{"influence":0.5,"strength":0.5,"target_agent_id":"b","trust":0.5}],'
    '"state":{"active":true,"adopted":false,"adoption_intent":0.19713888179527078,'
    '"competitor_pressure_override":null,"incentive_override":null,"price_override":null,'
    '"sentiment":0.0,"trust":0.5},"traits":{"conformity":0.5,"influence":0.5,"openness":0.5,'
    '"price_sensitivity":0.5,"risk_tolerance":0.5}},{"id":"b","memory":[],"metadata":{},'
    '"relationships":[],"state":{"active":true,"adopted":false,'
    '"adoption_intent":0.16972358562118928,"competitor_pressure_override":null,'
    '"incentive_override":null,"price_override":null,"sentiment":0.0,"trust":0.5},'
    '"traits":{"conformity":0.5,"influence":0.5,"openness":0.5,"price_sensitivity":0.5,'
    '"risk_tolerance":0.5}}],"current_tick":1,"event_log":[],"events":[{"id":"news",'
    '"metadata":{},"payload":{"sentiment_delta":0.2},"reach":0.5,"target":{'
    '"agent_ids":[],"group":null,"kind":"all"},"tick":1,"type":"NEWS"}],'
    '"global_state":{"competitor_pressure":0.0,"incentive":0.0,"price":99.9},'
    '"id":"legacy-world","metadata":{}}}'
)
LEGACY_CHECKSUM = "a0955cbba79a548e7c6747a94e3f9ccaad6e7111979d902d2c6a9462cd995959"


def fixture_world():
    return World(
        "legacy-world",
        agents=[Agent("a", relationships=[Relationship("b")]), Agent("b")],
        events=[Event("news", "NEWS", 1, {"sentiment_delta": 0.2}, reach=0.5)],
    )


def checked_envelope(schema_version, engine_version, simulation):
    """Recompute integrity so version/schema failures cannot rely on corruption."""
    integrity = {"schema_version": schema_version, "engine_version": engine_version,
                 "simulation": simulation}
    checksum = sha256(canonical_json(integrity).encode("utf-8")).hexdigest()
    identifier = f"{simulation['id']}:tick-{simulation['world']['current_tick']}:{checksum[:16]}"
    return canonical_json({**integrity, "id": identifier, "checksum": checksum})


class M3SnapshotTests(unittest.TestCase):
    def test_legacy_literal_restores_with_unchanged_json_checksum_and_transition(self):
        snapshot = Snapshot("legacy-run:tick-1:a0955cbba79a548e", SNAPSHOT_VERSION,
                            ENGINE_VERSION, LEGACY_SIMULATION_JSON, LEGACY_CHECKSUM)
        restored = restore_snapshot(snapshot)
        self.assertIsNone(restored.audit)
        self.assertEqual(restored.rng_state.draws, 3)
        original = run_ticks(create_simulation("legacy-run", 73, fixture_world()), 1)
        self.assertEqual(restored, original)
        self.assertEqual(create_snapshot(original), snapshot)
        self.assertEqual(create_snapshot(restored), snapshot)
        self.assertEqual(Snapshot.from_json(snapshot.to_json()), snapshot)
        self.assertNotIn("audit", parse_json(snapshot.simulation_json))
        self.assertEqual(run_ticks(restored, 6), run_ticks(original, 6))

    def test_codec_accepts_only_complete_legacy_field_set_without_defaults(self):
        legacy = parse_json(LEGACY_SIMULATION_JSON)
        before = deepcopy(legacy)
        restored = simulation_from_dict(legacy)
        self.assertEqual(simulation_to_dict(restored), legacy)
        self.assertEqual(legacy, before)
        incomplete = deepcopy(legacy)
        del incomplete["rng_state"]
        unknown = {**legacy, "unexpected": None}
        for candidate in (incomplete, unknown):
            with self.subTest(keys=sorted(candidate)), self.assertRaises(ValueError):
                simulation_from_dict(candidate)

    def test_m3_trace_and_summary_roundtrip_preserve_indexed_continuation(self):
        for mode in ("trace", "summary"):
            with self.subTest(mode=mode):
                source = run_ticks(create_simulation("m3-run", 73, fixture_world(),
                                                     audit_mode=mode), 3)
                before = deepcopy(source)
                snapshot = create_snapshot(source)
                self.assertEqual(snapshot.schema_version, M3_SNAPSHOT_VERSION)
                self.assertEqual(snapshot.engine_version, M3_ENGINE_VERSION)
                self.assertIsNotNone(parse_json(snapshot.simulation_json)["audit"])
                restored = restore_snapshot(Snapshot.from_json(snapshot.to_json()))
                self.assertEqual(restored, source)
                for frame in restored.audit.frames:
                    self.assertIs(type(frame.metrics["interaction_count"]), int)
                    self.assertIs(type(frame.metrics["event_count"]), int)
                self.assertEqual(source, before)
                final = run_ticks(source, 5)
                self.assertEqual(run_ticks(restored, 5), final)
                self.assertEqual(final.rng_state, source.rng_state)
                self.assertEqual(final.rng_state.draws, 0)
                self.assertEqual(create_snapshot(run_ticks(restored, 5)), create_snapshot(final))

    def test_m3_preserves_integer_values_in_accepted_float_fields(self):
        world = fixture_world()
        world.global_state.price = 70
        world.agents[0].traits.openness = 1
        world.events.append(Event("offer", "PRICE_CHANGE", 0, {"price": 70}))
        source = run_ticks(create_simulation("m3-run", 73, world,
                                             Configuration(noise=0), audit_mode="trace"), 3)
        snapshot = create_snapshot(source)
        restored = restore_snapshot(snapshot)
        self.assertEqual(simulation_to_dict(restored), simulation_to_dict(source))
        self.assertIs(type(restored.world.global_state.price), int)
        self.assertIs(type(restored.world.agents[0].traits.openness), int)
        self.assertIs(type(restored.configuration.noise), int)
        self.assertEqual(create_snapshot(restored), snapshot)
        self.assertEqual(run_ticks(restored, 5), run_ticks(source, 5))

    def test_checksum_valid_version_and_audit_mismatches_are_rejected(self):
        legacy = parse_json(LEGACY_SIMULATION_JSON)
        modern = simulation_to_dict(create_simulation("m3-run", 73, fixture_world(),
                                                      audit_mode="trace"))
        cases = [
            (1, M3_ENGINE_VERSION, legacy),
            (2, ENGINE_VERSION, modern),
            (1, ENGINE_VERSION, {**legacy, "audit": None}),
            (1, ENGINE_VERSION, modern),
            (2, M3_ENGINE_VERSION, legacy),
            (2, M3_ENGINE_VERSION, {**modern, "audit": None}),
            (999, "futureos-kernel-v999", legacy),
            (True, ENGINE_VERSION, legacy),
        ]
        for schema, engine, data in cases:
            with self.subTest(schema=schema, engine=engine,
                              audit_present="audit" in data), self.assertRaises(ValueError):
                Snapshot.from_json(checked_envelope(schema, engine, data))

    def test_m3_typed_dictionary_values_are_strict(self):
        source = run_ticks(create_simulation("m3-run", 73, fixture_world(),
                                             audit_mode="trace"), 2)
        modern = simulation_to_dict(source)
        for field, replacement in (("agent_hashes", {"a": []}),
                                   ("metrics", {"adoption_rate": True})):
            with self.subTest(field=field):
                invalid = deepcopy(modern)
                invalid["audit"]["frames"][0][field] = replacement
                with self.assertRaises(ValueError):
                    Snapshot.from_json(checked_envelope(2, M3_ENGINE_VERSION, invalid))

    def test_checksum_valid_envelope_cannot_hide_changed_audit_chain(self):
        source = run_ticks(create_simulation("m3-run", 73, fixture_world(),
                                             audit_mode="trace"), 2)
        modern = simulation_to_dict(source)
        for mutation in ("trajectory_hash", "frame_hash", "record_payload"):
            with self.subTest(mutation=mutation):
                invalid = deepcopy(modern)
                if mutation == "trajectory_hash":
                    invalid["audit"]["trajectory_hash"] = "0" * 64
                elif mutation == "frame_hash":
                    invalid["audit"]["frames"][0]["state_hash"] = "0" * 64
                else:
                    invalid["audit"]["records"][0]["payload"]["changed"] = True
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    Snapshot.from_json(checked_envelope(2, M3_ENGINE_VERSION, invalid))

    def test_m3_branches_and_restorations_keep_independent_audit_state(self):
        source = run_ticks(create_simulation("m3-run", 73, fixture_world(),
                                             audit_mode="trace"), 3)
        snapshot = create_snapshot(source)
        snapshot_before = snapshot.to_json()
        first = create_branch(snapshot, BranchConfiguration("A"))
        second = create_branch(snapshot, BranchConfiguration("B"))
        self.assertEqual(first.simulation.audit, source.audit)
        self.assertEqual(second.simulation.audit, source.audit)
        compare_branches([first, second])
        second_before = deepcopy(second)
        first.simulation.audit.frames[0].agent_hashes["a"] = "changed"
        first.simulation.audit.records[0].payload["changed"] = ["isolated"]
        self.assertEqual(second, second_before)
        self.assertEqual(snapshot.to_json(), snapshot_before)
        self.assertEqual(restore_snapshot(snapshot), source)
        siblings = {name: create_branch(snapshot, BranchConfiguration(name)) for name in "AB"}
        for name in "BA":
            siblings[name].simulation = run_ticks(siblings[name].simulation, 4)
        self.assertEqual(siblings["A"].simulation.audit, siblings["B"].simulation.audit)
        compare_branches(list(siblings.values()))

    def test_m3_disk_replay_in_another_process_matches_each_committed_tick(self):
        source = run_ticks(create_simulation("m3-run", 73, fixture_world(),
                                             audit_mode="trace"), 3)
        with tempfile.TemporaryDirectory() as directory:
            origin_path = Path(directory) / "origin.json"
            output_path = Path(directory) / "continuation.json"
            origin = create_snapshot(source)
            save_snapshot(origin, origin_path)
            script = (
                "from pathlib import Path; import sys; "
                "from futureos.codec import canonical_json,simulation_to_dict; "
                "from futureos.engine import run_ticks; "
                "from futureos.snapshots import load_snapshot,restore_snapshot; "
                "state=restore_snapshot(load_snapshot(sys.argv[1])); states=[]; "
                "exec('for _ in range(5):\\n state=run_ticks(state,1)\\n states.append(simulation_to_dict(state))'); "
                "Path(sys.argv[2]).write_text(canonical_json(states),encoding='utf-8')"
            )
            result = subprocess.run([sys.executable, "-c", script,
                                     str(origin_path), str(output_path)],
                                    cwd=Path(__file__).resolve().parents[1],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = []
            state = source
            for _ in range(5):
                state = run_ticks(state, 1)
                expected.append(simulation_to_dict(state))
            self.assertEqual(parse_json(output_path.read_text(encoding="utf-8")), expected)
            self.assertEqual(load_snapshot(origin_path), origin)


if __name__ == "__main__":
    unittest.main()
