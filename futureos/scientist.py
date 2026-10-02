"""Scientist Engine — deterministic, read-only. No LLM."""
from .scientist import ScientistReport, Observation, StabilityResult, PairedComparison
from .scientist import paired_comparison, detect_outliers, _stability
