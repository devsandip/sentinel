"""Analysis tools: the algorithms an analysis step invokes.

Each tool is a plain function over a DataFrame (or a dict of frames) that returns
a typed, JSON-friendly result. They are the "algos are tools" layer: an analysis
step names one of these, and the engine invokes it through the guardrail
allow-list so every call is scoped and audited. Tools use pandas/numpy only, so
they run on the small prod instance with no heavy dependency.
"""

from __future__ import annotations

from .features import FeatureResult, build_entity_features, leakage_scan
from .profiling import ProfileResult, profile_frame
from .quality import QualityReport, run_quality_checks

__all__ = [
    "ProfileResult",
    "profile_frame",
    "QualityReport",
    "run_quality_checks",
    "FeatureResult",
    "build_entity_features",
    "leakage_scan",
]
