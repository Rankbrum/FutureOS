"""Population proposal contracts shared by manual input and the LLM planner."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

from .models import Traits

VALID_TRAIT_KEYS = tuple(Traits.__dataclass_fields__)

SourceType = Literal["manual", "llm_generated", "dataset_calibrated"]
WarningType = Literal["SYNTHETIC_POPULATION", "UNCALIBRATED_POPULATION"]


@dataclass(slots=True)
class Archetype:
    id: str
    weight: float = 1.0
    traits: Traits = field(default_factory=Traits)
    metadata: dict[str, str | int | float | bool | None | list | dict] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("Archetype.id must be non-empty str")
        if self.weight < 0:
            raise ValueError("Archetype.weight must be >= 0")


@dataclass(slots=True)
class PopulationSpec:
    size: int
    archetypes: list[Archetype] = field(default_factory=list)
    relationship_policy: str | dict = "uniform"
    trait_distributions: dict[str, dict] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    source: SourceType = "manual"
    warnings: list[WarningType] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.size < 1:
            raise ValueError("PopulationSpec.size must be >= 1")
        if self.source not in ("manual", "llm_generated", "dataset_calibrated"):
            raise ValueError("Invalid source")
        for w in self.warnings:
            if w not in ("SYNTHETIC_POPULATION", "UNCALIBRATED_POPULATION"):
                raise ValueError("Invalid warning")

    def to_json(self) -> dict:
        """Return a detached JSON-compatible proposal for human review."""
        from .population_validation import validate_population_spec
        validate_population_spec(self)
        return asdict(self)

    @classmethod
    def from_json(cls, value: str | dict) -> PopulationSpec:
        """Decode the existing schema strictly, then apply its shared validator."""
        from .codec import canonical_json, parse_json
        from .population_validation import (
            PopulationSpecValidationError, validate_population_spec,
        )

        if isinstance(value, str):
            value = parse_json(value)
        if not isinstance(value, dict):
            raise PopulationSpecValidationError("PopulationSpec JSON must be an object")
        # Validate JSON values and detach all nested containers from the caller.
        value = parse_json(canonical_json(value))
        allowed = set(cls.__dataclass_fields__)
        unknown = set(value) - allowed
        if unknown:
            raise PopulationSpecValidationError("Unknown PopulationSpec field(s): " + ", ".join(sorted(unknown)))
        for key in ("size", "archetypes"):
            if key not in value:
                raise PopulationSpecValidationError(f"Missing PopulationSpec field: {key}")
        raw_archetypes = value["archetypes"]
        if not isinstance(raw_archetypes, list):
            raise PopulationSpecValidationError("archetypes must be a list")
        archetypes = []
        for index, raw in enumerate(raw_archetypes):
            path = f"archetypes[{index}]"
            if not isinstance(raw, dict):
                raise PopulationSpecValidationError(f"{path} must be an object")
            if set(raw) - set(Archetype.__dataclass_fields__):
                raise PopulationSpecValidationError(f"Unknown field at {path}")
            for key in ("id", "weight", "traits"):
                if key not in raw:
                    raise PopulationSpecValidationError(f"Missing {path}.{key}")
            traits = raw["traits"]
            if not isinstance(traits, dict):
                raise PopulationSpecValidationError(f"{path}.traits must be an object of numeric traits")
            unknown_traits = set(traits) - set(VALID_TRAIT_KEYS)
            if unknown_traits:
                raise PopulationSpecValidationError("Unknown trait(s): " + ", ".join(sorted(unknown_traits)))
            try:
                archetypes.append(Archetype(
                    id=raw["id"], weight=raw["weight"], traits=Traits(**traits),
                    metadata=raw.get("metadata", {}),
                ))
            except (TypeError, ValueError) as error:
                raise PopulationSpecValidationError(f"Invalid values at {path}") from error
        try:
            spec = cls(**{**value, "archetypes": archetypes})
        except (TypeError, ValueError) as error:
            raise PopulationSpecValidationError("Invalid PopulationSpec fields") from error
        validate_population_spec(spec)
        return spec
