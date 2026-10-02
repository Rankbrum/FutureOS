"""Measure the versioned kernel demo and optionally verify a repeat.

Run from the repository root with Python 3.13::

    python -m benchmarks.experiment --seeds 100 --ticks 30 \
        --output results/experiment-demo --verify-repeat

The repeat compares canonical deterministic reports, including each origin and
final state checksum. Wall-clock measurements are deliberately excluded.
"""

import argparse
from pathlib import Path
from time import perf_counter

from futureos.codec import canonical_json
from futureos.demo import DEFAULT_SCENARIO
from futureos.experiments import run_experiment, save_experiment, summarize_experiment


DETERMINISTIC_DOCUMENTS = ("manifest", "runs", "aggregate", "comparison")
MAX_BENCHMARK_SEEDS = 100_000


def positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=positive_integer, default=100,
                        help="seed count, maximum 100000; seeds are 1 through N (default: 100)")
    parser.add_argument("--ticks", type=positive_integer, default=30,
                        help="total horizon including the origin ticks (default: 30)")
    parser.add_argument("--output", type=Path, required=True,
                        help="absent or empty output directory")
    parser.add_argument("--verify-repeat", action="store_true",
                        help="repeat with reversed input seeds and compare deterministic reports")
    args = parser.parse_args(argv)
    if args.seeds > MAX_BENCHMARK_SEEDS:
        parser.error(f"--seeds must not exceed {MAX_BENCHMARK_SEEDS}; use smaller batches")
    if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
        parser.error("--output must be absent or empty; choose a new path")

    seeds = list(range(1, args.seeds + 1))
    print(f"Benchmark: {len(seeds)} seeds, horizon {args.ticks}; running baseline...", flush=True)
    try:
        result = run_experiment(DEFAULT_SCENARIO, seeds, ticks=args.ticks)
        if args.verify_repeat:
            print("Baseline complete; repeating with reversed input seeds...", flush=True)
            repeat_started = perf_counter()
            repeat = run_experiment(DEFAULT_SCENARIO, reversed(seeds), ticks=args.ticks)
            repeat_seconds = perf_counter() - repeat_started
            for name in DETERMINISTIC_DOCUMENTS:
                if canonical_json(getattr(result, name)) != canonical_json(getattr(repeat, name)):
                    raise RuntimeError(f"Deterministic repeat differs in {name}")
            result.benchmark["repeat_verification"] = {
                "status": "passed",
                "compared_documents": list(DETERMINISTIC_DOCUMENTS),
                "excluded_document": "benchmark",
                "input_seed_order": "reversed",
                "execution_seed_order": "canonical ascending, normalized by run_experiment",
                "repeat_seconds": repeat_seconds,
                "repeat_run_count": len(repeat.runs),
            }
        save_experiment(result, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Benchmark failed: {error}\n")
    print(summarize_experiment(result))
    if args.verify_repeat:
        print("Repeat verification: manifest, runs, aggregate and comparison are identical.")
    files = [path for path in args.output.rglob("*") if path.is_file()]
    print(f"Saved: {args.output.resolve()} | {len(files)} files | "
          f"{sum(path.stat().st_size for path in files)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
