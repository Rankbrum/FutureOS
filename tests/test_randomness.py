import unittest

from futureos.randomness import RandomState, SeededRandom, UINT64_MAX


class SeededRandomTests(unittest.TestCase):
    def test_splitmix64_reference_outputs_are_portable(self):
        rng = SeededRandom(0)
        # Published SplitMix64 seed-zero output sequence, before float conversion.
        expected = (0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F)
        self.assertEqual([rng.random() for _ in expected],
                         [(value >> 11) / (1 << 53) for value in expected])
        self.assertEqual(rng.state.draws, 3)

    def test_state_restores_exact_continuation_without_sharing(self):
        original = SeededRandom(UINT64_MAX)
        for _ in range(17):
            original.random()
        checkpoint = original.state
        restored = SeededRandom.from_state(checkpoint)
        expected = [original.random() for _ in range(100)]
        self.assertEqual(checkpoint.draws, 17)
        self.assertEqual([restored.random() for _ in range(100)], expected)
        self.assertEqual(restored.state, original.state)

    def test_probability_endpoints_do_not_draw(self):
        rng = SeededRandom(7)
        initial = rng.state
        self.assertFalse(rng.probability(0))
        self.assertTrue(rng.probability(1))
        self.assertEqual(rng.state, initial)
        rng.probability(0.5)
        self.assertEqual(rng.state.draws, 1)

    def test_collection_sampling_is_reproducible_and_preserves_input(self):
        values = list(range(20))
        left = SeededRandom(42)
        right = SeededRandom(42)
        self.assertEqual([left.choice(values) for _ in range(25)],
                         [right.choice(values) for _ in range(25)])
        shuffled = left.shuffle(values)
        self.assertEqual(shuffled, right.shuffle(values))
        self.assertEqual(sorted(shuffled), values)
        self.assertEqual(values, list(range(20)))
        self.assertIsNot(shuffled, values)
        with self.assertRaisesRegex(ValueError, "empty"):
            left.choice([])

    def test_invalid_seed_probability_and_state_fail_clearly(self):
        for invalid in (-1, UINT64_MAX + 1, True, 1.0, "1"):
            with self.subTest(seed=invalid), self.assertRaisesRegex(ValueError, "seed"):
                SeededRandom(invalid)
        rng = SeededRandom(1)
        for invalid in (-0.1, 1.1, True, float("nan"), float("inf"), 10 ** 400):
            with self.subTest(probability=invalid), self.assertRaisesRegex(ValueError, "probability"):
                rng.probability(invalid)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            RandomState(seed=1, state=2)
        with self.assertRaisesRegex(ValueError, "algorithm"):
            RandomState(seed=1, state=1, algorithm="unknown")


if __name__ == "__main__":
    unittest.main()
