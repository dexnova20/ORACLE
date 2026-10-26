"""Diagnostic experiment dataset schema and fixture definitions."""

from ml.dataset.schema import (
    DATASET_SCHEMA_VERSION,
    CaseFeatures,
    DiagnosticCase,
    ExpectedDiagnosticOutcome,
    GroundTruthLabel,
    ObservedSymptom,
    ProvenanceMetadata,
    TelemetryFeatures,
    TestResultFeature,
)
from ml.dataset.fixtures import (
    SYNTHETIC_DATABASE_UNREACHABLE_CASE,
    SYNTHETIC_CONFIG_MISSING_CASE,
    SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE,
)

__all__ = [
    "DATASET_SCHEMA_VERSION",
    "CaseFeatures",
    "DiagnosticCase",
    "ExpectedDiagnosticOutcome",
    "GroundTruthLabel",
    "ObservedSymptom",
    "ProvenanceMetadata",
    "TelemetryFeatures",
    "TestResultFeature",
    "SYNTHETIC_DATABASE_UNREACHABLE_CASE",
    "SYNTHETIC_CONFIG_MISSING_CASE",
    "SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE",
]
