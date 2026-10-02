from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

ExperimentSource = Literal["manual","llm_generated"]
@dataclass(slots=True)
class ExperimentSpec:
    id: str; name: str
    population_spec_path: str | None = None
    scenario_spec_path: str | None = None
    seeds: list[int] = field(default_factory=lambda: [2026])
    branch_tick: int = 0
    metadata: dict = field(default_factory=dict)
    source: ExperimentSource = "manual"
