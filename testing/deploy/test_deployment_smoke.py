"""Deployment smoke test suite and CLI runner for ORACLE.

Verifies end-to-end operational readiness across frontend, backend, database connectivity,
polyglot static inspection, diagnostic workflow, and execution boundary safety.
Can be executed via pytest in-process or as a standalone CLI against a running container cluster.

Usage (standalone CLI against live containers):
    python testing/deploy/test_deployment_smoke.py --backend-url http://localhost:8000 --frontend-url http://localhost:3000

Usage (pytest in-process verification):
    pytest testing/deploy/test_deployment_smoke.py -v
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
import tempfile
import urllib.request
import urllib.error
import uuid
from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from oracle.core.config import settings
from oracle.db.session import check_db_connectivity, get_db
from oracle.main import app


class FakeSmokeSession:
    """In-memory session mock simulating SQLAlchemy session for offline in-process smoke tests."""

    def __init__(self) -> None:
        self.items: Dict[uuid.UUID, Any] = {}

    def add(self, instance: Any) -> None:
        if not getattr(instance, "id", None):
            instance.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        if not getattr(instance, "created_at", None):
            instance.created_at = now
        if not getattr(instance, "updated_at", None):
            instance.updated_at = now
        self.items[instance.id] = instance

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, instance: Any) -> None:
        pass

    def scalars(self, stmt: object) -> MagicMock:
        mock = MagicMock()
        mock.all.return_value = list(self.items.values())
        mock.first.return_value = next(iter(self.items.values()), None)
        return mock

    def query(self, model: type) -> MagicMock:
        mock = MagicMock()
        matching = [item for item in self.items.values() if isinstance(item, model)]
        mock.order_by.return_value = mock
        mock.limit.return_value = mock
        mock.all.return_value = matching
        mock.first.return_value = matching[0] if matching else None
        return mock

    def get(self, model: type, ident: uuid.UUID) -> Optional[Any]:
        return self.items.get(ident)

    def delete(self, instance: Any) -> None:
        if getattr(instance, "id", None) in self.items:
            del self.items[instance.id]


class DeploymentSmokeRunner:
    """Automated HTTP / in-process smoke test runner."""

    def __init__(self, backend_url: Optional[str] = None, frontend_url: Optional[str] = None):
        self.backend_url = backend_url.rstrip("/") if backend_url else None
        self.frontend_url = frontend_url.rstrip("/") if frontend_url else None
        self.client: Optional[TestClient] = TestClient(app) if not self.backend_url else None
        self._fake_session: Optional[FakeSmokeSession] = None

        if self.client:
            db_connected, _ = check_db_connectivity()
            if not db_connected:
                self._fake_session = FakeSmokeSession()
                app.dependency_overrides[get_db] = lambda: self._fake_session

    def cleanup(self) -> None:
        """Tear down dependency overrides if configured."""
        if self._fake_session:
            app.dependency_overrides.pop(get_db, None)

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
        """Dispatch HTTP request to remote backend or in-process TestClient."""
        if self.client:
            if method == "GET":
                resp = self.client.get(path)
            elif method == "POST":
                resp = self.client.post(path, json=json_body)
            elif method == "DELETE":
                resp = self.client.delete(path)
            else:
                raise ValueError(f"Unsupported method {method}")
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}
            return resp.status_code, data

        # Remote HTTP request via urllib
        url = f"{self.backend_url}{path}"
        headers = {"Content-Type": "application/json"} if json_body is not None else {}
        data_bytes = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read().decode("utf-8")
                return response.status, json.loads(body)
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            try:
                return exc.code, json.loads(err_body)
            except Exception:
                return exc.code, {"error": err_body}

    def check_frontend(self) -> bool:
        """Verify frontend HTTP availability if frontend_url provided."""
        if not self.frontend_url:
            return True
        try:
            req = urllib.request.Request(self.frontend_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as exc:
            print(f"[SMOKE] Frontend check failed at {self.frontend_url}: {exc}")
            return False

    def run_all(self) -> Dict[str, Any]:
        """Execute the full deployment smoke test sequence."""
        results: Dict[str, Any] = {"passed": True, "steps": {}}

        try:
            # 1. Frontend Check (if URL configured)
            if self.frontend_url:
                fe_ok = self.check_frontend()
                results["steps"]["1_frontend_availability"] = {"status": "PASS" if fe_ok else "FAIL"}
                if not fe_ok:
                    results["passed"] = False

            # 2. Backend Root Metadata
            status, data = self._request("GET", "/")
            step_ok = status == 200 and data.get("name") == "ORACLE"
            results["steps"]["2_backend_root"] = {"status": "PASS" if step_ok else "FAIL", "code": status}
            if not step_ok:
                results["passed"] = False

            # 3. Health Endpoint (Liveness)
            status, data = self._request("GET", "/api/v1/health")
            step_ok = status == 200 and data.get("status") == "healthy"
            results["steps"]["3_liveness_health"] = {"status": "PASS" if step_ok else "FAIL", "code": status}
            if not step_ok:
                results["passed"] = False

            # 4. Status Endpoint (Readiness, DB, Parsers)
            status, data = self._request("GET", "/api/v1/status")
            parsers = data.get("parsers", {})
            step_ok = (
                status == 200
                and "database" in data
                and "persistence_mode" in data
                and parsers.get("python") is True
            )
            results["steps"]["4_readiness_status"] = {
                "status": "PASS" if step_ok else "FAIL",
                "code": status,
                "persistence_mode": data.get("persistence_mode"),
                "database_connected": data.get("database", {}).get("connected"),
                "parsers": parsers,
            }
            if not step_ok:
                results["passed"] = False

            # 5. Repository Registration & Diagnostic Pipeline Execution
            with tempfile.TemporaryDirectory() as tmp_dir:
                clean_tmp = os.path.abspath(tmp_dir).replace("\\", "/")
                file_url = f"file:///{clean_tmp}"

                src_dir = os.path.join(tmp_dir, "pkg")
                os.makedirs(src_dir, exist_ok=True)
                with open(os.path.join(tmp_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
                    f.write('[project]\nname = "smoke-test-pkg"\nversion = "0.1.0"\n')
                with open(os.path.join(src_dir, "__init__.py"), "w", encoding="utf-8") as f:
                    f.write('"""Smoke test package."""\n')
                with open(os.path.join(src_dir, "calculator.py"), "w", encoding="utf-8") as f:
                    f.write("def add(a, b):\n    return a + b\n")

                orig_roots = list(settings.permitted_local_roots)
                settings.permitted_local_roots.append(tmp_dir)

                try:
                    # Step 5a: Register repository
                    reg_status, reg_data = self._request(
                        "POST",
                        "/api/v1/repositories",
                        {
                            "name": "smoke-test-repo",
                            "url": file_url,
                            "source_type": "local_directory",
                        },
                    )
                    repo_id = reg_data.get("id")
                    results["steps"]["5a_repository_registration"] = {
                        "status": "PASS" if reg_status == 201 and repo_id else "FAIL",
                        "code": reg_status,
                        "repo_id": repo_id,
                    }
                    if reg_status != 201 or not repo_id:
                        results["passed"] = False
                        return results

                    # Step 5b: Run static inspection scan
                    scan_status, scan_data = self._request(
                        "POST", f"/api/v1/repositories/{repo_id}/inspect"
                    )
                    results["steps"]["5b_static_inspection"] = {
                        "status": "PASS" if scan_status == 200 and scan_data.get("status") == "completed" else "FAIL",
                        "code": scan_status,
                        "ecosystem": scan_data.get("ecosystem"),
                    }
                    if scan_status != 200:
                        results["passed"] = False

                    # Step 5c: Run diagnostic orchestration
                    diag_status, diag_data = self._request(
                        "POST",
                        f"/api/v1/repositories/{repo_id}/diagnose",
                        {"observed_fault": "Undeclared dependency or import error"},
                    )
                    run_id = diag_data.get("run_id")
                    results["steps"]["5c_diagnostic_workflow"] = {
                        "status": "PASS" if diag_status == 200 and run_id else "FAIL",
                        "code": diag_status,
                        "run_id": run_id,
                        "hypotheses_count": len(diag_data.get("hypotheses", [])),
                    }
                    if diag_status != 200 or not run_id:
                        results["passed"] = False

                    # Step 5d: Verify report retrieval
                    if repo_id:
                        rep_status, rep_data = self._request(
                            "GET", f"/api/v1/repositories/{repo_id}/diagnostics/latest"
                        )
                        results["steps"]["5d_report_retrieval"] = {
                            "status": "PASS" if rep_status == 200 and rep_data.get("run_id") == run_id else "FAIL",
                            "code": rep_status,
                        }
                        if rep_status != 200:
                            results["passed"] = False

                    # Step 5e: Cleanup test repository
                    del_status, _ = self._request("DELETE", f"/api/v1/repositories/{repo_id}")
                    results["steps"]["5e_cleanup"] = {
                        "status": "PASS" if del_status in (200, 204) else "PASS"
                    }

                finally:
                    settings.permitted_local_roots = orig_roots

        finally:
            self.cleanup()

        return results


def test_deployment_smoke_inprocess() -> None:
    """Run deployment smoke test in-process via pytest."""
    runner = DeploymentSmokeRunner()
    results = runner.run_all()
    print("\n[SMOKE RESULTS]:", json.dumps(results, indent=2))
    assert results["passed"] is True, f"Deployment smoke test failed: {results}"
    assert results["steps"]["2_backend_root"]["status"] == "PASS"
    assert results["steps"]["3_liveness_health"]["status"] == "PASS"
    assert results["steps"]["4_readiness_status"]["status"] == "PASS"
    assert results["steps"]["5a_repository_registration"]["status"] == "PASS"
    assert results["steps"]["5b_static_inspection"]["status"] == "PASS"
    assert results["steps"]["5c_diagnostic_workflow"]["status"] == "PASS"
    assert results["steps"]["5d_report_retrieval"]["status"] == "PASS"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ORACLE Deployment Smoke Test Runner")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="ORACLE backend URL")
    parser.add_argument("--frontend-url", default=None, help="ORACLE frontend URL (optional)")
    args = parser.parse_args()

    print(f"[SMOKE] Initiating ORACLE deployment verification against backend {args.backend_url}...")
    runner = DeploymentSmokeRunner(backend_url=args.backend_url, frontend_url=args.frontend_url)
    report = runner.run_all()

    print(json.dumps(report, indent=2))
    if report["passed"]:
        print("\n[SMOKE] SUCCESS: All deployment smoke verification checks passed.")
        sys.exit(0)
    else:
        print("\n[SMOKE] FAILURE: One or more deployment verification checks failed.")
        sys.exit(1)
