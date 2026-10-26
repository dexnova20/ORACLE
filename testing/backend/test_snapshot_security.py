"""Security, path traversal, resource limits, and parser resilience tests for ORACLE.

Verifies:
1. Rejection of directory traversal and outside path escapes.
2. Resource quota limits (max files and max bytes enforcement).
3. Subprocess isolation timeout and recovery in TypeScript AST worker.
4. Subprocess malformed output recovery in TypeScript AST worker.
5. Subprocess isolation timeout and recovery in Java AST worker.
6. Subprocess malformed output recovery in Java AST worker.
7. Multi-pattern credential and token redaction.
"""

import json
import os
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from oracle.inspection.java_parser import parse_java_files_batch
from oracle.inspection.policy import (
    PathTraversalError,
    ResourceLimiter,
    ResourceLimitExceededError,
    redact_secrets,
)
from oracle.inspection.snapshot import ingest_local_directory
from oracle.inspection.ts_parser import parse_ts_files_batch


def test_path_traversal_rejection_outside_permitted_roots(tmp_path) -> None:
    """Verify that ingest_local_directory rejects path traversal attempts."""
    permitted_root = tmp_path / "permitted"
    permitted_root.mkdir()
    inside_dir = permitted_root / "repo"
    inside_dir.mkdir()
    outside_dir = tmp_path / "secret_system_dir"
    outside_dir.mkdir()

    # Traversal attempt via ..
    traversal_path = str(inside_dir / ".." / ".." / "secret_system_dir")
    with pytest.raises(PathTraversalError):
        ingest_local_directory(traversal_path, permitted_roots=[str(permitted_root)])


def test_resource_limiter_file_count_quota() -> None:
    """Verify that ResourceLimiter raises ResourceLimitExceededError when max_file_count is exceeded."""
    limiter = ResourceLimiter(
        max_file_count=3,
        max_file_size_bytes=10_000,
        max_total_bytes=100_000,
        timeout_seconds=30.0,
    )
    limiter.register_file("f1.py", 100)
    limiter.register_file("f2.py", 100)
    limiter.register_file("f3.py", 100)
    assert limiter.scanned_file_count == 3

    with pytest.raises(ResourceLimitExceededError) as excinfo:
        limiter.register_file("f4.py", 100)
    assert "maximum file count limit" in str(excinfo.value)


def test_resource_limiter_byte_quota() -> None:
    """Verify that ResourceLimiter raises ResourceLimitExceededError when max_total_bytes is exceeded."""
    limiter = ResourceLimiter(
        max_file_count=10,
        max_file_size_bytes=10_000,
        max_total_bytes=500,
        timeout_seconds=30.0,
    )
    limiter.register_file("f1.py", 200)
    limiter.register_file("f2.py", 200)
    assert limiter.scanned_total_bytes == 400

    with pytest.raises(ResourceLimitExceededError) as excinfo:
        limiter.register_file("f3.py", 200)
    assert "maximum aggregate size limit" in str(excinfo.value)


def test_ts_parser_subprocess_timeout_recovery(tmp_path) -> None:
    """Verify that TypeScript AST parser recovers gracefully when worker subprocess times out."""
    ts_file = tmp_path / "test.ts"
    ts_file.write_text("export const answer: number = 42;", encoding="utf-8")

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["node"], timeout=30.0)):
        summaries = parse_ts_files_batch([{"path": "test.ts"}], {"test.ts"}, root_dir=str(tmp_path))
        assert len(summaries) == 1
        assert summaries[0].status == "analysis_failed"
        assert summaries[0].syntax_error is not None
        assert "timed out" in summaries[0].syntax_error.error_message.lower()


def test_ts_parser_malformed_worker_json_recovery(tmp_path) -> None:
    """Verify that TypeScript AST parser recovers gracefully when worker returns malformed JSON."""
    ts_file = tmp_path / "app.ts"
    ts_file.write_text("console.log('hello');", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "FATAL: Out of memory or corrupted garbage output <<not json>>"

    with patch("oracle.inspection.ts_parser.check_ts_parser_available", return_value=(True, None)):
        with patch("subprocess.run", return_value=mock_proc):
            summaries = parse_ts_files_batch([{"path": "app.ts"}], {"app.ts"}, root_dir=str(tmp_path))
            assert len(summaries) == 1
            assert summaries[0].status == "analysis_failed"
            assert summaries[0].syntax_error is not None
            assert "Parser execution failed" in summaries[0].syntax_error.error_message


def test_java_parser_subprocess_timeout_recovery(tmp_path) -> None:
    """Verify that Java AST parser recovers gracefully when worker subprocess times out."""
    java_file = tmp_path / "App.java"
    java_file.write_text("public class App { public static void main(String[] args) {} }", encoding="utf-8")

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["java"], timeout=30.0)):
        summaries = parse_java_files_batch([{"path": "App.java"}], {"App.java"}, root_dir=str(tmp_path))
        assert len(summaries) == 1
        assert summaries[0].status in ("skipped_by_policy", "analysis_failed")
        assert summaries[0].syntax_error is not None
        assert "timed out" in summaries[0].syntax_error.error_message.lower()


def test_java_parser_malformed_worker_json_recovery(tmp_path) -> None:
    """Verify that Java AST parser recovers gracefully when worker returns malformed JSON."""
    java_file = tmp_path / "Service.java"
    java_file.write_text("public class Service {}", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "OpenJDK 64-Bit Server VM warning: Sharing is only supported for boot loader classes... not json"

    with patch("oracle.inspection.java_parser.check_java_parser_available", return_value=(True, None)):
        with patch("subprocess.run", return_value=mock_proc):
            summaries = parse_java_files_batch([{"path": "Service.java"}], {"Service.java"}, root_dir=str(tmp_path))
            assert len(summaries) == 1
            assert summaries[0].status == "analysis_failed"
            assert summaries[0].syntax_error is not None
            assert "Java parser invocation error" in summaries[0].syntax_error.error_message


def test_secret_redaction_exhaustive_patterns() -> None:
    """Verify that credential patterns are redacted cleanly without leaking sensitive tokens."""
    sensitive_samples = [
        ("https://user:my_secret_token_12345@github.com/org/repo.git", "[REDACTED]"),
        ("postgresql://dbadmin:my_super_secret_db_pass@db.prod.internal:5432/main", "[REDACTED]"),
        ("api_key = 'sk_live_1234567890abcdef123456'", "api_key=[REDACTED]"),
        ("password: 'super_secret_password_999'", "password=[REDACTED]"),
        ("ghp_1234567890abcdef1234567890abcdef12345678", "[REDACTED_GITHUB_TOKEN]"),
        ("glpat-abcdef123456789012345678", "[REDACTED_GITLAB_TOKEN]"),
        ("AKIAIOSFODNN7EXAMPLE", "[REDACTED_AWS_KEY]"),
    ]

    for raw, expected_token_in_clean in sensitive_samples:
        redacted = redact_secrets(raw)
        assert expected_token_in_clean in redacted
        assert "my_secret_token_12345" not in redacted
        assert "my_super_secret_db_pass" not in redacted
        assert "sk_live_1234567890abcdef123456" not in redacted
        assert "super_secret_password_999" not in redacted
