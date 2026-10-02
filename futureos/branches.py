"""Independent continuations and numeric comparison from one immutable origin."""

from copy import deepcopy
from dataclasses import asdict, dataclass, field

from .models import JsonValue, Simulation
from .snapshots import Snapshot, restore_snapshot
from .validation import validate_json, validate_simulation


@dataclass
class BranchConfiguration:
    id: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass
class Branch:
    id: str
    parent_simulation_id: str
    parent_snapshot_id: str
    branch_point: int
    simulation: Simulation
    metadata: dict[str, JsonValue] = field(default_factory=dict)


def create_branch(snapshot: Snapshot, configuration: BranchConfiguration) -> Branch:
    if not isinstance(configuration, BranchConfiguration):
        raise ValueError("Expected BranchConfiguration")
    if type(configuration.id) is not str or not configuration.id.strip():
        raise ValueError("Branch id must be a nonempty string")
    if type(configuration.metadata) is not dict:
        raise ValueError("Branch metadata must be a JSON object")
    validate_json(configuration.metadata, "branch.metadata")
    simulation = restore_snapshot(snapshot)
    parent_id = simulation.id
    if configuration.id == parent_id:
        raise ValueError("Branch id must differ from parent simulation id")
    simulation.id = f"{parent_id}/branch/{configuration.id}"
    metadata = deepcopy(configuration.metadata)
    # Validate branch metadata through the same JSON-only simulation contract.
    simulation.metadata["lineage"] = {"parent_simulation_id": parent_id,
                                      "parent_snapshot_id": snapshot.id,
                                      "branch_point": simulation.world.current_tick,
                                      "branch_id": configuration.id,
                                      "metadata": deepcopy(metadata)}
    validate_simulation(simulation)
    return Branch(configuration.id, parent_id, snapshot.id,
                  simulation.world.current_tick, simulation, metadata)


def compare_branches(branches: list[Branch]) -> list[dict[str, JsonValue]]:
    if type(branches) is not list or not branches:
        raise ValueError("Comparison requires at least one branch")
    for branch in branches:
        if not isinstance(branch, Branch):
            raise ValueError("Comparison requires Branch objects")
        validate_simulation(branch.simulation)
        if type(branch.id) is not str or not branch.id.strip():
            raise ValueError("Branch id must be nonempty")
        if type(branch.branch_point) is not int or branch.branch_point < 0:
            raise ValueError("Branch point must be a nonnegative integer")
        if branch.simulation.world.current_tick < branch.branch_point:
            raise ValueError("Branch horizon precedes its origin")
        if type(branch.metadata) is not dict:
            raise ValueError("Branch metadata must be a JSON object")
        validate_json(branch.metadata, "branch.metadata")
        expected_lineage = {"parent_simulation_id": branch.parent_simulation_id,
                            "parent_snapshot_id": branch.parent_snapshot_id,
                            "branch_point": branch.branch_point, "branch_id": branch.id,
                            "metadata": branch.metadata}
        if branch.simulation.metadata.get("lineage") != expected_lineage:
            raise ValueError("Branch lineage is inconsistent with simulation metadata")
        if branch.simulation.id != f"{branch.parent_simulation_id}/branch/{branch.id}":
            raise ValueError("Branch simulation identity is inconsistent")
    first = branches[0]
    ids: set[str] = set()
    results: list[dict[str, JsonValue]] = []
    first_population = sorted((agent.id, agent.state.active) for agent in first.simulation.world.agents)
    for branch in branches:
        validate_simulation(branch.simulation)
        if branch.id in ids:
            raise ValueError("Comparison requires distinct branch IDs")
        ids.add(branch.id)
        if (branch.parent_snapshot_id != first.parent_snapshot_id
                or branch.parent_simulation_id != first.parent_simulation_id
                or branch.branch_point != first.branch_point):
            raise ValueError("Comparison requires the same snapshot origin")
        if branch.simulation.world.current_tick != first.simulation.world.current_tick:
            raise ValueError("Comparison requires the same tick horizon")
        if branch.simulation.configuration != first.simulation.configuration:
            raise ValueError("Comparison requires the same model configuration")
        audit = branch.simulation.audit
        first_audit = first.simulation.audit
        versions = ((audit.engine_version, audit.rng_version, audit.trace_version)
                    if audit else None)
        first_versions = ((first_audit.engine_version, first_audit.rng_version, first_audit.trace_version)
                          if first_audit else None)
        if versions != first_versions:
            raise ValueError("Comparison requires the same engine/RNG/trace versions")
        if branch.simulation.seed != first.simulation.seed:
            raise ValueError("Comparison requires the same seed")
        if sorted((agent.id, agent.state.active) for agent in branch.simulation.world.agents) != first_population:
            raise ValueError("Comparison requires the same population IDs and eligibility")
        results.append({"id": branch.id, "simulation_id": branch.simulation.id,
                        "parent_simulation_id": branch.parent_simulation_id,
                        "parent_snapshot_id": branch.parent_snapshot_id,
                        "branch_point": branch.branch_point,
                        "current_tick": branch.simulation.world.current_tick,
                        **asdict(branch.simulation.metrics)})
    return results
