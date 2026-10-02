import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from futureos.randomness import (
    RNG_POLICY, RandomStreams, SeededRandom, UINT64_MAX, derive_seed,
)


class RandomStreamsTests(unittest.TestCase):
    def test_canonical_derivation_reference_vector(self):
        self.assertEqual(RNG_POLICY, "sha256-path-splitmix64-v1")
        # SHA-256 of sorted, compact UTF-8 JSON with typed path components.
        self.assertEqual(derive_seed(42, "decisions", 7, "agent-001"),
                         2852571221993682078)

    def test_streams_repeat_and_restart_without_shared_generators(self):
        streams = RandomStreams(42)
        left = streams.stream("decisions", 7, "agent-001")
        right = RandomStreams(42).stream("decisions", 7, "agent-001")
        expected = [left.random() for _ in range(20)]
        self.assertEqual([right.random() for _ in range(20)], expected)
        restarted = streams.stream("decisions", 7, "agent-001")
        self.assertIsNot(left, restarted)
        self.assertEqual(restarted.state.draws, 0)
        self.assertEqual([restarted.random() for _ in range(20)], expected)

    def test_consumption_in_other_contexts_cannot_shift_target_stream(self):
        streams = RandomStreams(123)
        target = streams.stream("decisions", 2, "agent-003")
        control = streams.stream("decisions", 2, "agent-003")
        self.assertEqual(target.random(), control.random())
        for namespace in ("population", "events", "interactions", "social", "memory"):
            unrelated = streams.stream(namespace, 2, "agent-003")
            for _ in range(100):
                unrelated.random()
        other_agent = streams.stream("decisions", 2, "agent-004")
        for _ in range(100):
            other_agent.random()
        self.assertEqual([target.random() for _ in range(10)],
                         [control.random() for _ in range(10)])
        self.assertEqual(target.state, control.state)

    def test_typed_identifiers_boundaries_order_and_granularity_are_distinct(self):
        paths = (
            ("decisions",),
            ("decisions", 1),
            ("decisions", "1"),
            ("decisions", 1, "agent-1"),
            ("decisions", 2, "agent-1"),
            ("decisions", 1, "agent-2"),
            ("decisions", "agent-1", 1),
            ("interactions", 1, "agent-1", "agent-2"),
            ("interactions", 1, "agent-2", "agent-1"),
            ("ab", "c"),
            ("a", "bc"),
            ("a/b", "c"),
            ("a", "b/c"),
        )
        seeds = [derive_seed(42, *path) for path in paths]
        self.assertEqual(len(set(seeds)), len(paths))
        self.assertNotEqual(derive_seed(42, "decisions"),
                            derive_seed(43, "decisions"))

    def test_namespaces_are_arbitrary_nonempty_utf8_strings(self):
        streams = RandomStreams(UINT64_MAX)
        for namespace in ("population", "events", "interactions", "decisions",
                          "social", "memory", "custom-policy", "a\u00e7\u00e3o"):
            with self.subTest(namespace=namespace):
                rng = streams.stream(namespace)
                self.assertEqual(rng.state.seed, derive_seed(UINT64_MAX, namespace))
                self.assertEqual(rng.state.draws, 0)

    def test_derivation_is_stable_across_processes_and_python_hash_seeds(self):
        code = (
            "import json; from futureos.randomness import RandomStreams, derive_seed; "
            "rng = RandomStreams(42).stream('decisions', 7, 'a\\u00e7\\u00e3o'); "
            "print(json.dumps([derive_seed(42, 'decisions', 7, 'a\\u00e7\\u00e3o'), "
            "[rng.random() for _ in range(5)]]))"
        )
        expected_rng = RandomStreams(42).stream("decisions", 7, "a\u00e7\u00e3o")
        expected = [derive_seed(42, "decisions", 7, "a\u00e7\u00e3o"),
                    [expected_rng.random() for _ in range(5)]]
        project_root = Path(__file__).resolve().parents[1]
        for hash_seed in ("0", "1", "987654321", "random"):
            with self.subTest(hash_seed=hash_seed):
                environment = dict(os.environ, PYTHONHASHSEED=hash_seed)
                output = subprocess.check_output([sys.executable, "-c", code],
                                                 cwd=project_root, env=environment,
                                                 text=True)
                self.assertEqual(json.loads(output), expected)

    def test_invalid_roots_paths_and_namespaces_fail_clearly(self):
        for invalid in (-1, UINT64_MAX + 1, True, 1.0, "1"):
            with self.subTest(root_seed=invalid), self.assertRaisesRegex(ValueError, "seed"):
                derive_seed(invalid, "events")
            with self.subTest(factory_seed=invalid), self.assertRaisesRegex(ValueError, "seed"):
                RandomStreams(invalid)
        with self.assertRaisesRegex(ValueError, "path"):
            derive_seed(42)
        for invalid in ("", "\ud800", "\udfff", -1, True, 1.0, None, (), []):
            with self.subTest(component=repr(invalid)), self.assertRaisesRegex(ValueError, "path"):
                derive_seed(42, "events", invalid)
        for invalid in (None, 1, True, 1.0):
            with self.subTest(namespace=invalid), self.assertRaisesRegex(ValueError, "namespace"):
                RandomStreams(42).stream(invalid)
        for invalid in ("", "\ud800"):
            with self.subTest(namespace=repr(invalid)), self.assertRaises(ValueError):
                RandomStreams(42).stream(invalid)

    def test_existing_splitmix64_reference_outputs_remain_unchanged(self):
        generator = SeededRandom(0)
        expected = (0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F)
        self.assertEqual([generator.random() for _ in expected],
                         [(value >> 11) / (1 << 53) for value in expected])


if __name__ == "__main__":
    unittest.main()
