"""Validation shared by manual specs, reviewed JSON and LLM proposals."""
from __future__ import annotations

import math

from .codec import canonical_json
from .population_spec import Archetype, PopulationSpec, VALID_TRAIT_KEYS
from .models import Traits
from .relationship_generator import validate_relationship_policy

WEIGHT_EPSILON = 0.01
SUPPORTED_DISTRIBUTIONS = ("fixed", "uniform", "bounded_normal")
REQUIRED_LLM_WARNINGS = ("SYNTHETIC_POPULATION", "UNCALIBRATED_POPULATION")


class PopulationSpecValidationError(ValueError):
    pass


def _number(value, path, minimum=None, maximum=None):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise PopulationSpecValidationError(f"{path} must be a finite number")
    if minimum is not None and value < minimum:
        raise PopulationSpecValidationError(f"{path} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise PopulationSpecValidationError(f"{path} must be <= {maximum}")


def _check_dist(dist, path):
    if not isinstance(dist, dict):
        raise PopulationSpecValidationError(f"{path} must be an object")
    distribution = dist.get("type")
    fields = {
        "fixed": {"type", "value"},
        "uniform": {"type", "min", "max"},
        "bounded_normal": {"type", "mean", "spread", "min", "max"},
    }
    if not isinstance(distribution, str) or distribution not in fields:
        raise PopulationSpecValidationError(f"Unsupported distribution at {path}; use {SUPPORTED_DISTRIBUTIONS}")
    if set(dist) - fields[distribution]:
        raise PopulationSpecValidationError(f"Unknown distribution field at {path}")
    required = fields[distribution] if distribution != "bounded_normal" else {"type", "mean", "spread"}
    missing = required - set(dist)
    if missing:
        raise PopulationSpecValidationError(f"Missing {path} field(s): {', '.join(sorted(missing))}")
    if distribution == "fixed":
        _number(dist["value"], f"{path}.value", 0, 1)
        return
    minimum, maximum = dist.get("min", 0), dist.get("max", 1)
    _number(minimum, f"{path}.min", 0, 1)
    _number(maximum, f"{path}.max", 0, 1)
    if minimum > maximum:
        raise PopulationSpecValidationError(f"{path}.min must be <= max")
    if distribution == "bounded_normal":
        _number(dist["mean"], f"{path}.mean", minimum, maximum)
        _number(dist["spread"], f"{path}.spread", 0)


def _text_list(value, path):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise PopulationSpecValidationError(f"{path} must be a list of non-empty strings")


def validate_population_spec(spec):
    if not isinstance(spec, PopulationSpec):
        raise PopulationSpecValidationError("spec must be PopulationSpec")
    if type(spec.size) is not int or spec.size < 1:
        raise PopulationSpecValidationError("size must be a positive integer")
    if not isinstance(spec.archetypes, list) or not spec.archetypes:
        raise PopulationSpecValidationError("archetypes must be a non-empty list")
    ids, weights = [], []
    for index, archetype in enumerate(spec.archetypes):
        path = f"archetypes[{index}]"
        if not isinstance(archetype, Archetype):
            raise PopulationSpecValidationError(f"{path} must be Archetype")
        if not isinstance(archetype.id, str) or not archetype.id.strip():
            raise PopulationSpecValidationError(f"{path}.id must be non-empty")
        ids.append(archetype.id)
        _number(archetype.weight, f"{path}.weight", 0, 1)
        if archetype.weight == 0:
            raise PopulationSpecValidationError(f"{path}.weight must be > 0")
        weights.append(archetype.weight)
        if not isinstance(archetype.traits, Traits):
            raise PopulationSpecValidationError(f"{path}.traits must be Traits")
        for key in VALID_TRAIT_KEYS:
            _number(getattr(archetype.traits, key), f"{path}.traits.{key}", 0, 1)
        if not isinstance(archetype.metadata, dict):
            raise PopulationSpecValidationError(f"{path}.metadata must be an object")
        canonical_json(archetype.metadata)
    if len(ids) != len(set(ids)):
        raise PopulationSpecValidationError("duplicate archetype id")
    if abs(math.fsum(weights) - 1.0) > WEIGHT_EPSILON:
        raise PopulationSpecValidationError(f"invalid weight sum (epsilon={WEIGHT_EPSILON})")
    if not isinstance(spec.trait_distributions, dict):
        raise PopulationSpecValidationError("trait_distributions must be an object")
    for trait_name, dist in spec.trait_distributions.items():
        if trait_name not in VALID_TRAIT_KEYS:
            raise PopulationSpecValidationError(f"Unknown trait in trait_distributions: {trait_name}")
        _check_dist(dist, f"trait_distributions.{trait_name}")
    if spec.source not in ("manual", "llm_generated", "dataset_calibrated"):
        raise PopulationSpecValidationError("invalid source")
    _text_list(spec.assumptions, "assumptions")
    _text_list(spec.warnings, "warnings")
    if any(warning not in REQUIRED_LLM_WARNINGS for warning in spec.warnings):
        raise PopulationSpecValidationError("Unsupported population warning")
    if spec.source == "llm_generated":
        if not spec.assumptions:
            raise PopulationSpecValidationError("llm_generated requires explicit assumptions")
        if not set(REQUIRED_LLM_WARNINGS).issubset(spec.warnings):
            raise PopulationSpecValidationError("llm_generated requires SYNTHETIC_POPULATION and UNCALIBRATED_POPULATION warnings")
    if not isinstance(spec.metadata, dict):
        raise PopulationSpecValidationError("metadata must be an object")
    canonical_json(spec.metadata)
    try:
        validate_relationship_policy(spec)
    except (TypeError, ValueError) as error:
        raise PopulationSpecValidationError("Invalid relationship_policy") from error
