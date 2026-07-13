"""The governed analysis platform: analyses as declarative specs.

  spec     - ParamSpec / StepSpec / AnalysisSpec (an analysis is a spec)
  registry - the analysis catalog (profiling, feature engineering, credit risk)
  engine   - the governed interpreter for linear specs
  tools    - the algorithms a step invokes (profiling, quality, features)
"""

from __future__ import annotations

from .engine import STATUS_BLOCKED, STATUS_COMPLETED, AnalysisEngine, AnalysisRun
from .registry import (
    ANALYSES,
    all_analyses,
    get_analysis,
    linear_analyses,
)
from .spec import (
    ENGINE_CREDIT_RISK,
    ENGINE_LINEAR,
    AnalysisSpec,
    ParamError,
    ParamSpec,
    StepSpec,
)

__all__ = [
    "AnalysisSpec",
    "ParamSpec",
    "StepSpec",
    "ParamError",
    "ENGINE_LINEAR",
    "ENGINE_CREDIT_RISK",
    "ANALYSES",
    "all_analyses",
    "get_analysis",
    "linear_analyses",
    "AnalysisEngine",
    "AnalysisRun",
    "STATUS_COMPLETED",
    "STATUS_BLOCKED",
]
