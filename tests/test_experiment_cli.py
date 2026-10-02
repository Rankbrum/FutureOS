"""CLI experiment invocation, invalid input behavior, and legacy demo flags."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from futureos.__main__ import MAX_CLI_SEEDS, parse_seeds
from futureos.codec import canonical_json
from futureos.demo import DEFAULT_SCENARIO


ROOT = Path(__file__).resolve().parent.parent


class ExperimentCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        data = json.loads(DEFAULT_SCENARIO.read_text(encoding="utf-8"))
        data.update(population_size=3, initial_ticks=1, branch_ticks=1)
        data["events"] = []
        self.scenario = self.directory / "scenario.json"
        self.scenario.write_text(canonical_json(data), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def invoke(self, *arguments):
        return subprocess.run([sys.executable, "-m", "futureos", *map(str, arguments)],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)

    def test_seed_parser_is_inclusive_sorted_and_validated(self):
        self.assertEqual(parse_seeds("1:3"), [1, 2, 3])
        self.assertEqual(parse_seeds("0:0"), [0])
        self.assertEqual(parse_seeds("3,1,2"), [1, 2, 3])
        self.assertEqual(parse_seeds("0" * 5000 + "1"), [1])
        self.assertEqual(parse_seeds(str((1 << 64) - 1)), [(1 << 64) - 1])
        for value in ("3:1", "1,1", "-1", "", "1:2:3", "1,", "1.0", "true", str(1 << 64), "1" * 5000):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                parse_seeds(value)

    def test_cli_seed_limit_rejects_large_allocations(self):
        self.assertEqual(len(parse_seeds(f"1:{MAX_CLI_SEEDS}")), MAX_CLI_SEEDS)
        for value in (f"0:{MAX_CLI_SEEDS}", f"0:{(1 << 64) - 1}",
                      ",".join("1" for _ in range(MAX_CLI_SEEDS + 1))):
            with self.subTest(value_length=len(value)), self.assertRaisesRegex(
                    argparse.ArgumentTypeError, "at most 100000"):
                parse_seeds(value)

    def test_experiment_json_and_compact_output(self):
        output = self.directory / "batch"
        completed = self.invoke("experiment", "--scenario", self.scenario, "--seeds", "1:2",
                                "--ticks", "3", "--output", output, "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["manifest"]["seeds"], [1, 2])
        self.assertEqual(report["manifest"]["ticks"], 3)
        self.assertEqual(report["manifest"]["run_count"], 6)
        self.assertTrue(report["comparison"]["paired"])
        self.assertEqual(len(list((output / "runs").glob("*.json"))), 6)
        self.assertFalse(list(output.rglob("*.snapshot.json")))
        self.assertTrue((output / "benchmark.json").exists())

    def test_human_summary_and_sensitivity_option(self):
        specification = self.directory / "sensitivity.json"
        specification.write_text(canonical_json({"schema_version": 1, "variations": [
            {"target": "branch", "branch_id": "C", "parameter": "incentive",
             "baseline": 20, "values": [0, 20]},
        ]}), encoding="utf-8")
        output = self.directory / "sensitivity-result"
        completed = self.invoke("experiment", "--scenario", self.scenario, "--seeds", "1",
                                "--sensitivity", specification, "--output", output)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("FutureOS Experiment", completed.stdout)
        self.assertIn("Ticks: 2", completed.stdout)
        self.assertIn("One-at-a-time sensitivity", completed.stdout)
        self.assertIn("baseline=20", completed.stdout)
        self.assertIn("real-world probability", completed.stdout)
        self.assertIn("Original scenario experiment", completed.stdout)
        self.assertIn("Sensitivity total duration:", completed.stdout)
        self.assertIn("unique experiments", completed.stdout)
        report = json.loads((output / "sensitivity.json").read_text(encoding="utf-8"))
        self.assertEqual(report["method"], "one_at_a_time")

    def test_invalid_inputs_do_not_create_output(self):
        for flag, value in (("--seeds", "2:1"), ("--seeds", "1,1"), ("--ticks", "1")):
            with self.subTest(flag=flag, value=value):
                output = self.directory / "invalid"
                arguments = ["experiment", "--scenario", self.scenario, "--output", output]
                if flag != "--seeds":
                    arguments += ["--seeds", "1"]
                completed = self.invoke(*arguments, flag, value)
                self.assertEqual(completed.returncode, 2)
                self.assertFalse(output.exists())

    def test_invalid_late_sensitivity_value_does_not_create_output(self):
        specification = self.directory / "invalid-protocol.json"
        specification.write_text(canonical_json({"schema_version": 1, "variations": [
            {"target": "branch", "branch_id": "C", "parameter": "incentive",
             "baseline": 20, "values": [0, -10]},
        ]}), encoding="utf-8")
        output = self.directory / "invalid"
        completed = self.invoke("experiment", "--scenario", self.scenario, "--seeds", "1",
                                "--sensitivity", specification, "--output", output)
        self.assertEqual(completed.returncode, 2)
        self.assertFalse(output.exists())

    def test_legacy_demo_flags_still_save_complete_snapshots(self):
        output = self.directory / "demo"
        completed = self.invoke("--seed", "7", "--scenario", self.scenario,
                                "--output", output, "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["seed"], 7)
        self.assertEqual(report["horizon"], 2)
        self.assertEqual(report["population_size"], 3)
        self.assertEqual(len(list(output.glob("*.snapshot.json"))), 4)
        self.assertTrue((output / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
