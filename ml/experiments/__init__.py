"""Experimentation, evaluation, splitting, and tracking for diagnostic ML."""

from ml.experiments.splitting import (
    DataLeakageError,
    ProjectAwareSplitter,
    ScenarioAwareSplitter,
    group_cases_by_project,
    group_cases_by_scenario,
)
from ml.experiments.evaluation import (
    top_k_ranking_accuracy,
    classification_metrics,
    false_positive_rate,
    expected_calibration_error,
    abstention_metrics,
    diagnostic_cost_metrics,
)
from ml.experiments.tracking import (
    ExperimentManifest,
    LocalTrackingConfig,
    generate_run_name,
    sanitize_parameters,
)

__all__ = [
    "DataLeakageError",
    "ProjectAwareSplitter",
    "ScenarioAwareSplitter",
    "group_cases_by_project",
    "group_cases_by_scenario",
    "top_k_ranking_accuracy",
    "classification_metrics",
    "false_positive_rate",
    "expected_calibration_error",
    "abstention_metrics",
    "diagnostic_cost_metrics",
    "ExperimentManifest",
    "LocalTrackingConfig",
    "generate_run_name",
    "sanitize_parameters",
]
