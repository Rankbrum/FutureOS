"""Behavioral contracts for replayable M3 run artifacts and branch evidence."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.audit import _produced_bytes, profile_audit
from futureos.audit_runs import (
    HASH_FIELDS,
    compare_run_divergence,
    load_run_artifact,
    replay_run,
    run_audit_experiment,
    save_audit_experiment,
    trajectory_from_run,
    validate_run_artifact,
)
from futureos.codec import canonical_json, parse_json


def scenario_fixture():
    return {
        "schema_version": 1, "id": "audit-contract-fixture-v1", "population_size": 3,
        "initial_price": 110.0, "initial_ticks": 1, "branch_ticks": 2,
        "configuration": {"adoption_threshold": 0.52},
        "events": [{"id": "news-0", "type": "NEWS", "tick": 0,
                    "payload": {"sentiment_delta": 0.08}, "reach": 0.5}],
        "branches": [
            {"id": "A", "label": "Preço 70", "price": 70.0, "incentive": 0.0},
            {"id": "B", "label": "Preço 99,90", "price": 99.9, "incentive": 0.0},
            {"id": "C", "label": "Preço 70 e incentivo 20", "price": 70.0, "incentive": 20.0},
        ],
    }


class AuditRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = run_audit_experiment(scenario_fixture(), [2026], ticks=3, mode="summary")
        cls.trace = run_audit_experiment(scenario_fixture(), [2026], ticks=3, mode="trace")

    def test_summary_and_trace_have_same_identity_and_behavioral_hashes(self):
        self.assertEqual(self.summary.manifest["experimentId"], self.trace.manifest["experimentId"])
        for summary, trace in zip(self.summary.runs, self.trace.runs, strict=True):
            self.assertEqual(summary["runId"], trace["runId"])
            self.assertEqual(summary["frames"], trace["frames"])
            self.assertEqual(summary["traceCount"], trace["traceCount"])
            self.assertEqual(summary["metrics"], trace["metrics"])
            self.assertEqual({key: summary[key] for key in HASH_FIELDS},
                             {key: trace[key] for key in HASH_FIELDS})
            self.assertNotEqual(summary["originSnapshot"]["checksum"], trace["originSnapshot"]["checksum"])

    def test_same_seed_and_reordered_inputs_reproduce_artifacts(self):
        original = scenario_fixture()
        reordered = deepcopy(original)
        reordered["branches"].reverse()
        first = run_audit_experiment(original, [3, 1], ticks=2, mode="summary")
        second = run_audit_experiment(reordered, [1, 3], ticks=2, mode="summary")
        self.assertEqual(first, second)
        self.assertEqual(len({run["runId"] for run in first.runs}), 6)
        self.assertEqual(original, scenario_fixture())

    def test_identity_changes_with_protocol_content(self):
        scenario = scenario_fixture()
        scenario["configuration"]["noise"] = 0.05
        altered = run_audit_experiment(scenario, [2026], ticks=3)
        self.assertNotEqual(altered.manifest["experimentId"], self.summary.manifest["experimentId"])
        self.assertNotEqual(altered.runs[0]["runId"], self.summary.runs[0]["runId"])

    def test_summary_retains_compact_frames_and_no_full_trace_or_snapshot(self):
        for run in self.summary.runs:
            self.assertEqual(run["records"], [])
            self.assertEqual([frame["tick"] for frame in run["frames"]], [0, 1, 2])
            self.assertEqual([frame["stateTick"] for frame in run["frames"]], [1, 2, 3])
            self.assertEqual({frame["tickUnit"] for frame in run["frames"]}, {"synthetic_step"})
            self.assertEqual({frame["activeCount"] for frame in run["frames"]}, {3})
            self.assertGreater(run["traceCount"], 0)
            self.assertNotIn("simulation", run["originSnapshot"])
            self.assertNotIn("world", run)
        self.assertTrue(all(run["records"] for run in self.trace.runs))

    def test_branches_share_one_exact_origin_per_seed(self):
        origins = [run["originSnapshot"] for run in self.trace.runs]
        self.assertEqual(origins, [origins[0]] * 3)
        self.assertEqual({run["branchId"] for run in self.trace.runs}, {"A", "B", "C"})

    def test_replay_matches_all_hashes_in_both_modes(self):
        for result in (self.summary, self.trace):
            with self.subTest(mode=result.manifest["mode"]):
                report = replay_run(result.runs[0])
                self.assertTrue(report["matched"])
                self.assertIsNone(report["firstDivergence"])
                self.assertTrue(all(row["matched"] for row in report["hashes"].values()))

    def test_replay_reports_a_modified_hash_without_claiming_a_tick(self):
        run = deepcopy(self.summary.runs[0])
        run["trajectoryHash"] = "0" * 64
        report = replay_run(run)
        self.assertFalse(report["matched"])
        self.assertEqual(report["firstDivergence"]["kind"], "hash")
        self.assertEqual(report["firstDivergence"]["field"], "trajectoryHash")
        self.assertFalse(report["hashes"]["trajectoryHash"]["matched"])

    def test_replay_reports_first_modified_trace_record(self):
        run = deepcopy(self.trace.runs[0])
        index = 2
        run["records"][index]["payload"]["audit_tamper"] = True
        report = replay_run(run)
        self.assertFalse(report["matched"])
        self.assertEqual(report["firstDivergence"]["kind"], "record")
        self.assertEqual(report["firstDivergence"]["index"], index)
        self.assertEqual(report["firstDivergence"]["tick"], run["records"][index]["tick"])

    def test_replay_reports_first_modified_summary_frame(self):
        run = deepcopy(self.summary.runs[0])
        run["frames"][1]["metrics"]["average_trust"] += 0.001
        report = replay_run(run)
        self.assertFalse(report["matched"])
        self.assertEqual(report["firstDivergence"]["kind"], "frame")
        self.assertEqual(report["firstDivergence"]["tick"], 1)

    def test_replay_prefers_earlier_frame_to_later_record_divergence(self):
        run = deepcopy(self.trace.runs[0])
        record = next(record for record in run["records"] if record["tick"] == 2)
        record["payload"]["audit_tamper"] = True
        run["frames"][1]["metrics"]["average_trust"] += 0.001
        report = replay_run(run)
        self.assertEqual(report["firstDivergence"]["kind"], "frame")
        self.assertEqual(report["firstDivergence"]["tick"], 1)

    def test_replay_prefers_record_within_same_divergent_tick(self):
        run = deepcopy(self.trace.runs[0])
        record = next(record for record in run["records"] if record["tick"] == 1)
        record["payload"]["audit_tamper"] = True
        run["frames"][1]["metrics"]["average_trust"] += 0.001
        report = replay_run(run)
        self.assertEqual(report["firstDivergence"]["kind"], "record")
        self.assertEqual(report["firstDivergence"]["tick"], 1)

    def test_loaded_artifact_recovers_agent_trajectory_without_mutating_trace(self):
        run = parse_json(canonical_json(self.trace.runs[0]))
        agent_id = next(iter(run["frames"][0]["agentHashes"]))
        rows = trajectory_from_run(run, agent_id)
        self.assertTrue(rows)
        self.assertTrue(any(record["kind"] == "adoption_decision" for record in rows))
        for record in rows:
            self.assertTrue(record["entity"] == f"agent:{agent_id}"
                            or record["payload"].get("source_agent_id") == agent_id
                            or record["payload"].get("target_agent_id") == agent_id
                            or agent_id in record["payload"].get("target_ids", []))
        unchanged = deepcopy(run)
        rows[0]["payload"]["changed_by_reader"] = True
        self.assertEqual(run, unchanged)
        with self.assertRaisesRegex(ValueError, "trace mode"):
            trajectory_from_run(self.summary.runs[0], agent_id)
        with self.assertRaisesRegex(ValueError, "Unknown agent"):
            trajectory_from_run(run, "absent")

    def test_unsupported_versions_are_rejected_before_execution(self):
        for field in ("artifactVersion", "engineVersion", "rngVersion", "traceVersion", "replayProtocol"):
            with self.subTest(field=field):
                run = deepcopy(self.summary.runs[0])
                run[field] = 99 if field == "artifactVersion" else "unsupported-v99"
                with patch("futureos.audit_runs._origin") as origin:
                    with self.assertRaisesRegex(ValueError, "Unsupported"):
                        replay_run(run)
                    origin.assert_not_called()

    def test_changed_configuration_is_reported_as_context_before_execution(self):
        run = deepcopy(self.summary.runs[0])
        run["configuration"]["noise"] = 0.08
        with patch("futureos.audit_runs._origin") as origin:
            report = replay_run(run)
            origin.assert_not_called()
        self.assertFalse(report["matched"])
        self.assertEqual(report["firstDivergence"]["kind"], "context")
        self.assertEqual(report["firstDivergence"]["field"], "configuration")

    def test_changed_origin_is_reported_as_context(self):
        run = deepcopy(self.summary.runs[0])
        run["originSnapshot"]["checksum"] = "0" * 64
        report = replay_run(run)
        self.assertFalse(report["matched"])
        self.assertEqual(report["firstDivergence"]["field"], "originSnapshot")

    def test_branch_divergence_identifies_tick_agents_metrics_and_mechanisms(self):
        left, right = self.trace.runs[:2]
        report = compare_run_divergence(left, right)
        self.assertFalse(report["identical"])
        self.assertEqual(report["firstTick"], left["branchPoint"])
        self.assertTrue(report["agents"])
        self.assertIn("average_intent", report["metrics"])
        self.assertTrue(report["mechanisms"])
        self.assertTrue(report["detailAvailable"])
        self.assertIn("not real-world causality", report["interpretation"])

    def test_branch_divergence_in_summary_explains_missing_mechanism_detail(self):
        report = compare_run_divergence(*self.summary.runs[:2])
        self.assertEqual(report["firstTick"], 1)
        self.assertEqual(report["mechanisms"], [])
        self.assertFalse(report["detailAvailable"])
        self.assertIn("require trace", report["detailStatus"])

    def test_identical_run_has_no_detected_divergence(self):
        run = self.trace.runs[0]
        report = compare_run_divergence(run, deepcopy(run))
        self.assertTrue(report["identical"])
        self.assertIsNone(report["firstTick"])
        self.assertEqual(report["agents"], [])
        self.assertEqual(report["metrics"], {})
        self.assertEqual(report["mechanisms"], [])

    def test_wrong_origin_or_seed_is_rejected(self):
        for field in ("origin", "seed"):
            with self.subTest(field=field):
                right = deepcopy(self.summary.runs[1])
                if field == "origin":
                    right["originSnapshot"]["checksum"] = "f" * 64
                else:
                    right["seed"] += 1
                with self.assertRaisesRegex(ValueError, "same.*origin|same seed"):
                    compare_run_divergence(self.summary.runs[0], right)

    def test_origin_only_horizon_has_no_committed_branch_divergence(self):
        result = run_audit_experiment(scenario_fixture(), [2026], ticks=1)
        self.assertEqual({run["ticks"] for run in result.runs}, {1})
        self.assertTrue(all(report["identical"] for report in result.divergences))
        self.assertTrue(replay_run(result.runs[0])["matched"])

    def test_json_roundtrip_and_storage_are_strict_and_canonical(self):
        self.assertEqual(parse_json(canonical_json(self.trace.runs[0])), self.trace.runs[0])
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "audit"
            save_audit_experiment(self.trace, destination)
            files = [path for path in destination.rglob("*") if path.is_file()]
            self.assertEqual(len(files), 5)
            self.assertEqual(sum(path.stat().st_size for path in files), _produced_bytes(self.trace))
            self.assertEqual(load_run_artifact(destination / "runs" / "run-000001.json"), self.trace.runs[0])
            for path in files:
                contents = path.read_text(encoding="utf-8")
                self.assertEqual(contents, canonical_json(parse_json(contents)) + "\n")
            with self.assertRaisesRegex(ValueError, "absent or empty"):
                save_audit_experiment(self.trace, destination)

    def test_unknown_fields_nonfinite_json_and_summary_trace_are_rejected(self):
        mutations = [lambda run: run.update({"unknown": True}),
                     lambda run: run["metrics"].update({"average_trust": float("nan")}),
                     lambda run: run["records"].append(deepcopy(self.trace.runs[0]["records"][0]))]
        for mutate in mutations:
            run = deepcopy(self.summary.runs[0])
            mutate(run)
            with self.assertRaises(ValueError):
                validate_run_artifact(run)

    def test_invalid_record_delta_frame_population_and_metrics_are_rejected(self):
        corruptions = [
            lambda run: run["records"][0].update({"kind": "unknown"}),
            lambda run: next(record for record in run["records"]
                             if record["kind"] == "state_changed")["payload"].pop("before"),
            lambda run: run["frames"][1]["agentHashes"].pop(next(iter(run["frames"][1]["agentHashes"]))),
            lambda run: run["frames"][1]["metrics"].update({"average_trust": 2.0}),
            lambda run: run["frames"][1]["metrics"].update({"event_count": 0.5}),
            lambda run: run["frames"][1].update({"activeCount": 10}),
            lambda run: run["frames"][1].update({"tickUnit": "day"}),
            lambda run: run["frames"][1].update({"stateTick": 1}),
        ]
        for corrupt in corruptions:
            run = deepcopy(self.trace.runs[0])
            corrupt(run)
            with self.assertRaises(ValueError):
                validate_run_artifact(run)

    def test_invalid_mode_and_horizon_fail_before_any_ticks(self):
        for options in ({"mode": "full"}, {"ticks": 0}, {"ticks": True}):
            with self.subTest(options=options), patch("futureos.audit_runs.run_ticks") as execute:
                with self.assertRaises(ValueError):
                    run_audit_experiment(scenario_fixture(), [2026], **options)
                execute.assert_not_called()

    def test_profile_costs_are_separate_and_summary_trace_hashes_match(self):
        report, results = profile_audit(2026, [1, 2], scenario=scenario_fixture())
        self.assertEqual([row["ticks"] for row in report["measurements"]], [1, 2])
        for measurement, pair in zip(report["measurements"], results, strict=True):
            self.assertTrue(measurement["hashesEqual"])
            self.assertEqual(measurement["summary"]["traceRecordsStored"], 0)
            self.assertGreater(measurement["trace"]["traceRecordsStored"], 0)
            self.assertGreater(measurement["sizeRatioTraceToSummary"], 1)
            for result in pair.values():
                self.assertNotIn("seconds", result.manifest)
                self.assertTrue(all("seconds" not in run for run in result.runs))


if __name__ == "__main__":
    unittest.main()
