"""Small, offline acceptance evidence for the repaired M12 and optional M13.

Run with Python 3.13 from the workspace. Timings are observational evidence,
never deterministic identifiers. No providers other than the fake are called.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"
DESCRIPTION = "Donos de pequenos restaurantes avaliando uma solução de automação."
PROTECTED = ("engine.py", "models.py", "randomness.py", "audit.py", "codec.py",
             "snapshots.py", "validation.py", "branches.py", "population.py")


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + "\n", encoding="utf-8")


def source_integrity() -> dict:
    baseline = ROOT / "results" / "m13-baseline" / "futureos"
    rows = {}
    for name in PROTECTED:
        old, new = baseline / name, ROOT / "futureos" / name
        before = hashlib.sha256(old.read_bytes()).hexdigest()
        after = hashlib.sha256(new.read_bytes()).hexdigest()
        rows[name] = {"before": before, "after": after, "unchanged": before == after}
    return {"all_unchanged": all(row["unchanged"] for row in rows.values()),
            "files": rows, "comparison": "Bytes captured before this mission, not Git history"}


def small_smoke(spec) -> dict:
    from futureos.audit import final_state_hash
    from futureos.engine import run_ticks
    from futureos.population_generator import (
        create_simulation_from_population_spec, generate_population_with_relationships,
    )
    from futureos.population_spec import PopulationSpec
    from futureos.population_validation import validate_population_spec
    from futureos.codec import canonical_json

    validate_population_spec(spec)
    reviewed_json = canonical_json(spec.to_json())
    reviewed = PopulationSpec.from_json(reviewed_json)
    before = reviewed.to_json()
    agents = generate_population_with_relationships(reviewed, 2026)
    other = generate_population_with_relationships(PopulationSpec.from_json(reviewed_json), 2026)
    assert agents == other
    initial = create_simulation_from_population_spec(reviewed, 2026, audit_mode="trace")
    assert initial.world.agents == agents
    final = run_ticks(initial, 5)
    repeat = run_ticks(create_simulation_from_population_spec(
        PopulationSpec.from_json(reviewed_json), 2026, audit_mode="trace"), 5)
    assert final == repeat
    assert reviewed.to_json() == before
    assert initial.world.current_tick == 0
    return {"status": "COMPLETE", "execution": "REAL", "seed": 2026,
            "population_size": len(agents), "relationship_count": sum(len(a.relationships) for a in agents),
            "ticks_executed": final.world.current_tick, "audit_mode": "trace",
            "metrics": asdict(final.metrics), "hashes": {
                "finalStateHash": final_state_hash(final),
                "trajectoryHash": final.audit.trajectory_hash,
                "eventTraceHash": final.audit.event_trace_hash,
            },
            "same_json_and_seed_same_society": True, "repeat_hashes_match": True,
            "input_spec_preserved": True,
            "stages_executed": ["PopulationSpec", "validate_population_spec", "JSON review roundtrip",
                                "generate_population_with_relationships", "create_simulation_from_population_spec",
                                "5 ticks", "metrics", "repeat equality and hashes"]}


def run_m12_smoke() -> dict:
    from futureos.models import Traits
    from futureos.population_spec import Archetype, PopulationSpec
    spec = PopulationSpec(
        size=8, archetypes=[Archetype("a", 0.5, Traits(openness=0.7)),
                            Archetype("b", 0.5, Traits(openness=0.4))],
        relationship_policy={"type": "random_sparse", "average_degree": 2},
        trait_distributions={"risk_tolerance": {"type": "fixed", "value": 0.4},
                             "openness": {"type": "uniform", "min": 0.4, "max": 0.9},
                             "price_sensitivity": {"type": "bounded_normal", "mean": 0.7,
                                                   "spread": 0.1, "min": 0, "max": 1}},
        assumptions=["População sintética não calibrada; parâmetros são hipóteses."],
        warnings=["SYNTHETIC_POPULATION", "UNCALIBRATED_POPULATION"],
    )
    result = small_smoke(spec)
    result["initial_attempt"] = {
        "execution": "REAL", "status": "FAILED_CODE_DEPENDENCY",
        "error": "ImportError: population_generator imported validate_population_spec from population_spec",
        "environment_blocked": False,
        "missing_contract": "create_simulation_from_population_spec was absent",
        "baseline_suite": {"tests_run": 160, "failures": 4, "errors": 4, "seconds": 14.978, "exit_code": 1},
    }
    result["repairs"] = ["M12 import, spec-driven generation and Simulation helper",
                         "M11 minimal typed adapter", "legacy CLI and trajectory return isolation"]
    result["spec"] = spec.to_json()
    result["verified_at"] = datetime.now(timezone(timedelta(hours=-3))).isoformat()
    save(ROOT / "docs" / "M12_1_SMOKE_RESULT.json", result)
    return result


def run_m13_smoke() -> dict:
    from futureos.llm_provider import FakeLLMProvider
    from futureos.population_planner import LLMPopulationPlanner
    spec = LLMPopulationPlanner(FakeLLMProvider()).plan(DESCRIPTION, size=8)
    save(EVIDENCE / "M13_POPULATION_SPEC.json", spec.to_json())
    result = small_smoke(spec)
    result.update(description=DESCRIPTION, provider="fake", model=spec.metadata["model"],
                  planner_version=spec.metadata["planner_version"],
                  assumptions=spec.assumptions, warnings=spec.warnings,
                  provenance=spec.metadata, source_integrity=source_integrity(),
                  verified_at=datetime.now(timezone(timedelta(hours=-3))).isoformat())
    result["stages_executed"][:0] = ["Human description", "LLMPopulationPlanner with FakeLLMProvider"]
    assert result["source_integrity"]["all_unchanged"]
    save(EVIDENCE / "M13_SMOKE_RESULT.json", result)
    return result


def run_suite() -> dict:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    with (EVIDENCE / "M13_SUITE.txt").open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {"execution": "REAL", "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "skips": len(result.skipped), "successful": result.wasSuccessful(),
              "seconds": time.perf_counter() - started,
              "verified_at": datetime.now(timezone(timedelta(hours=-3))).isoformat()}
    save(EVIDENCE / "M13_SUITE_RESULT.json", report)
    smoke_path = ROOT / "docs" / "M12_1_SMOKE_RESULT.json"
    if smoke_path.exists():
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        smoke["final_suite"] = report
        save(smoke_path, smoke)
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("m12", "m13", "suite"))
    stage = parser.parse_args().stage
    result = {"m12": run_m12_smoke, "m13": run_m13_smoke, "suite": run_suite}[stage]()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if stage == "suite" and not result["successful"]:
        raise SystemExit(1)
