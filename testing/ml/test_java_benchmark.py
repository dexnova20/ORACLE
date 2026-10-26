"""Automated benchmark tests for Java AST Analysis and Polyglot Dependency Intelligence (Implementation 014).

Verifies:
- All 22 Java benchmark scenarios (CASE-039 to CASE-060) are registered and evaluated.
- Ground truth isolation and neutral scenario identifiers.
- Healthy Java controls produce 0 false-positive diagnoses.
- Java syntax errors and unresolved internal imports are accurately diagnosed.
- Multiple simultaneous faults across separate Java files are separated into distinct hypotheses.
- Maven undeclared external dependencies are flagged, while declared dependencies are recognized.
- Multi-module Maven projects resolve cross-module types cleanly.
- Polyglot repositories (Java + Python + TypeScript) are parsed into a unified system map.
- Graceful degradation on malformed manifests.
- Deliberate abstention on empty/unsupported Java projects.
"""

import os
import re
import sys
import uuid
import pytest

from ml.benchmark.adaptive_runner import AdaptiveBenchmarkRunner
from ml.benchmark.runner import BenchmarkRunner
from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.models.repository import Repository, SourceType
from oracle.schemas.diagnostics import DiagnosticRunRequest


@pytest.fixture
def fixtures_dir() -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(repo_root, "testing", "fixtures", "benchmark")


@pytest.fixture
def orchestrator() -> DiagnosticOrchestrator:
    return DiagnosticOrchestrator()


def test_java_benchmark_scenarios_registered():
    """Verify all 22 Java scenarios (CASE-039 to CASE-060) are properly registered."""
    scenarios = get_benchmark_scenarios()
    manifest = get_ground_truth_manifest()

    java_scenario_ids = [f"CASE-{i:03d}" for i in range(39, 61)]
    assert len(java_scenario_ids) == 22

    scenario_map = {s.scenario_id: s for s in scenarios}
    for sc_id in java_scenario_ids:
        assert sc_id in scenario_map, f"Scenario {sc_id} not found in benchmark scenarios"
        assert sc_id in manifest.entries, f"Scenario {sc_id} not found in ground truth manifest"

        sc = scenario_map[sc_id]
        assert sc.is_supported_statically is True
        assert sc.safety_classification == "safe_static_only"
        assert not hasattr(sc, "taxonomy_category")
        assert not hasattr(sc, "expected_diagnostic_outcome")


def test_java_healthy_controls(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify healthy Java controls produce 0 false-positive fault hypotheses."""
    healthy_cases = [
        ("CASE-039", "proj_39"),  # Multi-package
        ("CASE-040", "proj_40"),  # Interfaces & generics
        ("CASE-041", "proj_41"),  # Nested classes
        ("CASE-042", "proj_42"),  # Records
        ("CASE-043", "proj_43"),  # Valid cross-package import
        ("CASE-048", "proj_48"),  # Static import
        ("CASE-049", "proj_49"),  # Wildcard import
        ("CASE-050", "proj_50"),  # Stdlib imports
        ("CASE-051", "proj_51"),  # Declared Maven dependency
        ("CASE-053", "proj_53"),  # Maven unresolved version property
        ("CASE-054", "proj_54"),  # Declared Gradle dependency
        ("CASE-055", "proj_55"),  # Gradle computed dependency
        ("CASE-056", "proj_56"),  # Multi-module Maven
        ("CASE-057", "proj_57"),  # Circular dependencies
        ("CASE-058", "proj_58"),  # Mixed polyglot
        ("CASE-059", "proj_59"),  # Malformed manifest
    ]

    for sc_id, fixture in healthy_cases:
        fixture_path = os.path.join(fixtures_dir, fixture)
        repo = Repository(
            id=uuid.uuid4(),
            name=sc_id,
            url=f"file:///{fixture_path.replace(os.sep, '/')}",
            source_type=SourceType.LOCAL_DIRECTORY,
        )
        report = orchestrator.execute_diagnosis(
            repository=repo,
            request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
        )
        assert len(report.hypotheses) == 0, (
            f"Expected zero fault hypotheses for healthy control {sc_id} ({fixture}), "
            f"but found: {[h.category.value for h in report.hypotheses]}"
        )


def test_java_unresolved_internal_reference(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """CASE-044: Verify unresolved internal type reference is accurately diagnosed."""
    fixture_path = os.path.join(fixtures_dir, "proj_44")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-044",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) >= 1
    top1 = report.hypotheses[0]
    assert top1.category == FaultCategory.DEPENDENCY_IMPORT_FAILURE
    assert "UserService.java" in top1.affected_component


def test_java_multi_fault_separation(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """CASE-045 & CASE-046: Verify multiple independent faults are separated into distinct hypotheses."""
    # CASE-045: Two independent unresolved type references
    p45_path = os.path.join(fixtures_dir, "proj_45")
    repo45 = Repository(
        id=uuid.uuid4(),
        name="PRJ-045",
        url=f"file:///{p45_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report45 = orchestrator.execute_diagnosis(
        repository=repo45,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )
    verified_comps_45 = {
        h.affected_component
        for h in report45.hypotheses
        if h.category == FaultCategory.DEPENDENCY_IMPORT_FAILURE
    }
    assert len(verified_comps_45) >= 2, f"Expected at least 2 distinct affected components in CASE-045, got {verified_comps_45}"

    # CASE-046: Two independent syntax errors
    p46_path = os.path.join(fixtures_dir, "proj_46")
    repo46 = Repository(
        id=uuid.uuid4(),
        name="PRJ-046",
        url=f"file:///{p46_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report46 = orchestrator.execute_diagnosis(
        repository=repo46,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )
    verified_comps_46 = {
        h.affected_component
        for h in report46.hypotheses
        if h.category == FaultCategory.RUNTIME_EXCEPTION
    }
    assert len(verified_comps_46) >= 2, f"Expected at least 2 distinct affected components in CASE-046, got {verified_comps_46}"


def test_java_syntax_and_unresolved_combination(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """CASE-047: Verify syntax error and unresolved import coexist without masking."""
    fixture_path = os.path.join(fixtures_dir, "proj_47")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-047",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    categories = {h.category for h in report.hypotheses}
    assert FaultCategory.RUNTIME_EXCEPTION in categories
    assert FaultCategory.DEPENDENCY_IMPORT_FAILURE in categories


def test_java_undeclared_maven_dependency(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """CASE-052: Verify undeclared Maven external dependency is flagged as import failure."""
    fixture_path = os.path.join(fixtures_dir, "proj_52")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-052",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) >= 1
    top1 = report.hypotheses[0]
    assert top1.category == FaultCategory.DEPENDENCY_IMPORT_FAILURE
    assert any("org.slf4j" in e.observed_data.get("package", "") for e in report.evidence if e.evidence_type == "undeclared_external_dependency")


def test_java_multi_module_maven_resolution(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """CASE-056: Verify multi-module Maven project resolves cross-module type cleanly."""
    fixture_path = os.path.join(fixtures_dir, "proj_56")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-056",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) == 0
    assert report.system_map.unresolved_dependency_count == 0
    assert any("CoreService" in c.name for c in report.system_map.components)
    assert any("ApiController" in c.name for c in report.system_map.components)


def test_polyglot_repository_unified_mapping(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """CASE-058: Verify mixed Java + Python + TypeScript repo is parsed without collisions."""
    fixture_path = os.path.join(fixtures_dir, "proj_58")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-058",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) == 0
    comp_names = {c.name for c in report.system_map.components}
    assert "Main.java" in comp_names
    assert "main.py" in comp_names
    assert "index.ts" in comp_names


def test_java_empty_codebase_abstention(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """CASE-060: Verify empty Java project triggers deliberate abstention."""
    fixture_path = os.path.join(fixtures_dir, "proj_60")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-060",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) == 1
    assert report.hypotheses[0].category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE
    assert report.stopping_reason == "deliberate_abstention"
