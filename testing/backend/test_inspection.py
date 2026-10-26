"""Comprehensive tests for repository snapshot ingestion, AST parsing, ecosystem detection, and security policies."""

import os
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient

from oracle.inspection.ast_parser import parse_python_file
from oracle.inspection.detector import detect_ecosystems
from oracle.inspection.graph import build_dependency_graph
from oracle.inspection.policy import (
    PathTraversalError,
    ResourceLimiter,
    ResourceLimitExceededError,
    SnapshotTimeoutError,
    is_binary_file,
    is_excluded_directory,
    redact_secrets,
)
from oracle.inspection.service import inspection_service
from oracle.inspection.snapshot import (
    ingest_git_repository,
    ingest_local_directory,
)
from oracle.models.repository import Repository, SourceType


# ---------------------------------------------------------------------------
# 1. Supported and Unsupported Repository URL Schemes
# ---------------------------------------------------------------------------

def test_git_url_scheme_validation() -> None:
    """Verify that supported Git schemes pass initial checks and unsupported schemes are rejected."""
    # Unsupported scheme (ftp, gopher)
    with pytest.raises(Exception) as excinfo:
        ingest_git_repository("ftp://example.com/repo.git")
    assert "Unsupported repository scheme" in str(excinfo.value)

    # Empty URL
    with pytest.raises(Exception) as excinfo:
        ingest_git_repository("")
    assert "cannot be empty" in str(excinfo.value)

    # Embedded credentials in URL rejected for security
    with pytest.raises(Exception) as excinfo:
        ingest_git_repository("https://admin:super_secret_password@github.com/org/repo.git")
    assert "embedded user credentials" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 2. Local Path Containment and Traversal Attempts
# ---------------------------------------------------------------------------

def test_local_path_containment_and_traversal(tmp_path) -> None:
    """Verify that local repositories are strictly confined within permitted roots."""
    permitted_root = tmp_path / "permitted_area"
    permitted_root.mkdir()

    repo_dir = permitted_root / "my_project"
    repo_dir.mkdir()

    outside_dir = tmp_path / "forbidden_outside"
    outside_dir.mkdir()

    # 1. Valid directory within permitted root
    ctx = ingest_local_directory(str(repo_dir), permitted_roots=[str(permitted_root)])
    assert ctx.root_path == os.path.abspath(os.path.realpath(str(repo_dir)))
    assert ctx.source_type == "local_directory"

    # 2. Traversal attempt using ../
    traversal_target = str(repo_dir / ".." / ".." / "forbidden_outside")
    with pytest.raises(PathTraversalError):
        ingest_local_directory(traversal_target, permitted_roots=[str(permitted_root)])

    # 3. Direct outside path
    with pytest.raises(PathTraversalError):
        ingest_local_directory(str(outside_dir), permitted_roots=[str(permitted_root)])

    # 4. Non-existent path raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        ingest_local_directory(str(permitted_root / "does_not_exist"), permitted_roots=[str(permitted_root)])


def test_symlink_escape_attempt(tmp_path) -> None:
    """Verify that symlinks pointing outside permitted roots are caught and rejected."""
    permitted_root = tmp_path / "permitted"
    permitted_root.mkdir()
    secret_dir = tmp_path / "secret_outside"
    secret_dir.mkdir()

    symlink_target = permitted_root / "escape_link"
    try:
        os.symlink(str(secret_dir), str(symlink_target), target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation requires elevated privileges on this Windows environment.")

    with pytest.raises(PathTraversalError):
        ingest_local_directory(str(symlink_target), permitted_roots=[str(permitted_root)])


# ---------------------------------------------------------------------------
# 3. File Count, File Size, and Timeout Limits
# ---------------------------------------------------------------------------

def test_resource_limits_enforcement() -> None:
    """Verify that ResourceLimiter halts execution when bounds are exceeded."""
    limiter = ResourceLimiter(
        max_file_count=2,
        max_file_size_bytes=100,
        max_total_bytes=150,
        timeout_seconds=5.0,
    )

    # First file within bounds
    assert limiter.register_file("file1.py", size_bytes=60) is True
    # Second file within bounds
    assert limiter.register_file("file2.py", size_bytes=60) is True

    # Third file exceeds max_file_count (2)
    with pytest.raises(ResourceLimitExceededError) as excinfo:
        limiter.register_file("file3.py", size_bytes=10)
    assert "maximum file count" in str(excinfo.value)

    # Individual file size checker
    assert limiter.is_file_size_permitted(50) is True
    assert limiter.is_file_size_permitted(150) is False


def test_resource_limiter_timeout() -> None:
    """Verify that expired timeout triggers SnapshotTimeoutError."""
    limiter = ResourceLimiter(
        max_file_count=100,
        max_file_size_bytes=1000,
        max_total_bytes=5000,
        timeout_seconds=0.001,
    )
    import time
    time.sleep(0.01)

    with pytest.raises(SnapshotTimeoutError):
        limiter.check_timeout()


# ---------------------------------------------------------------------------
# 4. Excluded Directories and Binary Files
# ---------------------------------------------------------------------------

def test_excluded_directories_and_binary_detection() -> None:
    """Verify that hidden, cache, and virtual environment directories are excluded."""
    assert is_excluded_directory(".git") is True
    assert is_excluded_directory("node_modules") is True
    assert is_excluded_directory(".venv") is True
    assert is_excluded_directory("venv") is True
    assert is_excluded_directory("__pycache__") is True
    assert is_excluded_directory(".pytest_cache") is True
    assert is_excluded_directory("src") is False
    assert is_excluded_directory("backend") is False

    assert is_binary_file("module.pyc") is True
    assert is_binary_file("lib.so") is True
    assert is_binary_file("app.exe") is True
    assert is_binary_file("logo.png") is True
    assert is_binary_file("main.py") is False
    assert is_binary_file("package.json") is False


# ---------------------------------------------------------------------------
# 5. Python Import Extraction Without Code Execution
# ---------------------------------------------------------------------------

def test_python_import_extraction_without_execution() -> None:
    """Verify that Python files are parsed using AST without executing executable code."""
    # This source code contains a bomb if executed: raise SystemExit
    dangerous_code = """
import os
import sys
import math as m
from typing import Dict, List
from oracle.core.config import settings
from .models import Repository
from .missing_submodule import non_existent_thing

# If this code were executed, the process would abort immediately!
if True:
    raise SystemExit("Target code was executed! Security boundary violated!")
"""
    known_py_files = {"app/main.py", "app/models.py"}
    summary = parse_python_file(
        rel_path="app/main.py",
        source_code=dangerous_code,
        all_known_py_files=known_py_files,
    )

    assert summary.status == "analyzed"
    assert summary.line_count > 5
    assert summary.syntax_error is None

    extracted_targets = {imp.target_module for imp in summary.imports}
    assert "os" in extracted_targets
    assert "sys" in extracted_targets
    assert "math" in extracted_targets
    assert "typing" in extracted_targets
    assert "oracle.core.config" in extracted_targets
    assert "app.models" in extracted_targets

    # Check resolution statuses
    stdlib_imports = [imp for imp in summary.imports if imp.is_stdlib]
    assert any(imp.target_module == "os" for imp in stdlib_imports)
    assert any(imp.target_module == "sys" for imp in stdlib_imports)

    internal_imports = [imp for imp in summary.imports if imp.is_internal]
    assert any(imp.target_module == "app.models" for imp in internal_imports)

    unresolved_imports = [imp for imp in summary.imports if imp.resolution_status == "unresolved_reference"]
    assert any("missing_submodule" in imp.target_module for imp in unresolved_imports)


def test_syntax_error_handling_preserves_scan() -> None:
    """Verify that a Python syntax error is captured cleanly without crashing the scan."""
    broken_code = """
def broken_function(
    # Missing closing parenthesis and colon!
    x = 1
"""
    summary = parse_python_file("broken.py", broken_code, all_known_py_files=set())
    assert summary.status == "syntax_error"
    assert summary.syntax_error is not None
    assert summary.syntax_error.file_path == "broken.py"
    assert summary.syntax_error.line_number is not None


# ---------------------------------------------------------------------------
# 6. Dependency Graph Construction & Provenance Tracking
# ---------------------------------------------------------------------------

def test_dependency_graph_provenance_and_unresolved_nodes() -> None:
    """Verify that dependency graph edges preserve line numbers, raw statements, and unresolved states."""
    code_a = """
import os
from .service import process_data
"""
    code_b = """
from .unresolved_lib import something
"""
    known = {"pkg/a.py", "pkg/service.py", "pkg/b.py"}
    sum_a = parse_python_file("pkg/a.py", code_a, known)
    sum_b = parse_python_file("pkg/b.py", code_b, known)

    graph = build_dependency_graph([sum_a, sum_b])

    assert graph.total_nodes > 0
    assert graph.total_edges == 3
    assert graph.stdlib_edge_count == 1  # os
    assert graph.internal_edge_count == 1  # pkg.service
    assert graph.unresolved_edge_count == 1  # unresolved_lib

    # Check edge provenance
    unresolved_edge = [e for e in graph.edges if e.dependency_type == "unresolved"][0]
    assert unresolved_edge.source_node == "file:pkg/b.py"
    assert "unresolved_lib" in unresolved_edge.target_node
    assert unresolved_edge.line_number == 2
    assert unresolved_edge.is_resolved is False


# ---------------------------------------------------------------------------
# 7. Mixed-Language Ecosystem Detection
# ---------------------------------------------------------------------------

def test_mixed_language_ecosystem_detection() -> None:
    """Verify deterministic ecosystem detection identifies multiple ecosystems in polyglot repos."""
    polyglot_files = [
        "pyproject.toml",
        "backend/main.py",
        "package.json",
        "frontend/src/app/page.tsx",
        "pom.xml",
        "src/main/java/App.java",
        "CMakeLists.txt",
        "native/core.cpp",
        "README.md",
    ]

    ecosystems = detect_ecosystems(polyglot_files)
    detected_names = {e.name for e in ecosystems}

    assert "python" in detected_names
    assert "javascript_typescript" in detected_names
    assert "java_jvm" in detected_names
    assert "c_cpp" in detected_names

    py_eco = next(e for e in ecosystems if e.name == "python")
    assert py_eco.confidence == "high"
    assert "pyproject.toml" in py_eco.manifest_files


# ---------------------------------------------------------------------------
# 8. Secret Redaction
# ---------------------------------------------------------------------------

def test_secret_redaction() -> None:
    """Verify that credentials, tokens, and URLs are masked."""
    text = "Failed connecting to https://admin:my_secret_password_123@db.example.com/db with token ghp_1234567890abcdef1234567890abcdef and password='passWord123!'"
    redacted = redact_secrets(text)

    assert "my_secret_password_123" not in redacted
    assert "[REDACTED]:[REDACTED]" in redacted
    assert "ghp_1234567890abcdef" not in redacted
    assert "passWord123!" not in redacted


# ---------------------------------------------------------------------------
# 9. Inspection Service End-to-End on Local Directory
# ---------------------------------------------------------------------------

def test_inspection_service_local_run(tmp_path) -> None:
    """Verify that InspectionService inspects a controlled local directory without executing code."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Create Python source and manifest
    (repo_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (repo_dir / "main.py").write_text("import os\nfrom .util import helper\n", encoding="utf-8")
    (repo_dir / "util.py").write_text("def helper(): pass\n", encoding="utf-8")
    (repo_dir / "broken.py").write_text("def bad(\n", encoding="utf-8")

    repo_model = Repository(
        id=uuid.uuid4(),
        name="test-repo",
        url=str(repo_dir),
        source_type=SourceType.LOCAL_DIRECTORY.value,
    )

    report = inspection_service.inspect_repository(repo_model)

    assert report.repository_id == repo_model.id
    assert report.status == "partial"  # Partial because broken.py has a syntax error
    assert report.source_type == "local_directory"
    assert len(report.ecosystems) >= 1
    assert report.ecosystems[0].name == "python"
    assert report.total_files_discovered >= 4
    assert len(report.syntax_errors) == 1
    assert report.syntax_errors[0].file_path == "broken.py"
    assert report.dependency_graph.internal_edge_count >= 1

    # Verify report is cached
    cached = inspection_service.get_latest_report(repo_model.id)
    assert cached is not None
    assert cached.repository_id == repo_model.id


# ---------------------------------------------------------------------------
# 10. Inspection REST API Endpoints
# ---------------------------------------------------------------------------

class FakeSession:
    """In-memory session mock simulating SQLAlchemy session for offline unit tests."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, Repository] = {}

    def add(self, instance: Repository) -> None:
        if not instance.id:
            instance.id = uuid.uuid4()
        self.items[instance.id] = instance

    def commit(self) -> None:
        pass

    def refresh(self, instance: Repository) -> None:
        pass

    def get(self, model: type, ident: uuid.UUID) -> Repository | None:
        return self.items.get(ident)


@pytest.fixture
def mock_db() -> FakeSession:
    """Provide a fresh in-memory session mock for route testing."""
    from oracle.db.session import get_db
    from oracle.main import app

    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.pop(get_db, None)


def test_inspect_api_repository_not_found(client: TestClient, mock_db: FakeSession) -> None:
    """Verify POST /api/v1/repositories/{id}/inspect returns 404 for unknown repository."""
    non_existent_id = uuid.uuid4()
    res = client.post(f"/api/v1/repositories/{non_existent_id}/inspect")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_inspection_prior_to_inspect_returns_404(client: TestClient, mock_db: FakeSession) -> None:
    """Verify GET /api/v1/repositories/{id}/inspection returns 404 if not yet inspected."""
    # Register repository in mock DB
    repo = Repository(
        id=uuid.uuid4(),
        name="uninspected-repo",
        url="https://github.com/org/repo.git",
        source_type="git",
    )
    mock_db.add(repo)

    res = client.get(f"/api/v1/repositories/{repo.id}/inspection")
    assert res.status_code == 404
    assert "no inspection report found" in res.json()["detail"].lower()


def test_inspect_api_local_directory_success(client: TestClient, mock_db: FakeSession, tmp_path) -> None:
    """Verify POST /api/v1/repositories/{id}/inspect runs and returns InspectionReport."""
    repo_dir = tmp_path / "api_test_project"
    repo_dir.mkdir()
    (repo_dir / "requirements.txt").write_text("fastapi>=0.100.0\n", encoding="utf-8")
    (repo_dir / "app.py").write_text("import sys\n", encoding="utf-8")

    clean_dir = str(repo_dir).replace("\\", "/")
    repo_url = f"file:///{clean_dir}" if not clean_dir.startswith("/") else f"file://{clean_dir}"

    repo = Repository(
        id=uuid.uuid4(),
        name="api-local-target",
        url=repo_url,
        source_type="local_directory",
    )
    mock_db.add(repo)

    # Trigger inspection
    inspect_res = client.post(f"/api/v1/repositories/{repo.id}/inspect")
    assert inspect_res.status_code == 200
    report = inspect_res.json()

    assert report["repository_id"] == str(repo.id)
    assert report["status"] == "completed"
    assert report["source_type"] == "local_directory"
    assert len(report["ecosystems"]) >= 1
    assert report["ecosystems"][0]["name"] == "python"
    assert report["total_files_analyzed"] >= 1
    assert len(report["syntax_errors"]) == 0
    assert report["dependency_graph"]["stdlib_edge_count"] >= 1

    # Query latest inspection
    get_res = client.get(f"/api/v1/repositories/{repo.id}/inspection")
    assert get_res.status_code == 200
    assert get_res.json()["repository_id"] == str(repo.id)
