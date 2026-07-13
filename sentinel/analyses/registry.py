"""The analysis catalog: pre-built analyses as declarative specs.

Three analyses ship. Two are linear (the AnalysisEngine runs them): a
data-profiling + quality-triage analysis that applies to any tabular dataset,
and a relational feature-engineering analysis that applies to the Berka bank
tables. The third describes the credit-risk modeling pipeline as a spec for the
catalog, but is executed by the LangGraph Orchestrator because it has a human
approval gate and model promotion the linear engine deliberately omits.
"""

from __future__ import annotations

from ..datasets.contracts import (
    CAP_PROTECTED,
    CAP_RELATIONAL,
    CAP_TABULAR,
    CAP_TARGET,
)
from .spec import (
    ENGINE_CREDIT_RISK,
    ENGINE_LINEAR,
    P_BOOL,
    P_CHOICE,
    P_FLOAT,
    P_INT,
    AnalysisSpec,
    ParamSpec,
    StepSpec,
)

DATA_PROFILING = AnalysisSpec(
    id="data_profiling",
    name="Data profiling & quality triage",
    description="Profile any tabular dataset and run a declarative data-quality "
    "expectation suite. The quality gate is the control before modeling: a "
    "blocking failure (excess missingness, degenerate target) should stop a "
    "pipeline.",
    engine=ENGINE_LINEAR,
    requires=frozenset({CAP_TABULAR}),
    min_rows=100,
    default_dataset_id="uci_taiwan_credit",
    params=(
        ParamSpec(
            "sample_rows", "Profile sample size", P_INT, 0, minimum=0, maximum=100000,
            help="0 profiles all rows; a positive value profiles a deterministic sample.",
        ),
        ParamSpec(
            "max_cardinality", "High-cardinality threshold", P_INT, 50, minimum=2, maximum=1000,
            help="Categorical columns with more unique values are flagged.",
        ),
        ParamSpec(
            "missing_threshold", "Max missing fraction", P_FLOAT, 0.2, minimum=0.0, maximum=1.0,
            help="Columns above this missing fraction fail the quality gate (blocking).",
        ),
        ParamSpec(
            "outlier_z", "Outlier z-score", P_FLOAT, 4.0, minimum=1.0, maximum=10.0,
            help="Numeric values beyond this many standard deviations are counted as outliers.",
        ),
    ),
    steps=(
        StepSpec(
            "load", "Governed data access", "data_connector", "load_dataset_frames",
            "Load the registered dataset under a license check; access is audited.",
        ),
        StepSpec(
            "profile", "Profile columns", "data_profiler", "profile_dataset",
            "Per-column type, missingness, cardinality, and summary statistics.",
            produces=("profile",),
        ),
        StepSpec(
            "quality", "Quality expectation suite", "quality_checker", "run_quality_checks",
            "Evaluate the expectation suite and gate on blocking failures.",
            produces=("quality",),
        ),
    ),
    outputs=("profile", "quality"),
    tags=("EDA", "data-quality"),
)

FEATURE_ENGINEERING = AnalysisSpec(
    id="feature_engineering",
    name="Relational feature engineering",
    description="Build per-account features from the Berka bank tables with a "
    "pre-decision window guard, then independently scan the feature set for target "
    "leakage. Demonstrates relational aggregation with model-risk lineage.",
    engine=ENGINE_LINEAR,
    requires=frozenset({CAP_TABULAR, CAP_RELATIONAL}),
    min_rows=100,
    default_dataset_id="berka",
    params=(
        ParamSpec(
            "window_days", "Pre-decision window (days)", P_INT, 365, minimum=0, maximum=3650,
            help="Aggregate transactions only within this many days before the loan "
            "date. 0 uses all pre-loan history.",
        ),
        ParamSpec(
            "include_rfm", "Include RFM features", P_BOOL, True,
            help="Add recency / frequency / monetary features from the transaction log.",
        ),
        ParamSpec(
            "top_k", "Keep top-K features", P_INT, 0, minimum=0, maximum=20,
            help="0 keeps all features; else keep the K most correlated with the target.",
        ),
        ParamSpec(
            "corr_threshold", "Leakage correlation threshold", P_FLOAT, 0.98,
            minimum=0.5, maximum=1.0,
            help="A feature correlating with the target above this is flagged as leakage.",
        ),
    ),
    steps=(
        StepSpec(
            "load", "Governed data access", "data_connector", "load_dataset_frames",
            "Load the relational tables under a license check; access is audited.",
        ),
        StepSpec(
            "features", "Build entity features", "feature_engineer", "build_entity_features",
            "Aggregate transactions per account within the pre-decision window.",
            produces=("features",),
        ),
        StepSpec(
            "leakage", "Leakage scan", "feature_engineer", "leakage_scan",
            "Independently verify no feature leaks the target (structural + correlation).",
            produces=("leakage",),
        ),
    ),
    outputs=("features", "leakage"),
    tags=("feature-engineering", "relational"),
)

CREDIT_RISK = AnalysisSpec(
    id="credit_risk",
    name="Credit-default risk model (governed)",
    description="The hero pipeline: profile, EDA, train a baseline model, pause at "
    "the human approval gate, then fairness + eval gate. Executed by the LangGraph "
    "orchestrator because it promotes a model and needs the human gate.",
    engine=ENGINE_CREDIT_RISK,
    requires=frozenset({CAP_TABULAR, CAP_TARGET, CAP_PROTECTED}),
    min_rows=100,
    default_dataset_id="german_credit",
    params=(
        ParamSpec(
            "protected_attribute", "Protected attribute", P_CHOICE, "age_band",
            choices=("age_band", "sex", "foreign_worker"),
            help="The attribute the fairness step evaluates disparity across.",
        ),
        ParamSpec(
            "narration_mode", "Narration", P_CHOICE, "scripted",
            choices=("scripted", "live"),
            help="Scripted narration is free; live routes through the model gateway.",
        ),
        ParamSpec(
            "seed", "Random seed", P_INT, 42, minimum=0, maximum=999999,
            help="Seed for the train/test split.",
        ),
    ),
    steps=(
        StepSpec("profile", "Profiler", "profiler", "profile_dataset",
                 "Profile the data and flag class-balance risk.", produces=("profile",)),
        StepSpec("eda", "EDA / Feature", "eda", "profile_dataset",
                 "Review distributions and propose feature handling.", produces=("eda",)),
        StepSpec("model", "Modeler", "modeler", "train_model",
                 "Train the baseline model and request approval.", produces=("model",)),
        StepSpec("gate", "Human approval gate", "human_reviewer", "approve",
                 "Pause for a human promotion decision (interrupt).", gate=True),
        StepSpec("validate", "Validator", "validator", "run_eval_gate",
                 "Fairness review + eval gate; promote or block.", produces=("fairness", "evals")),
    ),
    outputs=("model", "fairness", "evals"),
    controls=("PII", "RBAC", "Audit", "Human Gate", "Eval Gate", "Contract"),
    tags=("modeling", "fairness", "hero"),
)

ANALYSES: list[AnalysisSpec] = [DATA_PROFILING, FEATURE_ENGINEERING, CREDIT_RISK]
_BY_ID = {a.id: a for a in ANALYSES}


def all_analyses() -> list[AnalysisSpec]:
    return list(ANALYSES)


def get_analysis(analysis_id: str) -> AnalysisSpec | None:
    return _BY_ID.get(analysis_id)


def linear_analyses() -> list[AnalysisSpec]:
    return [a for a in ANALYSES if a.engine == ENGINE_LINEAR]
