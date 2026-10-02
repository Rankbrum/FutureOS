"""OAT preflight, independence, paired deltas, and compact deterministic reports."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from futureos.codec import canonical_json, parse_json
from futureos.demo import DEFAULT_SCENARIO
from futureos.experiments import load_experiment_scenario, save_experiment
from futureos.sensitivity import load_sensitivity_protocol, run_sensitivity


def scenario():
    data = load_experiment_scenario(DEFAULT_SCENARIO)
    data["population_size"] = 4
    data["initial_ticks"] = 2
    data["branch_ticks"] = 2
    data["events"][0]["tick"] = 0
    data["events"][1]["tick"] = 3
    return data


def protocol(target="population", parameter="price_sensitivity", baseline=0.5,
             values=None, **selector):
    return {"schema_version": 1, "variations": [
        {"target": target, "parameter": parameter, "baseline": baseline,
         "values": [0.2, 0.5, 0.8] if values is None else values, **selector},
    ]}


class SensitivityTests(unittest.TestCase):
    def test_population_variants_are_deterministic_independent_and_explicit(self):
        source, specification = scenario(), protocol()
        untouched_source, untouched_protocol = deepcopy(source), deepcopy(specification)
        first = run_sensitivity(source, [2, 1], specification)
        repeated = run_sensitivity(source, [1, 2], specification)
        self.assertEqual(first.manifest, repeated.manifest)
        self.assertEqual(first.runs, repeated.runs)
        self.assertEqual(first.aggregate, repeated.aggregate)
        self.assertEqual(first.sensitivity, repeated.sensitivity)
        self.assertEqual(source, untouched_source)
        self.assertEqual(specification, untouched_protocol)
        analysis = first.sensitivity["analyses"][0]
        self.assertEqual(analysis["baseline_experiment"]["manifest"]["population_overrides"],
                         {"price_sensitivity": 0.5})
        self.assertEqual(first.manifest["population_overrides"], {})
        identifiers = set()
        intents = []
        for variant in analysis["variants"]:
            report = variant["experiment"]
            self.assertEqual(report["manifest"]["seeds"], [1, 2])
            self.assertEqual(report["manifest"]["ticks"], 4)
            self.assertEqual(report["manifest"]["population_overrides"],
                             {"price_sensitivity": variant["value"]})
            identifiers.add(report["manifest"]["experiment_id"])
            self.assertTrue(all(run["population_overrides"] == {"price_sensitivity": variant["value"]}
                                for run in report["runs"]))
            self.assertNotIn("benchmark", report)
            self.assertNotIn("snapshots", report)
            intents.append(report["aggregate"]["branches"][0]["metrics"]["average_intent"]["mean"])
        self.assertEqual(len(identifiers), 3)
        self.assertGreater(len(set(intents)), 1)
        self.assertEqual(first.benchmark["sensitivity"]["unique_experiment_count"], 4)
        # A cached baseline value produces copied, independently editable data.
        original_baseline = deepcopy(analysis["baseline_experiment"])
        analysis["variants"][1]["experiment"]["manifest"]["population_overrides"]["price_sensitivity"] = 0
        self.assertEqual(analysis["baseline_experiment"], original_baseline)

    def test_event_reach_is_changed_one_at_a_time_and_baseline_reuses_original(self):
        data = scenario()
        result = run_sensitivity(data, [1], protocol("event", "reach", 0.8,
                                 [0.0, 0.8, 1.0], event_id="news-3"))
        analysis = result.sensitivity["analyses"][0]
        self.assertEqual(result.benchmark["sensitivity"]["unique_experiment_count"], 3)
        self.assertEqual(analysis["baseline_experiment"]["manifest"], result.manifest)
        for variant in analysis["variants"]:
            variant_scenario = variant["experiment"]["manifest"]["scenario"]
            expected = deepcopy(data)
            expected["events"][0]["reach"] = variant["value"]
            self.assertEqual(variant_scenario, expected)
            self.assertEqual(variant["experiment"]["manifest"]["population_overrides"], {})

    def test_branch_incentive_deltas_align_each_seed_and_branch(self):
        result = run_sensitivity(scenario(), [2, 1], protocol("branch", "incentive", 20,
                                 [0, 20, 30], branch_id="C"))
        analysis = result.sensitivity["analyses"][0]
        baseline_rows = {(run["branch_id"], run["seed"]): run
                         for run in analysis["baseline_experiment"]["runs"]}
        for variant in analysis["variants"]:
            rows = {(run["branch_id"], run["seed"]): run
                    for run in variant["experiment"]["runs"]}
            for branch in variant["delta_vs_baseline"]["branches"]:
                for name, summary in branch["metrics"].items():
                    self.assertEqual(summary["count"], 2)
                    self.assertEqual([item["seed"] for item in summary["paired_deltas"]], [1, 2])
                    for pair in summary["paired_deltas"]:
                        key = branch["branch_id"], pair["seed"]
                        self.assertEqual(pair["delta"], rows[key]["metrics"][name]
                                         - baseline_rows[key]["metrics"][name])
                    if variant["is_baseline"] or branch["branch_id"] != "C":
                        self.assertEqual(summary["delta_mean"], 0)
            self.assertEqual(variant["delta_vs_baseline"]["comparison_scope"],
                             "independent_experiments_with_same_seeds_and_horizon")

    def test_event_amount_payload_can_be_varied(self):
        data = scenario()
        data["events"].append({"id": "bonus", "type": "INCENTIVE", "tick": 1,
                               "payload": {"amount": 5}, "reach": 1.0})
        result = run_sensitivity(data, [1], protocol("event", "amount", 5,
                                 [0, 5, 10], event_id="bonus"))
        for variant in result.sensitivity["analyses"][0]["variants"]:
            events = variant["experiment"]["manifest"]["scenario"]["events"]
            event = next(item for item in events if item["id"] == "bonus")
            self.assertEqual(event["payload"]["amount"], variant["value"])

    def test_different_factors_do_not_accumulate_changes(self):
        specification = protocol(values=[0.5])
        specification["variations"].append(
            protocol("branch", "price", 70.0, [50.0], branch_id="C")["variations"][0])
        result = run_sensitivity(scenario(), [1], specification)
        population, economic = result.sensitivity["analyses"]
        population_manifest = population["variants"][0]["experiment"]["manifest"]
        self.assertEqual(population_manifest["population_overrides"], {"price_sensitivity": 0.5})
        self.assertEqual(population_manifest["scenario"]["branches"], result.manifest["scenario"]["branches"])
        economic_manifest = economic["variants"][0]["experiment"]["manifest"]
        self.assertEqual(economic_manifest["population_overrides"], {})
        self.assertEqual(economic_manifest["scenario"]["branches"][2]["price"], 50.0)

    def test_all_parameters_have_supported_population_contracts(self):
        # Preflight exercises every parameter without paying for repeated ticks.
        from futureos.experiments import prepare_experiment
        for name in ("openness", "trust", "conformity", "influence", "risk_tolerance"):
            with self.subTest(parameter=name):
                loaded = load_sensitivity_protocol(protocol(parameter=name))
                self.assertEqual(loaded["variations"][0]["parameter"], name)
                prepare_experiment(scenario(), [1], population_overrides={name: 0.5})

    def test_late_invalid_variant_is_rejected_before_any_runner_call(self):
        data = scenario()
        valid = protocol()["variations"][0]
        invalid_variations = [
            protocol("event", "reach", 0.8, [0.2, 1.2], event_id="news-3")["variations"][0],
            protocol("branch", "incentive", 20, [0, -1], branch_id="C")["variations"][0],
            protocol("event", "amount", 0, [1], event_id="trust-18")["variations"][0],
            protocol("event", "reach", 0.8, [0.2], event_id="missing")["variations"][0],
            protocol("branch", "price", 70, [20], branch_id="missing")["variations"][0],
        ]
        for invalid in invalid_variations:
            with self.subTest(invalid=invalid), patch("futureos.sensitivity.run_experiment") as runner:
                with self.assertRaises(ValueError):
                    run_sensitivity(data, [1], {"schema_version": 1, "variations": [valid, invalid]})
                runner.assert_not_called()

    def test_protocol_rejects_malformed_values_and_definitions(self):
        specimens = []
        for key, value in (("baseline", True), ("baseline", float("nan")),
                           ("values", []), ("values", [0.5, 0.5]),
                           ("values", [0.5, float("inf")]), ("values", [10 ** 400]),
                           ("values", [False]), ("parameter", "priceSensitivity"),
                           ("parameter", []), ("target", []), ("baseline", -0.1)):
            specimen = protocol()
            specimen["variations"][0][key] = value
            specimens.append(specimen)
        missing = protocol()
        del missing["variations"][0]["baseline"]
        specimens += [missing, {"schema_version": True, "variations": []},
                      {"schema_version": 1, "variations": []}, []]
        unknown = protocol()
        unknown["variations"][0]["surprise"] = 1
        specimens.append(unknown)
        duplicate = protocol()
        duplicate["variations"] *= 2
        specimens.append(duplicate)
        for specimen in specimens:
            with self.subTest(specimen=specimen), self.assertRaises(ValueError):
                load_sensitivity_protocol(specimen)

    def test_invalid_seeds_and_horizons_fail_before_runner(self):
        for seeds, ticks in (([], 4), ([1, 1], 4), ([True], 4), ([1], 2), ([1], True)):
            with self.subTest(seeds=seeds, ticks=ticks), patch("futureos.sensitivity.run_experiment") as runner:
                with self.assertRaises(ValueError):
                    run_sensitivity(scenario(), seeds, protocol(), ticks=ticks)
                runner.assert_not_called()

    def test_event_variation_requires_an_existing_payload_field(self):
        data = scenario()
        del data["events"][0]["payload"]["trust_delta"]
        with patch("futureos.sensitivity.run_experiment") as runner:
            with self.assertRaisesRegex(ValueError, "existing supported payload"):
                run_sensitivity(data, [1], protocol("event", "trust_delta", 0, [0, 0.1],
                                                   event_id="news-3"))
            runner.assert_not_called()

    def test_saved_sensitivity_is_strict_json_without_snapshots_or_timings(self):
        result = run_sensitivity(scenario(), [1], protocol(values=[0.5]))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "protocol.json"
            source.write_text(canonical_json(protocol(values=[0.5])), encoding="utf-8")
            self.assertEqual(load_sensitivity_protocol(source), protocol(values=[0.5]))
            destination = Path(directory) / "result"
            save_experiment(result, destination)
            sensitivity = parse_json((destination / "sensitivity.json").read_text(encoding="utf-8"))
            self.assertEqual(sensitivity, result.sensitivity)
            text = canonical_json(sensitivity)
            self.assertNotIn('"benchmark"', text)
            self.assertNotIn('"simulation_json"', text)
            self.assertFalse(list(destination.rglob("*.snapshot.json")))
            benchmark = parse_json((destination / "benchmark.json").read_text(encoding="utf-8"))
            self.assertIn("sensitivity", benchmark)


if __name__ == "__main__":
    unittest.main()
