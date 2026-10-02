"""Measure M3 summary versus trace at total horizons 10, 30 and 60.

The benchmark compares all three deterministic hashes per branch before
reporting costs. Time includes preflight, execution and artifact serialization;
disk writes are excluded. This is a local observation, not a scale guarantee.
"""

import argparse
from pathlib import Path
import platform
from time import perf_counter

from futureos.audit_runs import HASH_FIELDS, run_audit_experiment, save_audit_experiment
from futureos.codec import canonical_json
from futureos.demo import DEFAULT_SCENARIO
from futureos.experiments import load_experiment_scenario
from futureos.randomness import validate_seed


def _ticks(value: str) -> list[int]:
    try:
        values = [int(part) for part in value.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("ticks must be comma-separated positive integers") from error
    if not values or any(tick < 1 for tick in values) or len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("ticks must be distinct positive integers")
    return sorted(values)


def _produced_bytes(result) -> int:
    documents = [result.manifest, result.divergences, *result.runs]
    return sum(len((canonical_json(document) + "\n").encode("utf-8")) for document in documents)


def profile_audit(seed: int = 2026, ticks=(10, 30, 60), *, scenario=DEFAULT_SCENARIO):
    """Execute summary then trace sequentially and verify hashes at each horizon."""
    validate_seed(seed)
    horizons = list(ticks)
    if (not horizons or any(type(tick) is not int or tick < 1 for tick in horizons)
            or len(set(horizons)) != len(horizons)):
        raise ValueError("Ticks must be distinct positive integer horizons")
    scenario_data = load_experiment_scenario(scenario)
    if any(horizon < scenario_data["initial_ticks"] for horizon in horizons):
        raise ValueError("Each horizon must be at or after the branch point")
    rows, results = [], []
    for horizon in horizons:
        measurements, pair = {}, {}
        for mode in ("summary", "trace"):
            started = perf_counter()
            result = run_audit_experiment(scenario_data, [seed], ticks=horizon, mode=mode)
            size = _produced_bytes(result)
            duration = perf_counter() - started
            pair[mode] = result
            measurements[mode] = {"seconds": duration, "bytesProduced": size,
                                  "runCount": len(result.runs),
                                  "traceRecordsStored": sum(len(run["records"]) for run in result.runs),
                                  "framesStored": sum(len(run["frames"]) for run in result.runs)}
        hashes = []
        for summary, trace in zip(pair["summary"].runs, pair["trace"].runs, strict=True):
            if summary["runId"] != trace["runId"] or any(summary[key] != trace[key] for key in HASH_FIELDS):
                raise RuntimeError(f"Summary/trace changed hashes at horizon {horizon}")
            hashes.append({"runId": summary["runId"], "branchId": summary["branchId"],
                           **{key: summary[key] for key in HASH_FIELDS}})
        summary, trace = measurements["summary"], measurements["trace"]
        time_ratio = trace["seconds"] / summary["seconds"] if summary["seconds"] else None
        size_ratio = trace["bytesProduced"] / summary["bytesProduced"] if summary["bytesProduced"] else None
        rows.append({"ticks": horizon, "summary": summary, "trace": trace,
                     "timeRatioTraceToSummary": time_ratio,
                     "timeOverheadPercent": (time_ratio - 1) * 100 if time_ratio is not None else None,
                     "sizeRatioTraceToSummary": size_ratio,
                     "sizeOverheadPercent": (size_ratio - 1) * 100 if size_ratio is not None else None,
                     "hashesEqual": True, "hashes": hashes})
        results.append(pair)
    report = {"benchmarkVersion": 1, "seed": seed, "pythonVersion": platform.python_version(),
              "platform": platform.platform(), "measurements": rows,
              "executionOrder": "summary then trace sequentially for each horizon",
              "timingScope": "Preflight, simulation, reports and canonical artifact serialization; excludes disk output",
              "sizeScope": "Canonical UTF-8 manifest, divergence report and run JSON files including final newline",
              "limitations": ["Local wall-clock measurements depend on machine load.",
                              "Timings and size overhead never enter run IDs or deterministic hashes.",
                              "Synthetic model; no real-world causal or prediction claim."]}
    return report, results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--ticks", type=_ticks, default=[10, 30, 60],
                        help="comma-separated total horizons (default: 10,30,60)")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--output", type=Path, help="absent or empty output directory")
    parser.add_argument("--json", action="store_true", help="print the complete benchmark JSON")
    args = parser.parse_args(argv)
    if args.output is not None and args.output.exists() and (
            not args.output.is_dir() or any(args.output.iterdir())):
        parser.error("--output must be absent or empty; choose a new path")
    try:
        report, results = profile_audit(args.seed, args.ticks, scenario=args.scenario)
        if args.output is not None:
            args.output.mkdir(parents=True, exist_ok=True)
            for row, pair in zip(report["measurements"], results, strict=True):
                for mode in ("summary", "trace"):
                    save_audit_experiment(pair[mode], args.output / f"ticks-{row['ticks']}-{mode}")
            (args.output / "benchmark.json").write_text(canonical_json(report) + "\n", encoding="utf-8", newline="\n")
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Audit benchmark failed: {error}\n")
    if args.json:
        print(canonical_json(report))
    else:
        for row in report["measurements"]:
            summary, trace = row["summary"], row["trace"]
            print(f"Ticks {row['ticks']}: summary {summary['seconds']:.3f}s / {summary['bytesProduced']} bytes; "
                  f"trace {trace['seconds']:.3f}s / {trace['bytesProduced']} bytes; "
                  f"time ratio {row['timeRatioTraceToSummary']:.3f}; size ratio {row['sizeRatioTraceToSummary']:.3f}; hashes equal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
