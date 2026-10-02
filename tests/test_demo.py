"""Acceptance flow exercised through the same use case as the terminal CLI."""

from pathlib import Path
import tempfile
import unittest

from futureos.codec import parse_json
from futureos.demo import run_demo, save_demo
from futureos.engine import run_ticks
from futureos.snapshots import load_snapshot, restore_snapshot


class DemoAcceptanceTests(unittest.TestCase):
    def test_full_demo_is_reproducible_and_uses_common_origin(self):
        first, repeated = run_demo(2026), run_demo(2026)
        self.assertEqual(first.report, repeated.report)
        self.assertEqual(first.branches, repeated.branches)
        self.assertEqual(first.report["external_calls"], 0)
        self.assertEqual(first.report["branch_point"], 10)
        self.assertEqual(first.report["horizon"], 30)
        self.assertEqual(len(first.branches), 3)
        self.assertEqual({branch.parent_snapshot_id for branch in first.branches}, {first.snapshot.id})
        self.assertTrue(all(branch.simulation.world.current_tick == 30 for branch in first.branches))
        self.assertGreater(len({row["average_intent"] for row in first.report["comparison"]}), 1)

    def test_saved_artifacts_restore_origin_and_every_branch(self):
        result = run_demo(2026)
        with tempfile.TemporaryDirectory() as directory:
            save_demo(result, directory)
            origin = load_snapshot(Path(directory) / "origin.snapshot.json")
            self.assertEqual(origin, result.snapshot)
            self.assertEqual(run_ticks(restore_snapshot(origin), 1).world.current_tick, 11)
            for index, branch in enumerate(result.branches):
                saved = load_snapshot(Path(directory) / f"branch-{index + 1}.snapshot.json")
                self.assertEqual(restore_snapshot(saved), branch.simulation)
            report = parse_json((Path(directory) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report, result.report)


if __name__ == "__main__":
    unittest.main()
