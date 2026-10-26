# ORACLE Verified Commands

This document contains verified commands for development, testing, database migrations, and troubleshooting. Always execute commands from the specified working directory.

---

## 1. Environment & Setup

### Python Virtual Environment Setup (Backend)

**Working Directory:** `<repository-root>`

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment in PowerShell
.\.venv\Scripts\Activate.ps1
# (Or in Bash / WSL)
# source .venv/bin/activate
```

> [!NOTE]
> If PowerShell raises an execution policy error when activating (`Activate.ps1 cannot be loaded because running scripts is disabled on this system`), run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> Alternatively, execute Python directly using `.\.venv\Scripts\python.exe`.

### Backend Dependency Installation

**Working Directory:** `<repository-root>\backend`

```powershell
# Install production and development dependencies
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### Frontend Dependency Installation

**Working Directory:** `<repository-root>\frontend`

```powershell
# Install Next.js, React, Tailwind CSS, and devDependencies
npm.cmd install
```

---

## 2. Running Local Development (Dual Terminal)

To develop ORACLE locally, run the FastAPI backend and Next.js frontend in separate terminal windows:

### Terminal 1: Backend Service
**Working Directory:** `<repository-root>\backend`

```powershell
# Start FastAPI backend with hot-reload on port 8000
..\.venv\Scripts\python.exe -m uvicorn oracle.main:app --reload --host 0.0.0.0 --port 8000
```
- **Backend API & Swagger Docs:** http://localhost:8000/docs
- **Health Endpoint:** http://localhost:8000/api/v1/health
- **Status Probe:** http://localhost:8000/api/v1/status

### Terminal 2: Frontend Client
**Working Directory:** `<repository-root>\frontend`

```powershell
# Start Next.js development server on port 3000
npm.cmd run dev
```
- **Frontend Dashboard:** http://localhost:3000

---

## 3. Running Automated Tests

All test suites and fixtures are located in the [`testing/`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/testing) subfolder.

### Backend Tests (pytest)

**Working Directory:** `<repository-root>`

```powershell
# Run the complete backend test suite
.\.venv\Scripts\python.exe -m pytest testing

# Run tests with verbose output
.\.venv\Scripts\python.exe -m pytest testing -v

# Run only Alembic migration tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_alembic.py

# Run only database connectivity and session tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_db.py

# Run only repository management endpoint tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_repositories.py

# Run only unified diagnostic engine tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_diagnostics.py

# Run only dynamic execution worker tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_execution.py

# Run only static code ingestion & inspection tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_inspection.py

# Run only ML research and experiment tests
.\.venv\Scripts\python.exe -m pytest testing/ml
```

### Frontend Tests & Type Checking

**Working Directory:** `<repository-root>\frontend`

```powershell
# Run TypeScript compilation check
npm.cmd run type-check

# Run ESLint check
npm.cmd run lint

# Run API client unit tests
npm.cmd run test

# Run Next.js production build verification
npm.cmd run build
```

Or from repository root:
```powershell
node --test testing/frontend/test_api_client.mjs
```

> [!IMPORTANT]
> Always execute python tools via `python.exe -m <tool>` rather than `<tool>.exe` on Windows to avoid Windows Application Control / Smart App Control blocks on unsigned executable wrappers in user directories.

---

## 4. Database & Alembic Migrations

**Working Directory:** `<repository-root>\backend`

### Safe Offline Operations (No Running PostgreSQL Required)

```powershell
# Generate static transactional PostgreSQL DDL without connecting to a live database
..\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

### Online Operations (Requires Running PostgreSQL)

```powershell
# Apply all pending migrations to the latest revision
..\.venv\Scripts\python.exe -m alembic upgrade head

# Inspect current database revision
..\.venv\Scripts\python.exe -m alembic current

# Generate a new migration revision from SQLAlchemy model metadata
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "description_of_changes"

# Revert the most recent migration
..\.venv\Scripts\python.exe -m alembic downgrade -1
```

---

## 5. Minimum PostgreSQL Service Requirements & Local Setup

ORACLE requires PostgreSQL 15+ (recommended PostgreSQL 16) with standard TCP connectivity on port 5432.

### Minimum Service Specifications

| Parameter | Development Value |
| :--- | :--- |
| **Engine** | PostgreSQL 15 or 16 |
| **Database Name** | `oracle_db` |
| **Port** | `5432` |
| **User** | `postgres` (or as configured in `.env`) |
| **Password** | `postgres` (or as configured in `.env`) |
| **Connection URL** | `postgresql+psycopg://postgres:postgres@localhost:5432/oracle_db` |

### Provisioning Methods

#### Method 1: Docker (When Docker Desktop is installed)
```powershell
docker run -d `
  --name oracle-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=oracle_db `
  -p 5432:5432 `
  postgres:16-alpine
```

#### Method 2: Native Windows PostgreSQL Installation
1. Download the official installer from [PostgreSQL Windows Downloads](https://www.postgresql.org/download/windows/).
2. Install with port `5432`, password `postgres`.
3. Open `pgAdmin` or `psql` and create the development database:
   ```sql
   CREATE DATABASE oracle_db;
   ```

#### Method 3: Windows Subsystem for Linux (WSL2)
```bash
sudo apt update && sudo apt install -y postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE DATABASE oracle_db OWNER postgres;"
```

---

## 6. Troubleshooting & Platform Notes

### Windows Smart App Control / Application Control (.exe blocks)
On Windows 11 with Smart App Control or WDAC policies enabled, pip wrapper executables (like `pytest.exe`, `alembic.exe`, `uvicorn.exe`) may be blocked with `An Application Control policy has blocked this file`.
- **Solution:** Always invoke tools via the Python module syntax:
  - Use `python -m pytest testing` instead of `pytest`
  - Use `python -m alembic` instead of `alembic`
  - Use `python -m uvicorn` instead of `uvicorn`

### Windows PowerShell Script Execution Policy (npm.ps1)
When calling `npm` from PowerShell, Windows may block `npm.ps1`.
- **Solution:** Execute `npm.cmd` explicitly or invoke via `cmd.exe /c npm <command>`.

### CORS & Connection Failures
If the frontend reports `Backend Unreachable` or network errors:
1. Verify the backend is listening on port 8000: `curl http://localhost:8000/api/v1/health`
2. Ensure `NEXT_PUBLIC_API_URL` in `frontend/.env.local` points to `http://localhost:8000`.
3. Check `cors_origins` in `backend/oracle/core/config.py` contains `http://localhost:3000`.

---

## 7. Diagnostic Target Management API (curl & PowerShell)

### Register a Diagnostic Target Repository

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"name": "auth-service", "url": "https://github.com/example/auth-service.git", "source_type": "git"}'
```

**curl:**
```bash
curl -X POST http://localhost:8000/api/v1/repositories \
  -H "Content-Type: application/json" \
  -d '{"name": "auth-service", "url": "https://github.com/example/auth-service.git", "source_type": "git"}'
```

### List Registered Targets

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories" -Method Get
```

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/repositories -H "Accept: application/json"
```

### Get Target Details by UUID

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/repositories/<UUID> -H "Accept: application/json"
```

### Delete Target Registration

**curl:**
```bash
curl -X DELETE http://localhost:8000/api/v1/repositories/<UUID>
```
*(Returns HTTP 204 No Content upon successful removal).*

---

## 8. Unified Diagnostic Engine Commands

**Working Directory:** `<repository-root>`

### Trigger End-to-End Diagnosis

**PowerShell:**
```powershell
$body = @{
    allow_dynamic = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories/<UUID>/diagnose" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

**curl:**
```bash
curl -X POST http://localhost:8000/api/v1/repositories/<UUID>/diagnose \
  -H "Content-Type: application/json" \
  -d '{"allow_dynamic": false}'
```

### Retrieve Latest Diagnostic Report for Target

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories/<UUID>/diagnostics/latest" -Method Get
```

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/repositories/<UUID>/diagnostics/latest -H "Accept: application/json"
```

### Retrieve Diagnostic Report by Run UUID

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/diagnostics/<RUN_UUID>" -Method Get
```

### List All Recorded Diagnostic Runs

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/diagnostics/runs" -Method Get
```

---

## 9. ML Research and Experiment Commands

**Working Directory:** `<repository-root>`

### Run ML Research Tests
```powershell
# Run all ML taxonomy, dataset schema, and experiment tests
.\.venv\Scripts\python.exe -m pytest testing/ml -v
```

### Inspect Fault Taxonomy via Python CLI
```powershell
.\.venv\Scripts\python.exe -c "from ml.taxonomy import list_taxonomy_categories, get_taxonomy_entry; [print(f'[{c.value}] {get_taxonomy_entry(c).title}') for c in list_taxonomy_categories()]"
```

### Inspect Baseline Model Progression
```powershell
.\.venv\Scripts\python.exe -c "from ml.baselines import list_baseline_specifications; [print(f'Stage {i+1}: {b.name}') for i, b in enumerate(list_baseline_specifications())]"
```

### Validate Dataset Fixtures Offline
```powershell
.\.venv\Scripts\python.exe -c "from ml.dataset import SYNTHETIC_DATABASE_UNREACHABLE_CASE; print('Features:', SYNTHETIC_DATABASE_UNREACHABLE_CASE.to_model_features().keys()); print('Target:', SYNTHETIC_DATABASE_UNREACHABLE_CASE.get_ground_truth_category())"
```

---

## 9. Repository Ingestion and Static Inspection Commands

**Working Directory:** `<repository-root>`

### Run Inspection Test Suite
```powershell
# Run all inspection unit and API tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_inspection.py -v
```

### Trigger Static Inspection on a Registered Target

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories/<UUID>/inspect" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"include_stdlib": false, "max_depth": 10}'
```

**curl:**
```bash
curl -X POST http://localhost:8000/api/v1/repositories/<UUID>/inspect \
  -H "Content-Type: application/json" \
  -d '{"include_stdlib": false, "max_depth": 10}'
```

### Retrieve Latest Cached Inspection Report

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories/<UUID>/inspection" -Method Get
```

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/repositories/<UUID>/inspection -H "Accept: application/json"
```

### Direct Static Inspection via Python CLI (Offline / Ad-Hoc Probe)
```powershell
.\.venv\Scripts\python.exe -c "
from oracle.inspection import InspectionService
from oracle.models.repository import Repository, SourceType
import uuid

repo = Repository(id=uuid.uuid4(), name='Self-Scan', url='file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE', source_type=SourceType.LOCAL_DIRECTORY)
service = InspectionService()
report = service.inspect_repository(repo)
print(f'Status: {report.status}, Files: {report.file_count}, Ecosystems: {[e.ecosystem for e in report.ecosystems]}, Edges: {len(report.dependency_graph.edges)}')
"
```

---

## 10. Controlled Fault-Injection Benchmark Commands

**Working Directory:** `<repository-root>`

### Run Benchmark Automated Test Suite
```powershell
# Run all benchmark unit, isolation, and scenario tests
.\.venv\Scripts\python.exe -m pytest testing/ml/test_benchmark.py -v
```

### Run Benchmark Runner (Human-Readable Output)
```powershell
.\.venv\Scripts\python.exe -m ml.benchmark.runner
```

### Output Machine-Readable JSON Benchmark Artifact
```powershell
.\.venv\Scripts\python.exe -m ml.benchmark.runner --json
```

### Save Benchmark Artifact to File
```powershell
.\.venv\Scripts\python.exe -m ml.benchmark.runner --output benchmark_run_summary.json
```

### Inspect Benchmark Scenarios via Python CLI
```powershell
.\.venv\Scripts\python.exe -c "
from ml.benchmark import get_benchmark_scenarios
for s in get_benchmark_scenarios():
    supp = 'Supported' if s.is_supported_statically else 'Unsupported'
    print(f'[{s.scenario_id}] {s.project_id} ({supp}) -> {s.reproduction_method}')
"
```

---

## 11. Sandboxed Dynamic Test Execution Commands

**Working Directory:** `<repository-root>`

### Run Dynamic Execution Automated Test Suite
```powershell
# Run all execution policy, preflight, worker, and endpoint tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_execution.py -v
```

### Probe Host Isolation Capabilities via Python CLI
```powershell
.\.venv\Scripts\python.exe -c "
from oracle.execution import check_isolation_preflight
status = check_isolation_preflight()
print(f'Available: {status.is_available}, Provider: {status.provider}')
if not status.is_available:
    for reason in status.missing_reasons:
        print(f'  - {reason}')
else:
    print(f'Capabilities: {status.capabilities}')
"
```

### Inspect Approved Workload Profiles via Python CLI
```powershell
.\.venv\Scripts\python.exe -c "
from oracle.execution import WORKLOAD_PROFILES
for pid, p in WORKLOAD_PROFILES.items():
    print(f'[{pid}] {p.name}: {p.command}')
"
```

### Probe Isolation Status via HTTP API

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/system/isolation" -Method Get
```

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/system/isolation -H "Accept: application/json"
```

### Trigger Dynamic Workload Execution on Target Repository

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories/<UUID>/execute" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"profile_id": "health-probe"}'
```

**curl:**
```bash
curl -X POST http://localhost:8000/api/v1/repositories/<UUID>/execute \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "health-probe"}'
```

### Retrieve Latest Dynamic Execution Report

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories/<UUID>/execution" -Method Get
```

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/repositories/<UUID>/execution -H "Accept: application/json"
```

---

## 12. Adaptive Probe Planning & Diagnostic Intelligence Commands

**Working Directory:** `<repository-root>`

### Run Adaptive Diagnostic Intelligence Tests
```powershell
# Run the 11 adaptive planning and intelligence unit tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_diagnostic_intelligence.py -v

# Run the 5 adaptive benchmark suite integration tests
.\.venv\Scripts\python.exe -m pytest testing/ml/test_adaptive_benchmark.py -v
```

### Run Adaptive Benchmark CLI Evaluation
```powershell
# Execute the complete 11-scenario adaptive benchmark runner
.\.venv\Scripts\python.exe ml/benchmark/adaptive_runner.py
```

### Trigger Adaptive Diagnostic Run via HTTP API

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/repositories/<UUID>/diagnose" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"capabilities": ["adaptive_probing", "evidence_collection"], "max_iterations": 5, "allow_dynamic": false}'
```

**curl:**
```bash
curl -X POST http://localhost:8000/api/v1/repositories/<UUID>/diagnose \
  -H "Content-Type: application/json" \
  -d '{"capabilities": ["adaptive_probing", "evidence_collection"], "max_iterations": 5, "allow_dynamic": false}'
```

### Retrieve Candidate and Executed Diagnostic Probes

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/diagnostics/<RUN_ID>/probes" -Method Get
```

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/diagnostics/<RUN_ID>/probes -H "Accept: application/json"
```

### Retrieve Investigation Decisions & Stopping Rationale

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/diagnostics/<RUN_ID>/decisions" -Method Get
```

**curl:**
```bash
curl -X GET http://localhost:8000/api/v1/diagnostics/<RUN_ID>/decisions -H "Accept: application/json"
```

---

## 13. Diagnostic Reliability, Adversarial Evaluation & Baseline Comparison Commands

**Working Directory:** `<repository-root>`

### Run 20-Scenario Reliability Evaluation Harness & Baseline Comparison
```powershell
# Run the complete adversarial evaluation harness across all 20 scenarios,
# compute granular metrics with numerators/denominators, and persist reports:
.\.venv\Scripts\python.exe ml/benchmark/evaluation_report.py
```

### Run Dedicated Diagnostic Reliability Unit Tests
```powershell
# Run the 11 diagnostic reliability tests covering order invariance,
# evidence deduplication, multi-fault separation, and cascade reasoning:
.\.venv\Scripts\python.exe -m pytest testing/backend/test_diagnostic_reliability.py -v
```

### Run Adversarial Benchmark Integration Tests
```powershell
# Run the 5 adversarial benchmark suite tests verifying all 20 scenarios:
.\.venv\Scripts\python.exe -m pytest testing/ml/test_adversarial_benchmark.py -v
```

### Inspect Generated Reliability Reports
```powershell
# View the Markdown evaluation report
Get-Content testing/reports/diagnostic_reliability_report.md

# View the raw JSON metrics artifact
Get-Content testing/reports/diagnostic_reliability_report.json
```

---

## 14. TypeScript/JavaScript AST Inspection & Polyglot Benchmark Commands (Implementation 013)

**Working Directory:** `<repository-root>`

### Run TypeScript/JavaScript AST Parser Unit Tests
```powershell
# Run the 12 dedicated parser tests covering all 8 extensions, import types,
# module resolution, path aliases, index fallbacks, and containment:
.\.venv\Scripts\python.exe -m pytest testing/backend/test_ts_ast_parser.py -v
```

### Run TypeScript Benchmark Integration Tests
```powershell
# Run the 7 dedicated TypeScript benchmark tests verifying CASE-021 through CASE-038:
.\.venv\Scripts\python.exe -m pytest testing/ml/test_ts_benchmark.py -v
```

### Run Complete 38-Scenario Benchmark & Reliability Evaluation
```powershell
# Run evaluation across all 38 scenarios (Python, JS, TS, polyglot),
# comparing Adaptive Engine vs Naive Baseline and generating updated reports:
.\.venv\Scripts\python.exe ml/benchmark/evaluation_report.py
```

### Direct TypeScript AST Worker Verification (Node.js CLI)
```powershell
# Test the isolated worker directly via stdin JSON:
echo '{"files": [{"path": "example.ts", "content": "import { useState } from \"react\";\nexport const x: number = 42;"}]}' | node backend/oracle/inspection/ts_ast_worker.mjs
```

---

## 15. Java AST Inspection & Polyglot Dependency Intelligence Commands (Implementation 014)

**Working Directory:** `<repository-root>`

### Run Java AST Parser Unit Tests
```powershell
# Run the 13 dedicated Java AST parser unit tests covering syntax errors,
# imports (static, wildcard, single-type), Maven POM parsing, and Gradle builds:
.\.venv\Scripts\python.exe -m pytest testing/backend/test_java_ast_parser.py -v
```

### Run Java Benchmark Integration Tests
```powershell
# Run the 9 dedicated Java benchmark tests verifying CASE-039 through CASE-060:
.\.venv\Scripts\python.exe -m pytest testing/ml/test_java_benchmark.py -v
```

### Run Complete 60-Scenario Adversarial Benchmark & Reliability Evaluation
```powershell
# Run full evaluation across all 60 scenarios (Python, JS, TS, Java, and mixed polyglot),
# comparing Adaptive Engine vs Naive Baseline and generating updated reports:
.\.venv\Scripts\python.exe ml/benchmark/evaluation_report.py
```

### Compile Java AST Worker (Standard OpenJDK 21)
```powershell
# Compile the zero-dependency Java AST worker into backend/ package tree:
javac -d backend backend/oracle/inspection/JavaAstWorker.java
```

### Direct Java AST Worker Verification (JVM CLI)
```powershell
# Test the isolated Java AST worker directly via stdin JSON:
echo '{"files": [{"path": "com/example/Test.java", "content": "package com.example;\npublic class Test {}"}]}' | java -cp backend oracle.inspection.JavaAstWorker
```

---

## 16. End-to-End Product Validation, Real-World Trials, and Persistence Verification Commands (Implementation 015)

**Working Directory:** `<repository-root>`

### Run Complete End-to-End Workflow Integration Tests
```powershell
# Verify full 17-step product workflow via FastAPI TestClient (registration, inspection,
# diagnosis, report retrieval, probes, decisions, polyglot workflows, deletion):
.\.venv\Scripts\python.exe -m pytest testing/backend/test_e2e_workflow.py -v
```

### Run Persistence and Database Lifecycle Tests
```powershell
# Verify offline Alembic DDL generation, honest persistence mode reporting,
# process restart survival, and 100% DiagnosticReport JSON roundtrip fidelity:
.\.venv\Scripts\python.exe -m pytest testing/backend/test_persistence_lifecycle.py -v
```

### Run Safe Snapshot & Parser Security Suite
```powershell
# Verify path traversal blocking, file count / byte size quota limits,
# worker timeout recovery, worker malformed JSON recovery, and secret redaction:
.\.venv\Scripts\python.exe -m pytest testing/backend/test_snapshot_security.py -v
```

### Run Real-World Trials Regression Suite
```powershell
# Verify 8 realistic repository configurations (FastAPI, Next.js, Spring Boot,
# mixed polyglot, clean controls, syntax defects, multiple independent faults):
.\.venv\Scripts\python.exe -m pytest testing/ml/test_real_world_trials.py -v
```

### Run Standalone Real-World Trials Evaluation Runner
```powershell
# Execute the real-world trials harness and regenerate JSON / Markdown reports:
.\.venv\Scripts\python.exe ml/benchmark/real_world_trials.py

# Inspect the generated Markdown trial evaluation report:
Get-Content testing/reports/real_world_trials_report.md
```

### Run Complete Quality Gates (Backend, ML, and Frontend)
```powershell
# 1. Complete Python and ML test suite
.\.venv\Scripts\python.exe -m pytest testing/

# 2. Complete 60-scenario adversarial reliability evaluation
.\.venv\Scripts\python.exe ml/benchmark/evaluation_report.py

# 3. Frontend TypeScript type checking, linting, tests, and production build
npm.cmd run type-check --prefix frontend
npm.cmd run lint --prefix frontend
npm.cmd run test --prefix frontend
npm.cmd run build --prefix frontend
```

---

## 17. Deployment Readiness, Container Lifecycle, and Smoke Testing Commands (Implementation 016)

**Working Directory:** `<repository-root>`

### Run Deployment Configuration & Hardening Test Suite
```powershell
# Verify production invariants, decomposed connection parameters, Dockerfile directives,
# Compose network isolation, entrypoint script syntax, and health endpoints contracts:
.\.venv\Scripts\python.exe -m pytest testing/backend/test_deployment_config.py -v
```

### Run Automated Deployment Smoke Test (In-Process Pytest)
```powershell
# Verify full deployment workflow in-process (root, liveness, readiness, registration,
# inspection, diagnosis, report retrieval, and non-destructive cleanup):
.\.venv\Scripts\python.exe -m pytest testing/deploy/test_deployment_smoke.py -v
```

### Run Automated Deployment Smoke Test (Standalone CLI against Live Containers)
```bash
# Execute against a running ORACLE container cluster:
python testing/deploy/test_deployment_smoke.py --backend-url http://localhost:8000 --frontend-url http://localhost:3000
```

### Docker Compose Service Lifecycle Commands
```bash
# 1. Prepare environment secrets
cp deploy/.env.example deploy/.env

# 2. Build production container images
docker compose -f deploy/docker-compose.yml build

# 3. Launch services in detached mode with automated health monitoring
docker compose -f deploy/docker-compose.yml up -d

# 4. Inspect service health status
docker compose -f deploy/docker-compose.yml ps

# 5. Tail container logs
docker compose -f deploy/docker-compose.yml logs -f backend

# 6. Stop all services cleanly
docker compose -f deploy/docker-compose.yml down
```

### Container Database Migration Commands
```bash
# Check current database revision
docker compose -f deploy/docker-compose.yml exec backend alembic current

# Apply pending database migrations
docker compose -f deploy/docker-compose.yml exec backend alembic upgrade head

# Downgrade schema by one revision
docker compose -f deploy/docker-compose.yml exec backend alembic downgrade -1
```

### Database Backup & Restore Procedures
```bash
# 1. Export compressed SQL backup from PostgreSQL container
docker compose -f deploy/docker-compose.yml exec -T db pg_dump -U oracle_user oracle_db | gzip > backup_oracle.sql.gz

# 2. Stop frontend and backend prior to restoration
docker compose -f deploy/docker-compose.yml stop backend frontend

# 3. Restore database from compressed dump
gunzip -c backup_oracle.sql.gz | docker compose -f deploy/docker-compose.yml exec -T db psql -U oracle_user -d oracle_db

# 4. Restart application services
docker compose -f deploy/docker-compose.yml start backend frontend
```

### Query Production Health and Readiness Probes
```powershell
# Liveness probe
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get

# Readiness probe (reports DB connectivity and polyglot parser operational status)
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/status" -Method Get
```

---

## 13. Generalization, Machine Learning Ranking, and Go Static Analysis (Implementation 017)

### Run Go AST Parser & Manifest Test Suite
**Working Directory:** `<repository-root>`

```powershell
.\.venv\Scripts\python.exe -m pytest testing/backend/test_go_ast_parser.py -v
```

### Run Telemetry & Traceback Analyzer Test Suite
**Working Directory:** `<repository-root>`

```powershell
.\.venv\Scripts\python.exe -m pytest testing/backend/test_telemetry_analyzer.py -v
```

### Run ML Hypothesis Ranker & Probability Calibration Test Suite
**Working Directory:** `<repository-root>`

```powershell
.\.venv\Scripts\python.exe -m pytest testing/ml/test_ml_ranker.py -v
```

### Run Adaptive vs Fixed Probe Evaluation Test Suite
**Working Directory:** `<repository-root>`

```powershell
.\.venv\Scripts\python.exe -m pytest testing/ml/test_probe_evaluation.py -v
```

### Run Generalization Dataset & Comparative Benchmark Test Suite
**Working Directory:** `<repository-root>`

```powershell
.\.venv\Scripts\python.exe -m pytest testing/ml/test_generalization_dataset.py -v
```

### Execute Official ML Model Comparison Benchmark Runner
**Working Directory:** `<repository-root>`

```powershell
# Runs comparative evaluation across all 20 generalization scenarios and updates reports
.\.venv\Scripts\python.exe -c "from ml.benchmark.ml_evaluation import run_comparative_ml_benchmark; res = run_comparative_ml_benchmark(); print('Report generated for', res['total_scenarios'], 'scenarios')"
```

---

## 14. Independent Audit, Feature Leakage & Verification Commands (Implementation 018)

### Run Remediated Go AST Lexical Scanner Test Suite
**Working Directory:** `<repository-root>`

```powershell
# Verifies 18 Go AST tests including delimiter handling inside raw strings, struct tags, and runes
.\.venv\Scripts\python.exe -m pytest testing/backend/test_go_ast_parser.py -v
```

### Run Telemetry Privacy, Secret Redaction & Chained Traceback E2E Suite
**Working Directory:** `<repository-root>`

```powershell
# Verifies end-to-end secret scrubbing, run-scoped evidence IDs, and chained/nested tracebacks
.\.venv\Scripts\python.exe -m pytest testing/backend/test_telemetry_e2e.py -v
```

### Run ML Feature Invariance & Target Leakage Prevention Suite
**Working Directory:** `<repository-root>`

```powershell
# Proves mathematically that feature extraction is invariant to scenario IDs, names, and labels
.\.venv\Scripts\python.exe -m pytest testing/ml/test_feature_leakage.py -v
```

### Run Scenario-Family 5-Fold Cross-Validation & Benchmark Suite
**Working Directory:** `<repository-root>`

```powershell
# Runs full 20-scenario generalization evaluation with 5-fold scenario-family cross-validation
.\.venv\Scripts\python.exe -m pytest testing/ml/test_generalization_dataset.py -v
```

### Run Combined Implementation 018 Targeted Verification Suite
**Working Directory:** `<repository-root>`

```powershell
# Runs all Implementation 018 audit, remediation, and verification tests
.\.venv\Scripts\python.exe -m pytest testing/backend/test_go_ast_parser.py testing/backend/test_telemetry_analyzer.py testing/backend/test_telemetry_e2e.py testing/ml/test_feature_leakage.py testing/ml/test_generalization_dataset.py -v
```








