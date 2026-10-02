"""Terminal entry points for deterministic runs and optional population planning."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .audit_runs import (compare_run_divergence, load_run_artifact, replay_run,
                         run_audit_experiment, save_audit_experiment,
                         trajectory_from_run)
from .codec import canonical_json
from .demo import DEFAULT_SCENARIO, run_demo, save_demo
from .experiments import run_experiment, save_experiment, summarize_experiment
from .sensitivity import run_sensitivity


MAX_CLI_SEEDS = 100_000
_MAX_SEED_TEXT = str((1 << 64) - 1)


def _seed_number(value: str) -> int:
    text = value.strip()
    if not text or any(char not in "0123456789" for char in text):
        raise argparse.ArgumentTypeError("Seeds must be uint64 integers")
    # Compare normalized digits before int(): arbitrary input need not allocate
    # an enormous integer or hit Python's integer-string conversion limit.
    digits = text.lstrip("0") or "0"
    if (len(digits) > len(_MAX_SEED_TEXT)
            or (len(digits) == len(_MAX_SEED_TEXT) and digits > _MAX_SEED_TEXT)):
        raise argparse.ArgumentTypeError("Seeds must be uint64 integers")
    return int(digits)


def parse_seeds(value: str) -> list[int]:
    """Parse an inclusive range or comma list without unbounded allocation."""
    limit_error = f"The CLI accepts at most {MAX_CLI_SEEDS} seeds"
    if ":" in value:
        if value.count(":") != 1 or "," in value:
            raise argparse.ArgumentTypeError("Use an inclusive start:end range or comma list")
        start, end = map(_seed_number, value.split(":"))
        if end < start:
            raise argparse.ArgumentTypeError("Seed range end must be at least its start")
        if end - start + 1 > MAX_CLI_SEEDS:
            raise argparse.ArgumentTypeError(limit_error)
        return list(range(start, end + 1))
    if value.count(",") + 1 > MAX_CLI_SEEDS:
        raise argparse.ArgumentTypeError(limit_error)
    seeds = [_seed_number(item) for item in value.split(",")]
    if len(set(seeds)) != len(seeds):
        raise argparse.ArgumentTypeError("Seeds must be distinct")
    return sorted(seeds)


def _demo_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed", type=_seed_number, default=2026)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the complete JSON report")


def _batch_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--seeds", type=parse_seeds, default=[2026])
    parser.add_argument("--ticks", type=int, help="Total horizon, including the common origin")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the complete JSON report")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FutureOS synthetic decision laboratory")
    _demo_arguments(parser)
    commands = parser.add_subparsers(dest="command")
    demo = commands.add_parser("demo", help="Run the legacy deterministic demo")
    _demo_arguments(demo)
    experiment = commands.add_parser("experiment", help="Run paired seed experiments")
    _batch_arguments(experiment)
    experiment.add_argument("--sensitivity", type=Path, help="One-at-a-time JSON protocol")
    audit = commands.add_parser("audit", help="Run versioned summary or trace experiments")
    _batch_arguments(audit)
    audit.add_argument("--mode", choices=("summary", "trace"), default="summary")
    replay = commands.add_parser("replay", help="Rebuild a saved audit run and verify its hashes")
    replay.add_argument("run", type=Path)
    trajectory = commands.add_parser("trajectory", help="Inspect an agent's saved trace")
    trajectory.add_argument("run", type=Path)
    trajectory.add_argument("--agent", required=True)
    divergence = commands.add_parser("divergence", help="Compare two sibling audit runs")
    divergence.add_argument("left", type=Path)
    divergence.add_argument("right", type=Path)
    population = commands.add_parser("population", help="Prepare a population specification for review")
    population_commands = population.add_subparsers(dest="population_command", required=True)
    plan = population_commands.add_parser("plan", help="Propose a PopulationSpec without generating agents")
    plan.add_argument("--description", required=True)
    plan.add_argument("--size", type=int)
    plan.add_argument("--context")
    plan.add_argument("--provider", choices=("fake",), default="fake")
    plan.add_argument("--output", type=Path, required=True)
    scenario = commands.add_parser("scenario", help="Scenario Builder: validate or show a ScenarioSpec")
    scenario_commands = scenario.add_subparsers(dest="scenario_command", required=True)
    scenario_validate = scenario_commands.add_parser("validate", help="Validate a ScenarioSpec JSON file")
    scenario_validate.add_argument("--spec", type=Path, required=True, help="Path to scenario JSON")
    scenario_show = scenario_commands.add_parser("show", help="Show a ScenarioSpec JSON file")
    scenario_show.add_argument("--spec", type=Path, required=True, help="Path to scenario JSON")
    return parser


def _summarize_demo(report: dict) -> str:
    lines = ["FutureOS Kernel Demo", f"Seed: {report['seed']} | Agents: {report['population_size']} | Ticks: {report['horizon']}"]
    for row in report["comparison"]:
        lines.append(f"Branch {row['id']}: adoption {row['adoption_rate']:.2%}, average intent {row['average_intent']:.4f}")
    lines.extend(report["limitations"])
    return "\n".join(lines)


def _scenario_validate(args) -> int:
    from .scenario_builder import scenario_from_json, validate_scenario_spec, scenario_fingerprint
    try:
        spec = scenario_from_json(args.spec.read_text(encoding="utf-8"))
        validate_scenario_spec(spec)
        fp = scenario_fingerprint(spec)
        print(f"VALID | id={spec.id} | name={spec.name} | duration={spec.duration_ticks} | branches={len(spec.branches)} | source={spec.source}")
        print(f"FINGERPRINT | {fp}")
        return 0
    except Exception as error:
        print(f"INVALID | {error}")
        return 1


def _scenario_show(args) -> int:
    from .scenario_builder import scenario_from_json, scenario_fingerprint
    try:
        spec = scenario_from_json(args.spec.read_text(encoding="utf-8"))
        fp = scenario_fingerprint(spec)
        print(f"id: {spec.id}")
        print(f"name: {spec.name}")
        print(f"description: {spec.description}")
        print(f"duration_ticks: {spec.duration_ticks}")
        print(f"source: {spec.source}")
        print(f"initial_state: {spec.initial_state}")
        print(f"branches: {len(spec.branches)}")
        for b in spec.branches:
            inter_count = len(b.interventions)
            print(f"  - {b.id} ({b.name}): interventions={inter_count}")
        print(f"assumptions: {spec.assumptions}")
        print(f"warnings: {spec.warnings}")
        print(f"fingerprint: {fp}")
        return 0
    except Exception as error:
        print(f"ERROR | {error}")
        return 1


def _summarize_sensitivity(result) -> str:
    lines = ["Original scenario experiment", summarize_experiment(result), "One-at-a-time sensitivity"]
    for analysis in result.sensitivity["analyses"]:
        identity = analysis.get("branch_id", analysis.get("event_id", "population"))
        lines.append(f"{analysis['target']} {identity}: {analysis['parameter']}, baseline={analysis['baseline']}")
    timing = result.benchmark["sensitivity"]
    lines.append(f"Sensitivity total duration: {timing['total_seconds']:.3f}s | {timing['unique_experiment_count']} unique experiments")
    return "\n".join(lines)


def _plan_population(args) -> None:
    # Keep the optional LLM adapter out of the deterministic command path.
    from .llm_registry import FakeLLMProvider
    from .population_planner import LLMPopulationPlanner
    from .population_validation import validate_population_spec

    if args.output.exists():
        raise ValueError("Population output already exists; choose a new file")
    spec = LLMPopulationPlanner(FakeLLMProvider()).plan(
        args.description, size=args.size, context=args.context,
    )
    validate_population_spec(spec)
    contents = json.dumps(spec.to_json(), ensure_ascii=False, indent=2,
                          sort_keys=True, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against a file created after preflight.
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(contents)
    print(f"PopulationSpec proposed for review: {args.output}")
    for warning in spec.warnings:
        print(f"Warning: {warning}")
    for assumption in spec.assumptions:
        print(f"Assumption: {assumption}")


def main(argv: list[str] | None = None) -> int:
    # Persisted JSON and redirected CLI reports use the same UTF-8 encoding on
    # Windows and Unix, including non-ASCII scenario text.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in (None, "demo"):
            result = run_demo(args.seed, args.scenario)
            if args.output is not None:
                save_demo(result, args.output)
            print(canonical_json(result.report) if args.json else _summarize_demo(result.report))
        elif args.command == "experiment":
            result = (run_sensitivity(args.scenario, args.seeds, args.sensitivity, ticks=args.ticks)
                      if args.sensitivity else run_experiment(args.scenario, args.seeds, ticks=args.ticks))
            if args.output is not None:
                save_experiment(result, args.output)
            print(canonical_json(asdict(result)) if args.json else
                  _summarize_sensitivity(result) if result.sensitivity else summarize_experiment(result))
        elif args.command == "audit":
            result = run_audit_experiment(args.scenario, args.seeds, args.ticks, mode=args.mode)
            if args.output is not None:
                save_audit_experiment(result, args.output)
            if args.json:
                print(canonical_json(asdict(result)))
            else:
                print(f"FutureOS Audit | Mode: {args.mode} | Runs: {len(result.runs)} | Ticks: {result.manifest['ticks']}")
                for limitation in result.manifest["limitations"]:
                    print(limitation)
        elif args.command == "replay":
            report = replay_run(load_run_artifact(args.run))
            print(canonical_json(report))
            return 0 if report["matched"] else 1
        elif args.command == "trajectory":
            run = load_run_artifact(args.run)
            print(canonical_json({"runId": run["runId"], "agentId": args.agent,
                                  "trajectory": trajectory_from_run(run, args.agent)}))
        elif args.command == "divergence":
            print(canonical_json(compare_run_divergence(load_run_artifact(args.left),
                                                       load_run_artifact(args.right))))
        elif args.command == "population":
            _plan_population(args)
        elif args.command == "scenario":
            if args.scenario_command == "validate":
                return _scenario_validate(args)
            elif args.scenario_command == "show":
                return _scenario_show(args)
        elif args.command == "experiment":
            return _run_experiment(args)
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    sys.exit(main())
def _run_experiment(args): from .experiment_runner import run_scenario_experiment; res=run_scenario_experiment(args.population,args.scenario,seeds=args.seeds if isinstance(args.seeds,list) else [int(args.seeds)],output_dir=args.output); args.output.mkdir(parents=True,exist_ok=True); (args.output/"manifest.json").write_text(str(res)); print("Experiment done"); return 0
