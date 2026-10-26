"""Automated benchmark tests for TypeScript and JavaScript static analysis scenarios (CASE-021 to CASE-038)."""

import os
import uuid
import pytest

from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.models.repository import Repository
from oracle.schemas.diagnostics import DiagnosticRunRequest
from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.taxonomy.fault_taxonomy import FaultCategory


@pytest.fixture
def orchestrator() -> DiagnosticOrchestrator:
    return DiagnosticOrchestrator()


@pytest.fixture
def fixtures_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "benchmark"))


def test_ts_healthy_controls_zero_false_positives(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify that all healthy TypeScript / JSX / Next.js controls generate ZERO false-positive fault hypotheses."""
    healthy_cases = [
        ("CASE-021", "proj_21"),  # Standard TS math module
        ("CASE-022", "proj_22"),  # React JSX/TSX components
        ("CASE-023", "proj_23"),  # Misleading comments
        ("CASE-024", "proj_24"),  # Import-like strings/templates
        ("CASE-026", "proj_26"),  # Directory index import
        ("CASE-027", "proj_27"),  # tsconfig path alias @/*
        ("CASE-028", "proj_28"),  # Re-export barrel file chain
        ("CASE-029", "proj_29"),  # Circular imports
        ("CASE-030", "proj_30"),  # Declared external package
        ("CASE-032", "proj_32"),  # Computed dynamic import
        ("CASE-036", "proj_36"),  # Mixed Python + TypeScript
        ("CASE-037", "proj_37"),  # Escaping root containment limitation
        ("CASE-038", "proj_38"),  # Next.js App Router layout
    ]

    for case_id, fixture_name in healthy_cases:
        proj_path = os.path.join(fixtures_dir, fixture_name)
        repo = Repository(
            id=uuid.uuid4(),
            name=f"Benchmark {case_id}",
            url=f"file:///{proj_path.replace(os.sep, '/')}",
            source_type="local_directory",
            status="registered",
        )
        report = orchestrator.execute_diagnosis(
            repository=repo,
            request=DiagnosticRunRequest(allow_dynamic=False, max_iterations=2),
        )

        assert report.status == "completed", f"{case_id} failed with status {report.status}: {report.error_message}"
        # A clean project must generate 0 hypotheses
        assert len(report.hypotheses) == 0, (
            f"{case_id} generated unexpected hypotheses: {[h.category_title for h in report.hypotheses]}"
        )


def test_ts_missing_relative_import_detection(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify CASE-025 detects missing relative import with Top-1 supported accuracy."""
    proj_path = os.path.join(fixtures_dir, "proj_25")
    repo = Repository(
        id=uuid.uuid4(),
        name="Benchmark CASE-025",
        url=f"file:///{proj_path.replace(os.sep, '/')}",
        source_type="local_directory",
        status="registered",
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(allow_dynamic=False, max_iterations=3),
    )

    assert len(report.hypotheses) > 0, "CASE-025 should formulate at least one hypothesis"
    top_hypo = report.hypotheses[0]
    assert top_hypo.category == FaultCategory.DEPENDENCY_IMPORT_FAILURE
    assert "missing_transport" in top_hypo.remediation_suggestion or "client.ts" in top_hypo.affected_component


def test_ts_undeclared_external_dependency_detection(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify CASE-031 detects undeclared package axios in package.json."""
    proj_path = os.path.join(fixtures_dir, "proj_31")
    repo = Repository(
        id=uuid.uuid4(),
        name="Benchmark CASE-031",
        url=f"file:///{proj_path.replace(os.sep, '/')}",
        source_type="local_directory",
        status="registered",
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(allow_dynamic=False, max_iterations=3),
    )

    assert len(report.hypotheses) > 0, "CASE-031 should formulate an undeclared dependency hypothesis"
    top_hypo = report.hypotheses[0]
    assert top_hypo.category == FaultCategory.DEPENDENCY_IMPORT_FAILURE
    assert "axios" in top_hypo.affected_component.lower()


def test_ts_syntax_error_detection_and_verification(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify CASE-033 detects syntax error in calculator.ts and confirms it via static probe."""
    proj_path = os.path.join(fixtures_dir, "proj_33")
    repo = Repository(
        id=uuid.uuid4(),
        name="Benchmark CASE-033",
        url=f"file:///{proj_path.replace(os.sep, '/')}",
        source_type="local_directory",
        status="registered",
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(allow_dynamic=False, max_iterations=3),
    )

    assert len(report.hypotheses) > 0, "CASE-033 should formulate a syntax error hypothesis"
    top_hypo = report.hypotheses[0]
    assert top_hypo.category == FaultCategory.RUNTIME_EXCEPTION
    assert "calculator.ts" in top_hypo.affected_component
    assert top_hypo.verification_status == "verified"


def test_ts_multiple_independent_syntax_errors(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify CASE-034 separates two independent syntax errors in parser.ts and formatter.ts."""
    proj_path = os.path.join(fixtures_dir, "proj_34")
    repo = Repository(
        id=uuid.uuid4(),
        name="Benchmark CASE-034",
        url=f"file:///{proj_path.replace(os.sep, '/')}",
        source_type="local_directory",
        status="registered",
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(allow_dynamic=False, max_iterations=3),
    )

    syntax_hypos = [
        h for h in report.hypotheses
        if h.category == FaultCategory.RUNTIME_EXCEPTION and any(
            "syntax" in eid.lower() for eid in h.supporting_evidence_ids
        )
    ]
    assert len(syntax_hypos) == 2, f"Should formulate 2 independent syntax hypotheses, got {len(syntax_hypos)}"
    affected_comps = {h.affected_component for h in syntax_hypos}
    assert any("parser.ts" in c for c in affected_comps)
    assert any("formatter.ts" in c for c in affected_comps)


def test_ts_mixed_syntax_and_import_faults(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify CASE-035 detects both syntax error in parser.ts and unresolved import in client.ts."""
    proj_path = os.path.join(fixtures_dir, "proj_35")
    repo = Repository(
        id=uuid.uuid4(),
        name="Benchmark CASE-035",
        url=f"file:///{proj_path.replace(os.sep, '/')}",
        source_type="local_directory",
        status="registered",
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(allow_dynamic=False, max_iterations=3),
    )

    categories = {h.category for h in report.hypotheses}
    assert FaultCategory.RUNTIME_EXCEPTION in categories
    assert FaultCategory.DEPENDENCY_IMPORT_FAILURE in categories


def test_mixed_python_and_typescript_unified_graph(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify CASE-036 constructs a unified system map spanning Python backend and TypeScript client."""
    proj_path = os.path.join(fixtures_dir, "proj_36")
    repo = Repository(
        id=uuid.uuid4(),
        name="Benchmark CASE-036",
        url=f"file:///{proj_path.replace(os.sep, '/')}",
        source_type="local_directory",
        status="registered",
    )
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(allow_dynamic=False, max_iterations=2),
    )

    assert report.system_map is not None
    comp_paths = [c.file_path for c in report.system_map.components if c.file_path]
    assert any("server.py" in p for p in comp_paths)
    assert any("client.ts" in p for p in comp_paths)
    assert len(report.hypotheses) == 0, "Healthy mixed repo should produce zero false positives"
