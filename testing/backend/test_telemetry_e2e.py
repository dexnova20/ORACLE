"""End-to-end integration tests for telemetry analysis, secret redaction, and diagnostic pipeline integration."""

import uuid
import pytest
from fastapi.testclient import TestClient

from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.diagnostics.telemetry_analyzer import parse_runtime_traceback, analyze_runtime_symptoms, telemetry_to_evidence
from oracle.main import app
from oracle.models.repository import Repository
from oracle.schemas.diagnostics import DiagnosticRunRequest
from ml.taxonomy.fault_taxonomy import FaultCategory


def test_telemetry_secret_redaction_in_traceback():
    """Verify that credentials and tokens embedded in tracebacks are strictly redacted."""
    sensitive_tb = """Traceback (most recent call last):
  File "app/database.py", line 45, in get_connection
    conn = psycopg.connect("postgresql://db_user:SuperSecretPassword123@db.prod.internal:5432/main_db?token=ghp_ABC1234567890abcdef1234567890abcdef")
psycopg.OperationalError: connection to server at "db.prod.internal" (10.0.0.5), port 5432 failed: password authentication failed for user "db_user"
"""
    tb = parse_runtime_traceback(sensitive_tb)
    assert tb is not None
    # Verify passwords and tokens do not exist in parsed structure
    assert "SuperSecretPassword123" not in tb.raw_text
    assert "ghp_ABC1234567890abcdef1234567890abcdef" not in tb.raw_text
    assert "[REDACTED]" in tb.raw_text

    findings = analyze_runtime_symptoms(traceback_text=sensitive_tb)
    evidence = telemetry_to_evidence(findings, start_seq=1, run_id="diag-abcdef123456")
    assert len(evidence) >= 1

    ev_str = str(evidence[0].model_dump())
    assert "SuperSecretPassword123" not in ev_str
    assert "ghp_ABC1234567890abcdef1234567890abcdef" not in ev_str


def test_telemetry_chained_traceback_python():
    """Verify parsing of chained Python exceptions with causal relationships."""
    chained_tb = """Traceback (most recent call last):
  File "data_loader.py", line 15, in load_raw
    raw = json.loads(payload)
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "service.py", line 88, in process_event
    raise DataValidationError("Corrupted event payload received")
DataValidationError: Corrupted event payload received
"""
    tb = parse_runtime_traceback(chained_tb)
    assert tb is not None
    assert tb.exception_class == "DataValidationError"
    assert len(tb.chained_causes) >= 2
    assert any("JSONDecodeError" in c for c in tb.chained_causes)


def test_telemetry_chained_traceback_java():
    """Verify parsing of nested Java exceptions with Caused by: clauses."""
    java_tb = """org.springframework.web.util.NestedServletException: Request processing failed
\tat org.springframework.web.servlet.FrameworkServlet.processRequest(FrameworkServlet.java:1014)
\tat com.example.controller.ApiController.handle(ApiController.java:42)
Caused by: com.example.service.DatabaseTimeoutException: Query execution timed out after 30000ms
\tat com.example.service.QueryService.execute(QueryService.java:99)
Caused by: org.postgresql.util.PSQLException: The connection attempt failed.
\tat org.postgresql.core.v3.ConnectionFactoryImpl.openConnectionImpl(ConnectionFactoryImpl.java:315)
"""
    tb = parse_runtime_traceback(java_tb)
    assert tb is not None
    # Innermost root cause
    assert tb.exception_class == "PSQLException"
    assert len(tb.chained_causes) == 2
    assert any("DatabaseTimeoutException" in c for c in tb.chained_causes)
    assert any("PSQLException" in c for c in tb.chained_causes)


def test_telemetry_unique_run_scoped_evidence_ids():
    """Verify that evidence IDs generated across runs are scoped to the specific run identifier."""
    findings = analyze_runtime_symptoms(
        symptom_text="Connection refused to port 5432",
        traceback_text="psycopg.OperationalError: Connection refused to port 5432",
    )

    ev_run_a = telemetry_to_evidence(findings, start_seq=1, run_id="diag-111122223333")
    ev_run_b = telemetry_to_evidence(findings, start_seq=1, run_id="diag-444455556666")

    assert len(ev_run_a) >= 1
    assert len(ev_run_b) >= 1
    assert ev_run_a[0].evidence_id != ev_run_b[0].evidence_id
    assert "11112222" in ev_run_a[0].evidence_id
    assert "44445555" in ev_run_b[0].evidence_id


def test_telemetry_end_to_end_orchestrator(tmp_path):
    """Verify full orchestrator execution incorporates telemetry findings and redacts secrets."""
    repo_dir = tmp_path / "telemetry_repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

    repo = Repository(
        id=uuid.uuid4(),
        name="telemetry-repo",
        source_type="local_directory",
        url=str(repo_dir),
    )

    req = DiagnosticRunRequest(
        symptom_description="Service failing with password auth error on postgresql://admin:leaked_pass_999@localhost:5432",
        runtime_traceback="psycopg.OperationalError: password authentication failed for user 'admin' using password='leaked_pass_999'",
    )

    orchestrator = DiagnosticOrchestrator()
    report = orchestrator.execute_diagnosis(repo, req)

    # 1. Assert diagnosis completed
    assert report.status == "completed"

    # 2. Assert telemetry evidence was created
    telem_ev = [e for e in report.evidence if e.evidence_type == "runtime_telemetry"]
    assert len(telem_ev) >= 1

    # 3. Assert secrets are redacted from serialized report
    dumped = report.model_dump_json()
    assert "leaked_pass_999" not in dumped
    assert "[REDACTED]" in dumped

    # 4. Assert top hypothesis targets database category
    assert len(report.hypotheses) >= 1
    top_hypo = report.hypotheses[0]
    assert top_hypo.category == FaultCategory.DATABASE_CONNECTIVITY_SCHEMA
