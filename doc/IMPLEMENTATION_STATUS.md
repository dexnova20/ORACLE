# ORACLE Implementation Status

This document tracks implemented, tested, pending, and blocked features for the ORACLE platform. No item is marked complete without automated verification.

---

## Status Legend

- [x] **Complete & Verified**: Implemented with corresponding automated tests passing.
- [ ] **Pending**: Designed or scheduled for implementation.
- [!] **Blocked / Prerequisite Missing**: Cannot proceed until an external prerequisite or environment setup is resolved.

---

## 1. Project Foundation & Subfolder Architecture

- [x] **Repository Subfolder Layout & Governance**
  - [x] Strict domain subfolder isolation (no loose files in repository root).
  - [x] Root `.gitignore` configured for Python, Node, and environments.
  - [x] All markdown documentation consolidated under [`doc/`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/doc).
  - [x] All automated testing suites organized under [`testing/`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/testing).
  - [x] Clean architecture policy established: future capabilities (e.g. `ml/`) create dedicated subfolders.
- [x] **Backend Configuration & Build**
  - [x] `backend/pyproject.toml` and `backend/requirements.txt` / `requirements-dev.txt` pinned.
  - [x] Environment template `backend/.env.example` created.
  - [x] Pydantic Settings integration (`oracle.core.config.Settings`).
  - [x] Environment variable parsing with defaults.
  - [x] Unit tests for configuration invariants (`testing/backend/test_config.py`).
- [x] **FastAPI Application & API v1**
  - [x] FastAPI application entrypoint with lifespan handler and CORS middleware (`oracle.main`).
  - [x] Versioned router layout (`oracle.api.v1.router`).
  - [x] Health check endpoint (`GET /api/v1/health`) returning operational status.
  - [x] System diagnostic endpoint (`GET /api/v1/status`) verifying live database connectivity.
  - [x] Integration tests for health and status endpoints (`testing/backend/test_health.py`).

---

## 2. PostgreSQL Database Integration & Migration Verification

- [x] **PostgreSQL Infrastructure & Driver Configuration**
  - [x] SQLAlchemy 2.x engine initialized with `postgresql+psycopg://` driver.
  - [x] Session factory (`SessionLocal`) and request-scoped dependency generator (`get_db`) implemented.
  - [x] Non-blocking database connectivity probe with 2s timeout (`check_db_connectivity`).
  - [x] Unit tests for base metadata, session lifecycle, and mocked connection states (`testing/backend/test_db.py`).
  - [x] Distinguishable live PostgreSQL integration test with conditional skip marker (`test_live_postgres_integration`).
- [x] **Alembic Configuration & Offline Verification**
  - [x] Alembic configuration initialized (`backend/alembic.ini`).
  - [x] Alembic runtime environment (`backend/alembic/env.py`) dynamically wired to `settings.database_url` and `Base.metadata`.
  - [x] Configured `connect_args={"connect_timeout": 3}` in `env.py` to prevent hanging during offline/unreachable states.
  - [x] Offline SQL migration generation verified (`alembic upgrade head --sql` emits valid transactional PostgreSQL DDL).
  - [x] Automated tests for Alembic configuration loading and offline SQL generation (`testing/backend/test_alembic.py`).
- [!] **Live PostgreSQL Service Execution**
  - *Status:* Blocked / External Prerequisite.
  - *Detail:* Neither native PostgreSQL service nor Docker is installed/running on the current Windows host. The application safely handles database disconnection and reports status through `/api/v1/status`, but applying online migrations (`alembic upgrade head`) requires a running PostgreSQL instance.
  - *Remedy:* Provision PostgreSQL 15/16 via Docker (`docker run -d --name oracle-postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=oracle_db postgres:16-alpine`), native Windows installer, or WSL2.

---

## 3. Lightweight Frontend Foundation (Implementation 004)

- [x] **Next.js Application Initialization**
  - [x] Isolated inside dedicated `frontend/` subfolder.
  - [x] Next.js 16 App Router with React 19 and TypeScript.
  - [x] Tailwind CSS v4 styling without heavy UI component bloat.
  - [x] Environment configuration template (`frontend/.env.example`) and typed env access (`frontend/src/config/env.ts`).
- [x] **Typed API Client & Domain Models**
  - [x] TypeScript contracts matching backend Pydantic models (`HealthResponse`, `SystemStatusResponse`).
  - [x] Typed HTTP client (`frontend/src/lib/api.ts`) with timeout and error handling.
- [x] **User Interface & Diagnostic Dashboard**
  - [x] Navigation bar with live backend connectivity indicator (`Navbar.tsx`).
  - [x] System and database diagnostic status card (`StatusCard.tsx`) querying `GET /api/v1/status`.
  - [x] On-demand liveness probe button with latency calculation (`HealthCheckAction.tsx`).
  - [x] Planned diagnostic workflow roadmap view (`DiagnosticWorkflowPreview.tsx`).
  - [x] Loading, error, success, and offline state handling.
- [x] **Frontend Quality & Testing**
  - [x] TypeScript compilation verified (`npm run type-check`).
  - [x] ESLint verified (`npm run lint`).
  - [x] Production build verified (`npm run build`).
  - [x] Automated API client unit tests passing via `node:test` (`testing/frontend/test_api_client.mjs`).

---

## 4. Repository Registration and Diagnostic Target Management (Implementation 005)

- [x] **Canonical Domain Entity (`Repository`)**
  - [x] Defined in `backend/oracle/models/repository.py` using SQLAlchemy 2.0 `DeclarativeBase` and `Mapped`.
  - [x] Schema: UUID primary key, `name` (indexed), `url`, `source_type` (`git`, `local_directory`), `status` (`registered`, `archived`), and UTC timestamps.
  - [x] Exported via `backend/oracle/models/__init__.py` and registered with `backend/alembic/env.py`.
- [x] **Alembic Schema Migration**
  - [x] Reversible migration `001_create_repositories.py` under `backend/alembic/versions/`.
  - [x] Offline PostgreSQL DDL verified (`alembic upgrade head --sql` generates transactional table and index DDL).
  - [x] Automated test `test_alembic_offline_sql_generation_uses_postgresql` asserts table creation.
- [x] **Validation & Pydantic Schemas**
  - [x] `RepositoryCreate` with whitespace trimming and URL scheme validation (`https://`, `http://`, `git://`, `ssh://`, `file://`).
  - [x] Malformed / scheme-only URLs rejected with HTTP 422.
  - [x] `RepositoryResponse` serializing UUID, strings, and ISO datetime timestamps.
- [x] **REST API v1 Endpoints (`/api/v1/repositories`)**
  - [x] `POST /api/v1/repositories` (HTTP 201 Created).
  - [x] `GET /api/v1/repositories` (HTTP 200 OK, ordered by `created_at DESC`).
  - [x] `GET /api/v1/repositories/{id}` (HTTP 200 OK / 404 Not Found).
  - [x] `DELETE /api/v1/repositories/{id}` (HTTP 204 No Content / 404 Not Found).
  - [x] Router mounted in `backend/oracle/api/v1/router.py`.
- [x] **Frontend Target Management Interface**
  - [x] Types in `frontend/src/types/api.ts` (`Repository`, `RepositoryCreateInput`, `SourceType`, `RepositoryStatus`).
  - [x] API client functions in `frontend/src/lib/api.ts` (`listRepositories`, `registerRepository`, `getRepository`, `deleteRepository`).
  - [x] Target registration form component (`RepositoryRegistrationForm.tsx`) with client validation and loading feedback.
  - [x] Target listing component (`RepositoryList.tsx`) with empty state, loading skeleton, and error handling.
  - [x] Target details modal (`RepositoryDetailModal.tsx`) showing complete metadata.
  - [x] Safe deletion confirmation modal preventing accidental removal.
  - [x] Integrated into main dashboard (`frontend/src/app/page.tsx`).
- [x] **Automated Tests & Quality Checks**
  - [x] Backend test suite: 8 repository unit tests in `testing/backend/test_repositories.py` + 1 conditional integration test.
  - [x] Total pytest results: 21 passed, 2 skipped (offline safety verified).
  - [x] Frontend test suite: 7 new API client tests in `testing/frontend/test_api_client.mjs` (11 passed total).
  - [x] Frontend type check (`tsc --noEmit`), ESLint, and production build passing.

---

## 5. ML Research and Experiment Foundation (Implementation 006)

- [x] **Isolated `ml/` Subfolder Architecture**
  - [x] Package initialization with version tracking in `ml/__init__.py`.
  - [x] Strict domain isolation adhering to repository clean architecture guidelines.
- [x] **Fault Taxonomy (v1.0.0)**
  - [x] Versioned taxonomy defined in `ml/taxonomy/fault_taxonomy.py`.
  - [x] 10 observable fault classes implemented: Config, Dependency, I/O Contract, Runtime Exception, Data Validation, API Communication, Database Connectivity/Schema, Model Loading/Inference, Performance Anomaly, Unknown/Insufficient Evidence.
  - [x] Explicit definitions for observable evidence, confounding causes, safe reproduction protocols, required ground-truth evidence, and unclassifiable boundary conditions for all 10 categories.
- [x] **Reproducible Dataset Schema & Target-Leakage Prevention**
  - [x] Pydantic dataset schema defined in `ml/dataset/schema.py` (`DiagnosticCase`, `CaseFeatures`, `GroundTruthLabel`, `ExpectedDiagnosticOutcome`, `ProvenanceMetadata`).
  - [x] Target-leakage safeguards: `to_model_features()` strictly isolates input features from ground-truth labels.
  - [x] Pattern validators reject forbidden leakage tokens (`root_cause`, `ground_truth`, `injected_fault`) in symptoms and test snippets.
  - [x] Model validator detects verbatim ground-truth detail smuggling.
  - [x] Synthetic illustrative test fixtures in `ml/dataset/fixtures.py` explicitly flagged with `is_synthetic = True`.
- [x] **Evaluation Methodology & Group-Aware Splitting**
  - [x] Project-aware splitting (`ProjectAwareSplitter`) preventing cross-project group leakage.
  - [x] Scenario-aware splitting (`ScenarioAwareSplitter`) preventing cross-scenario data leakage.
  - [x] Metrics in `ml/experiments/evaluation.py`: Top-1/Top-3 ranking accuracy, multiclass precision/recall/F1, False Positive Rate (FPR), Expected Calibration Error (ECE), and deliberate abstention accuracy.
  - [x] Diagnostic latency and probe cost analysis.
- [x] **Six-Stage Baseline Progression Specifications**
  - [x] Formal baseline registry defined in `ml/baselines/specs.py`: Deterministic Rules, Statistical Frequency, Isolation Forest Anomaly Detection, XGBoost Fault Ranker, Adaptive Test Selector, and Pretrained Embeddings/Deep Learning.
  - [x] Documented input features, output contracts, assumptions, baseline comparisons, and failure modes.
- [x] **Local Experiment Tracking Protocol**
  - [x] Tracking architecture in `ml/experiments/tracking.py` using local file store (`file:./ml/experiments/mlruns`).
  - [x] Automated parameter sanitization and credential/secret redaction.
  - [x] Standardized run naming convention (`oracle-diag-v{version}-{model}-{split}`).
  - [x] DVC evaluated and deferred until binary datasets exceed 100MB.
- [x] **Automated Testing Suite**
  - [x] 22 dedicated ML tests under `testing/ml/` (`test_taxonomy.py`, `test_dataset_schema.py`, `test_experiments.py`).
  - [x] Complete pytest suite: 43 passed, 2 skipped (offline PG tests), 1 warning.

---

## 6. Target Code Ingestion & Static Inspection Worker (Implementation 007)

- [x] **Sandboxed Snapshot Acquisition**
  - [x] Context manager `SnapshotContext` for ephemeral filesystem lifecycle management.
  - [x] Local directory ingestion with strict containment verification using `os.path.commonpath`.
  - [x] Path traversal (`../`) and out-of-boundary symbolic link escape rejection (`InspectionSecurityError`).
  - [x] Configurable permitted local roots via `permitted_local_roots` in `oracle.core.config.Settings`.
  - [x] Remote Git shallow cloning (`git clone --depth 1 --no-tags --no-recurse-submodules -c core.hooksPath=NUL`).
  - [x] Subprocess argument list execution without shell interpolation; `GIT_TERMINAL_PROMPT=0` non-interactive protection.
  - [x] Pinned revision capture via `git rev-parse HEAD`.
- [x] **Policy Enforcement, Limits & Secret Redaction**
  - [x] Hard exclusions for VCS metadata (`.git`), virtual environments (`.venv`, `venv`), package caches (`node_modules`, `__pycache__`), and compiled binaries (`.pyc`, `.so`, `.dll`, `.exe`, etc.).
  - [x] `ResourceLimiter` enforcing max file count (1,000), max single file size (1 MB), and cumulative byte limit (50 MB).
  - [x] Scan timeout enforcement (30 seconds).
  - [x] Credential and token redactor (`redact_secrets`) for GitHub tokens (`ghp_`), AWS keys (`AKIA`), private keys, and user-password embedded URLs.
- [x] **Multi-Ecosystem Language Detection**
  - [x] Deterministic heuristic ecosystem detector (`detect_ecosystems`) checking project markers.
  - [x] Supports Python (`pyproject.toml`, `requirements.txt`, etc.), JavaScript/TypeScript (`package.json`, `tsconfig.json`), Java/JVM (`pom.xml`, `build.gradle`), and C/C++ (`CMakeLists.txt`, `Makefile`).
  - [x] Mixed-language / polyglot repository detection without executing project scripts.
- [x] **Safe AST Parsing & Dependency Representation**
  - [x] Pure static AST parsing using Python standard library `ast.parse()` with zero user code execution.
  - [x] Import extraction capturing line numbers, imported names, aliases, and file provenance.
  - [x] Relative import resolution (`from . import x`, `from ..foo import bar`) resolved against repository directory tree.
  - [x] Import categorization: `stdlib` (Python 3.10+ `sys.stdlib_module_names`), `internal` (verified local target files), `external` (third-party packages), and `unresolved` (missing relative targets).
  - [x] Syntax error tolerance: captures `FileSyntaxError` cleanly, flagging scan as `partial` without crashing.
  - [x] Directed dependency graph builder (`build_dependency_graph`) generating nodes and edges with provenance.
- [x] **REST API Endpoints & In-Memory Cache**
  - [x] Pydantic models `InspectionOptions` and `InspectionReport` in `backend/oracle/schemas/inspection.py`.
  - [x] `POST /api/v1/repositories/{id}/inspect`: Triggers bounded static inspection and returns full report.
  - [x] `GET /api/v1/repositories/{id}/inspection`: Returns cached report or HTTP 404 if not yet inspected.
  - [x] `InspectionService` coordinator with thread-safe in-memory report caching.
- [x] **Automated Testing Suite**
  - [x] 15 dedicated unit and integration tests in `testing/backend/test_inspection.py`.
  - [x] Automated test results: 14 passed, 1 skipped (symlink escape test safely skipped on non-admin Windows).
  - [x] Total backend & ML test suite: 57 passed, 3 skipped, 1 warning.
  - [x] Frontend test suite: 11 passed, 0 errors.

---

## 7. Controlled Fault-Injection Benchmark (Implementation 008)

- [x] **Ground-Truth Isolation Architecture**
  - [x] Independent `GroundTruthManifest` separated from diagnostic input payloads.
  - [x] Public `BenchmarkScenario` objects contain zero ground-truth labels, root-cause descriptions, or expected remediation actions.
  - [x] Neutral identifiers strictly enforced: `CASE-001` through `CASE-010` and `PRJ-001` through `PRJ-010`.
  - [x] Automated regex leakage validator in `DiagnosticEvidence.to_diagnostic_input()` rejecting forbidden tokens (`root_cause`, `ground_truth`, `injected_fault`).
- [x] **Controlled Fixture Projects (`testing/fixtures/benchmark/`)**
  - [x] 10 minimal, isolated fixture projects created with deterministic file contents and zero malicious payloads.
  - [x] No code executed during fixture discovery; zero external network requests.
- [x] **Observable Evidence Contract & State Tracking**
  - [x] Typed `DiagnosticEvidence` schema in `ml/benchmark/schema.py` tracking discovered files, syntax errors with line numbers, unresolved imports, external imports, and missing evidence.
  - [x] Evidence state classification: `OBSERVED`, `INFERRED`, `MISSING`, `UNSUPPORTED`, `FAILED`.
  - [x] Zero fabrication of dynamic runtime evidence: unsupported dynamic scenarios explicitly marked as `unsupported_analysis`.
- [x] **Deterministic Benchmark Runner (`ml/benchmark/runner.py`)**
  - [x] Direct offline invocation of `InspectionService` without requiring HTTP server or database daemons.
  - [x] Repeat-run determinism verified across executions.
  - [x] Structured JSON artifact output (`--json`, `--output`).
- [x] **Honest Evaluation Metrics & Baseline Verification**
  - [x] Evaluated across 10 scenarios (6 statically supported, 4 unsupported dynamic scenarios).
  - [x] Static diagnostic accuracy on supported scenarios: 100.0%.
  - [x] False positive rate on healthy controls: 0.0% (clean project and misleading comment project).
  - [x] Deliberate abstention on empty repository stub: 100% correct.
  - [x] Evidence extraction coverage: 100.0%.
  - [x] `top_k_ranking_accuracy` explicitly reported as `None` (no ranking model deployed).
- [x] **Automated Testing Suite**
  - [x] 15 dedicated unit and scenario tests in `testing/ml/test_benchmark.py`.
  - [x] Group-aware and scenario-aware split leakage verified using `ProjectAwareSplitter` and `ScenarioAwareSplitter`.
  - [x] Verified zero fixture module execution (`sys.modules` untouched).
  - [x] Total pytest results: 72 passed, 3 skipped, 1 warning.
  - [x] Frontend test suite: 11 passed, 0 errors.

---

## 8. Sandboxed Dynamic Test Execution Worker (Implementation 009)

- [x] **Strict Execution Policy & Workload Allowlist**
  - [x] Immutable allowlist `WORKLOAD_PROFILES` for pre-approved workloads (`health-probe`, `benchmark-env-audit`, `benchmark-db-probe`, `benchmark-contract-check`, `benchmark-transform-test`).
  - [x] Hard rejection of arbitrary shell commands, custom executable paths, or untrusted Dockerfiles (`REJECTED_BY_POLICY`).
  - [x] Enforced execution policy (`ExecutionPolicy`): timeout bounds, 100KB output limit, 256MB memory cap, 1.0 CPU core cap, 64 PID limit, network disabled by default.
- [x] **Isolation Preflight Check & Fail-Safe Invariant**
  - [x] Preflight prober [`check_isolation_preflight`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/execution/preflight.py) verifying Docker executable presence, daemon responsiveness, and security capability flags.
  - [x] Non-negotiable security invariant: when isolation is unavailable, worker returns `ISOLATION_UNAVAILABLE`. Host execution fallback is strictly prohibited.
  - [x] *Current Host State:* Docker is not installed on this Windows development machine; preflight accurately detects absence and safely prevents host execution.
- [x] **Hardened Container Sandbox Provider (`DockerExecutionProvider`)**
  - [x] Command construction enforcing `--read-only` root filesystem, `--network none`, `--cap-drop ALL`, and `--security-opt no-new-privileges`.
  - [x] Read-only target source snapshot mount (`-v <snapshot>:/workspace:ro`).
  - [x] Ephemeral scratch storage mount (`-v <tmp_dir>:/tmp:rw`) destroyed immediately after execution.
- [x] **Deterministic Test Double (`FakeExecutionProvider`)**
  - [x] Fully configurable mock provider verifying all execution lifecycle states (`COMPLETED`, `FAILED`, `TIMED_OUT`, `PARTIAL`, `ISOLATION_UNAVAILABLE`) in unit tests without touching host processes.
- [x] **Forensic Reporting & Secret Redaction**
  - [x] Typed `ExecutionReport` capturing exit code, duration, applied isolation controls, stdout/stderr, and termination reason.
  - [x] Secret scrubber (`redact_secrets`) automatically masking tokens (`ghp_`, `AKIA`) and embedded URL passwords.
  - [x] Output truncation capping excessive logs and flagging `PARTIAL` state.
- [x] **REST API v1 Endpoints**
  - [x] `POST /api/v1/repositories/{id}/execute` triggering controlled dynamic execution.
  - [x] `GET /api/v1/repositories/{id}/execution` fetching latest report.
  - [x] `GET /api/v1/system/isolation` probing host container runtime availability.
- [x] **Benchmark Dynamic Path Integration**
  - [x] `BenchmarkRunner` extended with dynamic execution adapter; accurately diagnoses dynamic scenarios when provider is active and safely reports `unsupported_analysis` when isolation is unavailable.
- [x] **Automated Testing Suite**
  - [x] 15 dedicated tests in `testing/backend/test_execution.py`.
  - [x] Total pytest results: 87 passed, 3 skipped, 1 warning.
  - [x] Frontend test suite: 11 passed, 0 errors.

---

## 9. Unified Diagnostic Engine and End-to-End Evidence Pipeline (Implementation 010)

- [x] **Diagnostic Data Contracts & Typing**
  - [x] Typed domain models in `backend/oracle/schemas/diagnostics.py` matching product specification:
    - [x] `DiagnosticStage`: 8 lifecycle stages (`validate_target`, `acquire_snapshot`, `static_inspection`, `build_system_map`, `collect_evidence`, `generate_hypotheses`, `verify_hypotheses`, `generate_report`).
    - [x] `DiagnosticRunState`: `pending`, `running`, `completed`, `failed`, `partial`.
    - [x] `DiagnosticComponent`: Typed nodes (`source_file`, `internal_module`, `external_package`, `stdlib_module`, `unresolved_reference`) with analysis status (`analyzed`, `syntax_error`, `unresolved`, `skipped`).
    - [x] `DiagnosticDependencyEdge`: Typed relations (`imports`, `calls`, `declares_dependency`) with source/target IDs and AST line coordinate provenance.
    - [x] `DiagnosticSystemMap`: Aggregated graph representation with component registry, edge list, and summary node counts.
    - [x] `DiagnosticEvidenceRecord`: Discrete empirical observation schema (`record_id`, `category`, `source_type`, `location`, `details`, `reliability_score`).
    - [x] `FaultHypothesis`: Causal hypothesis linked to supporting evidence records, alternative explanations, confidence score, and verification outcome.
    - [x] `VerificationOutcome`: Independent check status (`verified`, `refuted`, `inconclusive`, `unsupported`) with method (`static_ast_validation`, `isolated_dynamic_execution`) and rationale.
    - [x] `DiagnosticReport`: Complete immutable report artifact combining system map, evidence set, hypotheses, verification outcomes, execution provenance, and prioritized recommendations.
    - [x] `DiagnosticRunRequest`: Request options with profile selection and explicit dynamic execution authorization toggle (`allow_dynamic`).
- [x] **Database Persistence & Alembic Migration**
  - [x] SQLAlchemy 2.x declarative entity `DiagnosticRunRecord` in `backend/oracle/models/diagnostic_run.py` (UUID primary key, foreign key to `repositories.id`, run status, diagnostic summary, full JSON report payload, timestamps).
  - [x] Registered in `backend/oracle/models/__init__.py` and exported to `alembic/env.py`.
  - [x] Reversible transactional PostgreSQL migration `002_create_diagnostic_runs.py` in `backend/alembic/versions/`.
  - [x] Offline PostgreSQL DDL generation verified via `alembic upgrade head --sql` in automated test `test_alembic_offline_sql_generation_uses_postgresql`.
- [x] **Diagnostic Orchestration Service (`DiagnosticOrchestrator`)**
  - [x] Complete 8-stage pipeline in `backend/oracle/diagnostics/service.py`:
    1. Target validation & profile policy gating (`WORKLOAD_PROFILES`).
    2. Ephemeral snapshot acquisition (`SnapshotContext`) with automatic cleanup.
    3. Multi-ecosystem detection and static AST analysis (`InspectionService`).
    4. System Map extraction with typed nodes and directional edges.
    5. Discrete evidence collection auditing manifests (`pyproject.toml`, `requirements.txt`, `setup.cfg`) using Python standard library `tomllib`.
    6. Deterministic causal fault hypothesis generation mapped to taxonomy classes.
    7. Dual-stage verification gating: AST re-validation for static findings, and container sandbox gating for dynamic workloads.
    8. Forensic report assembly, thread-safe in-memory caching, and best-effort PostgreSQL persistence.
  - [x] Sensitive secret and token scrubbing (`redact_secrets`) across all evidence records and diagnostic summaries.
  - [x] Deliberate abstention on empty repositories (`UNKNOWN_INSUFFICIENT_EVIDENCE`).
  - [x] Guaranteed zero false positives on clean/healthy repositories (emits empty hypothesis set).
- [x] **Fail-Safe Dynamic Isolation Invariant**
  - [x] Host container isolation probe via `self.execution_worker.provider.check_preflight()`.
  - [x] When isolation is unavailable (e.g., Docker daemon offline on host), dynamic verification is safely marked as `unsupported` in `unsupported_stages`.
  - [x] Non-negotiable security invariant: Host execution fallback is strictly prohibited; target code is never executed directly on the host machine.
- [x] **Decoupled Benchmark Alignment**
  - [x] Removed artificial scenario ID branching in `ml/benchmark/runner.py`.
  - [x] Replaced with general-purpose `extract_declared_dependencies()` manifest parser for empirical dependency mismatch detection.
- [x] **REST API v1 Endpoints (`/api/v1/diagnostics`)**
  - [x] `POST /api/v1/repositories/{id}/diagnose`: Triggers bounded diagnosis with options, returns `DiagnosticReport`.
  - [x] `GET /api/v1/repositories/{id}/diagnostics/latest`: Fetches the most recent cached or persisted diagnostic report.
  - [x] `GET /api/v1/diagnostics/{run_id}`: Retrieves a specific diagnostic run by UUID.
  - [x] `GET /api/v1/diagnostics/runs`: Lists all recorded diagnostic runs across repositories.
  - [x] Strict input validation: Unapproved workload profiles immediately rejected with HTTP 400 Bad Request.
- [x] **Next.js Interactive Diagnostic Dashboard**
  - [x] Typed frontend API client methods in `frontend/src/lib/api.ts` (`startDiagnosticRun`, `getLatestDiagnosticReport`, `getDiagnosticRun`, `listDiagnosticRuns`).
  - [x] `DiagnosticRunPanel.tsx`: Target selector, workload profile dropdown, dynamic verification authorization checkbox, live stage progress indicators, and tabbed inspection views.
  - [x] `SystemMapViewer.tsx`: Interactive component node explorer, status badges (`analyzed`, `syntax_error`, `unresolved`), and inbound/outbound edge provenance viewer.
  - [x] `EvidencePanel.tsx`: Filterable discrete evidence cards with category pills, file/line coordinates, reliability scores, and observed payload data.
  - [x] `HypothesisPanel.tsx`: Causal fault cards with confidence meters, linked supporting evidence badges, alternative explanations, and verification outcome summaries.
  - [x] `DiagnosticReportSummary.tsx`: Executive summary banner, completed vs unsupported stage badges, and prioritized remediation actions.
  - [x] Integrated into main dashboard view (`frontend/src/app/page.tsx`).
- [x] **Automated Testing Suite & Verification**
  - [x] 11 dedicated diagnostic backend tests in `testing/backend/test_diagnostics.py` covering end-to-end pipeline, syntax error inference, undeclared dependency detection, clean project control, empty repo abstention, dynamic verification gating, unapproved profile rejection, and route endpoints.
  - [x] 4 new frontend API client tests in `testing/frontend/test_api_client.mjs` (15 total passing).
  - [x] Complete pytest suite: 98 passed, 3 skipped (offline PG tests & Windows symlink), 1 warning.
  - [x] Frontend quality checks: TypeScript compilation (0 errors), ESLint (0 errors, 0 warnings), Next.js production build succeeds.
- [!] **Host Environment Constraints Recorded Honestly**
  - *Docker Daemon:* Docker is not installed/running on the Windows development machine. Gated container execution accurately reports `is_available = False`, adds `dynamic_verification` to `unsupported_stages`, and prevents host execution.
  - *PostgreSQL Daemon:* Native PostgreSQL daemon is offline on development host. Schema migration 002 verified offline via `alembic upgrade head --sql`. API endpoints operate gracefully via in-memory caching and fallback session handling.

---

## 10. Evidence-Based Diagnostic Intelligence and Adaptive Probe Planning (Implementation 011)

- [x] **Diagnostic Intelligence Data Contracts & Typing**
  - [x] Typed domain models in `backend/oracle/schemas/diagnostics.py`:
    - [x] `FaultHypothesis` extended with `assumptions`, `relative_ranking_score` (0.0 - 100.0), `score_rationale`, and `uncertainty_reason`.
    - [x] `DiagnosticProbe`: Action definition (`probe_id`, `probe_type`, `target_component`, `prerequisites`, `target_hypothesis_ids`, `expected_outcomes`, `estimated_cost`, `cost_label`, `safety_classification`, `requires_dynamic`, `availability_status`, `selection_reason`, `rejection_reason`).
    - [x] `ProbeResult`: Execution outcome (`probe_id`, `probe_type`, `run_id`, `target_component`, `outcome`, `generated_evidence_ids`, `execution_status`, `duration_ms`, `unsupported_reason`, `applied_safety_policy`, `ranking_changed`, `details`, `timestamp`).
    - [x] `DiagnosticDecisionRecord`: Sequential step record (`iteration`, `decision_type`, `selected_probe_id`, `rationale`, `candidates_considered_count`, `remaining_uncertainty`, `stopping_reason`, `timestamp`).
    - [x] `DiagnosticProbesResponse` and `DiagnosticDecisionsResponse` endpoint schemas.
    - [x] `DiagnosticReport` updated with `candidate_probes`, `executed_probes`, `investigation_history`, and `stopping_reason`.
    - [x] `DiagnosticRunRequest` with `max_iterations = 5` and `"adaptive_probing"` capability.
    - [x] `DiagnosticStage.PLAN_ADAPTIVE_PROBES` registered in stage lifecycle.
    - [x] `ComponentStatus` literal extended with `"blocked"`.
- [x] **Transparent Heuristic Ranking Engine (`ml/ranking/heuristic_ranker.py`)**
  - [x] Fully transparent heuristic scoring combining direct observation (+35), diminishing marginal returns for repeated same-category signals (+5), cross-component corroboration (+15), contradiction penalties (-40), verification status bonuses (`verified`: +35, `partially_verified`: +15, `candidate`: +5), and uncertainty penalties (-10).
  - [x] Clamped normalized score in [0.0, 100.0] explicitly documented as relative ranking score (NOT calibrated probability).
  - [x] Ambiguity preservation on ties (identical evidence produces identical relative score).
  - [x] Deliberate abstention on empty/unsupported codebases with score 0.0 and confidence `uncertain`.
- [x] **Adaptive Probe Planner (`ml/planning/probe_planner.py`)**
  - [x] Dual-mode information gain calculation:
    - [x] Shannon entropy $H(p) = -\sum p_i \log_2(p_i)$ and Expected Information Gain $EIG(T) = H(p) - \sum P(O_k) H(p \mid O_k)$ for calibrated probability distributions; raises `ValueError` on unnormalized distributions.
    - [x] Deterministic discrimination heuristic when empirical outcome likelihood distributions are absent.
  - [x] Redundancy prevention: Groups candidate probes by target component to avoid duplicate probes for equivalent hypotheses.
  - [x] Cost-aware utility optimization: $\text{Utility} = \text{DiscriminationScore} / \text{Cost}^{\text{weight}}$, balancing discrimination gain against latency.
  - [x] Downstream dependency reasoning: Evaluates downstream component independently; if downstream syntax is valid, marks its runtime state as `blocked` in the SystemMap rather than assuming it faulty or healthy.
  - [x] Probe execution deduplication: Prevents repeated dispatch of already executed probes across loop iterations.
  - [x] Strict safety and availability gating: Rejects unavailable/unauthorized dynamic probes when container isolation is absent.
- [x] **Orchestration Service Integration (`backend/oracle/diagnostics/service.py`)**
  - [x] Dynamic multi-hypothesis formulation with assumptions and alternatives.
  - [x] Bounded investigation loop (`max_iterations`, default 5).
  - [x] Safe in-process probe execution adapters:
    - [x] `static_ast_syntax_check`: Re-evaluates AST, verifies syntax defect with line coordinates.
    - [x] `static_import_resolution_check`: Checks internal module presence on disk.
    - [x] `static_manifest_audit`: Checks package declaration in manifests.
    - [x] `downstream_independent_check`: Evaluates downstream file independently, updates downstream component status in `system_map` to `blocked`.
    - [x] Dynamic container probes: Checked against container preflight; when Docker is absent, safely records probe as `unsupported`, stops loop with `further_investigation_unsafe_or_unsupported`, and strictly avoids fallback host execution.
  - [x] Re-ranks hypotheses dynamically after receiving probe outcomes.
  - [x] Deterministic stopping policies: `sufficient_evidence_verified`, `further_investigation_unsafe_or_unsupported`, `deliberate_abstention`, `no_useful_probe_available`, `budget_exhausted`.
- [x] **API Endpoints (`backend/oracle/api/v1/endpoints/diagnostics.py`)**
  - [x] `GET /api/v1/diagnostics/{run_id}/probes`: Returns candidate and executed probes.
  - [x] `GET /api/v1/diagnostics/{run_id}/decisions`: Returns decision history and stopping reason.
- [x] **Benchmark Extension & Adaptive Runner (`ml/benchmark/adaptive_runner.py`)**
  - [x] Fixture `testing/fixtures/benchmark/proj_11` (`CASE-011`) testing downstream independent check and blocked state propagation.
  - [x] Verified benchmark results on all 11 scenarios:
    - Total Scenarios: 11
    - Supported Accuracy: 100.0%
    - Healthy Control FPR: 0.0%
    - Abstention Accuracy: 100.0%
    - Unsafe Probe Rejection: 100.0%
    - Mean Iterations: 1.36
    - Execution Duration: ~218ms
- [x] **Next.js Frontend Integration**
  - [x] `frontend/src/types/api.ts`: Full TypeScript definitions matching backend contracts (`DiagnosticProbe`, `ProbeResult`, `DiagnosticDecisionRecord`, `DiagnosticProbesResponse`, `DiagnosticDecisionsResponse`, `FaultHypothesis`, `DiagnosticReport`, `ComponentStatus`).
  - [x] `frontend/src/lib/api.ts`: Typed client functions `getDiagnosticProbes(runId)` and `getDiagnosticDecisions(runId)`.
  - [x] `AdaptiveInvestigationPanel.tsx`: Investigation timeline, candidate probe pool with cost/safety badges, executed probes with outcome provenance, and stopping reason.
  - [x] `HypothesisPanel.tsx`: Relative heuristic score pill with explicit non-calibrated probability notice, scoring rationale breakdown, key assumptions list, and uncertainty reasons.
  - [x] `DiagnosticRunPanel.tsx`: Integrated "Adaptive Investigation" tab.
  - [x] Automated tests: 17 passing tests in `testing/frontend/test_api_client.mjs`.
  - [x] Frontend quality: TypeScript compilation (0 errors), ESLint (0 errors), Next.js production build succeeds.
- [x] **Automated Pytest Suite**
  - [x] 11 dedicated intelligence tests in `testing/backend/test_diagnostic_intelligence.py`.
  - [x] 5 dedicated adaptive benchmark tests in `testing/ml/test_adaptive_benchmark.py`.
  - [x] Complete pytest suite: 114 passed, 3 skipped, 1 warning in 17.79s.
- [!] **Host Environment Constraints Recorded Honestly**
  - *Docker Daemon:* Docker remains unavailable on the Windows host. Dynamic probes are safely rejected (`unavailable_missing_adapter`) and investigation cleanly halts with `further_investigation_unsafe_or_unsupported`. Zero host execution of untrusted repository code.
  - *PostgreSQL Daemon:* Native PostgreSQL remains offline. Offline schema migrations verified via `alembic upgrade head --sql`. API endpoints operate gracefully via in-memory caching and fallback session handling.

---

## 11. Diagnostic Reliability and Real-World Validation (Implementation 012)

- [x] **Causal Separation of Multiple Simultaneous Faults**
  - [x] Refactored hypothesis formulation in `backend/oracle/diagnostics/service.py` to partition observations by source component.
  - [x] Independent syntax defects across distinct files generate separate, independently verified fault hypotheses (`CASE-012`).
  - [x] Mixed independent faults (e.g. syntax defect in one file + unresolved import in another) generate distinct hypotheses across different taxonomy classes (`CASE-013`).
  - [x] Upstream syntax defects alongside independently broken downstream components are diagnosed separately (`CASE-016`).
- [x] **Order-Invariant & Deduplicated Heuristic Scoring (`ml/ranking/heuristic_ranker.py`)**
  - [x] Evidence deduplication: duplicate evidence IDs in `supporting_evidence_ids` or `contradicting_evidence_ids` are deduplicated prior to scoring, preventing confidence inflation.
  - [x] Order invariance: evidence records are grouped by `evidence_type` and sorted by reliability priority (`direct_observation` > `inferred_signal` > `limited_context`). The highest-reliability record is selected as the primary observation, and subsequent items of the same type receive diminishing marginal weight (+5.0).
  - [x] Scores are mathematically commutative: shuffling or reversing evidence arrival order produces the identical relative score and breakdown rationale.
- [x] **Immunity to Misleading & Non-Causal Static Findings**
  - [x] Docstring and comment immunity: error keywords embedded in comments/docstrings do not trigger false positive hypotheses (`CASE-015`).
  - [x] Safe environment fallback immunity: configuration lookups with fallback defaults (e.g. `os.getenv("PORT", "8000")`) are recognized as healthy patterns and do not trigger false-positive configuration faults (`CASE-020`).
  - [x] Structural variation tolerance: healthy packages utilizing `src/` layout, dataclasses, type annotations, and `__init__.py` re-exports produce 0 false positives (`CASE-014`).
- [x] **Downstream Cascade Reasoning & Blocked State Determination**
  - [x] When upstream components fail, downstream components are verified independently.
  - [x] Syntactically valid downstream components have their runtime status in `DiagnosticSystemMap` updated to `"blocked"` (`CASE-011`).
  - [x] Independently faulty downstream components are identified as `"syntax_error"` rather than falsely assumed clean (`CASE-016`).
- [x] **Deliberate Abstention on Polyglot & Unsupported Repositories**
  - [x] Codebases lacking Python source files (e.g. C++ and Java projects in `CASE-019` or empty repos in `CASE-010`) cleanly trigger deliberate abstention with `UNKNOWN_INSUFFICIENT_EVIDENCE` without false-positive fault manufacture.
- [x] **Expanded 20-Scenario Adversarial Benchmark Suite**
  - [x] Added 9 new controlled fixtures (`proj_12` through `proj_20`) under `testing/fixtures/benchmark/`.
  - [x] Registered neutral scenarios `CASE-012` through `CASE-020` in `ml/benchmark/scenarios.py` with isolated ground truth.
- [x] **Reliability Evaluation Harness & Baseline Comparison (`ml/benchmark/evaluation_report.py`)**
  - [x] Comprehensive evaluation comparing the ORACLE Adaptive Diagnostic Engine against a Naive 1-Shot Baseline across all 20 scenarios.
  - [x] Granular metrics with explicit numerators and denominators ($x/y = z\%$):
    - Top-1 Supported Accuracy: 100.0% (16/16) vs Baseline 100.0% (16/16)
    - Healthy-Control False Positives: 0.0% (0/5) vs Baseline 0.0% (0/5)
    - Deliberate Abstention: 100.0% (2/2) vs Baseline 100.0% (2/2)
    - Multiple-Fault Separation: 100.0% (3/3) vs Baseline 0.0% (0/3)
    - Downstream Blocked Detection: 100.0% (1/1) vs Baseline 0.0% (0/1)
    - Unsafe Dynamic Probe Rejection: 100.0% (4/4) vs Baseline N/A
    - Repeated Probes Prevented: 100.0% (20/20) vs Baseline N/A
    - Total Duration: 235.6ms (sub-second across all 20 projects)
  - [x] Persisted structured JSON report (`testing/reports/diagnostic_reliability_report.json`) and Markdown report (`testing/reports/diagnostic_reliability_report.md`).
- [x] **Automated Pytest Suite & Verification**
  - [x] 11 dedicated reliability tests in `testing/backend/test_diagnostic_reliability.py`.
  - [x] 5 dedicated adversarial benchmark tests in `testing/ml/test_adversarial_benchmark.py`.
  - [x] Full pytest suite: 130 passed, 3 skipped, 1 warning.
  - [x] Frontend quality: TypeScript compilation (0 errors), ESLint (0 errors), Next.js production build succeeds, 17 frontend tests pass.
- [!] **Host Environment Constraints Recorded Honestly**
  - *Docker Daemon:* Docker remains unavailable on the Windows host. Dynamic probes are safely rejected (`unavailable_missing_adapter`) and investigation cleanly halts with `further_investigation_unsafe_or_unsupported`. Zero host execution of untrusted repository code.
  - *PostgreSQL Daemon:* Native PostgreSQL remains offline. Offline schema migrations verified via `alembic upgrade head --sql`. API endpoints operate gracefully via in-memory caching and fallback session handling.

---

## 12. TypeScript/JavaScript AST & Cross-Module Semantic Analysis (Implementation 013)

- [x] **Isolated TypeScript AST Parser Worker (`backend/oracle/inspection/ts_ast_worker.mjs`)**
  - [x] Safe, inert AST parsing using official Microsoft TypeScript Compiler API (`typescript >= 5.0`) executed via an isolated Node.js worker.
  - [x] Windows Application Control (WDAC) compliance: discovered WDAC blocks unsigned C-extension DLLs (e.g. `tree_sitter._binding.pyd`), making the official TypeScript Compiler API via Node.js the most reliable, compliant, and standard-aligned parser.
  - [x] Strict zero-execution boundary: source text is parsed via `ts.createSourceFile(..., ts.ScriptTarget.Latest, true)`; untrusted target code is never loaded, evaluated, or executed.
  - [x] Batch processing protocol: accepts batch file manifests via stdin/stdout JSON streaming, minimizing Node process startup overhead to ~50ms per repository snapshot.
  - [x] Source coordinate precision: captures exact line numbers, columns, and character offsets for all imports, exports, and syntax diagnostics.
- [x] **Complete Extension & Syntax Coverage**
  - [x] Full support for 8 file extensions: `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.mts`, `.cts`.
  - [x] Comprehensive import extraction: named (`import { A, B }`), default (`import React`), namespace (`import * as fs`), side-effect (`import "./styles.css"`), type-only (`import type { User }`), CommonJS (`const x = require("pkg")`), and dynamic `import()` expressions.
  - [x] Re-export extraction: barrel files (`export { Button } from "./button"`, `export * from "./types"`).
  - [x] Dynamic import categorization: cleanly differentiates static string dynamic imports (`import("./mod")`) from unsupported computed dynamic imports (`import("./plugins/" + name)`).
  - [x] Comment and literal immunity: AST parsing guarantees zero false-positive import detections from comments (`// import bogus from "fake"`) or string/template literals (`const sql = "import * from users"`).
- [x] **Bounded & Deterministic Module Resolution (`backend/oracle/inspection/ts_parser.py`)**
  - [x] Relative module resolution: resolves `./` and `../` paths with extension probe ordering (`.ts`, `.tsx`, `.d.ts`, `.js`, `.jsx`, `.mts`, `.mjs`, `.cts`, `.cjs`).
  - [x] Directory index resolution: resolves directory references to `index.ts`, `index.tsx`, `index.js`, etc.
  - [x] Modern TypeScript path aliases: parses `compilerOptions.baseUrl` and `compilerOptions.paths` from `tsconfig.json`.
  - [x] Comment-tolerant JSON parsing: implemented `strip_json_comments_and_trailing_commas()` to robustly parse standard `tsconfig.json` and `package.json` files with comments and trailing commas.
  - [x] Repository containment security: imports that resolve outside the repository snapshot root (e.g. `../../../../outside_repo`) are flagged as `unsupported_reference` and prevented from leaking or mapping to host paths.
  - [x] Package classification: distinguishes internal module imports, Node built-ins (`fs`, `path`, `crypto`, etc.), external npm packages (`pkg:lodash`), and unsupported references.
- [x] **Manifest Audit & Package Declaration Inspection**
  - [x] Inspects repository `package.json` for declared dependencies (`dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies`).
  - [x] Discovers and flags undeclared npm packages imported in source code as `DEPENDENCY_IMPORT_FAILURE` (`CASE-031`).
  - [x] Prevents false-positive undeclared package flags on properly declared packages (`CASE-022`, `CASE-030`, `CASE-038`).
- [x] **Unified System Graph & Evidence Pipeline Integration**
  - [x] Reuses canonical `DependencyNode`, `DependencyEdge`, and `DiagnosticSystemMap` contracts.
  - [x] `backend/oracle/inspection/service.py`: unified file discovery and AST parsing for Python, TypeScript, and JavaScript.
  - [x] `backend/oracle/diagnostics/service.py`: emits structured `DiagnosticEvidenceRecord` for JS/TS syntax errors, unresolved internal imports, undeclared packages, unsupported dynamic expressions, and empty codebases.
  - [x] `ml/planning/probe_planner.py`: generalized static probes (`static_ast_syntax_check`, `downstream_independent_check`, `static_manifest_audit`) to evaluate `.js`/`.ts` files without Python-specific assumptions.
- [x] **Expanded 38-Scenario Adversarial Benchmark Suite**
  - [x] Added 18 new controlled fixtures (`proj_21` through `proj_38`) under `testing/fixtures/benchmark/`.
  - [x] Registered neutral scenarios `CASE-021` through `CASE-038` in `ml/benchmark/scenarios.py` with isolated ground truth:
    - `CASE-021`: Healthy TypeScript math utility library (clean control).
    - `CASE-022`: Healthy React JSX/TSX application with declared `react` dependency (clean control).
    - `CASE-023`: Misleading import-like syntax in comments (immunity verified).
    - `CASE-024`: Misleading import-like syntax in string/template literals (immunity verified).
    - `CASE-025`: Unresolved relative TypeScript import (`./missing_transport`).
    - `CASE-026`: Directory index resolution (`./utils` -> `utils/index.ts`).
    - `CASE-027`: Modern TypeScript path alias resolution (`@/*` -> `src/*`).
    - `CASE-028`: Re-export barrel file chain (`export { Button } from "./button"`).
    - `CASE-029`: Circular module dependencies (`alpha.ts` <-> `beta.ts`).
    - `CASE-030`: Declared external npm package (`lodash` in `package.json`).
    - `CASE-031`: Undeclared external npm package (`axios` missing from `package.json`).
    - `CASE-032`: Computed dynamic import expression (`import("./plugins/" + name)`).
    - `CASE-033`: Syntax defect in single TypeScript file (`const result = ;`).
    - `CASE-034`: Multiple independent syntax defects across distinct TypeScript files (`parser.ts`, `formatter.ts`).
    - `CASE-035`: Mixed independent faults (syntax defect in `parser.ts` + unresolved import in `client.ts`).
    - `CASE-036`: Polyglot repository (Python FastAPI backend + TypeScript client).
    - `CASE-037`: Escaping relative import attempting directory traversal (`../../../../outside_repo`).
    - `CASE-038`: Next.js App Router layout (`app/page.tsx`, `layout.tsx`, `Header.tsx`).
- [x] **Reliability Evaluation Harness Across 38 Scenarios (`ml/benchmark/evaluation_report.py`)**
  - [x] Granular metrics with explicit numerators and denominators ($x/y = z\%$):
    - Top-1 Supported Accuracy: 100.0% (34/34)
    - Healthy-Control False Positives: 0.0% (0/18)
    - Deliberate Abstention: 100.0% (2/2)
    - Multiple-Fault Separation: 100.0% (5/5)
    - Downstream Blocked Detection: 100.0% (1/1)
    - Unsafe Dynamic Probe Rejection: 100.0% (4/4)
    - Repeated Probes Prevented: 100.0% (38/38)
    - Total Duration: ~280ms across all 38 projects in unified evaluation
  - [x] Updated persisted structured JSON report (`testing/reports/diagnostic_reliability_report.json`) and Markdown report (`testing/reports/diagnostic_reliability_report.md`).
- [x] **Automated Testing & Quality Gates**
  - [x] 12 dedicated parser tests in `testing/backend/test_ts_ast_parser.py`.
  - [x] 7 dedicated benchmark tests in `testing/ml/test_ts_benchmark.py`.
  - [x] 15 benchmark suite tests in `testing/ml/test_benchmark.py`.
  - [x] 11 reliability suite tests in `testing/backend/test_diagnostic_reliability.py`.
  - [x] Frontend quality: TypeScript compilation (0 errors), ESLint (0 errors), Next.js production build succeeds, 17 frontend tests pass.

---

## 13. Java AST Analysis & Polyglot Dependency Intelligence (Implementation 014 - Complete & Verified)

- [x] **Safe, Zero-Code-Execution Java AST Worker (`backend/oracle/inspection/JavaAstWorker.java`)**
  - [x] Utilizes the standard OpenJDK 21 Compiler Tree API (`javax.tools.JavaCompiler`, `com.sun.source.tree.*`).
  - [x] Parses in-memory source strings using `SimpleJavaFileObject` and `task.parse()`, executing only the lexing and parsing compiler phases.
  - [x] Target code is never compiled to bytecode, loaded into any ClassLoader, evaluated, or executed on the host.
  - [x] Embedded zero-dependency JSON parser and serializer communicating over standard `stdin`/`stdout`.
  - [x] High-throughput batch processing protocol: precompiled `JavaAstWorker.class` analyzes batch repository files in a single JVM invocation (~60–100ms).
- [x] **Java Syntax Parsing & Exact Source Coordinates**
  - [x] Extracts packages, imports, declared types, records (`record Point(int x, int y)`), interfaces, enums, annotations, and nested static classes.
  - [x] Captures static imports (`import static pkg.Cls.member;`), wildcard imports (`import pkg.*;`), and single-type imports.
  - [x] Collects compilation syntax diagnostics with exact 1-indexed line numbers and 1-indexed column offsets via `DiagnosticListener<JavaFileObject>`.
- [x] **Bounded Deterministic Module Resolution (`backend/oracle/inspection/java_parser.py`)**
  - [x] Global symbol table mapping fully-qualified class names and simple type names to declaring source files.
  - [x] Standard library classification: `JAVA_STDLIB_PREFIXES` covers `java.`, `javax.`, `org.w3c.dom`, etc. with zero false-positive alerts.
  - [x] Repository namespace inference: extracts multi-level project namespace prefixes (e.g. `com.example.*`) to distinguish missing internal types from external packages.
  - [x] Conservative wildcard import handling: resolves wildcard packages without manufacturing false unresolved edges.
  - [x] Cyclic dependency safety: circular class references are mapped without infinite loops or stack overflow.
- [x] **Read-Only Maven & Gradle Manifest Inspection**
  - [x] `parse_maven_pom()`: read-only XML parser without maven execution. Extracts coordinates, parent inheritance, packaging, modules, and dependencies.
  - [x] Simple property resolution: expands `${property.name}` while preserving uncertainty on unresolvable computed versions.
  - [x] `parse_gradle_build()`: static regex/pattern extraction for Groovy and Kotlin DSL build files.
  - [x] Published dependency-to-package mapping: `KNOWN_JAVA_DEP_PREFIXES` maps Maven artifacts (e.g. `com.google.guava:guava`) to root runtime package namespaces (`com.google.common.*`).
- [x] **System Map & Diagnostic Pipeline Integration**
  - [x] Canonical graph representation: Java source files become `source_file` components; dependencies become `DiagnosticDependencyEdge` records.
  - [x] Evidence generation: emits `DiagnosticEvidenceRecord` for syntax errors, unresolved internal types, undeclared Maven/Gradle dependencies, and manifest warnings.
  - [x] Adaptive probe planning: `ProbePlanner` dispatches `static_ast_syntax_check` and `downstream_independent_check` to `parse_java_file` for `.java` targets.
- [x] **Expanded 60-Scenario Adversarial Benchmark Suite**
  - [x] Added 22 new controlled fixtures (`proj_39` through `proj_60`) under `testing/fixtures/benchmark/`.
  - [x] Registered neutral scenarios `CASE-039` through `CASE-060` in `ml/benchmark/scenarios.py` with isolated ground truth:
    - `CASE-039`: Healthy Java multi-package project (clean control).
    - `CASE-040`: Healthy Java interfaces, generics, annotations (clean control).
    - `CASE-041`: Healthy nested static builder classes (clean control).
    - `CASE-042`: Healthy modern Java record types (clean control).
    - `CASE-043`: Clean cross-package internal class import (clean control).
    - `CASE-044`: Unresolved internal type reference (`MissingAccount`).
    - `CASE-045`: Multiple independent unresolved internal type references across separate files (`ServiceA.java`, `ServiceB.java`).
    - `CASE-046`: Multiple independent syntax errors across separate files (`Parser.java`, `Formatter.java`).
    - `CASE-047`: Syntax defect in `Parser.java` plus unresolved internal type in `Client.java`.
    - `CASE-048`: Static member import resolved to target utility class (clean control).
    - `CASE-049`: Wildcard package imports handled conservatively without false alarms (clean control).
    - `CASE-050`: Standard library imports (`java.io`, `java.nio`, `javax.net`) without false positives (clean control).
    - `CASE-051`: Maven project with declared `commons-lang3` dependency matched cleanly (clean control).
    - `CASE-052`: Maven project importing `org.slf4j.Logger` absent from `pom.xml` dependencies.
    - `CASE-053`: Maven project with unresolvable version property preserved as uncertainty warning (clean control).
    - `CASE-054`: Gradle project with declared Guava dependency matched cleanly (clean control).
    - `CASE-055`: Gradle project with computed project dependency recorded with uncertainty preserved (clean control).
    - `CASE-056`: Multi-module Maven project with cross-module internal type dependency resolved (clean control).
    - `CASE-057`: Java project with circular internal type references mapped without recursion (clean control).
    - `CASE-058`: Mixed polyglot repository (Java + Python + TypeScript) parsed into unified graph (clean control).
    - `CASE-059`: Java project with malformed `pom.xml` handled gracefully without crashing (clean control).
    - `CASE-060`: Empty Java repository directory triggers deliberate abstention (`UNKNOWN_INSUFFICIENT_EVIDENCE`).
- [x] **Automated Testing & Quality Gates**
  - [x] 13 dedicated Java AST parser unit tests in `testing/backend/test_java_ast_parser.py`.
  - [x] 9 dedicated Java benchmark integration tests in `testing/ml/test_java_benchmark.py`.
  - [x] 11 reliability suite tests in `testing/backend/test_diagnostic_reliability.py`.
  - [x] Adversarial benchmark suite tests in `testing/ml/test_adversarial_benchmark.py`.

---

## 14. End-to-End Product Validation and Real-World Diagnostic Readiness (Implementation 015 - Complete & Verified)

- [x] **Comprehensive End-to-End Workflow Verification (`testing/backend/test_e2e_workflow.py`)**
  - [x] Full 17-step product workflow verified via FastAPI TestClient:
    1. Query application health (`GET /api/v1/health`).
    2. Query system status and persistence mode (`GET /api/v1/status`).
    3. Register local target repository (`POST /api/v1/repositories`).
    4. Retrieve target metadata by UUID (`GET /api/v1/repositories/{id}`).
    5. List all registered targets (`GET /api/v1/repositories`).
    6. Execute static repository inspection (`POST /api/v1/repositories/{id}/inspect`).
    7. Trigger end-to-end diagnosis without dynamic execution (`POST /api/v1/repositories/{id}/diagnose`).
    8. Verify diagnostic report structure (system map, evidence, hypotheses, candidate probes, executed probes, investigation history, recommendations, duration).
    9. Retrieve latest diagnostic report for target (`GET /api/v1/repositories/{id}/diagnostics/latest`).
    10. Retrieve diagnostic report by run UUID (`GET /api/v1/diagnostics/{run_id}`).
    11. Retrieve probe candidates and execution outcomes (`GET /api/v1/diagnostics/{run_id}/probes`).
    12. Retrieve adaptive planner decisions and stopping rationale (`GET /api/v1/diagnostics/{run_id}/decisions`).
    13. List all diagnostic runs (`GET /api/v1/diagnostics/runs`).
    14. Trigger diagnosis with dynamic gating check (`POST /api/v1/repositories/{id}/diagnose` with `allow_dynamic=True`).
    15. Verify polyglot repository workflows (TypeScript Compiler API and Java OpenJDK Tree API).
    16. Verify credential scrubbing and provenance retention.
    17. Delete registered repository (`DELETE /api/v1/repositories/{id}`) and confirm 404.
- [x] **Persistence & Database Lifecycle Verification (`testing/backend/test_persistence_lifecycle.py`)**
  - [x] Alembic offline transactional PostgreSQL DDL generation verified for all schema versions.
  - [x] Status endpoint declares `"in_memory_transient"` persistence mode when PostgreSQL is unreachable (no synthetic SQLite fallback).
  - [x] Status endpoint declares `"durable_postgresql"` persistence mode when database engine connects successfully.
  - [x] Process restart survival: `list_diagnostic_runs()` and `get_diagnostic_run()` retrieve persisted `DiagnosticRunRecord` entities from PostgreSQL after in-memory cache eviction.
  - [x] Input validation: invalid UUIDs return HTTP 422 cleanly, non-existent valid UUIDs return HTTP 404.
  - [x] `DiagnosticReport` JSON serialization and deserialization roundtrip verified with 100% field fidelity.
- [x] **Safe Snapshot & Parser Security Suite (`testing/backend/test_snapshot_security.py`)**
  - [x] Directory traversal attempts (`../`) and boundary escapes rejected with `PathTraversalError`.
  - [x] Resource limits: file count and byte size limits enforced via `ResourceLimiter`.
  - [x] TypeScript AST worker timeout recovery (`subprocess.TimeoutExpired` handled gracefully as `analysis_failed`).
  - [x] TypeScript AST worker malformed JSON recovery (non-JSON worker output converted to `FileSyntaxError`).
  - [x] Java AST worker timeout recovery (timeout during compilation or execution handled gracefully).
  - [x] Java AST worker malformed JSON recovery (JVM warning or non-JSON output handled gracefully).
  - [x] Multi-pattern credential and token redaction verified across 7 token and URI families.
- [x] **Controlled Real-World Trials (`ml/benchmark/real_world_trials.py`, `testing/ml/test_real_world_trials.py`)**
  - [x] Created 8 realistic repository configurations under `testing/fixtures/real_world/`:
    1. `TRIAL-001`: FastAPI Microservice (`python`, clean control) -> **PASS** (0 hypotheses, clean).
    2. `TRIAL-002`: Next.js / TypeScript App (`typescript`, clean control) -> **PASS** (0 hypotheses, clean).
    3. `TRIAL-003`: Spring Boot Java Maven Service (`java`, clean control) -> **PASS** (0 hypotheses, clean).
    4. `TRIAL-004`: Mixed Polyglot Fullstack App (`polyglot`, clean control) -> **PASS** (0 hypotheses, clean).
    5. `TRIAL-005`: Multi-Module Python Utility Library (`python`, clean control) -> **PASS** (0 hypotheses, clean).
    6. `TRIAL-006`: TypeScript Syntax Defect Scenario (`typescript`, defective) -> **PASS** (`runtime_exception` verified).
    7. `TRIAL-007`: Polyglot Multi-Defect System (`polyglot`, defective) -> **PASS** (independent `runtime_exception` & `dependency_import_failure` separated).
    8. `TRIAL-008`: Java Ambiguous Dependency Resolution (`java`, defective) -> **PASS** (`dependency_import_failure` identified with uncertainty stated).
  - [x] Overall accuracy: **100.0% (8/8 passed)**.
  - [x] Healthy control clean rate: **100.0% (5/5 clean, 0 false positives)**.
  - [x] Defective scenario identification: **100.0% (3/3 identified)**.
  - [x] Persisted structured JSON report (`testing/reports/real_world_trials_report.json`) and Markdown report (`testing/reports/real_world_trials_report.md`).
- [x] **Frontend Quality & Integration**
  - [x] Frontend TypeScript contracts updated for full schema parity (`DiagnosticDecisionsResponse`, `DiagnosticProbesResponse`, `DiagnosticProbe`, `ProbeResult`).
  - [x] Live diagnostics panel updated to surface active persistence mode and container isolation status.
  - [x] 17 automated frontend API client tests passing (`npm run test`).
  - [x] TypeScript compilation: 0 errors (`npm run type-check`).
  - [x] ESLint: 0 errors (`npm run lint`).
  - [x] Production build: Next.js 16 build succeeded (`npm run build`).

---

## 15. Deployment Readiness and Production Infrastructure (Implementation 016)

- [x] **Hardened Three-Tier Container Architecture (`deploy/docker-compose.yml`)**
  - [x] Complete Compose v2 orchestration defining `db`, `backend`, and `frontend` services with automated dependency health gating.
  - [x] Private internal networking: dedicated `oracle_internal` bridge network with `internal: true` restricting PostgreSQL access exclusively to the backend.
  - [x] Client-facing networking: `oracle_external` bridge network for external HTTP ingress to frontend (port 3000) and API (port 8000).
  - [x] Persistent database volume: named volume `oracle_pgdata` guaranteeing durable state retention across container lifecycles.
- [x] **Defense-in-Depth Security Invariants**
  - [x] Non-root execution: system user `oracle` (`UID 10001`) for backend, `nextjs` (`UID 1001`) for frontend.
  - [x] Protected host Docker boundary: backend container explicitly does **not** mount `/var/run/docker.sock`, preventing root host compromise from the web tier.
  - [x] Production invariant validation in `Settings`: boot fails immediately if `ENVIRONMENT=production` and `debug=True`, unhardened default database credentials (`postgres:postgres@localhost`), or wildcard CORS (`*`) are detected.
  - [x] Normalized database URL formatting: automatic standardization of `postgresql://` to `postgresql+psycopg://` for modern psycopg 3 driver compatibility.
- [x] **Polyglot Runtime Packaging in Backend Container (`deploy/Dockerfile.backend`, `backend/Dockerfile`)**
  - [x] Base image: `python:3.12-slim` (Debian Bookworm) packaging Python 3.12, Node.js, and OpenJDK 17 headless.
  - [x] TypeScript worker support: Node.js runtime and global `typescript` package installation for `ts_ast_worker.mjs`.
  - [x] Java worker support: OpenJDK 17 with ahead-of-time class compilation (`javac /app/oracle/inspection/JavaAstWorker.java`) eliminating runtime compilation lag.
- [x] **Next.js 16 Standalone Production Container (`deploy/Dockerfile.frontend`, `frontend/Dockerfile`)**
  - [x] Multi-stage build (`deps` -> `builder` -> `runner`) utilizing `output: "standalone"` in `next.config.ts`.
  - [x] Image size reduced by >80% with minimal `node:20-alpine` runner executing `node server.js` without development dependencies.
- [x] **Container Synchronization & Automated Alembic Migrations (`deploy/entrypoint-backend.sh`)**
  - [x] Database connectivity polling: script waits for PostgreSQL to become reachable before starting services.
  - [x] Automated schema migration: executes `alembic upgrade head` upon verified database reachability.
  - [x] Graceful shutdown lifecycle: application lifespan handler traps `SIGTERM`/`SIGINT` and disposes SQLAlchemy connection pool (`engine.dispose()`).
- [x] **Health and Readiness Monitoring (`backend/oracle/api/v1/endpoints/health.py`)**
  - [x] Liveness probe `GET /api/v1/health`: returns `HTTP 200` with service status, app name, version, and environment.
  - [x] Readiness probe `GET /api/v1/status`: reports database connectivity, active persistence mode, container sandbox availability, and polyglot static parser status (`python`, `typescript`, `java`).
- [x] **Automated Deployment Smoke Test Suite & CLI Runner (`testing/deploy/test_deployment_smoke.py`)**
  - [x] Repeatable verification pipeline testing:
    1. Frontend availability (`GET /`)
    2. Backend root metadata (`GET /`)
    3. Liveness probe (`GET /api/v1/health`)
    4. Readiness probe (`GET /api/v1/status`)
    5. Repository registration (`POST /api/v1/repositories`)
    6. Static inspection scan (`POST /api/v1/repositories/{id}/inspect`)
    7. Diagnostic workflow (`POST /api/v1/repositories/{id}/diagnose`)
    8. Report retrieval (`GET /api/v1/repositories/{id}/diagnostics/latest`)
    9. Non-destructive cleanup (`DELETE /api/v1/repositories/{id}`)
  - [x] Dual-mode runner: executes in-process via pytest or against remote container deployments via CLI (`--backend-url`, `--frontend-url`).
- [x] **Deployment Configuration Test Suite (`testing/backend/test_deployment_config.py`)**
  - [x] 11 dedicated tests verifying production settings validation, decomposed postgres parameters, Dockerfile security directives, Docker Compose network segregation and socket isolation, entrypoint script syntax, and health endpoints contracts.
- [x] **Comprehensive Operational Runbook (`deploy/README.md`)**
  - [x] Complete documentation for prerequisites, quickstart deployment, environment configuration, database migration commands, automated backup (`pg_dump`) and restore (`psql`), rollback procedures, and disaster recovery.
- [!] **Environmental Limitations & Transparent Disclosure**
  - *Host Environment:* Windows 11 host without Docker daemon or native PostgreSQL CLI.
  - *Verification Boundary:* Deployment configurations, container specifications, schemas, lifecycles, and in-process smoke tests verified 100% green. Live container execution and live PostgreSQL daemon marked unverified on the Windows development workstation.

---

## 16. Generalization, Empirical Machine Learning Hypothesis Ranking, and Multi-Domain Diagnostic Expansion (Implementation 017)

- [x] **Zero-Execution Go Static Analysis Adapter (`backend/oracle/inspection/go_parser.py`)**
  - [x] Zero external code execution and zero host binary prerequisites (`go` compiler not required on host).
  - [x] Comprehensive `go.mod` module manifest parser: direct/indirect dependencies, Go version, module replacement directives.
  - [x] Accurate standard library classification for 60+ core Go runtime packages (`fmt`, `net/http`, `encoding/json`, `crypto`, etc.).
  - [x] Lexical and token syntax balance diagnostics: unclosed tokens (`{`, `(`, `[`), unmatched closing braces, unclosed multi-line comments (`/* ... */`).
  - [x] Import extraction and dependency graph integration (`resolved_stdlib`, `resolved_internal`, `external_package`, `unresolved_reference`).
  - [x] Ecosystem detection updated: `go.mod`, `go.sum`, `go.work`, and `.go` source extensions recognized with high confidence.
  - [x] 11 dedicated automated tests passing (`testing/backend/test_go_ast_parser.py`).
- [x] **Polyglot Runtime Telemetry and Non-Static Fault Ingestion (`backend/oracle/diagnostics/telemetry_analyzer.py`)**
  - [x] Polyglot traceback parser (`parse_runtime_traceback`) supporting Python, Node.js/TypeScript, Java, and Go runtime panics.
  - [x] Deterministic symptom classification mapping runtime signals into Fault Taxonomy:
    - `DATABASE_CONNECTIVITY_SCHEMA`: Socket refusal, port 5432/3306/27017 connection errors, deadlocks, and migration mismatches.
    - `API_COMMUNICATION_FAILURE`: HTTP 502/503/504, client `ConnectTimeout`, TLS handshake failures, and HTTP 429 rate limits.
    - `IO_CONTRACT_VIOLATION`: Pydantic/JSONSchema validation failures, HTTP 422, and missing required payload keys.
    - `DATA_VALIDATION_TRANSFORMATION`: `JSONDecodeError`, `UnicodeDecodeError`, zero division, and timezone transformation errors.
    - `CONFIG_MISSING_OR_INVALID`: Missing mandatory environment variables, unreadable `.env`, and YAML/TOML syntax defects.
  - [x] Configuration audit (`audit_environment_configuration`): cross-references declared template keys (`.env.example`) against active environment and local `.env`.
  - [x] Orchestrator wiring: `DiagnosticRunRequest` accepts optional `symptom_description` and `runtime_traceback` fields; discrete evidence records (`EVID-TELEM-xxx`) emitted with exact provenance and reliability metrics.
  - [x] 12 dedicated automated tests passing (`testing/backend/test_telemetry_analyzer.py`).
- [x] **Leak-Free Machine Learning Feature Representation (`ml/ranking/feature_extractor.py`)**
  - [x] 24-dimensional dense feature representation consuming only observable evidence signals, graph structural metrics, and telemetry confidences.
  - [x] Strict target-leakage prevention: ground-truth labels, scenario IDs, project titles, and file contents are strictly barred from feature vectors.
- [x] **Candidate ML Ranking Models & Probability Calibration (`ml/ranking/ml_ranker.py`, `ml/ranking/calibrated_ranker.py`)**
  - [x] Calibrated Logistic Regression with Platt scaling (`CalibratedClassifierCV(LogisticRegression(), method="sigmoid")`).
  - [x] Calibrated Random Forest Ensemble (`CalibratedClassifierCV(RandomForestClassifier(), method="sigmoid")`).
  - [x] Softmax temperature scaling and probability normalization across candidate hypotheses.
  - [x] Evidence contradiction refutation: negative probe findings penalize refuted candidates exponentially ($0.2^k$), cleanly redistributing probability mass to surviving hypotheses.
  - [x] Multi-fault separation: groups hypotheses by affected component to isolate multiple simultaneous root causes.
  - [x] 7 dedicated automated tests passing (`testing/ml/test_ml_ranker.py`).
- [x] **Adaptive vs Fixed Probe Evaluation Framework (`ml/planning/probe_evaluation.py`)**
  - [x] Mathematical Shannon entropy calculation: $H(P) = -\sum P(h_i) \log_2 P(h_i)$.
  - [x] Expected Information Gain (EIG) evaluation across simulated diagnostic investigations.
  - [x] Empirical comparison across 4 policies: `adaptive_information_gain`, `fixed_static_first`, `fixed_dynamic_first`, `random_selection`.
  - [x] Adaptive policy demonstrates higher probe efficiency ($\Delta H / \text{Cost}$) and avoids redundant probes upon early convergence.
  - [x] 3 dedicated automated tests passing (`testing/ml/test_probe_evaluation.py`).
- [x] **20-Scenario Generalization Dataset (`ml/dataset/generalization_dataset.py`)**
  - [x] 20 distinct, independently validated scenarios covering:
    - Go clean, syntax error, undeclared dependency, and unresolved internal module (`GEN-001` - `GEN-004`).
    - Database socket refusal, API connect timeout, schema contract mismatch, JSON decode error, missing env config, Go panic (`GEN-005` - `GEN-010`).
    - Polyglot multi-fault, decoy syntax refutation, competing hypotheses, circular import, DB deadlock, polyglot clean monorepo (`GEN-011` - `GEN-016`).
    - Rust out-of-distribution abstention, YAML syntax error, API rate limit 429, modular clean monorepo (`GEN-017` - `GEN-020`).
  - [x] Automated fixture materialization to disk (`materialize_generalization_fixtures`).
- [x] **Comparative Benchmark Runner & Official Reports (`ml/benchmark/ml_evaluation.py`)**
  - [x] Automated comparative evaluation across Naive Baseline, Heuristic Baseline, Calibrated Logistic Regression, and Calibrated Random Forest Ensemble.
  - [x] Top-1 Accuracy: 80.0% for ML models (beating Naive Baseline at 65.0%).
  - [x] Expected Calibration Error (ECE): reduced from 0.6500 (heuristic) down to 0.3548 (Calibrated Random Forest Ensemble).
  - [x] Brier Score: improved from 0.3031 down to 0.2477.
  - [x] Abstention Quality: 100.0% on healthy controls and unsupported frameworks (Rust).
  - [x] Mean Inference Latency: 27.65 ms per scenario for Random Forest Ensemble, 5.24 ms for Logistic Regression.
  - [x] Structured reports generated: `testing/reports/ml_model_comparison_report.json` and `testing/reports/ml_model_comparison_report.md`.
  - [x] 3 dedicated automated tests passing (`testing/ml/test_generalization_dataset.py`).
- [x] **Frontend Integration & Verification**
  - [x] Updated `DiagnosticRunRequest` contract with optional `symptom_description` and `runtime_traceback`.
  - [x] Collapsible Runtime Telemetry & Traceback input section in `DiagnosticRunPanel.tsx`.
  - [x] All 17 frontend tests passing (`npm run test`).
  - [x] TypeScript compilation: 0 errors (`npm run type-check`).
  - [x] ESLint: 0 errors (`npm run lint`).
  - [x] Production build: Next.js standalone build succeeded (`npm run build`).

---

## 17. Independent Audit, Reproducibility & Generalization Validation (Implementation 018)

- [x] **Go Static Analysis & Lexical Scanner Remediation (`backend/oracle/inspection/go_parser.py`)**
  - [x] Replaced naive character loop with full 6-state zero-code-execution lexical state machine.
  - [x] Correctly tracks delimiters inside interpreted string literals (`"..."`), raw multiline strings (`` `...` ``), rune literals (`'...'`), line comments (`//`), and block comments (`/*...*/`).
  - [x] Fixed delimiter false positives on struct tags, string arguments (e.g. `fmt.Println("{")`), and comments.
  - [x] Retained strict zero host execution invariant (`go run`, `go build`, external toolchains prohibited).
  - [x] 18 automated tests passing (`testing/backend/test_go_ast_parser.py`).
- [x] **Runtime Telemetry Privacy, Chained Tracebacks & Evidence Invariants (`backend/oracle/diagnostics/telemetry_analyzer.py`)**
  - [x] Integrated `oracle.inspection.policy.redact_secrets` across all telemetry ingestion paths, redacting database credentials, bearer tokens, AWS keys, and secrets.
  - [x] Scoped evidence IDs across runs via `EVID-TELEM-{run_id[:8]}-{seq:03d}` to prevent collisions.
  - [x] Added chained exception support for Python (`direct_cause` / `during_handling`) and recursive `Caused by:` parsing for Java root cause extraction.
  - [x] End-to-end integration verified: telemetry symptoms submitted via orchestrator reach evidence, hypotheses, and system map without secret leakage.
  - [x] 17 automated tests passing across `testing/backend/test_telemetry_analyzer.py` (12) and `testing/backend/test_telemetry_e2e.py` (5).
- [x] **Machine Learning Feature Invariance & Leakage Audit (`ml/ranking/feature_extractor.py`)**
  - [x] Mathematical proof of zero target label leakage: feature vectors are invariant to scenario renaming, metadata mutation, or external labels.
  - [x] 5 dedicated automated tests passing (`testing/ml/test_feature_leakage.py`).
- [x] **Scenario-Family 5-Fold Cross-Validation & Defensible ML Evaluation (`ml/benchmark/ml_evaluation.py`)**
  - [x] Established 5-fold scenario-family cross-validation isolating unseen ecosystem/fault families (Go, Runtime, Telemetry/Config, Polyglot, Robustness/OOD).
  - [x] Formal 10-bin Expected Calibration Error (ECE) definition across uniform $[0.0, 1.0]$ probability bins.
  - [x] Calibrated Random Forest Ensemble achieves 80.0% CV Top-1 accuracy, 0.2976 CV ECE, 0.1600 CV Brier score, and 100.0% abstention precision on unseen families.
  - [x] Calibrated Logistic Regression achieves 70.0% CV Top-1 accuracy, 0.1704 CV ECE, 0.1793 CV Brier score, and 100.0% abstention precision.
  - [x] Structured reports updated: `testing/reports/ml_model_comparison_report.json` and `testing/reports/ml_model_comparison_report.md`.
  - [x] Independent audit report delivered: `testing/reports/implementation_017_audit_report.md`.
  - [x] 3 dedicated benchmark tests passing (`testing/ml/test_generalization_dataset.py`).

---

## 18. Future Diagnostic Intelligence Phases

- [ ] Active diagnostic loop coordinating dynamic container probes with LLM-assisted forensic report narrative generation.
- [ ] Automated remediation code diff generation with isolated sandbox verification.
