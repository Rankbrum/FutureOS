"""Paired synthetic experiments with compact, reproducible run summaries.

Wall-clock measurements are kept out of deterministic reports. Each seed owns
one complete origin snapshot; each continuation restores independent state.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations
from pathlib import Path
import math
import platform
import statistics
from time import perf_counter
from typing import Any, Iterable

from .branches import BranchConfiguration, compare_branches, create_branch
from .codec import canonical_json, parse_json
from .demo import DEFAULT_SCENARIO, _require_fields
from .engine import create_simulation, run_ticks, schedule_event
from .models import Configuration, ENGINE_VERSION, Event, GlobalState, Metrics, World
from .population import create_population
from .randomness import SeededRandom, validate_seed
from .snapshots import create_snapshot
from .validation import _validate_configuration, validate_json


EXPERIMENT_VERSION = 1
METRICS = tuple(Metrics.__dataclass_fields__)
POPULATION_PARAMETERS = {
    "price_sensitivity": "traits", "openness": "traits", "trust": "state",
    "conformity": "traits", "influence": "traits", "risk_tolerance": "traits",
}
LIMITATIONS = [
    "The model is synthetic and its rules have not been calibrated.",
    "Agents do not represent a real population.",
    "Simulated frequency is not a real-world probability.",
    "Results test infrastructure and explore model behavior under declared assumptions.",
    "Each branch copies the same origin RNG stream; differing draw consumption can misalign later samples.",
    "No empirical calibration, revenue model, LLM or external calls.",
]


@dataclass
class ExperimentResult:
    manifest: dict[str, Any]
    runs: list[dict[str, Any]]
    aggregate: dict[str, Any]
    comparison: dict[str, Any]
    benchmark: dict[str, Any]
    sensitivity: dict[str, Any] | None = None


def _hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_seeds(seeds: Iterable[int]) -> list[int]:
    if isinstance(seeds, (str, bytes, dict)):
        raise ValueError("Seeds must be a nonempty iterable of distinct uint64 integers")
    try:
        values = list(seeds)
    except TypeError as error:
        raise ValueError("Seeds must be an iterable") from error
    if not values:
        raise ValueError("Seeds must not be empty")
    for seed in values:
        validate_seed(seed)
    if len(set(values)) != len(values):
        raise ValueError("Seeds must be distinct")
    return sorted(values)


def _initial_simulation(scenario: dict, seed: int, overrides: dict):
    rng = SeededRandom(seed)
    agents = create_population(scenario["population_size"], rng)
    for agent in agents:
        for name, value in overrides.items():
            setattr(getattr(agent, POPULATION_PARAMETERS[name]), name, value)
    try:
        configuration = Configuration(**scenario["configuration"])
    except TypeError as error:
        raise ValueError(f"Invalid scenario configuration: {error}") from error
    world = World(id=f"world:{scenario['id']}", agents=agents,
                  global_state=GlobalState(price=scenario["initial_price"]),
                  metadata={"scenario_id": scenario["id"], "synthetic": True,
                            "population_overrides": deepcopy(overrides)})
    simulation = create_simulation(f"simulation:{scenario['id']}:seed-{seed}",
                                   seed, world, configuration, rng_state=rng.state)
    for definition in scenario["events"]:
        simulation = schedule_event(simulation, Event(**definition))
    return simulation


def _interventions(definition: dict, tick: int) -> list[Event]:
    return [Event(f"{definition['id']}:1-price", "PRICE_CHANGE", tick,
                  {"price": definition["price"]}),
            Event(f"{definition['id']}:2-incentive", "INCENTIVE", tick,
                  {"amount": definition["incentive"]})]


def _population_overrides(value: Any) -> dict:
    overrides = {} if value is None else value
    if type(overrides) is not dict or set(overrides) - set(POPULATION_PARAMETERS):
        raise ValueError("Unsupported population overrides")
    validate_json(overrides, "population_overrides")
    for key, number in overrides.items():
        try:
            valid = type(number) in (int, float) and math.isfinite(number) and 0 <= number <= 1
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"population_overrides.{key} must be a finite number in [0,1]")
    return deepcopy(overrides)


def load_experiment_scenario(scenario: str | Path | dict = DEFAULT_SCENARIO) -> dict:
    """Validate the legacy versioned scenario without executing any ticks."""
    if isinstance(scenario, (str, Path)):
        data = parse_json(Path(scenario).read_text(encoding="utf-8"))
    else:
        validate_json(scenario, "scenario")
        data = deepcopy(scenario)
    _require_fields(data, {"schema_version", "id", "population_size", "initial_price",
                          "initial_ticks", "branch_ticks", "configuration", "events",
                          "branches"}, "scenario")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported scenario schema version")
    if type(data["id"]) is not str or not data["id"].strip():
        raise ValueError("Scenario id must be nonempty")
    for key in ("population_size", "initial_ticks", "branch_ticks"):
        if type(data[key]) is not int or data[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if type(data["configuration"]) is not dict:
        raise ValueError("Scenario configuration must be an object")
    if type(data["events"]) is not list or type(data["branches"]) is not list:
        raise ValueError("Scenario events and branches must be arrays")
    for event in data["events"]:
        _require_fields(event, {"id", "type", "tick", "payload", "reach"}, "scenario event")
    branch_ids = []
    for branch in data["branches"]:
        _require_fields(branch, {"id", "label", "price", "incentive"}, "scenario branch")
        if type(branch["id"]) is not str or not branch["id"].strip():
            raise ValueError("Branch id must be nonempty")
        if type(branch["label"]) is not str:
            raise ValueError("Branch label must be a string")
        branch_ids.append(branch["id"])
    if not branch_ids or len(set(branch_ids)) != len(branch_ids):
        raise ValueError("Scenario requires distinct branches")
    data["branches"].sort(key=lambda branch: branch["id"])
    # Numeric/event contracts come from the kernel, including duplicate IDs.
    simulation = _initial_simulation(data, 0, {})
    data["events"].sort(key=lambda event: (event["tick"], event["id"]))
    for branch in data["branches"]:
        probe = simulation
        for event in _interventions(branch, data["initial_ticks"]):
            probe = schedule_event(probe, event)
    return data


def prepare_experiment(scenario, seeds, branches=None, ticks=None, *, population_overrides=None):
    """Preflight reusable by sensitivity: no simulation ticks or output writes."""
    data = load_experiment_scenario(scenario)
    if branches is not None:
        data["branches"] = deepcopy(branches)
        data = load_experiment_scenario(data)
    values = normalize_seeds(seeds)
    horizon = data["initial_ticks"] + data["branch_ticks"] if ticks is None else ticks
    if type(horizon) is not int or horizon <= data["initial_ticks"]:
        raise ValueError("Ticks must be a total horizon greater than the branch point")
    overrides = _population_overrides(population_overrides)
    # Population validation is independent of the random realization; all seeds
    # have already passed uint64 validation. Probe the exact overrides once.
    _initial_simulation(data, values[0], overrides)
    return data, values, horizon, overrides


def _validated_groups(runs: list[dict]) -> dict[str, list[dict]]:
    if type(runs) is not list or not runs:
        raise ValueError("Reports require a nonempty list of run summaries")
    validate_json(runs, "runs")
    groups: dict[str, list[dict]] = {}
    identifiers: set[str] = set()
    for run in runs:
        required = {"run_id", "seed", "scenario_version", "engine_version", "model_version",
                    "branch_id", "branch_point", "ticks", "origin_snapshot_id", "origin_checksum",
                    "configuration", "population_size", "active_agent_ids", "metrics",
                    "intervention", "experiment_id", "scenario_checksum", "rng_algorithm",
                    "scenario_schema_version", "population_overrides", "final_snapshot_id",
                    "final_checksum", "status", "branch_label"}
        if type(run) is not dict or not required <= set(run):
            raise ValueError("Run summary is missing required provenance")
        for key in ("run_id", "branch_id", "scenario_version", "engine_version", "model_version",
                    "origin_snapshot_id", "origin_checksum", "experiment_id", "scenario_checksum",
                    "rng_algorithm", "final_snapshot_id", "final_checksum"):
            if type(run[key]) is not str or not run[key].strip():
                raise ValueError(f"Run {key} must be nonempty text")
        validate_seed(run["seed"])
        if run["run_id"] in identifiers:
            raise ValueError("Run IDs must be unique")
        identifiers.add(run["run_id"])
        for key in ("branch_point", "ticks", "population_size"):
            if type(run[key]) is not int or run[key] < 0:
                raise ValueError(f"Run {key} must be a nonnegative integer")
        if run["ticks"] <= run["branch_point"]:
            raise ValueError("Run horizon must follow its branch point")
        active = run["active_agent_ids"]
        if (type(active) is not list or any(type(item) is not str or not item for item in active)
                or len(set(active)) != len(active) or len(active) > run["population_size"]):
            raise ValueError("Invalid active agent IDs")
        if (type(run["configuration"]) is not dict
                or set(run["configuration"]) != set(Configuration.__dataclass_fields__)):
            raise ValueError("Run configuration must be an object")
        configuration = Configuration(**run["configuration"])
        _validate_configuration(configuration)
        if configuration.model_version != run["model_version"] or run["engine_version"] != ENGINE_VERSION:
            raise ValueError("Run model/engine version is incompatible")
        if type(run["population_overrides"]) is not dict or type(run["intervention"]) is not dict:
            raise ValueError("Run overrides and intervention must be objects")
        _population_overrides(run["population_overrides"])
        intervention = run["intervention"]
        _require_fields(intervention, {"id", "label", "price", "incentive"}, "run intervention")
        if intervention["id"] != run["branch_id"] or intervention["label"] != run["branch_label"]:
            raise ValueError("Run intervention must match its branch identity and label")
        for field in ("price", "incentive"):
            try:
                number = intervention[field]
                valid = type(number) in (int, float) and math.isfinite(number) and number >= 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError("Run economic intervention values must be finite and nonnegative")
        for key in ("origin_checksum", "final_checksum", "scenario_checksum"):
            checksum = run[key]
            if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
                raise ValueError("Run checksums must be lowercase SHA-256 hex")
        if type(run["scenario_schema_version"]) is not int or run["scenario_schema_version"] != 1:
            raise ValueError("Unsupported run scenario schema")
        if run["status"] != "completed" or type(run["branch_label"]) is not str:
            raise ValueError("Reports require completed, labelled runs")
        if type(run["metrics"]) is not dict or set(run["metrics"]) != set(METRICS):
            raise ValueError("Run metrics must include exactly the six kernel metrics")
        for metric, value in run["metrics"].items():
            try:
                valid = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"Metric {metric} must be finite")
            if metric.endswith("_count"):
                if type(value) is not int or value < 0:
                    raise ValueError(f"Metric {metric} must be a nonnegative integer")
            elif not (-1 if metric == "average_sentiment" else 0) <= value <= 1:
                raise ValueError(f"Metric {metric} is outside its range")
        groups.setdefault(run["branch_id"], []).append(run)
    reference = runs[0]
    for group in groups.values():
        group.sort(key=lambda run: run["seed"])
        if len({run["seed"] for run in group}) != len(group):
            raise ValueError("Duplicate seed within branch")
        for run in group:
            for key in ("scenario_version", "engine_version", "model_version", "branch_point",
                        "ticks", "configuration", "population_size", "scenario_checksum",
                        "population_overrides", "rng_algorithm", "experiment_id", "scenario_schema_version"):
                if run.get(key) != reference.get(key):
                    raise ValueError(f"Incompatible run {key}")
            if (run["intervention"] != group[0]["intervention"]
                    or run["branch_label"] != group[0]["branch_label"]):
                raise ValueError("A branch must keep the same intervention and label across seeds")
    siblings: dict[int, dict] = {}
    for run in runs:
        prior = siblings.setdefault(run["seed"], run)
        if (run["origin_snapshot_id"] != prior["origin_snapshot_id"]
                or run["origin_checksum"] != prior["origin_checksum"]
                or sorted(run["active_agent_ids"]) != sorted(prior["active_agent_ids"])):
            raise ValueError("Branches within one seed must share origin and eligibility")
    return dict(sorted(groups.items()))


def aggregate_runs(runs: list[dict]) -> dict:
    groups = _validated_groups(runs)
    branches = []
    for branch_id, group in groups.items():
        metrics = {}
        for name in METRICS:
            values = [run["metrics"][name] for run in group]
            metrics[name] = {
                "count": len(values), "mean": statistics.mean(values),
                "median": statistics.median(values), "min": min(values), "max": max(values),
                "standard_deviation": statistics.pstdev(values),
                "variance": statistics.pvariance(values),
                "distribution": [{"seed": run["seed"], "run_id": run["run_id"],
                                  "value": run["metrics"][name]} for run in group],
            }
        branches.append({"branch_id": branch_id, "label": group[0].get("branch_label", branch_id),
                         "metrics": metrics})
    return {"report_version": EXPERIMENT_VERSION, "metrics": list(METRICS),
            "standard_deviation": "population", "branches": branches}


def compare_runs(runs: list[dict]) -> dict:
    groups = _validated_groups(runs)
    seed_sets = [{run["seed"] for run in group} for group in groups.values()]
    if any(seeds != seed_sets[0] for seeds in seed_sets):
        raise ValueError("Paired comparison requires the same seeds in every branch")
    pairs = []
    for left_id, right_id in combinations(groups, 2):
        left, right = groups[left_id], groups[right_id]
        for a, b in zip(left, right, strict=True):
            for key in ("origin_snapshot_id", "origin_checksum"):
                if a[key] != b[key]:
                    raise ValueError("Paired branches must share the exact origin per seed")
            if sorted(a["active_agent_ids"]) != sorted(b["active_agent_ids"]):
                raise ValueError("Paired branches must share active population IDs")
        metrics = {}
        for name in METRICS:
            deltas = [a["metrics"][name] - b["metrics"][name]
                      for a, b in zip(left, right, strict=True)]
            metrics[name] = {
                "delta_mean": statistics.mean([a["metrics"][name] for a in left])
                              - statistics.mean([b["metrics"][name] for b in right]),
                "delta_median": statistics.median([a["metrics"][name] for a in left])
                                - statistics.median([b["metrics"][name] for b in right]),
                "mean_paired_delta": statistics.mean(deltas),
                "median_paired_delta": statistics.median(deltas),
                "standard_deviation_paired_delta": statistics.pstdev(deltas),
                "left_greater": sum(delta > 0 for delta in deltas),
                "right_greater": sum(delta < 0 for delta in deltas),
                "ties": sum(delta == 0 for delta in deltas),
                "paired_deltas": [{"seed": run["seed"], "delta": delta}
                                  for run, delta in zip(left, deltas, strict=True)],
            }
        pairs.append({"left_branch_id": left_id, "right_branch_id": right_id,
                      "count": len(left), "metrics": metrics})
    return {"report_version": EXPERIMENT_VERSION, "paired": True,
            "delta_direction": "left minus right", "pairs": pairs,
            "limitations": deepcopy(LIMITATIONS),
            "interpretation": "Greater is numeric only; frequencies describe this simulated seed set."}


def run_experiment(scenario, seeds, branches=None, ticks=None, *, population_overrides=None) -> ExperimentResult:
    started = perf_counter()
    data, values, horizon, overrides = prepare_experiment(
        scenario, seeds, branches, ticks, population_overrides=population_overrides)
    scenario_checksum = _hash(data)
    protocol = {"report_version": EXPERIMENT_VERSION, "scenario": data,
                "seeds": values, "ticks": horizon, "population_overrides": overrides,
                "engine_version": ENGINE_VERSION}
    experiment_id = f"experiment-{_hash(protocol)}"
    runs, timings, origins = [], [], []
    for seed in values:
        origin_started = perf_counter()
        simulation = _initial_simulation(data, seed, overrides)
        origin = run_ticks(simulation, data["initial_ticks"])
        snapshot = create_snapshot(origin)
        origin_seconds = perf_counter() - origin_started
        origins.append({"seed": seed, "duration_seconds": origin_seconds,
                        "snapshot_bytes": len(snapshot.to_json().encode("utf-8")),
                        "memory_count": sum(len(agent.memory) for agent in origin.world.agents)})
        # Keep only this seed's small continuations until core comparability is
        # checked, then release them. No full snapshots accumulate across seeds.
        completed = []
        for definition in data["branches"]:
            branch_started = perf_counter()
            branch = create_branch(snapshot, BranchConfiguration(definition["id"],
                                   {"label": definition["label"], "intervention": definition}))
            for event in _interventions(definition, data["initial_ticks"]):
                branch.simulation = schedule_event(branch.simulation, event)
            branch.simulation = run_ticks(branch.simulation, horizon - data["initial_ticks"])
            final_snapshot = create_snapshot(branch.simulation)
            final_bytes = len(final_snapshot.to_json().encode("utf-8"))
            run_id = f"run-{_hash({'experiment_id': experiment_id, 'seed': seed, 'branch_id': branch.id})}"
            runs.append({
                "run_id": run_id, "experiment_id": experiment_id, "seed": seed,
                "scenario_version": data["id"], "scenario_schema_version": data["schema_version"],
                "scenario_checksum": scenario_checksum, "engine_version": ENGINE_VERSION,
                "model_version": branch.simulation.configuration.model_version,
                "rng_algorithm": branch.simulation.rng_state.algorithm,
                "branch_id": branch.id, "branch_label": definition["label"],
                "branch_point": data["initial_ticks"], "ticks": horizon,
                "origin_snapshot_id": snapshot.id, "origin_checksum": snapshot.checksum,
                "final_snapshot_id": final_snapshot.id, "final_checksum": final_snapshot.checksum,
                "configuration": asdict(branch.simulation.configuration),
                "population_size": data["population_size"], "population_overrides": deepcopy(overrides),
                "active_agent_ids": sorted(agent.id for agent in branch.simulation.world.agents if agent.state.active),
                "intervention": deepcopy(definition), "metrics": asdict(branch.simulation.metrics),
                "status": "completed",
            })
            duration = perf_counter() - branch_started
            timings.append({"run_id": run_id, "seed": seed, "branch_id": branch.id,
                            "continuation_seconds": duration,
                            "duration_seconds": duration + origin_seconds / len(data["branches"]),
                            "final_snapshot_bytes": final_bytes,
                            "final_memory_count": sum(len(agent.memory) for agent in branch.simulation.world.agents)})
            completed.append(branch)
        compare_branches(completed)
    aggregate, comparison = aggregate_runs(runs), compare_runs(runs)
    manifest = {
        **protocol, "experiment_id": experiment_id, "scenario_version": data["id"],
        "scenario_checksum": scenario_checksum,
        "scenario_version_policy": "Versioned scenario ID plus canonical content SHA-256",
        "model_version": runs[0]["model_version"], "configuration": deepcopy(runs[0]["configuration"]),
        "rng_algorithm": runs[0]["rng_algorithm"], "rng_pairing_policy": "shared-origin-single-stream-v1",
        "branch_point": data["initial_ticks"], "population_size": data["population_size"],
        "run_count": len(runs), "primary_metric": "adoption_rate", "external_calls": 0,
        "metric_semantics": {"rates": "Final state, denominator = active agents; empty = zero",
                             "counts": "Cumulative since tick 0, including shared origin",
                             "standard_deviation": "Population, denominator N; singleton = zero"},
        "population_override_policy": "Absolute value for all agents at tick 0 after seeded generation; fixed group metadata",
        "storage_policy": "Compact run summaries and checksums; full states released per seed; no persisted snapshots",
        "limitations": deepcopy(LIMITATIONS),
    }
    total = perf_counter() - started
    benchmark = {"total_seconds": total, "run_count": len(runs),
                 "runs_per_second": len(runs) / total if total else 0.0,
                 "mean_seconds_per_run": total / len(runs),
                 "population_size": data["population_size"], "ticks": horizon,
                 "seed_count": len(values), "branch_count": len(data["branches"]),
                 "executed_ticks": len(values) * (data["initial_ticks"] + len(data["branches"]) * (horizon - data["initial_ticks"])),
                 "python_version": platform.python_version(), "platform": platform.platform(),
                 "timing_scope": "Preflight, simulation, snapshot sizing and reports; excludes disk output",
                 "per_run_duration_policy": "Continuation plus equal share of this seed's origin; overhead in total only",
                 "origins": origins, "runs": timings}
    return ExperimentResult(manifest, runs, aggregate, comparison, benchmark)


def save_experiment(result: ExperimentResult, directory: str | Path) -> None:
    """Pre-serialize, then write to a fresh/empty directory; never merge batches."""
    documents = {"manifest.json": result.manifest, "aggregate.json": result.aggregate,
                 "comparison.json": result.comparison, "benchmark.json": result.benchmark,
                 "sensitivity.json": result.sensitivity or {"status": "not_requested"}}
    serialized = {name: canonical_json(data) + "\n" for name, data in documents.items()}
    run_documents = [canonical_json(run) + "\n" for run in result.runs]
    destination = Path(directory)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Experiment output directory must be absent or empty; choose a new path")
    destination.mkdir(parents=True, exist_ok=True)
    run_directory = destination / "runs"
    run_directory.mkdir()
    for name, contents in serialized.items():
        (destination / name).write_text(contents, encoding="utf-8")
    for index, contents in enumerate(run_documents, 1):
        (run_directory / f"run-{index:06d}.json").write_text(contents, encoding="utf-8")


def summarize_experiment(result: ExperimentResult) -> str:
    manifest = result.manifest
    lines = ["FutureOS Experiment", f"Seeds: {len(manifest['seeds'])} | Agents: {manifest['population_size']} | Ticks: {manifest['ticks']} | Runs: {manifest['run_count']}"]
    for branch in result.aggregate["branches"]:
        metric = branch["metrics"]["adoption_rate"]
        lines.append(f"Branch {branch['branch_id']}: adoption mean {metric['mean']:.2%}, median {metric['median']:.2%}, std dev {metric['standard_deviation']:.2%}, range {metric['min']:.2%}..{metric['max']:.2%}")
    for pair in result.comparison["pairs"]:
        metric = pair["metrics"]["adoption_rate"]
        lines.append(f"{pair['left_branch_id']} > {pair['right_branch_id']} in {metric['left_greater']} / {pair['count']} paired runs; {pair['right_branch_id']} > {pair['left_branch_id']} in {metric['right_greater']} / {pair['count']}; ties {metric['ties']}")
    lines.append(f"Duration: {result.benchmark['total_seconds']:.3f}s | {result.benchmark['runs_per_second']:.3f} runs/s")
    lines.extend(LIMITATIONS[:4])
    return "\n".join(lines)
