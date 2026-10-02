"""End-to-end CLI checks for persisted audit artifacts and replay failures."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from futureos.audit_runs import run_audit_experiment, save_audit_experiment
from futureos.codec import canonical_json, parse_json
from test_audit_runs import scenario_fixture


ROOT = Path(__file__).resolve().parent.parent


class AuditCliTests(unittest.TestCase):
    def cli(self, *arguments):
        return subprocess.run([sys.executable, "-m", "futureos", *map(str, arguments)],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8")

    def test_audit_persists_and_all_consultation_commands_work(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scenario = root / "scenario.json"
            scenario.write_text(canonical_json(scenario_fixture()), encoding="utf-8")
            result = self.cli("audit", "--scenario", scenario, "--seeds", "2026", "--ticks", "3",
                              "--mode", "trace", "--output", root / "output", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            body = parse_json(result.stdout)
            self.assertEqual(len(body["runs"]), 3)
            first = root / "output/runs/run-000001.json"
            second = root / "output/runs/run-000002.json"
            replay = self.cli("replay", first)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertTrue(parse_json(replay.stdout)["matched"])
            divergence = self.cli("divergence", first, second)
            self.assertEqual(divergence.returncode, 0, divergence.stderr)
            self.assertEqual(parse_json(divergence.stdout)["firstTick"], 1)
            trajectory = self.cli("trajectory", first, "--agent", "agent-001")
            self.assertEqual(trajectory.returncode, 0, trajectory.stderr)
            self.assertTrue(parse_json(trajectory.stdout)["trajectory"])

    def test_summary_has_no_trace_and_trajectory_reports_required_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_audit_experiment(scenario_fixture(), [42], ticks=2, mode="summary")
            save_audit_experiment(result, root / "summary")
            trajectory = self.cli("trajectory", root / "summary/runs/run-000001.json", "--agent", "agent-001")
            self.assertEqual(trajectory.returncode, 2)
            self.assertIn("trace", trajectory.stderr.lower())

    def test_replay_mismatch_returns_failure_and_first_detectable_difference(self):
        with tempfile.TemporaryDirectory() as temp:
            run = deepcopy(run_audit_experiment(scenario_fixture(), [42], ticks=2).runs[0])
            run["trajectoryHash"] = "f" * 64
            path = Path(temp) / "changed.json"
            path.write_text(canonical_json(run), encoding="utf-8")
            result = self.cli("replay", path)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = parse_json(result.stdout)
            self.assertFalse(report["matched"])
            self.assertEqual(report["firstDivergence"]["field"], "trajectoryHash")

    def test_invalid_audit_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "invalid"
            result = self.cli("audit", "--ticks", "-1", "--output", destination)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
