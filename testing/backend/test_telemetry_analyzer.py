"""Tests for runtime telemetry, polyglot traceback parsing, and non-static fault classification."""

import os
import tempfile
import uuid
import pytest

from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.diagnostics.telemetry_analyzer import (
    analyze_runtime_symptoms,
    audit_environment_configuration,
    classify_symptom_category,
    parse_runtime_traceback,
    telemetry_to_evidence,
)
from oracle.models.repository import Repository
from oracle.schemas.diagnostics import DiagnosticRunRequest


def test_parse_python_traceback():
    """Verify parsing of standard Python stack traces."""
    tb_text = """Traceback (most recent call last):
  File "app/main.py", line 42, in start_server
    app.run()
  File "app/core/server.py", line 105, in run
    connect_to_db()
  File "app/db/connection.py", line 28, in connect_to_db
    raise psycopg.OperationalError("connection to server at 'localhost', port 5432 failed: Connection refused")
psycopg.OperationalError: connection to server at 'localhost', port 5432 failed: Connection refused
"""
    parsed = parse_runtime_traceback(tb_text)
    assert parsed is not None
    assert parsed.exception_class == "OperationalError"
    assert "Connection refused" in parsed.error_message
    assert len(parsed.frames) == 3

    root = parsed.root_frame
    assert root is not None
    assert root.file_path == "app/db/connection.py"
    assert root.line_number == 28
    assert root.function_name == "connect_to_db"


def test_parse_nodejs_traceback():
    """Verify parsing of Node.js / TypeScript stack traces."""
    tb_text = """Error: connect ECONNREFUSED 127.0.0.1:8080
    at TCPConnectWrap.afterConnect [as oncomplete] (net.js:1146:16)
    at Object.sendRequest (src/client/api.ts:54:12)
"""
    parsed = parse_runtime_traceback(tb_text)
    assert parsed is not None
    assert parsed.exception_class == "Error"
    assert "ECONNREFUSED" in parsed.error_message
    assert len(parsed.frames) >= 1

    f = parsed.frames[-1]
    assert "src/client/api.ts" in f.file_path
    assert f.line_number == 54


def test_parse_java_traceback():
    """Verify parsing of Java exception stack traces."""
    tb_text = """java.lang.NullPointerException: Cannot invoke method on null object
    at com.example.service.OrderService.processOrder(OrderService.java:88)
    at com.example.controller.OrderController.handle(OrderController.java:34)
"""
    parsed = parse_runtime_traceback(tb_text)
    assert parsed is not None
    assert parsed.exception_class == "NullPointerException"
    assert len(parsed.frames) == 2
    assert parsed.frames[0].file_path == "OrderService.java"
    assert parsed.frames[0].line_number == 88


def test_parse_go_panic():
    """Verify parsing of Go runtime panic traces."""
    tb_text = """panic: runtime error: index out of range [5] with length 3
goroutine 1 [running]:
main.processItems(0xc0000a6000, 0x3, 0x3)
\t/home/user/app/main.go:45 +0x8a
main.main()
\t/home/user/app/main.go:12 +0x24
"""
    parsed = parse_runtime_traceback(tb_text)
    assert parsed is not None
    assert parsed.exception_class == "Panic"
    assert "index out of range" in parsed.error_message
    assert len(parsed.frames) == 2
    assert parsed.frames[0].line_number == 45


def test_classify_symptom_database():
    """Verify classification of database connectivity errors."""
    symptom = "psycopg.OperationalError: connection to server at port 5432 failed"
    cat, conf, _ = classify_symptom_category(symptom)
    assert cat == FaultCategory.DATABASE_CONNECTIVITY_SCHEMA
    assert conf >= 0.85


def test_classify_symptom_api_network():
    """Verify classification of API communication failure."""
    symptom = "httpx.ConnectTimeout: timed out while connecting to https://api.stripe.com/v1"
    cat, conf, _ = classify_symptom_category(symptom)
    assert cat == FaultCategory.API_COMMUNICATION_FAILURE
    assert conf >= 0.85


def test_classify_symptom_io_contract():
    """Verify classification of IO schema contract violation."""
    symptom = "pydantic.ValidationError: 1 validation error for RequestModel\nname\n  Field required [type=missing]"
    cat, conf, _ = classify_symptom_category(symptom)
    assert cat == FaultCategory.IO_CONTRACT_VIOLATION
    assert conf >= 0.85


def test_classify_symptom_data_transformation():
    """Verify classification of data transformation errors."""
    symptom = "json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)"
    cat, conf, _ = classify_symptom_category(symptom)
    assert cat == FaultCategory.DATA_VALIDATION_TRANSFORMATION
    assert conf >= 0.85


def test_classify_symptom_configuration():
    """Verify classification of configuration errors."""
    symptom = "KeyError: 'DATABASE_URL' missing mandatory environment variable"
    cat, conf, _ = classify_symptom_category(symptom)
    assert cat == FaultCategory.CONFIG_MISSING_OR_INVALID
    assert conf >= 0.85


def test_audit_environment_configuration(tmp_path):
    """Verify config audit identifies missing environment keys."""
    env_example = tmp_path / ".env.example"
    env_example.write_text("API_SECRET_KEY=replace_me\nPORT=8000\nDATABASE_URL=postgres://...\n", encoding="utf-8")

    env_actual = tmp_path / ".env"
    env_actual.write_text("PORT=8000\n", encoding="utf-8")

    findings = audit_environment_configuration(str(tmp_path))
    assert len(findings) == 1
    f = findings[0]
    assert f.category == FaultCategory.CONFIG_MISSING_OR_INVALID
    assert "API_SECRET_KEY" in f.observed_signals["missing_keys"]
    assert "DATABASE_URL" in f.observed_signals["missing_keys"]


def test_telemetry_to_evidence_conversion():
    """Verify telemetry findings correctly transform into DiagnosticEvidenceRecord."""
    findings = analyze_runtime_symptoms(
        symptom_text="ConnectionRefusedError: [Errno 111] Connection refused to port 5432",
        traceback_text=None,
    )
    assert len(findings) >= 1
    evidence = telemetry_to_evidence(findings, start_seq=5)
    assert len(evidence) == 1
    ev = evidence[0]
    assert ev.evidence_id == "EVID-TELEM-005"
    assert ev.evidence_type == "runtime_telemetry"
    assert ev.extraction_method == "telemetry_analyzer"
    assert ev.observed_data["fault_category"] == FaultCategory.DATABASE_CONNECTIVITY_SCHEMA.value


def test_orchestrator_integration_with_runtime_traceback(tmp_path):
    """Verify end-to-end diagnosis utilizes runtime traceback to identify database fault."""
    repo_dir = tmp_path / "app"
    repo_dir.mkdir()
    code_file = repo_dir / "service.py"
    code_file.write_text("def run():\n    pass\n", encoding="utf-8")

    repo = Repository(
        id=uuid.uuid4(),
        name="test-repo",
        source_type="local_directory",
        url=str(repo_dir),
    )

    tb = """Traceback (most recent call last):
  File "service.py", line 12, in connect
    raise psycopg.OperationalError("connection to server at 'localhost', port 5432 failed: Connection refused")
psycopg.OperationalError: connection to server at 'localhost', port 5432 failed: Connection refused
"""
    orchestrator = DiagnosticOrchestrator()
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(runtime_traceback=tb),
    )

    assert report.status == "completed"
    assert len(report.hypotheses) >= 1
    top_hypo = report.hypotheses[0]
    assert top_hypo.category == FaultCategory.DATABASE_CONNECTIVITY_SCHEMA
    assert any(e.evidence_type == "runtime_telemetry" for e in report.evidence)
