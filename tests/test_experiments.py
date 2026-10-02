"""Behavioral contracts for local batches and matched-seed comparisons."""

from copy import deepcopy
import math
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest.mock import patch

from futureos.codec import canonical_json, parse_json
from futureos.experiments import (
    aggregate_runs,
    compare_runs,
    load_experiment_scenario,
    run_experiment,
    save_experiment,
    summarize_experiment,
)


METRICS = (
    "adoption_rate", "average_trust", "average_sentiment", "average_intent",
    "interaction_count", "event_count",
)


def small_scenario():
    """Exercise the real kernel without repeating a hundred-seed benchmark."""
    return {
        "schema_version": 1,
        "id": "batch-contract-fixture-v1",
        "population_size": 3,
        "initial_price": 110.0,
        "initial_ticks": 1,
        "branch_ticks": 2,
        "configuration": {"adoption_threshold": 0.52},
        "events": [
            {"id": "news-0", "type": "NEWS", "tick": 0,
             "payload": {"sentiment_delta": 0.08}, "reach": 0.5},
        ],
        "branches": [
            {"id": "A", "label": "Price 70", "price": 70.0, "incentive": 0.0},
            {"id": "B", "label": "Price 99.90", "price": 99.9, "incentive": 0.0},
            {"id": "C", "label": "Price 70 plus incentive", "price": 70.0,
             "incentive": 20.0},
        ],
    }


def synthetic_metric_runs():
    """Keep genuine identities/origins; provide calculable summary values."""
    runs = run_experiment(small_scenario(), [1, 2, 3], ticks=3).runs
    values = {
        "A": [0.0, 1 / 3, 2 / 3],
        "B": [1 / 3, 1 / 3, 1 / 3],
        "C": [2 / 3, 2 / 3, 2 / 3],
    }
    for run in runs:
        index = run["seed"] - 1
        value = values[run["branch_id"]][index]
        run["metrics"] = {
            "adoption_rate": value,
            "average_trust": value,
            "average_sentiment": value - 1 / 3,
            "average_intent": value,
            "interaction_count": index + 1,
            "event_count": index,
        }
    return runs


def deterministic_fields(result):
    return (result.manifest, result.runs, result.aggregate, result.comparison)


class BatchExecutionTests(unittest.TestCase):
    def test_repeated_seeds_reproduce_every_deterministic_report(self):
        first = run_experiment(small_scenario(), [3, 1, 2], ticks=3)
        second = run_experiment(small_scenario(), [3, 1, 2], ticks=3)
        self.assertEqual(deterministic_fields(first), deterministic_fields(second))
        self.assertEqual(len(first.runs), 9)
        self.assertEqual(len({run["run_id"] for run in first.runs}), 9)
        self.assertEqual({run["ticks"] for run in first.runs}, {3})

    def test_seed_and_branch_input_order_do_not_change_results(self):
        scenario = small_scenario()
        first = run_experiment(scenario, [3, 1, 2], ticks=3)
        reordered = deepcopy(scenario)
        reordered["branches"].reverse()
        second = run_experiment(reordered, [2, 3, 1], ticks=3)
        self.assertEqual(first.aggregate, second.aggregate)
        self.assertEqual(first.comparison, second.comparison)
        self.assertEqual(first.runs, second.runs)
        self.assertEqual(first.manifest, second.manifest)

    def test_runs_share_one_origin_only_within_the_same_seed(self):
        result = run_experiment(small_scenario(), [1, 2, 3], ticks=3)
        origins = []
        for seed in (1, 2, 3):
            rows = [run for run in result.runs if run["seed"] == seed]
            self.assertEqual({run["branch_id"] for run in rows}, {"A", "B", "C"})
            self.assertEqual(len({run["origin_snapshot_id"] for run in rows}), 1)
            self.assertEqual(len({run["origin_checksum"] for run in rows}), 1)
            self.assertEqual({run["branch_point"] for run in rows}, {1})
            self.assertTrue(all(run["active_agent_ids"] == rows[0]["active_agent_ids"]
                                for run in rows))
            origins.append(rows[0]["origin_snapshot_id"])
        self.assertEqual(len(set(origins)), 3)

    def test_caller_inputs_and_individual_run_reports_are_isolated(self):
        scenario = small_scenario()
        unchanged = deepcopy(scenario)
        seeds = [3, 1, 2]
        result = run_experiment(scenario, seeds, ticks=3)
        self.assertEqual(scenario, unchanged)
        self.assertEqual(seeds, [3, 1, 2])
        other_rows = deepcopy(result.runs[1:])
        aggregate = deepcopy(result.aggregate)
        manifest = deepcopy(result.manifest)
        result.runs[0]["metrics"]["adoption_rate"] = 0.987
        result.runs[0]["configuration"]["noise"] = 0.987
        result.runs[0]["active_agent_ids"].append("outside-run")
        self.assertEqual(result.runs[1:], other_rows)
        self.assertEqual(result.aggregate, aggregate)
        self.assertEqual(result.manifest, manifest)
        fresh = run_experiment(scenario, seeds, ticks=3)
        self.assertEqual(fresh.aggregate, aggregate)

    def test_every_invalid_seed_list_fails_before_any_tick(self):
        for seeds in ([], [1, 1], [True], [-1], [1 << 64], [1.5], [None]):
            with self.subTest(seeds=seeds), patch("futureos.experiments.run_ticks") as ticks:
                with self.assertRaises(ValueError):
                    run_experiment(small_scenario(), seeds, ticks=3)
                ticks.assert_not_called()

    def test_invalid_horizon_fails_before_any_tick(self):
        for horizon in (0, True, -1, 1.5):
            with self.subTest(horizon=horizon), patch("futureos.experiments.run_ticks") as ticks:
                with self.assertRaises(ValueError):
                    run_experiment(small_scenario(), [1, 2], ticks=horizon)
                ticks.assert_not_called()

    def test_invalid_late_intervention_and_scenario_fail_before_any_tick(self):
        variants = []
        negative = small_scenario()
        negative["branches"][-1]["incentive"] = -1
        variants.append(negative)
        configuration = small_scenario()
        configuration["configuration"]["noise"] = math.nan
        variants.append(configuration)
        unknown_event = small_scenario()
        unknown_event["events"].append({
            "id": "bad-late-event", "type": "UNKNOWN", "tick": 2,
            "payload": {}, "reach": 1.0,
        })
        variants.append(unknown_event)
        duplicate = small_scenario()
        duplicate["branches"][-1]["id"] = "A"
        variants.append(duplicate)
        for index, scenario in enumerate(variants):
            with self.subTest(index=index), patch("futureos.experiments.run_ticks") as ticks:
                with self.assertRaises(ValueError):
                    run_experiment(scenario, [1, 2], ticks=3)
                ticks.assert_not_called()

    def test_population_overrides_are_explicit_reproducible_and_validated(self):
        overrides = {"price_sensitivity": 0.5, "trust": 0.6}
        unchanged = deepcopy(overrides)
        first = run_experiment(small_scenario(), [1, 2], ticks=3,
                               population_overrides=overrides)
        second = run_experiment(small_scenario(), [2, 1], ticks=3,
                                population_overrides=overrides)
        self.assertEqual(overrides, unchanged)
        self.assertEqual(deterministic_fields(first), deterministic_fields(second))
        self.assertEqual(first.manifest["population_overrides"], overrides)
        self.assertTrue(all(run["population_overrides"] == overrides for run in first.runs))
        baseline = run_experiment(small_scenario(), [1, 2], ticks=3)
        self.assertNotEqual(first.manifest["experiment_id"], baseline.manifest["experiment_id"])
        for invalid in ({"unknown": 0.5}, {"trust": -0.1}, {"openness": True},
                        {"influence": math.inf}, {"risk_tolerance": 1.1}):
            with self.subTest(overrides=invalid), patch("futureos.experiments.run_ticks") as ticks:
                with self.assertRaises(ValueError):
                    run_experiment(small_scenario(), [1, 2], ticks=3,
                                   population_overrides=invalid)
                ticks.assert_not_called()

    def test_scenario_file_and_dict_have_equivalent_execution(self):
        scenario = small_scenario()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            path.write_text(canonical_json(scenario), encoding="utf-8")
            self.assertEqual(load_experiment_scenario(path),
                             load_experiment_scenario(scenario))
            from_file = run_experiment(path, [1, 2], ticks=3)
        from_dict = run_experiment(scenario, [1, 2], ticks=3)
        self.assertEqual(deterministic_fields(from_file), deterministic_fields(from_dict))


class AggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = synthetic_metric_runs()

    def test_all_six_metrics_have_correct_population_statistics_and_distribution(self):
        aggregate = aggregate_runs(self.runs)
        self.assertEqual(set(aggregate["metrics"]), set(METRICS))
        self.assertEqual(aggregate["standard_deviation"], "population")
        by_branch = {branch["branch_id"]: branch for branch in aggregate["branches"]}
        for branch_id in ("A", "B", "C"):
            rows = sorted((run for run in self.runs if run["branch_id"] == branch_id),
                          key=lambda run: run["seed"])
            for metric in METRICS:
                values = [row["metrics"][metric] for row in rows]
                actual = by_branch[branch_id]["metrics"][metric]
                with self.subTest(branch=branch_id, metric=metric):
                    self.assertEqual(actual["count"], 3)
                    self.assertAlmostEqual(actual["mean"], statistics.mean(values))
                    self.assertAlmostEqual(actual["median"], statistics.median(values))
                    self.assertEqual(actual["min"], min(values))
                    self.assertEqual(actual["max"], max(values))
                    self.assertAlmostEqual(actual["variance"], statistics.pvariance(values))
                    self.assertAlmostEqual(actual["standard_deviation"], statistics.pstdev(values))
                    self.assertEqual(actual["distribution"], [
                        {"seed": row["seed"], "run_id": row["run_id"],
                         "value": row["metrics"][metric]} for row in rows
                    ])

    def test_single_seed_variance_and_deviation_are_zero(self):
        aggregate = aggregate_runs([row for row in self.runs if row["seed"] == 1])
        for branch in aggregate["branches"]:
            for metric in branch["metrics"].values():
                self.assertEqual(metric["count"], 1)
                self.assertEqual(metric["variance"], 0)
                self.assertEqual(metric["standard_deviation"], 0)

    def test_summary_order_is_independent_of_run_order(self):
        self.assertEqual(aggregate_runs(self.runs), aggregate_runs(list(reversed(self.runs))))
        self.assertEqual(compare_runs(self.runs), compare_runs(list(reversed(self.runs))))

    def test_empty_duplicate_and_nonfinite_run_summaries_are_rejected(self):
        duplicate = deepcopy(self.runs)
        duplicate.append(deepcopy(duplicate[0]))
        nonfinite = deepcopy(self.runs)
        nonfinite[0]["metrics"]["average_trust"] = math.inf
        missing_metric = deepcopy(self.runs)
        del missing_metric[0]["metrics"]["average_trust"]
        for runs in ([], duplicate, nonfinite, missing_metric):
            for operation in (aggregate_runs, compare_runs):
                with self.subTest(operation=operation.__name__, size=len(runs)):
                    with self.assertRaises(ValueError):
                        operation(runs)

    def test_missing_provenance_and_changed_intervention_are_rejected(self):
        provenance = ("intervention", "experiment_id", "scenario_checksum", "rng_algorithm",
                      "scenario_schema_version", "population_overrides", "final_snapshot_id",
                      "final_checksum", "status", "branch_label")
        for field in provenance:
            incomplete = deepcopy(self.runs)
            del incomplete[-1][field]
            for operation in (aggregate_runs, compare_runs):
                with self.subTest(field=field, operation=operation.__name__):
                    with self.assertRaises(ValueError):
                        operation(incomplete)
        altered = deepcopy(self.runs)
        altered[-1]["intervention"]["price"] += 1
        for operation in (aggregate_runs, compare_runs):
            with self.subTest(operation=operation.__name__), self.assertRaises(ValueError):
                operation(altered)

    def test_intervention_labels_and_schema_versions_must_match(self):
        for field, value in (("branch_label", "different label"),
                             ("scenario_schema_version", 2)):
            altered = deepcopy(self.runs)
            altered[-1][field] = value
            for operation in (aggregate_runs, compare_runs):
                with self.subTest(field=field, operation=operation.__name__):
                    with self.assertRaises(ValueError):
                        operation(altered)

    def test_invalid_configuration_overrides_and_intervention_cannot_be_reaggregated(self):
        variants = []
        configuration = deepcopy(self.runs)
        for run in configuration:
            run["configuration"]["noise"] = -1
        variants.append(configuration)
        missing_configuration = deepcopy(self.runs)
        for run in missing_configuration:
            run["configuration"] = {}
        variants.append(missing_configuration)
        overrides = deepcopy(self.runs)
        for run in overrides:
            run["population_overrides"] = {"unknown": 0.5}
        variants.append(overrides)
        intervention = deepcopy(self.runs)
        for run in intervention:
            if run["branch_id"] == "A":
                run["intervention"]["price"] = -1
        variants.append(intervention)
        identity = deepcopy(self.runs)
        for run in identity:
            if run["branch_id"] == "A":
                run["intervention"]["id"] = "B"
        variants.append(identity)
        for index, rows in enumerate(variants):
            for operation in (aggregate_runs, compare_runs):
                with self.subTest(index=index, operation=operation.__name__):
                    with self.assertRaises(ValueError):
                        operation(rows)


class PairedComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = synthetic_metric_runs()

    def test_comparison_counts_greater_lower_and_equal_by_seed(self):
        comparison = compare_runs(self.runs)
        self.assertTrue(comparison["paired"])
        pairs = {(pair["left_branch_id"], pair["right_branch_id"]): pair
                 for pair in comparison["pairs"]}
        self.assertEqual(set(pairs), {("A", "B"), ("A", "C"), ("B", "C")})
        pair = pairs[("A", "B")]
        self.assertEqual(pair["count"], 3)
        adoption = pair["metrics"]["adoption_rate"]
        self.assertEqual(adoption["left_greater"], 1)
        self.assertEqual(adoption["right_greater"], 1)
        self.assertEqual(adoption["ties"], 1)
        self.assertAlmostEqual(adoption["delta_mean"], 0)
        self.assertAlmostEqual(adoption["delta_median"], 0)
        self.assertEqual(adoption["paired_deltas"], [
            {"seed": 1, "delta": -1 / 3},
            {"seed": 2, "delta": 0.0},
            {"seed": 3, "delta": 1 / 3},
        ])
        self.assertTrue(comparison["limitations"])

    def test_incomplete_seed_pairing_is_rejected(self):
        missing = [run for run in self.runs
                   if not (run["seed"] == 3 and run["branch_id"] == "B")]
        with self.assertRaises(ValueError):
            compare_runs(missing)

    def test_incompatible_origins_versions_horizons_and_eligibility_are_rejected(self):
        changes = {
            "origin_snapshot_id": "other-origin",
            "origin_checksum": "0" * 64,
            "scenario_version": "other-scenario-v1",
            "engine_version": "other-engine",
            "model_version": "other-model",
            "branch_point": 0,
            "ticks": 4,
            "population_size": 4,
            "active_agent_ids": ["outside-population"],
        }
        for field, value in changes.items():
            altered = deepcopy(self.runs)
            altered[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                compare_runs(altered)
        altered = deepcopy(self.runs)
        altered[0]["configuration"]["noise"] = 0.987
        with self.assertRaises(ValueError):
            compare_runs(altered)


class BatchArtifactTests(unittest.TestCase):
    def test_structured_result_is_strict_json_and_saves_minimal_indexed_runs(self):
        result = run_experiment(small_scenario(), [1, 2], ticks=3)
        for report in (result.manifest, result.runs, result.aggregate,
                       result.comparison, result.benchmark):
            self.assertEqual(parse_json(canonical_json(report)), report)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "experiment"
            save_experiment(result, destination)
            for filename, expected in (
                ("manifest.json", result.manifest),
                ("aggregate.json", result.aggregate),
                ("comparison.json", result.comparison),
                ("benchmark.json", result.benchmark),
                ("sensitivity.json", {"status": "not_requested"}),
            ):
                saved = parse_json((destination / filename).read_text(encoding="utf-8"))
                self.assertEqual(saved, expected)
            files = sorted((destination / "runs").glob("*.json"))
            self.assertEqual(len(files), 6)
            saved_runs = [parse_json(path.read_text(encoding="utf-8")) for path in files]
            self.assertEqual(saved_runs, result.runs)
            self.assertEqual(list(destination.rglob("*.snapshot.json")), [])
        summary = summarize_experiment(result)
        self.assertIsInstance(summary, str)
        self.assertTrue(all(branch in summary for branch in ("A", "B", "C")))

    def test_save_rejects_nonempty_destination_and_preserves_existing_files(self):
        result = run_experiment(small_scenario(), [1], ticks=3)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            marker = destination / "existing.txt"
            marker.write_text("preserve", encoding="utf-8")
            with self.assertRaises((ValueError, FileExistsError)):
                save_experiment(result, destination)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
            self.assertEqual(list(destination.iterdir()), [marker])


if __name__ == "__main__":
    unittest.main()
