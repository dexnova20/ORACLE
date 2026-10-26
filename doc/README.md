# ORACLE

ORACLE is an extensible platform engineered for inspecting software systems, identifying faults, testing components independently, and producing evidence-backed diagnoses.

---

## Clean Architecture Directory Arrangement

The repository enforces strict domain subfolder isolation: no domain files or documentation files reside loose in the root directory. Every component lives strictly within its assigned subfolder:

```
ORACLE/
├── backend/                  # Backend source code, migrations, configs, and dependencies
├── deploy/                   # Production containerization, compose topology, and operational runbook
├── doc/                      # All markdown (.md) documentation files
├── frontend/                 # Next.js App Router, TypeScript, and Tailwind CSS UI
├── ml/                       # ML research: taxonomy, dataset schemas, evaluation, baselines
├── testing/                  # All automated test suites, fixtures, and runner configs
│   ├── backend/              # Backend test suite (pytest)
│   ├── deploy/               # Deployment smoke test suite and CLI runner (pytest/CLI)
│   ├── frontend/             # Frontend API client test suite (node:test)
│   └── ml/                   # ML taxonomy, schema, and experiment tests (pytest)
└── [future subfolders]/      # Dedicated subfolders for future domains
```

---

## Architecture & Technology Baseline

- **Independent Audit, Reproducibility & Generalization Validation (Implementation 018):** Independent, evidence-driven verification audit of Implementation 017 across static inspection, telemetry parsing, and machine learning pipelines. Discovered and remediated high-severity delimiter false positives in `backend/oracle/inspection/go_parser.py` via a zero-code-execution 6-state lexical scanner, accurately isolating delimiters inside interpreted strings (`"..."`), raw multiline strings (`` `...` ``), rune literals (`'...'`), line comments (`//`), and block comments (`/*...*/`). Enforced mandatory secret sanitization (`redact_secrets`) across runtime tracebacks and telemetry evidence generation in `backend/oracle/diagnostics/telemetry_analyzer.py`, with run-scoped evidence IDs (`EVID-TELEM-{run_id[:8]}-{seq:03d}`). Added chained exception extraction for Python and recursive `Caused by:` parsing for Java root cause isolation. Formally proved zero target label leakage in the 24-dimensional feature extractor via dedicated invariance tests (`testing/ml/test_feature_leakage.py`). Rebuilt the ML evaluation protocol in `ml/benchmark/ml_evaluation.py` with Scenario-Family 5-Fold Cross-Validation, demonstrating 80.0% CV Top-1 accuracy, 0.2976 CV ECE, 0.1600 CV Brier score, and 100.0% abstention precision on unseen families. Delivered formal audit report at `testing/reports/implementation_017_audit_report.md`.
- **Generalization, Go Static Analysis, Telemetry Ingestion, and Calibrated ML Ranking (Implementation 017):** Extends ORACLE beyond static-first benchmarks and beyond Python/TypeScript/Java to native Go static analysis (`backend/oracle/inspection/go_parser.py`) with zero host binary dependencies, full `go.mod` module manifest extraction, standard library classification (60+ packages), and token syntax diagnostics. Introduces polyglot runtime telemetry ingestion (`backend/oracle/diagnostics/telemetry_analyzer.py`) parsing stack traces across Python, Node.js/TypeScript, Java, and Go panics, classifying non-static faults (database socket refusal on port 5432/3306, API network timeouts, schema validation failures, JSON decode errors, and missing environment variables) deterministically into the versioned ORACLE Fault Taxonomy. Establishes leak-free machine learning feature representation (24 dense features with zero label/scenario leakage) and candidate ML ranking models (`ml/ranking/ml_ranker.py`) with Platt/Sigmoid probability calibration. Calibrated Random Forest Ensemble reduces Expected Calibration Error (ECE) from 0.6500 down to 0.3548 and Brier score from 0.3031 down to 0.2477 on an independently validated 20-scenario generalization dataset (`ml/dataset/generalization_dataset.py`, `ml/benchmark/ml_evaluation.py`) with 80.0% Top-1 accuracy, 100.0% abstention quality on healthy controls/unsupported targets, and sub-30ms inference latency. Quantitatively proves adaptive probe policy superiority over fixed sequences via Shannon entropy reduction ($\Delta H / \text{Cost}$) in `ml/planning/probe_evaluation.py`.
- **Architecture:** Modular monolith designed for maintainability and clear module boundaries.
- **Backend:** Python 3.14+, FastAPI, Pydantic, SQLAlchemy 2.x, psycopg 3, Alembic migrations.
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4.
- **Deployment Readiness & Production Infrastructure (Implementation 016):** Hardened, three-tier containerized production topology (`deploy/docker-compose.yml`, `deploy/Dockerfile.backend`, `deploy/Dockerfile.frontend`). Network segregation isolates the PostgreSQL 16 database onto a private, internal-only non-routable bridge (`oracle_internal`). Enforces non-root execution (`oracle` UID 10001, `nextjs` UID 1001) and strict Docker host boundary protection: the FastAPI backend never mounts `/var/run/docker.sock`. Polyglot backend container packages Python 3.12, Node.js + TypeScript Compiler API, and OpenJDK 17 + precompiled `JavaAstWorker.class`. Production frontend uses Next.js 16 standalone output (`node server.js`) with >80% reduction in image size. Boot-time production invariant validation rejects weak credentials, `debug=True`, and wildcard CORS. Includes an automated deployment smoke test (`testing/deploy/test_deployment_smoke.py`), deployment configuration test suite (`testing/backend/test_deployment_config.py`), and operational runbook (`deploy/README.md`) covering migrations, backup (`pg_dump`), restore (`psql`), and disaster recovery.
- **End-to-End Product Validation & Real-World Diagnostic Readiness (Implementation 015):** Complete vertical validation of the ORACLE platform across the full 17-step product lifecycle. Validates repository registration, inspection, diagnosis, report persistence, adaptive probe inspection, and deletion through the FastAPI HTTP interface. Synchronizes frontend and backend contracts (`DiagnosticDecisionsResponse`, `DiagnosticProbesResponse`), establishes honest persistence mode declarations (`durable_postgresql` vs `in_memory_transient`), and implements deep polyglot manifest discovery across monorepo and polyglot subdirectories. Evaluated across 8 realistic repository configurations (`ml/benchmark/real_world_trials.py`) with 100.0% accuracy (8/8 passed), 0.0% healthy control false positives (0/5), and 100.0% defective scenario identification (3/3).
- **Java AST Analysis & Polyglot Dependency Intelligence (Implementation 014):** Safe, zero-code-execution Java AST inspection worker (`backend/oracle/inspection/JavaAstWorker.java`) utilizing the standard OpenJDK 21 Compiler Tree API (`javax.tools.JavaCompiler`, `com.sun.source.tree.*`). Executes only the syntactic and lexical analysis phase (`task.parse()`), guaranteeing target code is never compiled to bytecode, loaded into any ClassLoader, evaluated, or executed on the host. Implements a self-contained, zero-dependency embedded JSON parser and serializer communicating over stdin/stdout, and precompiles to `JavaAstWorker.class` for batch snapshot parsing in ~60–100ms. Extracts packages, static/wildcard/single-type imports, classes, interfaces, records, enums, annotations, and nested types with exact 1-indexed line and column coordinates. Performs deterministic cross-module symbol resolution, standard library prefix classification (`JAVA_STDLIB_PREFIXES`), and repository namespace inference (`com.example.*`). Read-only static inspection of Maven (`pom.xml`) and Gradle (`build.gradle`, `build.gradle.kts`) build manifests with property expansion and uncertainty preservation. Maps published dependencies to root package namespaces via `KNOWN_JAVA_DEP_PREFIXES` (e.g. `com.google.guava:guava` -> `com.google.common.*`).
- **TypeScript/JavaScript AST & Cross-Module Semantic Analysis (Implementation 013):** Safe, isolated AST parser worker (`backend/oracle/inspection/ts_ast_worker.mjs`) leveraging the official Microsoft TypeScript Compiler API (`typescript >= 5.0`) over a high-throughput stdin/stdout JSON batch protocol. Enforces a strict zero-execution boundary (parsing inert source text with `ts.createSourceFile`) and Windows Application Control (WDAC) compliance without native C-extension DLLs. Extracts full syntax diagnostics and exact coordinates across 8 file extensions (`.ts`, `.tsx`, `.mts`, `.cts`, `.js`, `.jsx`, `.mjs`, `.cjs`). Performs deterministic module resolution (relative probing, directory index fallback, `tsconfig.json` path aliases via `paths`/`baseUrl`), repository root containment boundary security (flagging escaping imports as `unsupported_reference`), and manifest dependency auditing against `package.json`. Integrates seamlessly with `DiagnosticSystemMap`, `DiagnosticEvidenceRecord`, and the adaptive probe planner.
- **Diagnostic Reliability & Adversarial Validation (Implementations 012, 013 & 014):** Rigorous 60-scenario adversarial benchmark (`CASE-001` through `CASE-060`) validating diagnostic reasoning across Python, TypeScript, JavaScript, Java, and mixed polyglot repositories. Evaluates multiple simultaneous independent faults (`syntax_error` + `syntax_error`, `syntax_error` + `missing_import`), incomplete dependency declarations, misleading comments and string literals, structural variations (`src/` layout, packages, dataclasses, multi-module Maven), upstream faults with independently broken downstream components, polyglot repositories triggering deliberate abstention, and safe configuration lookups. Guarantees mathematical order invariance ($f(A, B) = f(B, A)$) and evidence deduplication in heuristic ranking, strictly prevents repeated diagnostic probes, enforces zero false positives on clean control repositories ($0.0\%$, $0/34$), achieves $100.0\%$ ($56/56$) Top-1 supported accuracy, and isolates multiple independent faults ($100.0\%$, $8/8$). Generates automated machine-readable JSON and human-readable Markdown evaluation reports under `testing/reports/`.
- **Evidence-Based Diagnostic Intelligence & Adaptive Probe Planning:** Active investigation engine that formulates competing causal hypotheses with explicit assumptions and alternatives, scores hypotheses using transparent relative heuristic ranking with diminishing marginal returns, calculates dual-mode expected information gain (Shannon entropy for valid probabilities, discrimination heuristic otherwise), plans utility-optimized diagnostic probes (`static_ast_syntax_check`, `static_import_resolution_check`, `static_manifest_audit`, `downstream_independent_check`, `dynamic_container_execution`), independently verifies downstream components and marks downstream state as `blocked` at runtime, gates against unisolated dynamic execution, and halts cleanly under formal stopping policies (`GET /api/v1/diagnostics/{run_id}/probes`, `GET /api/v1/diagnostics/{run_id}/decisions`).
- **Unified Diagnostic Engine:** Complete 8-stage operational pipeline (`validate_target` → `acquire_snapshot` → `static_inspection` → `build_system_map` → `collect_evidence` → `generate_hypotheses` → `verify_hypotheses` → `generate_report`) connecting target ingestion to interactive Next.js visualization (`POST /api/v1/repositories/{id}/diagnose`, `GET /api/v1/repositories/{id}/diagnostics/latest`, `GET /api/v1/diagnostics/{run_id}`, `GET /api/v1/diagnostics/runs`).
- **Target Ingestion & Static Inspection:** Secure snapshot acquisition (local path containment via `commonpath` and bounded shallow git clone), deterministic multi-ecosystem language detection (Python, TypeScript, Java, C++), and safe zero-execution AST dependency graph extraction (`POST /api/v1/repositories/{id}/inspect`, `GET /api/v1/repositories/{id}/inspection`).
- **System Map & Evidence Contracts:** Normalized architectural graph representation (`DiagnosticSystemMap`) with typed component nodes and directional dependency edges. Discrete empirical evidence records (`DiagnosticEvidenceRecord`) auditing manifests (`pyproject.toml`) via standard library `tomllib` with automatic secret redaction.
- **Causal Reasoning & Verification Gating:** Deterministic fault hypotheses mapped to versioned taxonomy, dual-stage verification (AST re-validation and container sandbox gating), deliberate abstention on empty codebases, and guaranteed zero false positives on clean control repositories.
- **Sandboxed Dynamic Test Execution:** Hardened container worker (`DockerExecutionProvider`) with `--read-only` root, `--network none`, `--cap-drop ALL`, `no-new-privileges`, and read-only source mounts. Enforces an immutable allowlist of approved workload profiles (`WORKLOAD_PROFILES`). Gated by isolation preflight (`check_isolation_preflight`) that strictly prohibits host execution when container sandboxing is unavailable.
- **Controlled Fault-Injection Benchmark:** 11 isolated fixture projects (`testing/fixtures/benchmark/`), independent ground-truth manifest, neutral identifiers (`CASE-001` to `CASE-011`), leak-proof observable evidence contract (`DiagnosticEvidence`), and adaptive benchmark runner (`python ml/benchmark/adaptive_runner.py`) measuring 100% supported accuracy, 0% false positives, 100% abstention accuracy, 100% unsafe probe rejection, and 1.36 mean iterations.
- **ML Research Foundation:** 10-class observable fault taxonomy (v1.0.0), target-leakage-free dataset schema (`DiagnosticCase`), project-aware evaluation splitters (`ProjectAwareSplitter`), calibrated evaluation metrics (Top-k, ECE, abstention), and 6-stage baseline specifications.
- **Testing:** Centralized automated test suite with pytest (backend & ML) and native node:test (frontend) under `testing/`.
- **Database:** PostgreSQL via psycopg 3 (`postgresql+psycopg://`) with reversible Alembic migrations (`001_create_repositories.py`, `002_create_diagnostic_runs.py`).

---

## Documentation

Comprehensive engineering documentation is maintained in [`doc/`](.):

- [Architecture Reference](ARCHITECTURE.md): System design, layer boundaries, data flow, PostgreSQL lifecycle, and security rules.
- [Learning Log](LEARNING_LOG.md): Chronological, beginner-friendly explanations of every implementation step, technical decisions, and bug fixes.
- [Implementation Status](IMPLEMENTATION_STATUS.md): Real-time tracking of implemented, tested, and pending features.
- [Verified Commands](COMMANDS.md): Setup, migration, testing, and troubleshooting commands.

---

## Quickstart

### 1. Setup Backend Environment
```powershell
# Create virtual environment from root
python -m venv .venv

# Install backend dependencies
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### 2. Setup Frontend Environment
```powershell
cd frontend
npm.cmd install
```

### 3. Run Automated Tests
```powershell
# Run backend and ML tests (from root):
.\.venv\Scripts\python.exe -m pytest testing

# Run frontend tests & checks (from frontend/):
cd frontend
npm.cmd run type-check
npm.cmd run lint
npm.cmd run test
```

### 4. Run Diagnostic Reliability Evaluation & Real-World Trials
```powershell
# Run the 60-scenario adversarial benchmark comparison (Baseline vs ORACLE):
.\.venv\Scripts\python.exe ml/benchmark/evaluation_report.py

# Run the 8 real-world repository validation trials:
.\.venv\Scripts\python.exe ml/benchmark/real_world_trials.py

# Run the 20-scenario generalization benchmark (Comparative ML Model Evaluation):
.\.venv\Scripts\python.exe -c "from ml.benchmark.ml_evaluation import run_comparative_ml_benchmark; res = run_comparative_ml_benchmark(); print('Completed', res['total_scenarios'], 'scenarios')"
```
- Reliability JSON report: `testing/reports/diagnostic_reliability_report.json`
- Real-World Trials JSON report: `testing/reports/real_world_trials_report.json`
- ML Model Comparison report: `testing/reports/ml_model_comparison_report.md`
- Reliability Markdown summary: `testing/reports/diagnostic_reliability_report.md`
- Real-World Trials JSON report: `testing/reports/real_world_trials_report.json`
- Real-World Trials Markdown summary: `testing/reports/real_world_trials_report.md`

### 5. Run Development Servers (Two Terminals)

**Terminal 1 (Backend API):**
```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn oracle.main:app --reload --host 0.0.0.0 --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Status Probe: [http://localhost:8000/api/v1/status](http://localhost:8000/api/v1/status)

**Terminal 2 (Frontend Dashboard):**
```powershell
cd frontend
npm.cmd run dev
```
- UI Dashboard: [http://localhost:3000](http://localhost:3000)

### 6. Containerized Production Deployment (Docker Compose)

Deploy the complete three-tier production architecture (PostgreSQL 16, Polyglot Backend, Next.js Standalone Frontend):

```bash
# 1. Copy deployment environment template
cp deploy/.env.example deploy/.env

# 2. Build and launch containers
docker compose -f deploy/docker-compose.yml up -d --build

# 3. Check container health status
docker compose -f deploy/docker-compose.yml ps

# 4. Run automated deployment smoke test
python testing/deploy/test_deployment_smoke.py --backend-url http://localhost:8000 --frontend-url http://localhost:3000
```
- Operational Runbook & Disaster Recovery: [deploy/README.md](deploy/README.md)

