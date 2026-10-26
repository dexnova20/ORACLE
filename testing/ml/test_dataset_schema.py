"""Unit tests for diagnostic dataset schema and target-leakage prevention."""

import pytest
from pydantic import ValidationError

from ml.dataset import (
    DATASET_SCHEMA_VERSION,
    CaseFeatures,
    DiagnosticCase,
    ExpectedDiagnosticOutcome,
    GroundTruthLabel,
    ObservedSymptom,
    ProvenanceMetadata,
    TelemetryFeatures,
    TestResultFeature,
    SYNTHETIC_DATABASE_UNREACHABLE_CASE,
    SYNTHETIC_CONFIG_MISSING_CASE,
    SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE,
)
from ml.taxonomy import FaultCategory


def test_schema_version_is_consistent() -> None:
    """Verify dataset schema version string."""
    assert DATASET_SCHEMA_VERSION == "1.0.0"


def test_synthetic_fixtures_are_valid_and_marked_synthetic() -> None:
    """Assert all synthetic test fixtures validate and have is_synthetic set to True."""
    fixtures = [
        SYNTHETIC_DATABASE_UNREACHABLE_CASE,
        SYNTHETIC_CONFIG_MISSING_CASE,
        SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE,
    ]

    for fixture in fixtures:
        assert isinstance(fixture, DiagnosticCase)
        assert fixture.is_synthetic is True
        assert fixture.case_id.startswith("synth-case-")
        assert len(fixture.project_id) > 0
        assert len(fixture.scenario_id) > 0
        assert fixture.ground_truth.root_cause_category in FaultCategory
        assert len(fixture.expected_outcome.primary_action) > 0


def test_target_leakage_safeguard_in_to_model_features() -> None:
    """Critical safeguard: to_model_features() must NEVER contain ground truth or outcome."""
    case = SYNTHETIC_DATABASE_UNREACHABLE_CASE
    features = case.to_model_features()

    # Must contain input feature fields
    assert "symptoms" in features
    assert "component_identifiers" in features
    assert "dependency_identifiers" in features
    assert "test_results" in features
    assert "telemetry" in features
    assert "missing_evidence_indicators" in features

    # Must NOT contain target labels or outcomes
    assert "ground_truth" not in features
    assert "expected_outcome" not in features
    assert "root_cause_category" not in features
    assert "root_cause_component" not in features
    assert "root_cause_detail" not in features
    assert "primary_action" not in features


def test_forbidden_target_leakage_token_in_symptom_raises_validation_error() -> None:
    """Verify that symptoms containing forbidden target tokens ('root_cause', 'ground_truth') are rejected."""
    with pytest.raises(ValidationError) as excinfo:
        ObservedSymptom(
            symptom_type="log",
            source="app",
            message_pattern="Error occurred: root_cause is database connection dropped",
        )
    assert "Target leakage detected" in str(excinfo.value)


def test_forbidden_target_leakage_token_in_test_snippet_raises_validation_error() -> None:
    """Verify that test snippets containing forbidden target tokens are rejected."""
    with pytest.raises(ValidationError) as excinfo:
        TestResultFeature(
            test_id="test_db",
            passed=False,
            duration_ms=10.0,
            error_message_snippet="AssertionError: ground_truth check failed",
        )
    assert "Target leakage detected" in str(excinfo.value)


def test_verbatim_ground_truth_smuggling_into_symptoms_raises_validation_error() -> None:
    """Verify that model validator catches cases where ground-truth text is smuggled into symptoms."""
    leaked_detail = "Specific secret bug in auth module line 42"
    with pytest.raises(ValidationError) as excinfo:
        DiagnosticCase(
            case_id="leak-test-001",
            project_id="test-proj",
            scenario_id="test-scen",
            is_synthetic=True,
            features=CaseFeatures(
                symptoms=[
                    ObservedSymptom(
                        symptom_type="log",
                        source="auth",
                        message_pattern=f"Log: {leaked_detail} happened unexpectedly",
                    )
                ]
            ),
            ground_truth=GroundTruthLabel(
                root_cause_category=FaultCategory.RUNTIME_EXCEPTION,
                root_cause_component="auth",
                root_cause_detail=leaked_detail,
            ),
            expected_outcome=ExpectedDiagnosticOutcome(
                primary_action="REPLACE_LINE_42",
            ),
        )
    assert "Target leakage detected" in str(excinfo.value)


def test_telemetry_numeric_validation() -> None:
    """Verify out-of-range telemetry metrics raise ValidationError."""
    # Negative latency
    with pytest.raises(ValidationError):
        TelemetryFeatures(latency_p50_ms=-5.0)

    # Error rate > 1.0
    with pytest.raises(ValidationError):
        TelemetryFeatures(error_rate=1.5)

    # CPU > 100%
    with pytest.raises(ValidationError):
        TelemetryFeatures(cpu_utilization_pct=105.0)
