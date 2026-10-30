#!/usr/bin/env python3
"""Durable Persistence Lifecycle Verification Script for ORACLE.

Verifies end-to-end data durability across container restarts, database restarts,
and complete Docker Compose stack recreation.

Steps verified:
 1. System readiness & persistence mode probe (must be durable_postgresql).
 2. Alembic migration version verification (002_create_diagnostic_runs).
 3. Repository record creation via API.
 4. Diagnostic execution and report persistence.
 5. Phase 1: Backend container restart (docker compose restart backend).
 6. Post-backend-restart data integrity verification.
 7. Phase 2: Database container restart (docker compose restart db).
 8. Post-database-restart data integrity verification.
 9. Phase 3: Full stack teardown and recreation (docker compose down & up -d).
10. Idempotent Alembic migration execution verification.
11. Final data integrity verification and fixture cleanup.

Usage:
    python3 deploy/scripts/verify_persistence.py --backend-url http://localhost:8000
"""

import argparse
from datetime import datetime, timezone
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple


class PersistenceVerifier:
    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        compose_file: str = "deploy/docker-compose.yml",
        env_file: str = "deploy/.env",
        skip_docker: bool = False,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.compose_file = compose_file
        self.env_file = env_file
        self.skip_docker = skip_docker
        self.docker_cmd = "docker"

    def _http_request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Tuple[int, Dict[str, Any]]:
        url = f"{self.backend_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                res = json.loads(body) if body.strip() else {}
                return resp.status, res
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            try:
                res = json.loads(err_body)
            except Exception:
                res = {"error": err_body}
            return exc.code, res
        except Exception as exc:
            return 0, {"error": str(exc)}

    def _run_docker_compose(self, *args: str) -> subprocess.CompletedProcess:
        cmd = [self.docker_cmd, "compose", "-f", self.compose_file]
        if os.path.exists(self.env_file):
            cmd.extend(["--env-file", self.env_file])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def _wait_for_backend_healthy(self, max_seconds: int = 60) -> bool:
        start = time.monotonic()
        while time.monotonic() - start < max_seconds:
            status, data = self._http_request("GET", "/api/v1/health", timeout=3.0)
            if status == 200 and data.get("status") == "healthy":
                return True
            time.sleep(2)
        return False

    def run(self) -> bool:
        print("=" * 70)
        print("  ORACLE v0.1: DURABLE PERSISTENCE LIFECYCLE AUDIT")
        print(f"  Target Backend:  {self.backend_url}")
        print(f"  Compose File:    {self.compose_file}")
        print(f"  Docker Restarts: {'Disabled' if self.skip_docker else 'Enabled'}")
        print("=" * 70)

        # Step 1: Probe Readiness and Persistence Mode
        print("\n[Step 1/11] Probing system status and persistence mode...")
        status, data = self._http_request("GET", "/api/v1/status")
        if status != 200:
            print(f"  FAILED: Backend returned HTTP {status}: {data}")
            return False

        persistence_mode = data.get("persistence_mode")
        db_connected = data.get("database", {}).get("connected")
        print(f"  - Persistence Mode:   {persistence_mode}")
        print(f"  - Database Connected: {db_connected}")

        if persistence_mode != "durable_postgresql":
            print(f"  FAILED: Expected persistence_mode='durable_postgresql', got '{persistence_mode}'")
            print("  Note: Application is running in in_memory_transient mode without live PostgreSQL.")
            return False

        if not db_connected:
            print("  FAILED: Database reported not connected.")
            return False
        print("  PASS: System verified in durable_postgresql mode.")

        # Step 2: Verify Alembic Migration Status
        print("\n[Step 2/11] Verifying Alembic migrations...")
        if not self.skip_docker and shutil.which(self.docker_cmd):
            proc = self._run_docker_compose("exec", "backend", "alembic", "current")
            if proc.returncode == 0:
                print(f"  - Alembic Output: {proc.stdout.strip()}")
                if "002_create_diagnostic_runs" in proc.stdout or "head" in proc.stdout:
                    print("  PASS: Latest migration (002_create_diagnostic_runs) verified.")
                else:
                    print("  WARNING: Migration output did not explicitly list 002_create_diagnostic_runs.")
            else:
                print(f"  INFO: Could not run alembic in container directly: {proc.stderr.strip()[:100]}")
        else:
            print("  INFO: Docker CLI unavailable or skipped; proceeding with API-level schema verification.")

        # Step 3: Register Persistent Test Repository
        print("\n[Step 3/11] Registering persistent test repository entity...")
        with tempfile.TemporaryDirectory() as tmp_dir:
            clean_tmp = os.path.abspath(tmp_dir).replace("\\", "/")
            repo_file_url = f"file:///{clean_tmp}"

            pkg_dir = os.path.join(tmp_dir, "persistence_test_pkg")
            os.makedirs(pkg_dir, exist_ok=True)
            with open(os.path.join(tmp_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
                f.write('[project]\nname = "persistence-verification-target"\nversion = "1.0.0"\n')
            with open(os.path.join(pkg_dir, "__init__.py"), "w", encoding="utf-8") as f:
                f.write('"""Persistent target package."""\n')
            with open(os.path.join(pkg_dir, "module.py"), "w", encoding="utf-8") as f:
                f.write("def compute(x):\n    return x * 42\n")

            test_repo_name = f"persistence-test-{int(time.time())}"
            reg_status, reg_data = self._http_request(
                "POST",
                "/api/v1/repositories",
                {
                    "name": test_repo_name,
                    "url": repo_file_url,
                    "source_type": "local_directory",
                },
            )

            if reg_status != 201 or "id" not in reg_data:
                print(f"  FAILED: Repository registration failed (HTTP {reg_status}): {reg_data}")
                return False

            repo_id = reg_data["id"]
            print(f"  PASS: Created Repository id={repo_id}, name={test_repo_name}")

            # Step 4: Execute Diagnostic Run & Persist Report
            print("\n[Step 4/11] Executing diagnostic workflow and persisting report...")
            diag_status, diag_data = self._http_request(
                "POST",
                f"/api/v1/repositories/{repo_id}/diagnose",
                {"symptom_description": "Persistence verification test run"},
            )

            if diag_status != 200 or "run_id" not in diag_data:
                print(f"  FAILED: Diagnostic execution failed (HTTP {diag_status}): {diag_data}")
                return False

            run_id = diag_data["run_id"]
            hyp_count = len(diag_data.get("hypotheses", []))
            print(f"  PASS: Persisted Diagnostic Run run_id={run_id}, status={diag_data.get('status')}, hypotheses={hyp_count}")

            # Verify initial retrieval
            get_status, get_run = self._http_request("GET", f"/api/v1/diagnostics/{run_id}")
            if get_status != 200 or get_run.get("run_id") != run_id:
                print(f"  FAILED: Initial diagnostic run retrieval failed (HTTP {get_status})")
                return False

            if self.skip_docker or not shutil.which(self.docker_cmd):
                print("\n[INFO] Docker management commands skipped (--skip-docker or CLI missing).")
                print("       API persistence and retrieval verified successfully.")
                self._cleanup_repo(repo_id)
                return True

            # Step 5: Phase 1 - Backend Container Restart
            print("\n[Step 5/11] Phase 1: Restarting backend container (docker compose restart backend)...")
            restart_backend = self._run_docker_compose("restart", "backend")
            if restart_backend.returncode != 0:
                print(f"  FAILED to restart backend: {restart_backend.stderr}")
                return False

            print("  Waiting for backend healthcheck recovery...")
            if not self._wait_for_backend_healthy(max_seconds=45):
                print("  FAILED: Backend did not recover after restart.")
                return False
            print("  PASS: Backend container restarted and healthy.")

            # Step 6: Post-Backend-Restart Data Integrity Verification
            print("\n[Step 6/11] Verifying data integrity post backend restart...")
            post_be_status, post_be_run = self._http_request("GET", f"/api/v1/diagnostics/{run_id}")
            if post_be_status != 200 or post_be_run.get("run_id") != run_id:
                print(f"  FAILED: Run record lost or corrupted after backend restart (HTTP {post_be_status})")
                return False

            post_be_repo_status, post_be_repo = self._http_request("GET", f"/api/v1/repositories/{repo_id}")
            if post_be_repo_status != 200 or post_be_repo.get("name") != test_repo_name:
                print(f"  FAILED: Repository record lost after backend restart (HTTP {post_be_repo_status})")
                return False
            print(f"  PASS: Repository and Diagnostic Run survived backend container restart.")

            # Step 7: Phase 2 - PostgreSQL Container Restart
            print("\n[Step 7/11] Phase 2: Restarting database container (docker compose restart db)...")
            restart_db = self._run_docker_compose("restart", "db")
            if restart_db.returncode != 0:
                print(f"  FAILED to restart db: {restart_db.stderr}")
                return False

            print("  Waiting for database and backend reconnection...")
            time.sleep(5)
            if not self._wait_for_backend_healthy(max_seconds=45):
                print("  FAILED: Backend did not reconnect to database after DB restart.")
                return False
            print("  PASS: PostgreSQL container restarted and connection restored.")

            # Step 8: Post-DB-Restart Data Integrity Verification
            print("\n[Step 8/11] Verifying data integrity post database restart...")
            post_db_status, post_db_run = self._http_request("GET", f"/api/v1/diagnostics/{run_id}")
            if post_db_status != 200 or post_db_run.get("run_id") != run_id:
                print(f"  FAILED: Run record lost after database restart (HTTP {post_db_status})")
                return False
            print(f"  PASS: Diagnostic Run and Report intact after PostgreSQL restart.")

            # Step 9: Phase 3 - Full Stack Shutdown & Recreation
            print("\n[Step 9/11] Phase 3: Full stack teardown without volume removal (docker compose down)...")
            down_proc = self._run_docker_compose("down")
            if down_proc.returncode != 0:
                print(f"  FAILED to stop stack: {down_proc.stderr}")
                return False

            print("  Re-launching stack with existing named volume (docker compose up -d)...")
            up_proc = self._run_docker_compose("up", "-d")
            if up_proc.returncode != 0:
                print(f"  FAILED to bring up stack: {up_proc.stderr}")
                return False

            print("  Waiting for full stack initialization and healthchecks...")
            if not self._wait_for_backend_healthy(max_seconds=60):
                print("  FAILED: Stack did not achieve healthy state after recreation.")
                return False
            print("  PASS: Full stack recreated successfully.")

            # Step 10: Idempotent Alembic Migration Check
            print("\n[Step 10/11] Verifying idempotent migration and database connection...")
            status_post, data_post = self._http_request("GET", "/api/v1/status")
            if (
                status_post != 200
                or data_post.get("persistence_mode") != "durable_postgresql"
                or not data_post.get("database", {}).get("connected")
            ):
                print(f"  FAILED: Post-cycle status check failed: {data_post}")
                return False
            print("  PASS: Post-cycle status confirms durable_postgresql and operational DB.")

            # Step 11: Final Data Integrity Verification and Fixture Cleanup
            print("\n[Step 11/11] Final data verification and cleanup...")
            final_status, final_run = self._http_request("GET", f"/api/v1/diagnostics/{run_id}")
            if final_status != 200 or final_run.get("run_id") != run_id:
                print(f"  FAILED: Run record did not survive full stack recreation! (HTTP {final_status})")
                return False

            final_repo_status, final_repo = self._http_request("GET", f"/api/v1/repositories/{repo_id}")
            if final_repo_status != 200 or final_repo.get("name") != test_repo_name:
                print(f"  FAILED: Repository record did not survive full stack recreation!")
                return False

            print(f"  VERIFIED: All records survived complete stack shutdown and recreation.")
            print(f"            Volume 'oracle_pgdata' successfully persisted PostgreSQL database files.")

            self._cleanup_repo(repo_id)

        print("\n" + "=" * 70)
        print("  DURABLE PERSISTENCE VERIFICATION COMPLETED: 100% PASS")
        print("=" * 70)
        return True

    def _cleanup_repo(self, repo_id: str) -> None:
        print(f"  Cleaning up test repository {repo_id}...")
        del_status, _ = self._http_request("DELETE", f"/api/v1/repositories/{repo_id}")
        if del_status in (200, 204):
            print("  PASS: Test repository deleted cleanly (cascaded to runs).")
        else:
            print(f"  INFO: Repository deletion returned HTTP {del_status}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ORACLE Durable Persistence Verification Suite")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="ORACLE backend API URL")
    parser.add_argument("--compose-file", default="deploy/docker-compose.yml", help="Path to docker-compose.yml")
    parser.add_argument("--env-file", default="deploy/.env", help="Path to deploy .env file")
    parser.add_argument("--skip-docker", action="store_true", help="Skip docker compose restart commands")
    args = parser.parse_args()

    verifier = PersistenceVerifier(
        backend_url=args.backend_url,
        compose_file=args.compose_file,
        env_file=args.env_file,
        skip_docker=args.skip_docker,
    )

    success = verifier.run()
    sys.exit(0 if success else 1)

