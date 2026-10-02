"""A small reproducible experiment; scenario values are synthetic fixtures."""

from dataclasses import asdict, dataclass
from pathlib import Path
import platform
from typing import Any

from .branches import Branch, BranchConfiguration, compare_branches, create_branch
from .codec import canonical_json, parse_json
from .engine import create_simulation, run_ticks, schedule_event
from .models import Configuration, ENGINE_VERSION, Event, GlobalState, World
from .population import create_population
from .randomness import SeededRandom
from .snapshots import Snapshot, create_snapshot, restore_snapshot, save_snapshot


DEFAULT_SCENARIO = Path(__file__).resolve().parent.parent / "scenarios" / "kernel-demo.json"


@dataclass
class DemoResult:
    snapshot: Snapshot
    branches: list[Branch]
    report: dict[str, Any]


def _require_fields(value: Any, expected: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{label}: missing or unknown fields")


def load_scenario(path: str | Path) -> dict[str, Any]:
    scenario = parse_json(Path(path).read_text(encoding="utf-8"))
    _require_fields(scenario, {"schema_version", "id", "population_size", "initial_price",
                              "initial_ticks", "branch_ticks", "configuration", "events",
                              "branches"}, "scenario")
    if type(scenario["schema_version"]) is not int or scenario["schema_version"] != 1:
        raise ValueError("Unsupported scenario schema version")
    if type(scenario["id"]) is not str or not scenario["id"].strip():
        raise ValueError("Scenario id must be nonempty")
    for key in ("population_size", "initial_ticks", "branch_ticks"):
        if type(scenario[key]) is not int or scenario[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if type(scenario["configuration"]) is not dict:
        raise ValueError("Scenario configuration must be an object")
    if type(scenario["events"]) is not list or type(scenario["branches"]) is not list:
        raise ValueError("Scenario events and branches must be arrays")
    branch_ids = []
    for branch in scenario["branches"]:
        _require_fields(branch, {"id", "label", "price", "incentive"}, "scenario branch")
        if type(branch["id"]) is not str or not branch["id"].strip():
            raise ValueError("Scenario branch id must be nonempty")
        if type(branch["label"]) is not str:
            raise ValueError("Scenario branch label must be a string")
        branch_ids.append(branch["id"])
        # Validate intervention numbers through the core event contract below.
    if not branch_ids or len(set(branch_ids)) != len(branch_ids):
        raise ValueError("Scenario requires distinct branches")
    for event in scenario["events"]:
        _require_fields(event, {"id", "type", "tick", "payload", "reach"}, "scenario event")
    return scenario


def run_demo(seed: int = 2026, scenario_path: str | Path = DEFAULT_SCENARIO) -> DemoResult:
    scenario = load_scenario(scenario_path)
    rng = SeededRandom(seed)
    agents = create_population(scenario["population_size"], rng)
    try:
        configuration = Configuration(**scenario["configuration"])
    except TypeError as error:
        raise ValueError(f"Invalid scenario configuration: {error}") from error
    world = World(id=f"world:{scenario['id']}", agents=agents,
                  global_state=GlobalState(price=scenario["initial_price"]),
                  metadata={"scenario_id": scenario["id"], "synthetic": True})
    simulation = create_simulation(f"simulation:{scenario['id']}", seed, world,
                                   configuration, rng_state=rng.state)
    for definition in scenario["events"]:
        simulation = schedule_event(simulation, Event(**definition))
    # Validate every intervention before executing any ticks.
    interventions = {}
    for definition in scenario["branches"]:
        events = [Event(f"{definition['id']}:1-price", "PRICE_CHANGE", scenario["initial_ticks"],
                        {"price": definition["price"]}),
                  Event(f"{definition['id']}:2-incentive", "INCENTIVE", scenario["initial_ticks"],
                        {"amount": definition["incentive"]})]
        for event in events:
            schedule_event(simulation, event)
        interventions[definition["id"]] = events
    origin = run_ticks(simulation, scenario["initial_ticks"])
    snapshot = Snapshot.from_json(create_snapshot(origin).to_json())
    resumed = restore_snapshot(snapshot)
    if resumed != origin:
        raise RuntimeError("Snapshot roundtrip changed simulation state")
    branches = [create_branch(snapshot, BranchConfiguration(item["id"],
                {"label": item["label"], "intervention": item})) for item in scenario["branches"]]
    for branch in branches:
        for event in interventions[branch.id]:
            branch.simulation = schedule_event(branch.simulation, event)
        branch.simulation = run_ticks(branch.simulation, scenario["branch_ticks"])
    report = {
        "manifest_version": 1,
        "engine_version": ENGINE_VERSION,
        "model_version": configuration.model_version,
        "python_version": platform.python_version(),
        "rng_algorithm": rng.state.algorithm,
        "seed": seed,
        "scenario": scenario,
        "configuration": asdict(configuration),
        "population_size": len(agents),
        "tick_unit": configuration.tick_unit,
        "origin_snapshot_id": snapshot.id,
        "origin_checksum": snapshot.checksum,
        "branch_point": origin.world.current_tick,
        "horizon": origin.world.current_tick + scenario["branch_ticks"],
        "origin_metrics": asdict(origin.metrics),
        "comparison": compare_branches(branches),
        "external_calls": 0,
        "limitations": ["Synthetic population and provisional uncalibrated adoption rule.",
                        "Conditional engineering experiment, not a prediction or business recommendation.",
                        "One seed; no statistical sensitivity analysis or empirical validation.",
                        "Price and incentive persist until another event replaces them; no revenue model.",
                        "One isolated RNG stream per simulation; differing reach can alter subsequent draws."]
    }
    return DemoResult(snapshot, branches, report)


def save_demo(result: DemoResult, directory: str | Path) -> None:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    save_snapshot(result.snapshot, destination / "origin.snapshot.json")
    for index, branch in enumerate(result.branches):
        # File names use an index; user-defined branch IDs never become paths.
        save_snapshot(create_snapshot(branch.simulation), destination / f"branch-{index + 1}.snapshot.json")
    (destination / "report.json").write_text(canonical_json(result.report) + "\n", encoding="utf-8")
