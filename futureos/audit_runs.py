"""Versioned M3 artifacts, deterministic replay and branch divergence.

Runs retain hashes, compact tick frames and an optional detailed trace. Their
replay protocol rebuilds the declared scenario; a run is not a resumable final
snapshot. Timings and filesystem paths never participate in identities.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from .audit import RECORD_KINDS, final_state_hash
from .branches import BranchConfiguration, create_branch
from .codec import canonical_json, parse_json
from .demo import DEFAULT_SCENARIO
from .engine import create_simulation, run_ticks, schedule_event
from .experiments import load_experiment_scenario, normalize_seeds
from .models import Configuration, Event, GlobalState, M3_ENGINE_VERSION, Metrics, TRACE_VERSION, World
from .population import create_population
from .randomness import RNG_POLICY, RandomStreams, validate_seed
from .snapshots import Snapshot, create_snapshot
from .validation import _number, _validate_configuration, validate_json


ARTIFACT_VERSION = 1
REPLAY_PROTOCOL = "scenario-rebuild-v1"
HASH_FIELDS = ("finalStateHash", "trajectoryHash", "eventTraceHash")
VERSION_FIELDS = {"engineVersion": M3_ENGINE_VERSION,
                  "rngVersion": RNG_POLICY, "traceVersion": TRACE_VERSION}
LIMITATIONS = [
    "Synthetic agents and uncalibrated rules; results are conditional on the declared assumptions.",
    "Internal mechanisms describe algorithm provenance, not real-world causality.",
    "Summary retains tick hashes and metrics but cannot recover detailed agent trajectories.",
    "SHA-256 detects changed contents; it does not authenticate an author.",
    "Scenario replay requires the supported engine, RNG and trace versions.",
]


@dataclass
class AuditExperimentResult:
    manifest: dict[str, Any]
    runs: list[dict[str, Any]]
    divergences: list[dict[str, Any]]


def _hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _prepare(scenario: str | Path | dict, seeds: Iterable[int], ticks: int | None,
             mode: str) -> tuple[dict, list[int], int]:
    if mode not in ("summary", "trace"):
        raise ValueError("Audit mode must be summary or trace")
    data = load_experiment_scenario(scenario)
    values = normalize_seeds(seeds)
    horizon = data["initial_ticks"] + data["branch_ticks"] if ticks is None else ticks
    if type(horizon) is not int or horizon < data["initial_ticks"]:
        raise ValueError("Ticks must be a total horizon at or after the branch point")
    return data, values, horizon


def _protocol(data: dict, horizon: int) -> dict:
    return {"artifactVersion": ARTIFACT_VERSION, "replayProtocol": REPLAY_PROTOCOL,
            "scenario": data, "ticks": horizon, **VERSION_FIELDS}


def _experiment_id(data: dict, horizon: int) -> str:
    # A protocol can be replayed for one seed without changing its identity.
    return f"audit-experiment-{_hash(_protocol(data, horizon))}"


def _interventions(definition: dict, tick: int) -> list[Event]:
    return [Event(f"{definition['id']}:1-price", "PRICE_CHANGE", tick,
                  {"price": definition["price"]}),
            Event(f"{definition['id']}:2-incentive", "INCENTIVE", tick,
                  {"amount": definition["incentive"]})]


def _origin(data: dict, seed: int, mode: str):
    streams = RandomStreams(seed)
    agents = create_population(data["population_size"], streams.stream("population"))
    world = World(id=f"world:{data['id']}", agents=agents,
                  global_state=GlobalState(price=data["initial_price"]),
                  metadata={"scenario_id": data["id"], "synthetic": True})
    simulation = create_simulation(f"simulation:{data['id']}:seed-{seed}", seed,
                                   world, Configuration(**data["configuration"]),
                                   audit_mode=mode)
    for definition in data["events"]:
        simulation = schedule_event(simulation, Event(**definition))
    simulation = run_ticks(simulation, data["initial_ticks"])
    return simulation, create_snapshot(simulation)


def _frame(frame) -> dict:
    return {"tick": frame.tick, "stateHash": frame.state_hash,
            "stateTick": frame.tick + 1, "tickUnit": frame.tick_unit, "activeCount": frame.active_count,
            "agentHashes": deepcopy(frame.agent_hashes), "metrics": deepcopy(frame.metrics)}


def _run(data: dict, seed: int, horizon: int, mode: str,
         definition: dict, origin, snapshot: Snapshot) -> dict:
    branch = create_branch(snapshot, BranchConfiguration(definition["id"],
                           {"label": definition["label"], "intervention": definition}))
    interventions = _interventions(definition, data["initial_ticks"])
    for event in interventions:
        branch.simulation = schedule_event(branch.simulation, event)
    simulation = run_ticks(branch.simulation, horizon - data["initial_ticks"])
    audit = simulation.audit
    if audit is None:
        raise RuntimeError("M3 runner requires an audited simulation")
    experiment_id = _experiment_id(data, horizon)
    run_id = f"audit-run-{_hash({'experimentId': experiment_id, 'seed': seed, 'branchId': definition['id']})}"
    artifact = {
        "artifactVersion": ARTIFACT_VERSION, "runId": run_id, "experimentId": experiment_id,
        "seed": seed, "scenarioVersion": data["id"], "scenarioSchemaVersion": data["schema_version"],
        "scenarioChecksum": _hash(data), "scenario": deepcopy(data), **VERSION_FIELDS,
        "configuration": asdict(simulation.configuration), "mode": mode,
        "branchId": definition["id"], "branchLabel": definition["label"],
        "branchPoint": data["initial_ticks"], "ticks": horizon,
        "intervention": deepcopy(definition), "interventions": [asdict(event) for event in interventions],
        "originSnapshot": {"id": snapshot.id, "checksum": snapshot.checksum,
                           "schemaVersion": snapshot.schema_version,
                           "engineVersion": snapshot.engine_version,
                           "tick": origin.world.current_tick, "stateHash": final_state_hash(origin)},
        "replayProtocol": REPLAY_PROTOCOL, "status": "completed",
        "finalStateHash": final_state_hash(simulation),
        "trajectoryHash": audit.trajectory_hash, "eventTraceHash": audit.event_trace_hash,
        "traceCount": audit.trace_count, "metrics": asdict(simulation.metrics),
        "frames": [_frame(frame) for frame in audit.frames],
        "records": [asdict(record) for record in audit.records] if mode == "trace" else [],
    }
    validate_json(artifact, "auditRun")
    return artifact


def run_audit_experiment(scenario: str | Path | dict = DEFAULT_SCENARIO,
                         seeds: Iterable[int] = (2026,), ticks: int | None = None,
                         *, mode: str = "summary") -> AuditExperimentResult:
    """Run isolated branches from one M3 origin per seed in canonical order.

    ``ticks`` is a total horizon; equality with the branch point is permitted for
    the 10-tick profiling case. Its branch interventions remain scheduled.
    """
    data, values, horizon = _prepare(scenario, seeds, ticks, mode)
    runs, divergences = [], []
    for seed in values:
        origin, snapshot = _origin(data, seed, mode)
        siblings = [_run(data, seed, horizon, mode, definition, origin, snapshot)
                    for definition in data["branches"]]
        runs.extend(siblings)
        divergences.extend(compare_run_divergence(left, right)
                           for left, right in combinations(siblings, 2))
    manifest = {**_protocol(data, horizon), "experimentId": _experiment_id(data, horizon),
                "seeds": values, "mode": mode, "scenarioVersion": data["id"],
                "scenarioChecksum": _hash(data), "branchPoint": data["initial_ticks"],
                "configuration": deepcopy(runs[0]["configuration"]),
                "runIds": [run["runId"] for run in runs], "externalCalls": 0,
                "storagePolicy": "Scenario rebuild, origin references and compact frames; detailed records only in trace",
                "identityPolicy": "Protocol content plus seed and branch; excludes audit mode, clocks and paths",
                "limitations": deepcopy(LIMITATIONS)}
    return AuditExperimentResult(manifest, runs, divergences)


def _nonempty_text(value: Any, label: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be nonempty text")


def _digest(value: Any, label: str) -> None:
    if (type(value) is not str or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)):
        raise ValueError(f"{label} must be lowercase SHA-256 hex")


def _metrics(value: dict, label: str) -> None:
    if type(value) is not dict or set(value) != set(Metrics.__dataclass_fields__):
        raise ValueError(f"{label} must contain exactly the kernel metrics")
    for field, number in value.items():
        if field.endswith("_count"):
            if type(number) is not int or number < 0:
                raise ValueError(f"{label}.{field} must be a nonnegative integer")
        else:
            _number(number, f"{label}.{field}", -1 if field == "average_sentiment" else 0, 1)


def validate_run_artifact(run: dict) -> None:
    """Validate the external M3 schema before replay or report generation."""
    validate_json(run, "auditRun")
    expected = {"artifactVersion", "runId", "experimentId", "seed", "scenarioVersion",
                "scenarioSchemaVersion", "scenarioChecksum", "scenario", "engineVersion",
                "rngVersion", "traceVersion", "configuration", "mode", "branchId", "branchLabel",
                "branchPoint", "ticks", "intervention", "interventions", "originSnapshot",
                "replayProtocol", "status", "finalStateHash", "trajectoryHash", "eventTraceHash",
                "traceCount", "metrics", "frames", "records"}
    if type(run) is not dict or set(run) != expected:
        raise ValueError("Audit run has missing or unknown fields")
    if type(run["artifactVersion"]) is not int or run["artifactVersion"] != ARTIFACT_VERSION:
        raise ValueError("Unsupported audit artifact version")
    for key, version in VERSION_FIELDS.items():
        if run[key] != version:
            raise ValueError(f"Unsupported {key}: {run[key]!r}")
    if run["replayProtocol"] != REPLAY_PROTOCOL:
        raise ValueError("Unsupported replay protocol")
    validate_seed(run["seed"])
    for key in ("runId", "experimentId", "scenarioVersion", "branchId"):
        _nonempty_text(run[key], key)
    if type(run["branchLabel"]) is not str:
        raise ValueError("branchLabel must be text")
    if run["mode"] not in ("summary", "trace") or run["status"] != "completed":
        raise ValueError("Audit report requires completed summary or trace runs")
    if type(run["scenarioSchemaVersion"]) is not int or run["scenarioSchemaVersion"] != 1:
        raise ValueError("Unsupported scenario schema version")
    for key in ("branchPoint", "ticks", "traceCount"):
        if type(run[key]) is not int or run[key] < 0:
            raise ValueError(f"{key} must be a nonnegative integer")
    if run["ticks"] < run["branchPoint"]:
        raise ValueError("Run horizon precedes its origin")
    for key in (*HASH_FIELDS, "scenarioChecksum"):
        _digest(run[key], key)
    for key in ("scenario", "configuration", "intervention", "originSnapshot", "metrics"):
        if type(run[key]) is not dict:
            raise ValueError(f"{key} must be an object")
    scenario_fields = {"schema_version", "id", "population_size", "initial_price", "initial_ticks",
                       "branch_ticks", "configuration", "events", "branches"}
    if set(run["scenario"]) != scenario_fields:
        raise ValueError("Scenario has missing or unknown fields")
    population_size = run["scenario"]["population_size"]
    if type(population_size) is not int or population_size < 1:
        raise ValueError("Scenario population_size must be a positive integer")
    if set(run["configuration"]) != set(Configuration.__dataclass_fields__):
        raise ValueError("Run configuration has missing or unknown fields")
    _validate_configuration(Configuration(**run["configuration"]))
    _metrics(run["metrics"], "run.metrics")
    origin_fields = {"id", "checksum", "schemaVersion", "engineVersion", "tick", "stateHash"}
    origin = run["originSnapshot"]
    if set(origin) != origin_fields:
        raise ValueError("originSnapshot has missing or unknown fields")
    _nonempty_text(origin["id"], "originSnapshot.id")
    _digest(origin["checksum"], "originSnapshot.checksum")
    _digest(origin["stateHash"], "originSnapshot.stateHash")
    if (type(origin["schemaVersion"]) is not int or origin["schemaVersion"] != 2
            or origin["engineVersion"] != M3_ENGINE_VERSION
            or type(origin["tick"]) is not int or origin["tick"] != run["branchPoint"]):
        raise ValueError("Unsupported or inconsistent M3 origin snapshot")
    for key in ("interventions", "frames", "records"):
        if type(run[key]) is not list:
            raise ValueError(f"{key} must be an array")
    if run["mode"] == "summary" and run["records"]:
        raise ValueError("Summary artifact must not store the full trace")
    for frame in run["frames"]:
        if (type(frame) is not dict or set(frame) != {"tick", "stateHash", "agentHashes", "metrics",
                                                   "stateTick", "tickUnit", "activeCount"}
                or type(frame["tick"]) is not int or frame["tick"] < 0
                or type(frame["agentHashes"]) is not dict or type(frame["metrics"]) is not dict):
            raise ValueError("Invalid tick frame")
        if (type(frame["stateTick"]) is not int or frame["stateTick"] != frame["tick"] + 1
                or frame["tickUnit"] != run["configuration"]["tick_unit"]
                or type(frame["activeCount"]) is not int or not 0 <= frame["activeCount"] <= population_size):
            raise ValueError("Invalid frame state tick, unit or active denominator")
        _digest(frame["stateHash"], "frame.stateHash")
        for agent_id, checksum in frame["agentHashes"].items():
            _nonempty_text(agent_id, "frame agent ID")
            _digest(checksum, "frame agent hash")
        _metrics(frame["metrics"], "frame.metrics")
    frame_ticks = [frame["tick"] for frame in run["frames"]]
    if frame_ticks != list(range(run["ticks"])):
        raise ValueError("Run frames must cover every processed tick exactly once")
    agent_ids = set(run["frames"][0]["agentHashes"]) if run["frames"] else set()
    if len(agent_ids) != population_size or any(set(frame["agentHashes"]) != agent_ids for frame in run["frames"]):
        raise ValueError("Run frame population must match the scenario and remain consistent")
    for record in run["records"]:
        if (type(record) is not dict or set(record) != {"tick", "kind", "entity", "mechanism", "payload"}
                or type(record["tick"]) is not int or not 0 <= record["tick"] < run["ticks"]
                or type(record["payload"]) is not dict):
            raise ValueError("Invalid trace record")
        for key in ("kind", "entity", "mechanism"):
            _nonempty_text(record[key], f"record.{key}")
        if record["kind"] not in RECORD_KINDS:
            raise ValueError("Unsupported trace record kind")
        payload = record["payload"]
        if record["kind"] in ("state_changed", "relationship_changed"):
            if not {"field", "before", "after"} <= set(payload):
                raise ValueError("State delta requires field/before/after")
            _nonempty_text(payload["field"], "state delta field")
        if "contributions" in payload and (type(payload["contributions"]) is not list
                or any(type(item) is not dict for item in payload["contributions"])):
            raise ValueError("State contributions must be an array of objects")
        if "target_ids" in payload:
            targets = payload["target_ids"]
            if (type(targets) is not list or any(type(item) is not str for item in targets)
                    or len(set(targets)) != len(targets) or set(targets) - agent_ids):
                raise ValueError("Trace targets must be distinct known agent IDs")
        for key in ("target_agent_id", "source_agent_id"):
            if key in payload and (type(payload[key]) is not str or payload[key] not in agent_ids):
                raise ValueError("Trace interaction must reference known agent IDs")
    if run["mode"] == "trace" and len(run["records"]) != run["traceCount"]:
        raise ValueError("Trace record count differs from traceCount")
    record_ticks = [record["tick"] for record in run["records"]]
    if record_ticks != sorted(record_ticks):
        raise ValueError("Trace records must be ordered by processed tick")


def _first_difference(expected: list, actual: list) -> tuple[int, Any, Any] | None:
    for index in range(max(len(expected), len(actual))):
        left = expected[index] if index < len(expected) else None
        right = actual[index] if index < len(actual) else None
        if left != right:
            return index, left, right
    return None


def replay_run(expected: dict) -> dict:
    """Reexecute a supported artifact and locate the first detectable mismatch.

    Unsupported versions and malformed JSON/schema raise before tick execution.
    A well-formed but altered context, frame, trace or hash returns ``matched=False``.
    """
    validate_run_artifact(expected)
    data, _, horizon = _prepare(expected["scenario"], [expected["seed"]],
                                expected["ticks"], expected["mode"])
    definitions = {definition["id"]: definition for definition in data["branches"]}
    definition = definitions.get(expected["branchId"])
    checks = {
        "scenarioVersion": data["id"], "scenarioChecksum": _hash(data),
        "branchPoint": data["initial_ticks"], "configuration": asdict(Configuration(**data["configuration"])),
        "experimentId": _experiment_id(data, horizon),
        "intervention": definition,
        "branchLabel": definition["label"] if definition else None,
        "interventions": [asdict(event) for event in _interventions(definition, data["initial_ticks"])] if definition else None,
        "runId": f"audit-run-{_hash({'experimentId': _experiment_id(data, horizon), 'seed': expected['seed'], 'branchId': expected['branchId']})}",
    }
    for field, actual in checks.items():
        if expected[field] != actual:
            return {"runId": expected["runId"], "matched": False,
                    "firstDivergence": {"kind": "context", "field": field,
                                        "expected": expected[field], "actual": actual},
                    "hashes": {}, "interpretation": "Algorithm provenance; no real-world causal claim"}
    origin, snapshot = _origin(data, expected["seed"], expected["mode"])
    actual = _run(data, expected["seed"], horizon, expected["mode"], definition, origin, snapshot)
    hashes = {field: {"expected": expected[field], "actual": actual[field],
                      "matched": expected[field] == actual[field]} for field in HASH_FIELDS}
    divergence = None
    if expected["originSnapshot"] != actual["originSnapshot"]:
        divergence = {"kind": "context", "field": "originSnapshot",
                      "expected": expected["originSnapshot"], "actual": actual["originSnapshot"]}
    else:
        # Compare chronologically; records provide finer evidence within one tick.
        candidates = []
        for field, kind in (("records", "record"), ("frames", "frame")):
            difference = _first_difference(expected[field], actual[field])
            if difference:
                index, left, right = difference
                ticks = [item["tick"] for item in (left, right) if item is not None]
                candidates.append({"kind": kind, "index": index, "tick": min(ticks) if ticks else None,
                                   "expected": left, "actual": right})
        if candidates:
            divergence = min(candidates, key=lambda row: (row["tick"], row["kind"] != "record"))
        if divergence is None:
            for field in (*HASH_FIELDS, "traceCount", "metrics"):
                if expected[field] != actual[field]:
                    divergence = {"kind": "hash" if field in HASH_FIELDS else "summary",
                                  "field": field, "expected": expected[field], "actual": actual[field]}
                    break
    return {"runId": expected["runId"], "matched": divergence is None,
            "firstDivergence": divergence, "hashes": hashes,
            "detailAvailable": expected["mode"] == "trace",
            "interpretation": "Algorithm provenance; no real-world causal claim"}


def trajectory_from_run(run: dict, agent_id: str) -> list[dict]:
    """Recover owned changes, received events and interactions from a trace artifact."""
    validate_run_artifact(run)
    if run["mode"] != "trace":
        raise ValueError("Agent trajectory requires trace mode")
    if type(agent_id) is not str or agent_id not in run["frames"][0]["agentHashes"]:
        raise ValueError("Unknown agent ID")
    rows = [record for record in run["records"]
            if (record["entity"] == f"agent:{agent_id}"
                or record["payload"].get("source_agent_id") == agent_id
                or record["payload"].get("target_agent_id") == agent_id
                or agent_id in record["payload"].get("target_ids", []))]
    return deepcopy(rows)


def compare_run_divergence(left: dict, right: dict) -> dict:
    """Find the first differing committed tick for compatible sibling runs."""
    validate_run_artifact(left)
    validate_run_artifact(right)
    for field in ("seed", "scenarioVersion", "scenarioChecksum", "scenario", "branchPoint", "ticks",
                  "configuration", "engineVersion", "rngVersion", "traceVersion", "replayProtocol"):
        if left[field] != right[field]:
            raise ValueError(f"Branch divergence requires the same {field}")
    if left["originSnapshot"] != right["originSnapshot"]:
        raise ValueError("Branch divergence requires the exact same origin snapshot")
    first_tick, agents, metrics = None, [], {}
    first_metrics_tick, first_metrics = None, {}
    for a, b in zip(left["frames"], right["frames"], strict=True):
        metric_changes = {name: {"left": a["metrics"].get(name), "right": b["metrics"].get(name)}
                          for name in sorted(set(a["metrics"]) | set(b["metrics"]))
                          if a["metrics"].get(name) != b["metrics"].get(name)}
        if first_metrics_tick is None and metric_changes:
            first_metrics_tick, first_metrics = a["tick"], metric_changes
        if first_tick is None and a["stateHash"] != b["stateHash"]:
            first_tick = a["tick"]
            agents = [agent_id for agent_id in sorted(set(a["agentHashes"]) | set(b["agentHashes"]))
                      if a["agentHashes"].get(agent_id) != b["agentHashes"].get(agent_id)]
            metrics = metric_changes
    detail_available = left["mode"] == right["mode"] == "trace"
    changed_records = {"left": [], "right": []}
    mechanisms = []
    if first_tick is not None and detail_available:
        a = [record for record in left["records"] if record["tick"] == first_tick]
        b = [record for record in right["records"] if record["tick"] == first_tick]
        a_keys, b_keys = {canonical_json(record) for record in a}, {canonical_json(record) for record in b}
        changed_records = {"left": [record for record in a if canonical_json(record) not in b_keys],
                           "right": [record for record in b if canonical_json(record) not in a_keys]}
        mechanisms = sorted({record["mechanism"] for records in changed_records.values() for record in records})
    return {"leftRunId": left["runId"], "rightRunId": right["runId"], "seed": left["seed"],
            "originSnapshotId": left["originSnapshot"]["id"], "branchPoint": left["branchPoint"],
            "ticks": left["ticks"], "identical": first_tick is None, "firstTick": first_tick,
            "agents": agents, "metrics": metrics, "firstMetricsTick": first_metrics_tick,
            "firstMetrics": first_metrics, "mechanisms": mechanisms,
            "detailAvailable": detail_available, "records": deepcopy(changed_records),
            "detailStatus": "available" if detail_available else "Detailed mechanisms require trace mode",
            "interpretation": "First committed state difference and associated algorithm records; not real-world causality"}


def save_audit_experiment(result: AuditExperimentResult, directory: str | Path) -> None:
    """Pre-serialize to a fresh/empty directory; never overwrite an earlier run."""
    for run in result.runs:
        validate_run_artifact(run)
    documents = {"manifest.json": result.manifest, "divergences.json": result.divergences}
    serialized = {name: canonical_json(document) + "\n" for name, document in documents.items()}
    run_texts = [canonical_json(run) + "\n" for run in result.runs]
    destination = Path(directory)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Audit output directory must be absent or empty; choose a new path")
    destination.mkdir(parents=True, exist_ok=True)
    runs_directory = destination / "runs"
    runs_directory.mkdir()
    for name, contents in serialized.items():
        (destination / name).write_text(contents, encoding="utf-8", newline="\n")
    for index, contents in enumerate(run_texts, 1):
        (runs_directory / f"run-{index:06d}.json").write_text(contents, encoding="utf-8", newline="\n")


def load_run_artifact(path: str | Path) -> dict:
    run = parse_json(Path(path).read_text(encoding="utf-8"))
    validate_run_artifact(run)
    return run
