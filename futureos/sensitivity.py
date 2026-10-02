"""Local one-at-a-time experiments with explicit baselines and paired seeds.

Variants are complete, independent experiments. Their origins may differ, so
baseline deltas are never passed to the kernel's same-origin branch comparison.
Only compact manifests and metrics are retained, without full snapshots.
"""

from copy import deepcopy
from pathlib import Path
from statistics import mean, median, pstdev
from time import perf_counter
from typing import Any

from .codec import canonical_json, parse_json
from .experiments import ExperimentResult, prepare_experiment, run_experiment
from .validation import validate_json


POPULATION_PARAMETERS = frozenset({
    "price_sensitivity", "openness", "trust", "conformity", "influence",
    "risk_tolerance",
})
EVENT_PARAMETERS = {
    "PRICE_CHANGE": frozenset({"price"}),
    "INCENTIVE": frozenset({"amount"}),
    "NEWS": frozenset({"sentiment_delta", "trust_delta"}),
    "TRUST_SHOCK": frozenset({"trust_delta"}),
    "COMPETITOR_ENTRY": frozenset({"pressure"}),
}
LIMITATIONS = [
    "Synthetic agents and provisional rules are not calibrated to a real population.",
    "Simulated frequencies are not real-world probabilities or business recommendations.",
    "One-at-a-time analysis explores local changes, not interactions or global sensitivity.",
    "Population overrides set every agent's selected attribute at tick zero without extra RNG draws.",
    "Variants use identical seeds and horizons but may have different origin snapshots.",
    "Each simulation uses one RNG stream; different event reach can change later draw alignment.",
]


def load_sensitivity_protocol(protocol: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load a strict JSON protocol; validate every definition without executing."""
    if isinstance(protocol, (str, Path)):
        protocol = parse_json(Path(protocol).read_text(encoding="utf-8"))
    validate_json(protocol, "sensitivity protocol")
    if type(protocol) is not dict:
        raise ValueError("sensitivity protocol must be an object")
    required = {"schema_version", "variations"}
    if not required <= set(protocol) or set(protocol) - required - {"id"}:
        raise ValueError("sensitivity protocol has missing or unknown fields")
    if type(protocol["schema_version"]) is not int or protocol["schema_version"] != 1:
        raise ValueError("unsupported sensitivity schema_version")
    if "id" in protocol and (type(protocol["id"]) is not str or not protocol["id"].strip()):
        raise ValueError("sensitivity protocol id must be nonempty")
    variations = protocol["variations"]
    if type(variations) is not list or not variations:
        raise ValueError("sensitivity variations must be a nonempty array")
    identities = set()
    for index, variation in enumerate(variations):
        label = f"sensitivity variations[{index}]"
        if type(variation) is not dict:
            raise ValueError(f"{label} must be an object")
        target = variation.get("target")
        if type(target) is not str or target not in {"population", "event", "branch"}:
            raise ValueError(f"{label} has an unsupported target")
        fields = {"target", "parameter", "baseline", "values"}
        if target != "population":
            fields.add(f"{target}_id")
        if set(variation) != fields:
            raise ValueError(f"{label} has missing or unknown fields")
        parameter = variation["parameter"]
        if type(parameter) is not str:
            raise ValueError(f"{label}.parameter must be a string")
        if target == "population" and parameter not in POPULATION_PARAMETERS:
            raise ValueError(f"unsupported population sensitivity parameter: {parameter}")
        if target == "branch" and parameter not in {"price", "incentive"}:
            raise ValueError(f"unsupported branch sensitivity parameter: {parameter}")
        if target == "event" and parameter not in {
            "reach", "price", "amount", "sentiment_delta", "trust_delta", "pressure",
        }:
            raise ValueError(f"unsupported event sensitivity parameter: {parameter}")
        identifier = ""
        if target != "population":
            identifier = variation[f"{target}_id"]
            if type(identifier) is not str or not identifier.strip():
                raise ValueError(f"{label}.{target}_id must be nonempty")
        identity = (target, identifier, parameter)
        if identity in identities:
            raise ValueError(f"duplicate sensitivity variation: {identity}")
        identities.add(identity)
        values = variation["values"]
        if type(values) is not list or not values:
            raise ValueError(f"{label}.values must be a nonempty array")
        for value in [variation["baseline"], *values]:
            if type(value) not in (int, float):
                raise ValueError(f"{label} baseline and values must be finite numbers")
            try:
                # validate_json rejects nonfinite floats; converting rejects
                # integers that cannot be represented by kernel float fields.
                float(value)
            except OverflowError as error:
                raise ValueError(f"{label} value is too large") from error
            if target == "population" and not 0 <= value <= 1:
                raise ValueError(f"{label} population values must be in [0, 1]")
        if len(set(values)) != len(values):
            raise ValueError(f"{label}.values must be distinct")
    result = deepcopy(protocol)
    for variation in result["variations"]:
        variation["values"].sort()
    return result


def _variant(scenario: dict[str, Any], variation: dict[str, Any],
             value: float) -> tuple[dict[str, Any], dict[str, float]]:
    variant = deepcopy(scenario)
    target, parameter = variation["target"], variation["parameter"]
    overrides = {}
    if target == "population":
        overrides[parameter] = value
    elif target == "branch":
        selected = next((branch for branch in variant["branches"]
                         if branch["id"] == variation["branch_id"]), None)
        if selected is None:
            raise ValueError(f"unknown sensitivity branch_id: {variation['branch_id']}")
        selected[parameter] = value
    else:
        selected = next((event for event in variant["events"]
                         if event["id"] == variation["event_id"]), None)
        if selected is None:
            raise ValueError(f"unknown sensitivity event_id: {variation['event_id']}")
        if parameter == "reach":
            selected["reach"] = value
        elif (parameter in EVENT_PARAMETERS[selected["type"]]
              and parameter in selected["payload"]):
            selected["payload"][parameter] = value
        else:
            raise ValueError(f"{selected['id']} has no existing supported payload parameter {parameter}")
    return variant, overrides


def _report(result: ExperimentResult) -> dict[str, Any]:
    return deepcopy({
        "manifest": result.manifest, "runs": result.runs,
        "aggregate": result.aggregate, "comparison": result.comparison,
    })


def _baseline_deltas(baseline: ExperimentResult,
                     variant: ExperimentResult) -> dict[str, Any]:
    branches = []
    baseline_rows = {row["branch_id"]: row for row in baseline.aggregate["branches"]}
    for row in variant.aggregate["branches"]:
        reference = baseline_rows[row["branch_id"]]
        metrics = {}
        for metric, summary in row["metrics"].items():
            expected = {item["seed"]: item["value"]
                        for item in reference["metrics"][metric]["distribution"]}
            paired = [{"seed": item["seed"], "delta": item["value"] - expected[item["seed"]]}
                      for item in summary["distribution"]]
            deltas = [item["delta"] for item in paired]
            metrics[metric] = {
                "count": len(deltas),
                "delta_mean": summary["mean"] - reference["metrics"][metric]["mean"],
                "delta_median": summary["median"] - reference["metrics"][metric]["median"],
                "mean_paired_delta": mean(deltas), "median_paired_delta": median(deltas),
                "standard_deviation_paired_delta": pstdev(deltas),
                "variant_greater": sum(value > 0 for value in deltas),
                "baseline_greater": sum(value < 0 for value in deltas),
                "ties": sum(value == 0 for value in deltas),
                "paired_deltas": paired,
            }
        branches.append({"branch_id": row["branch_id"], "metrics": metrics})
    return {
        "paired": True, "delta_direction": "variant_minus_baseline",
        "comparison_scope": "independent_experiments_with_same_seeds_and_horizon",
        "branches": branches,
    }


def run_sensitivity(scenario: str | Path | dict[str, Any], seeds: list[int],
                    protocol: str | Path | dict[str, Any], branches=None,
                    ticks: int | None = None) -> ExperimentResult:
    """Execute an original experiment plus fully prevalidated OAT variants.

    The returned main manifest/runs describe the original scenario. Each analysis
    contains its own explicit baseline; population baselines replace one field
    for all agents and therefore need not equal the heterogeneous original.
    """
    protocol = load_sensitivity_protocol(protocol)
    base = prepare_experiment(scenario, seeds, branches, ticks)
    data, seed_values, horizon, _ = base
    normalized_scenario = deepcopy(data)
    specifications = []
    # Prepare every baseline and value before the first runner call. A bad late
    # variation must not leave partially executed experiments or output files.
    for variation in protocol["variations"]:
        prepared_values = []
        for value in [variation["baseline"], *variation["values"]]:
            variant, overrides = _variant(normalized_scenario, variation, value)
            prepared = prepare_experiment(variant, seed_values, None, horizon,
                                          population_overrides=overrides)
            prepared_values.append((value, prepared))
        specifications.append((variation, prepared_values))
    cache: dict[str, ExperimentResult] = {}

    def execute(prepared) -> ExperimentResult:
        variant, selected_seeds, selected_horizon, overrides = prepared
        key = canonical_json({"scenario": variant,
                              "seeds": selected_seeds, "ticks": selected_horizon,
                              "population_overrides": overrides})
        if key not in cache:
            cache[key] = run_experiment(
                variant, selected_seeds, ticks=selected_horizon,
                population_overrides=overrides,
            )
        return cache[key]

    started = perf_counter()
    result = execute(base)
    analyses = []
    for index, (variation, prepared_values) in enumerate(specifications, 1):
        baseline = execute(prepared_values[0][1])
        analysis = deepcopy(variation)
        analysis["id"] = f"oat-{index}"
        analysis["baseline_experiment"] = _report(baseline)
        analysis["variants"] = []
        for value, prepared in prepared_values[1:]:
            variant = execute(prepared)
            analysis["variants"].append({
                "value": value, "is_baseline": value == variation["baseline"],
                "experiment": _report(variant),
                "delta_vs_baseline": _baseline_deltas(baseline, variant),
            })
        analyses.append(analysis)
    result.sensitivity = {
        "schema_version": 1, "method": "one_at_a_time", "protocol": protocol,
        "analyses": analyses, "limitations": LIMITATIONS.copy(),
    }
    # Wall-clock data is intentionally outside the deterministic sensitivity JSON.
    timings = [{"experiment_id": experiment.manifest["experiment_id"],
                "benchmark": deepcopy(experiment.benchmark)} for experiment in cache.values()]
    total_seconds = perf_counter() - started
    run_count = sum(len(experiment.runs) for experiment in cache.values())
    result.benchmark["sensitivity"] = {
        "total_seconds": total_seconds,
        "unique_experiment_count": len(cache),
        "run_count": run_count,
        "runs_per_second": run_count / total_seconds if total_seconds else 0.0,
        "mean_seconds_per_run": total_seconds / run_count,
        "seed_count": len(seed_values), "population_size": data["population_size"],
        "ticks": horizon, "experiments": timings,
        "timing_scope": "All unique experiment executions and sensitivity summaries; excludes preflight and disk output",
    }
    return result
