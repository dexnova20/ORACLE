"""Experiment tracking protocol and reproducibility configuration.

Supports local MLflow integration (file-store based) and metadata manifests
without requiring remote server infrastructure or cloud dependencies.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

# Keys that may contain sensitive data or credentials and must be redacted
SENSITIVE_PARAM_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"key", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"database_url", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
]

REDACTED_PLACEHOLDER = "[REDACTED]"


def sanitize_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize experiment parameters by redacting sensitive secrets or credentials."""
    sanitized: Dict[str, Any] = {}
    for key, value in params.items():
        is_sensitive = any(pattern.search(key) for pattern in SENSITIVE_PARAM_PATTERNS)
        if is_sensitive:
            sanitized[key] = REDACTED_PLACEHOLDER
        elif isinstance(value, str) and ("://" in value and "@" in value):
            # Potential connection string with embedded credentials: postgresql://user:pass@host
            sanitized[key] = re.sub(r"://[^:]+:[^@]+@", "://[REDACTED]:[REDACTED]@", value)
        else:
            sanitized[key] = value
    return sanitized


def generate_run_name(
    model_name: str,
    split_strategy: str,
    taxonomy_version: str = "1.0.0",
) -> str:
    """Generate standardized, unambiguous MLflow experiment run name."""
    clean_model = model_name.lower().replace(" ", "_")
    clean_split = split_strategy.lower().replace(" ", "_")
    return f"oracle-diag-v{taxonomy_version}-{clean_model}-{clean_split}"


class ExperimentManifest(BaseModel):
    """Immutable audit record for a reproducible diagnostic model experiment."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., description="Unique run identifier")
    run_name: str = Field(..., description="Standardized run name")
    experiment_name: str = Field(default="oracle-diagnostics", description="Logical experiment container")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC experiment execution timestamp",
    )
    git_commit_sha: Optional[str] = Field(None, description="Exact Git commit hash of the research codebase")
    dataset_schema_version: str = Field(..., description="Dataset schema version string")
    dataset_case_count: int = Field(..., ge=0, description="Total number of diagnostic cases in dataset")
    split_strategy: str = Field(
        ...,
        description="Dataset splitting strategy (e.g. project_aware, scenario_aware)",
    )
    model_type: str = Field(..., description="Model architecture or baseline type")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized hyperparameter and configuration dictionary",
    )
    metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Evaluation metrics (top1_acc, top3_acc, macro_f1, ece, latency_ms)",
    )
    artifact_paths: List[str] = Field(
        default_factory=list,
        description="Relative paths to logged artifacts (confusion_matrix.json, model.onnx, etc.)",
    )


class LocalTrackingConfig(BaseModel):
    """Configuration for local experiment tracking without remote servers."""

    model_config = ConfigDict(frozen=True)

    tracking_uri: str = Field(
        default="file:./ml/experiments/mlruns",
        description="Local directory URI for MLflow file store",
    )
    artifact_root: str = Field(
        default="./ml/experiments/artifacts",
        description="Local directory for model artifacts",
    )
    dvc_enabled: bool = Field(
        default=False,
        description=(
            "DVC is not enabled for Phase 006: dataset schemas and test fixtures are lightweight (<1MB) "
            "and versioned directly in git. DVC will be activated when binary dataset artifacts exceed 100MB."
        ),
    )
