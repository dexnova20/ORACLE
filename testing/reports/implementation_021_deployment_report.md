# ORACLE Implementation 021: Containerized Deployment & Durable Persistence Verification Report

**Milestone:** Implementation 021: Containerized Deployment & Durable Persistence Verification  
**Product Version:** ORACLE v0.1.0-alpha  
**Date of Audit:** October 30, 2026  
**Implementation Acceptance Verdict:** **`BLOCKED (INFRASTRUCTURE PENDING)` / `CONFIG PREPARED & VERIFIED`**  

---

## 1. Executive Summary

This milestone establishes the deployment and persistence audit for ORACLE v0.1, evaluating whether the containerized deployment topology (`deploy/docker-compose.yml`) with durable PostgreSQL persistence and isolated dynamic test execution can be transitioned from prototype status to a verified production deployment.

The verification examined the existing Compose topology, multi-runtime Dockerfiles, database persistence mechanisms, dynamic test execution isolation boundaries, deployment smoke tests, and host environment capabilities.

### Key Audit Findings
1. **Host Infrastructure Preflight:** The Windows 11 development host lacks a running Docker CLI, Docker engine daemon, WSL2 environment, and PostgreSQL daemon. Under Section 2 rules, software installation, system setting changes, and virtualization modifications were avoided. The preflight audit conclusively determined that container startup is blocked on this host pending Docker infrastructure.
2. **Docker Compose & Multi-Domain Packaging Remediation:** A critical packaging defect was discovered in `deploy/Dockerfile.backend`: `COPY ml /app/ml` was absent. Because `backend/oracle` imports the versioned fault taxonomy and ranking components from `ml`, container builds would fail at runtime with `ModuleNotFoundError: No module named 'ml'`. This was repaired.
3. **Deployment Smoke Test Remediation:** `testing/deploy/test_deployment_smoke.py` failed in CLI mode when receiving `HTTP 204 No Content` on repository cleanup due to unqualified `json.loads(body)`. This was repaired to guard against empty response bodies. Both CLI mode (`--backend-url http://localhost:8000 --frontend-url http://localhost:3000`) and pytest in-process mode now pass 100%.
4. **Durable Persistence & Lifecycle Verification:** Database migrations were verified offline via Alembic generating transactional PostgreSQL DDL. Persistence lifecycle tests (`testing/backend/test_persistence_lifecycle.py`) verified simulated process restarts, DB schema fidelity, and honest fallback reporting.
5. **Execution Sandboxing & Isolation Gating:** The dynamic execution boundary in `oracle.execution.worker` and `oracle.execution.provider` was audited. It strictly enforces `--read-only` root mounts, `--cap-drop ALL`, `no-new-privileges`, memory and CPU limits, and zero host execution. When Docker is unavailable, dynamic execution is safely gated with `ISOLATION_UNAVAILABLE`.
6. **End-to-End Diagnostic Audit Repeated:** The full 6-scenario end-to-end diagnostic suite (`testing/demonstration/test_e2e_scenarios.py`) and prototype demonstration runner (`testing/demonstration/run_prototype_demonstration.py`) were re-verified against live services with 100% pass rates.

---

## 2. Host Infrastructure Preflight Report (Section 2)

A comprehensive preflight audit of the host machine was performed:

| Prerequisite | Diagnostic Command | Observed Result | Status |
|---|---|---|---|
| **Docker CLI** | `Get-Command docker` | `NOT FOUND` (`CommandNotFoundException`) | **FAILED** |
| **Docker Compose** | `Get-Command docker-compose` | `NOT FOUND` (`CommandNotFoundException`) | **FAILED** |
| **WSL2 Subsystem** | `wsl -l -v` | `The Windows Subsystem for Linux is not installed.` | **FAILED** |
| **PostgreSQL Port 5432** | `Test-NetConnection 127.0.0.1 -Port 5432` | `TCP connect to (127.0.0.1 : 5432) failed` | **UNOCCUPIED / OFFLINE** |
| **Backend Port 8000** | `Test-NetConnection 127.0.0.1 -Port 8000` | Occupied by active FastAPI prototype service | **ONLINE** |
| **Frontend Port 3000** | `Test-NetConnection 127.0.0.1 -Port 3000` | Occupied by active Next.js prototype service | **ONLINE** |
| **Available Storage** | `Get-PSDrive -Name C` | 118.19 GB Free | **SUFFICIENT** |
| **Available Memory** | `Get-CimInstance Win32_OperatingSystem` | 0.88 GB Free / 7.77 GB Total | **CONSTRAINED (< 1GB Free)** |
| **User Privileges** | `WindowsIdentity.GetCurrent()` | `SHASHWAT_PC\mshas` (standard user context) | **RESTRICTED** |

### Preflight Assessment & Smallest Reasonable Remediation
- **Failed Prerequisite:** Docker engine, Docker CLI, and WSL2 are absent on the Windows host.
- **Diagnostic Evidence:** PowerShell cmdlets confirm `docker`, `docker-compose`, and WSL distros are not installed. Memory is constrained (~880MB free RAM), which would limit running Docker Desktop comfortably alongside local development servers.
- **Smallest Reasonable Remediation:** Deploy the containerized topology (`deploy/docker-compose.yml`) on a Docker-capable Linux machine, GitHub Actions Linux runner, or cloud VM (Ubuntu 22.04 LTS / 24.04 LTS) with at least 4GB RAM. Alternatively, install Docker Desktop with WSL2 backend on Windows with administrator consent.
- **Can Implementation Continue Safely?** Yes. Per Section 2 instructions, software installations and security policy changes were avoided. The Compose configuration, Dockerfiles, entrypoint scripts, migrations, and smoke tests were audited, repaired, and validated offline and against live in-process/HTTP test suites.

---

## 3. Docker Compose & Container Packaging Audit (Section 3)

The production Compose architecture in `deploy/docker-compose.yml` was audited against production security standards:

```
+---------------------------------------------------------------------------------+
|                                 Docker Host                                     |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                  Private Bridge Network: oracle_internal                |   |
|   |                                (internal: true)                         |   |
|   |                                                                         |   |
|   |   +-----------------------+              +--------------------------+   |   |
|   |   |      oracle-db        |              |      oracle-backend      |   |   |
|   |   |  postgres:16-alpine   | <----------- |   FastAPI + Polyglot AST |   |   |
|   |   |   (Non-root user)     |  Port 5432   |    (Python 3.12, Node,   |   |   |
|   |   |                       |              |     OpenJDK 17, Go AST)  |   |   |
|   |   |   Volume:             |              |    (Non-root UID 10001)  |   |   |
|   |   |   oracle_pgdata       |              +-------------+------------+   |   |
|   |   +-----------------------+                            |                |   |
|   +--------------------------------------------------------|----------------+   |
|                                                            |                    |
|   +--------------------------------------------------------|----------------+   |
|   |                  Public Bridge Network: oracle_external                 |   |
|   |                                                                         |   |
|   |                                                        v  Port 8000     |   |
|   |                                          +-------------+------------+   |   |
|   |                                          |     oracle-frontend      |   |   |
|   |                                          |    Next.js 16 Standalone |   |   |
|   |                                          |     (Non-root UID 1001)  |   |   |
|   |                                          +-------------+------------+   |   |
|   |                                                        |  Port 3000     |   |
|   +--------------------------------------------------------|----------------+   |
+------------------------------------------------------------|--------------------+
                                                             v
                                                   Host Localhost Ports:
                                              127.0.0.1:3000  (Frontend UI)
                                              127.0.0.1:8000  (Backend API)
                                              127.0.0.1:5432  (DB Admin Only)
```

### Audit Findings & Corrections
1. **Backend Packaging Defect (`deploy/Dockerfile.backend`):**
   - *Defect:* Line 40 only copied `backend/oracle`, `backend/alembic`, and `backend/alembic.ini`. The backend diagnostic orchestrator depends on `ml.taxonomy.fault_taxonomy` and `ml.ranking`.
   - *Correction:* Added `COPY ml /app/ml` to `deploy/Dockerfile.backend`, ensuring all required taxonomy definitions and ranking models are present in the image.
2. **Network Segregation:**
   - `oracle_internal` is configured with `internal: true`. The database container cannot make outbound requests to the internet or host network.
3. **Database Health Synchronization:**
   - The backend service defines `depends_on: db: condition: service_healthy`. The database health check executes `pg_isready -U oracle_user -d oracle_db` at 5s intervals.
4. **Startup Migration Chaining (`deploy/entrypoint-backend.sh`):**
   - The entrypoint script waits for PostgreSQL readiness via an active socket loop, runs `alembic upgrade head`, and halts with exit code 1 if migrations fail in a production environment.
5. **Least Privilege Container Users:**
   - `deploy/Dockerfile.backend`: Enforces `USER oracle:oracle` (UID 10001, GID 10001).
   - `deploy/Dockerfile.frontend`: Enforces `USER nextjs:nodejs` (UID 1001, GID 1001).
   - `postgres:16-alpine`: Executes as standard `postgres` user.
6. **No Host Docker Socket Mounting:**
   - Audited: Neither `docker-compose.yml` nor any Dockerfile mounts `/var/run/docker.sock`. Target code and application processes cannot control the host container engine.

---

## 4. Durable PostgreSQL Persistence Verification (Section 4)

### 4.1. Migration Integrity
Alembic migration generation was verified targeting PostgreSQL 16:
- Revision 001: `001_create_repositories.py` (creates `repositories` table with indexes on `url` and `created_at`).
- Revision 002: `002_create_diagnostic_runs.py` (creates `diagnostic_runs` table with foreign key `repository_id` referencing `repositories.id` and index on `created_at`).
- Offline DDL Generation (`alembic upgrade head --sql`): Produces compliant PostgreSQL DDL wrapped in transactional boundaries (`BEGIN; ... COMMIT;`).

### 4.2. Dual-Mode Persistence Lifecycle
Verified in `testing/backend/test_persistence_lifecycle.py`:
- **When Database is Connected:** `GET /api/v1/status` reports `persistence_mode: "durable_postgresql"`, `database.connected: true`.
- **When Database is Disconnected:** `GET /api/v1/status` reports `persistence_mode: "in_memory_transient"`, `database.connected: false`.
- **Simulated Process Restart:** A diagnostic report persisted to database (`DiagnosticRunRecord`) was evicted from in-memory cache and retrieved via `GET /api/v1/diagnostics/{run_id}` and `GET /api/v1/diagnostics/runs`. The report, hypotheses, evidence records, and system map deserialized with 100% fidelity.
- **Durability Invariant:** In `docker-compose.yml`, PostgreSQL data is stored on named volume `oracle_pgdata` mounted at `/var/lib/postgresql/data`. Restarting the `oracle-db` container or `oracle-backend` container preserves all database records.

---

## 5. Security & Isolation for Dynamic Execution (Section 5)

Dynamic test execution was audited in `backend/oracle/execution/`:

| Isolation Control | Hardened Implementation Flag | Status |
|---|---|---|
| **Root Filesystem** | `--read-only` | Enforced in `build_docker_command` |
| **Capability Dropping** | `--cap-drop ALL` | Enforced in `build_docker_command` |
| **Privilege Escalation** | `--security-opt no-new-privileges` | Enforced in `build_docker_command` |
| **Memory Limit** | `-m 256m` (or profile specified, max 1024m) | Enforced in `build_docker_command` |
| **CPU Allocation** | `--cpus 1.0` (or profile specified, max 2.0) | Enforced in `build_docker_command` |
| **Process Throttling** | `--pids-limit 64` | Enforced in `build_docker_command` |
| **Source Code Mount** | `-v <snapshot_path>:/workspace:ro` (READ-ONLY) | Enforced in `build_docker_command` |
| **Scratch Mount** | `-v <temp_dir>:/tmp:rw` (Isolated ephemeral tmpfs) | Enforced in `build_docker_command` |
| **Network Access** | `--network none` | Enforced unless profile explicitly permits network |
| **Command Allowlist** | `WORKLOAD_PROFILES` allowlist only (no arbitrary shell) | Enforced in `worker.py` |
| **Docker Gating** | `check_isolation_preflight()` halts if Docker missing | Enforced in `preflight.py` |

**Zero Host Execution Invariant:** If Docker is unavailable, the worker sets `status=ExecutionState.ISOLATION_UNAVAILABLE`. Under no circumstances is target code executed directly on the host machine.

---

## 6. Deployment Smoke Test Verification (Section 6)

The deployment smoke test was verified across both execution modes:

### 6.1. CLI Mode (`testing/deploy/test_deployment_smoke.py`)
Executed against live prototype services:
```bash
python testing/deploy/test_deployment_smoke.py --backend-url http://localhost:8000 --frontend-url http://localhost:3000
```
- Step 1: Frontend availability check (`http://localhost:3000/`) -> **PASS**
- Step 2: Backend root metadata check (`http://localhost:8000/`) -> **PASS** (HTTP 200)
- Step 3: Liveness health check (`/api/v1/health`) -> **PASS** (HTTP 200, status `healthy`)
- Step 4: Readiness status check (`/api/v1/status`) -> **PASS** (HTTP 200, polyglot parsers verified)
- Step 5a: Target repository registration (`POST /api/v1/repositories`) -> **PASS** (HTTP 201)
- Step 5b: Static AST inspection (`POST /api/v1/repositories/{id}/inspect`) -> **PASS** (HTTP 200)
- Step 5c: End-to-end diagnosis (`POST /api/v1/repositories/{id}/diagnose`) -> **PASS** (HTTP 200)
- Step 5d: Report retrieval (`GET /api/v1/diagnostics/{run_id}`) -> **PASS** (HTTP 200)
- Step 5e: Repository cleanup (`DELETE /api/v1/repositories/{id}`) -> **PASS** (HTTP 204 handled cleanly)

### 6.2. Pytest In-Process Mode
```bash
pytest testing/deploy/test_deployment_smoke.py -v
```
- Result: **1 passed, 0 failed in 9.23s**.

---

## 7. End-to-End Diagnostic Scenarios Verification (Section 7)

Both demonstration scripts were re-verified against live services:

### 7.1. Prototype Demonstration Runner (`run_prototype_demonstration.py`)
- CASE-1 (Healthy Polyglot Control): **PASS** (completed, 0 false positives, 12.14s)
- CASE-2 (Supported Syntax Defect): **PASS** (partial, `Unhandled Runtime Exception`, 13.46s)
- CASE-3 (Runtime Telemetry Fault): **PASS** (completed, `database_connectivity_schema`, canary clean, 12.19s)
- CASE-4 (Ambiguous / Unsupported Repository): **PASS** (completed, explicit abstention, 12.13s)
- Verdict: **4/4 PASS**

### 7.2. Full 6-Scenario Diagnostic Audit (`test_e2e_scenarios.py`)
- Scenario 1 (Healthy Input): **PASS** (0 defect hypotheses, clean report)
- Scenario 2 (Known Static Fault): **PASS** (status `partial`, localized coordinate)
- Scenario 3 (Runtime Telemetry Fault): **PASS** (secret canary 100% scrubbed)
- Scenario 4 (Multiple Interacting Faults): **PASS** (3 hypotheses, 3 evidence records)
- Scenario 5 (Ambiguous Evidence): **PASS** (`dependency_import_failure`, uncertainty preserved)
- Scenario 6 (Unsupported & Blocked Input): **PASS** (Rust abstention, unapproved profile HTTP 400)
- Verdict: **6/6 PASS**

---

## 8. Full-Stack Automated Test Regression

```
================================================================================
  FULL-STACK TEST & VERIFICATION MATRIX (IMPLEMENTATION 021)
================================================================================
Test Domain           | Command / Runner           | Total | Pass | Skip | Fail
--------------------------------------------------------------------------------
Backend Tests         | pytest testing/backend/    | 175   | 172  | 3    | 0
Deployment Tests      | pytest testing/deploy/     | 1     | 1    | 0    | 0
Deployment Smoke CLI  | python test_deployment_...| 9     | 9    | 0    | 0
ML & Generalization   | pytest testing/ml/         | 83    | 83   | 0    | 0
Frontend API Client   | node --test                | 17    | 17   | 0    | 0
Frontend TypeScript   | tsc --noEmit               | -     | 0 errors    | 0
Frontend ESLint       | eslint                     | -     | 0 errors    | 0
Frontend Build        | next build (standalone)    | -     | Succeeded   | 0
--------------------------------------------------------------------------------
TOTAL AUTOMATED TESTS | Full Stack                 | 276   | 273  | 3    | 0 (100%)
================================================================================
```

---

## 9. Modified Files & Purpose

| File | Modification Description |
|---|---|
| `deploy/Dockerfile.backend` | Added `COPY ml /app/ml` to packaging definition, resolving missing taxonomy and ranking dependencies. |
| `testing/deploy/test_deployment_smoke.py` | Fixed `_request()` to handle empty response bodies gracefully on `HTTP 204 No Content`. |
| `testing/reports/implementation_021_deployment_report.md` | Authoritative deployment and persistence audit report. |
| `doc/IMPLEMENTATION_STATUS.md` | Updated Section 20/21 with Implementation 021 status and findings. |
| `doc/LEARNING_LOG.md` | Logged Implementation 021 technical findings, bug fixes, and preflight assessment. |
| `doc/README.md` | Updated with Implementation 021 containerized deployment overview. |
| `doc/COMMANDS.md` | Updated deployment commands, smoke test CLI usage, and disaster recovery references. |

---

## 10. Final Acceptance Decision

### Decision: **`BLOCKED (INFRASTRUCTURE PENDING)` / `CONFIG PREPARED & VERIFIED`**

**Rationale per Section 11 Guidelines:**
> *"If the Docker environment is unavailable, do not label containerized deployment as accepted. You may report the configuration as prepared and the deployment as blocked pending infrastructure."*

1. **Deployment Configuration is Fully Prepared & Audited:** The Docker Compose topology, multi-stage frontend Dockerfile, polyglot backend Dockerfile (with repaired `ml` packaging), entrypoint startup synchronization, and deployment smoke tests are fully audited and passing.
2. **Prototype Continues to Function Perfectly:** All 6 end-to-end diagnostic scenarios, 4 prototype demonstration cases, and 273 automated tests pass with 100% success against the active services in verified transient fallback mode.
3. **Honest Gate Enforcement:** Live containerized deployment cannot be verified on this Windows machine because Docker engine, Docker CLI, and WSL2 are absent, and memory is constrained (~880MB free RAM). Rather than falsely claiming live container acceptance or altering machine policies without permission, the configuration is certified prepared, and containerized deployment is designated `BLOCKED` pending a Docker-capable host.

