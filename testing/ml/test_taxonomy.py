"""Unit tests for the ORACLE fault taxonomy."""

import pytest
from ml.taxonomy import (
    FAULT_TAXONOMY,
    TAXONOMY_VERSION,
    FaultCategory,
    get_taxonomy_entry,
    get_taxonomy_version,
    list_taxonomy_categories,
)


def test_taxonomy_version() -> None:
    """Verify taxonomy version string is consistent."""
    assert get_taxonomy_version() == "1.0.0"
    assert TAXONOMY_VERSION == "1.0.0"


def test_taxonomy_contains_all_ten_mandatory_categories() -> None:
    """Assert all ten required fault categories exist in the taxonomy."""
    expected_categories = {
        FaultCategory.CONFIG_MISSING_OR_INVALID,
        FaultCategory.DEPENDENCY_IMPORT_FAILURE,
        FaultCategory.IO_CONTRACT_VIOLATION,
        FaultCategory.RUNTIME_EXCEPTION,
        FaultCategory.DATA_VALIDATION_TRANSFORMATION,
        FaultCategory.API_COMMUNICATION_FAILURE,
        FaultCategory.DATABASE_CONNECTIVITY_SCHEMA,
        FaultCategory.MODEL_LOADING_INFERENCE_FAILURE,
        FaultCategory.PERFORMANCE_ANOMALY,
        FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE,
    }

    actual_categories = set(list_taxonomy_categories())
    assert actual_categories == expected_categories
    assert len(FAULT_TAXONOMY) == 10


def test_every_taxonomy_entry_has_complete_documentation() -> None:
    """Assert that every entry has observable evidence, confounding causes, reproduction, ground truth, and unclassifiable conditions."""
    for category in list_taxonomy_categories():
        entry = get_taxonomy_entry(category)

        assert entry.category == category
        assert len(entry.title.strip()) > 3
        assert len(entry.description.strip()) > 20

        # Observable evidence must have multiple distinct signals
        assert len(entry.observable_evidence) >= 2
        for signal in entry.observable_evidence:
            assert len(signal.strip()) > 5

        # Confounding causes must be articulated
        assert len(entry.confounding_causes) >= 1
        for cause in entry.confounding_causes:
            assert len(cause.strip()) > 5

        # Safe reproduction must be documented
        assert len(entry.safe_reproduction.strip()) > 15

        # Required ground truth evidence must be specified
        assert len(entry.required_ground_truth_evidence) >= 1
        for evidence in entry.required_ground_truth_evidence:
            assert len(evidence.strip()) > 5

        # Unclassifiable boundary conditions must be identified
        assert len(entry.unclassifiable_boundary_conditions) >= 1
        for boundary in entry.unclassifiable_boundary_conditions:
            assert len(boundary.strip()) > 5


def test_unknown_category_lookup_raises_key_error() -> None:
    """Verify attempting to lookup an invalid category raises KeyError."""
    with pytest.raises(KeyError):
        get_taxonomy_entry("non_existent_category")  # type: ignore[arg-type]
