# ORACLE Architecture

## 1. System Overview

ORACLE is an extensible platform engineered to inspect software systems, isolate faults, test components independently, and generate evidence-backed diagnoses.

The platform is designed as a **modular monolith** with strict boundaries between layers. It prioritizes clarity, maintainability, and security over distributed complexity.

```mermaid
flowchart TD
    Client["Client / Browser"]
    Frontend["Next.js Frontend (TypeScript, Tailwind CSS)"]
    APIClient["Typed API Client (frontend/src/lib/api.ts)"]
    API["FastAPI HTTP API (Python, Pydantic)"]
    Router["API v1 Router (/api/v1)"]
    CoreConfig["Core Settings (pydantic-settings)"]
    DiagEngine["Diagnostic & Fault Isolation Logic (Future)"]
    DBLayer["Database Layer (SQLAlchemy 2.x, psycopg 3)"]
    AlembicRunner["Alembic Migration Runner (env.py)"]
    Postgres[("PostgreSQL Database (Port 5432)")]

    Client --> Frontend
    Frontend --> APIClient
    APIClient -->|"HTTP / REST API Contracts (JSON)"| API
    API --> Router
    Router --> CoreConfig
    Router --> DiagEngine
    Router --> DBLayer
    DBLayer -->|"TCP (postgresql+psycopg)"| Postgres
    AlembicRunner -->|"Schema Migrations / DDL"| Postgres
    AlembicRunner -.->|"Reads Models"| DBLayer
    AlembicRunner -.->|"Reads Database URL"| CoreConfig
```

---

## 2. Technology Baseline & Language Allocation

In alignment with the **Polyglot Engineering Policy**:

| Layer / Responsibility | Technology | Justification |
| :--- | :--- | :--- |
| **Frontend UI** | TypeScript, Next.js (App Router), Tailwind CSS v4 | Type-safe browser state, responsive component rendering, and developer ergonomics without heavy runtime dependencies. |
| **Backend & Orchestration** | Python 3.14+, FastAPI, Pydantic, SQLAlchemy 2.x | High-performance asynchronous API framework, strict data validation models, and rich ecosystem for diagnostic planning. |
| **Database & Migrations** | PostgreSQL, psycopg 3, Alembic | ACID-compliant relational persistence, native connection pooling, and strict schema version control. |
| **ML Research & Evaluation** | Python, Pydantic, Fault Taxonomy, Local MLflow | Reproducible diagnostic experiment schema, target-leakage prevention, group-aware cross-validation, and calibrated evaluation. |
| **Testing** | pytest, node:test, httpx, TestClient | Automated unit, integration, and diagnostic probe testing isolated in `testing/`. |
| **Future Polyglot Inspectors** | Java (JVM tools), C++ (native profiling) | Dedicated language inspectors will connect through explicit contracts (HTTP/CLI/IPC) only when concrete diagnostic capabilities justify them. |

---

## 3. Clean Architecture Subfolder Policy & Repository Structure

To ensure long-term maintainability, clean boundaries, and zero root-directory pollution, ORACLE enforces the **Subfolder Isolation Policy**:

- **Every file must belong to its assigned subfolder.** No loose code, tests, or documentation files may reside in the main root directory (except necessary VCS configs such as `.gitignore`).
- **All documentation files (`*.md`)** reside in [`doc/`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/doc).
- **All automated testing files** reside in [`testing/`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/testing).
- **All backend service code and configs** reside in [`backend/`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend).
- **All frontend user interface code** resides in [`frontend/`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/frontend).
- **Future Sections (e.g. `ml/`):** When introducing a new domain or capability (e.g., machine learning pipelines), a dedicated subfolder must be created at the root level (e.g., `ml/`), and all files belonging to that domain must be kept exclusively within that subfolder.

```
ORACLE/
├── .gitignore
├── backend/                  # Backend implementation & service configs
│   ├── alembic/              # Alembic schema migration environment & revisions
│   │   ├── env.py            # Alembic runtime execution script
│   │   ├── script.py.mako    # Revision file template
│   │   └── versions/         # Migration script history
│   │       └── 001_create_repositories.py # Reversible DDL creating repositories table
│   ├── alembic.ini           # Alembic migration configuration
│   ├── pyproject.toml        # Backend build system & dependency configuration
│   ├── requirements.txt      # Production pinned dependencies
│   ├── requirements-dev.txt  # Testing and development dependencies
│   ├── .env.example          # Environment variable template
│   └── oracle/
│       ├── __init__.py       # Package metadata and version definition
│       ├── main.py           # FastAPI application instantiation, CORS, and lifespan
│       ├── core/
│       │   ├── __init__.py
│       │   └── config.py     # Pydantic BaseSettings for environment configuration
│       ├── db/
│       │   ├── __init__.py
│       │   ├── base.py       # DeclarativeBase model registry for SQLAlchemy 2.x
│       │   └── session.py    # Engine factory, sessionmaker, and connectivity probes
│       ├── models/
│       │   ├── __init__.py
│       │   └── repository.py # Repository SQLAlchemy 2.x declarative entity
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── repository.py # RepositoryCreate and RepositoryResponse Pydantic schemas
│       │   ├── inspection.py # InspectionOptions and InspectionReport schemas
│       │   └── execution.py  # ExecutionRequest and ExecutionReport schemas
│       ├── inspection/       # Static code ingestion & sandboxed inspection worker
│       │   ├── __init__.py
│       │   ├── policy.py     # File/dir exclusions, resource limits, secret redactor
│       │   ├── snapshot.py   # Local path containment & shallow git clone adapters
│       │   ├── detector.py   # Deterministic multi-ecosystem detection
│       │   ├── ast_parser.py # Safe Python AST parsing & import resolution
│       │   ├── graph.py      # Dependency graph builder & edge provenance tracking
│       │   └── service.py    # Inspection coordinator & in-memory report cache
│       ├── execution/        # Sandboxed dynamic test execution worker & provider adapters
│       │   ├── __init__.py
│       │   ├── policy.py     # WorkloadProfile allowlist, ExecutionPolicy, lifecycle states
│       │   ├── preflight.py  # Host container runtime & security capability prober
│       │   ├── provider.py   # DockerExecutionProvider and FakeExecutionProvider doubles
│       │   └── worker.py     # DynamicExecutionWorker orchestrating sandbox execution
│       └── api/
│           ├── __init__.py
│           └── v1/
│               ├── __init__.py
│               ├── router.py # API v1 centralized route registration
│               └── endpoints/
│                   ├── __init__.py
│                   ├── health.py       # Health & diagnostic readiness endpoints
│                   ├── repositories.py # Diagnostic target registration & management
│                   ├── inspection.py   # Trigger and fetch static inspection reports
│                   └── execution.py    # Trigger and fetch sandboxed dynamic execution reports
├── doc/                      # All project documentation & markdown files
│   ├── ARCHITECTURE.md       # Architecture reference & subfolder policies
│   ├── COMMANDS.md           # Verified environment, test, and run commands
│   ├── IMPLEMENTATION_STATUS.md # Granular status & blocker tracking
│   ├── LEARNING_LOG.md       # Educational chronological engineering log
│   └── README.md             # Project overview and quickstart guide
├── frontend/                 # Next.js TypeScript App Router frontend
│   ├── .env.example          # Frontend environment variable template
│   ├── next.config.ts        # Next.js build and Turbopack configuration
│   ├── package.json          # Frontend scripts and pinned dependencies
│   ├── tsconfig.json         # TypeScript compiler options
│   └── src/
│       ├── app/
│       │   ├── globals.css   # Tailwind CSS v4 directives
│       │   ├── layout.tsx    # Root HTML shell & metadata
│       │   └── page.tsx      # Main landing & diagnostic status dashboard
│       ├── components/
│       │   ├── DiagnosticWorkflowPreview.tsx # Planned diagnostic engine roadmap
│       │   ├── HealthCheckAction.tsx         # On-demand health check trigger & latency
│       │   ├── Navbar.tsx                    # Header with live connectivity pill
│       │   ├── RepositoryDetailModal.tsx     # Full target metadata view dialog
│       │   ├── RepositoryList.tsx            # Target list with deletion confirmation
│       │   ├── RepositoryRegistrationForm.tsx # Client-validated target creation form
│       │   └── StatusCard.tsx                # System & PostgreSQL status card
│       ├── config/
│       │   └── env.ts        # Type-safe environment variable access
│       ├── lib/
│       │   └── api.ts        # Typed fetch client with timeout & error handling
│       └── types/
│           └── api.ts        # TypeScript schemas matching backend Pydantic models
├── ml/                       # Machine learning research & experiment foundation
│   ├── __init__.py           # ML package version definition
│   ├── taxonomy/             # Versioned fault taxonomy
│   │   ├── __init__.py
│   │   └── fault_taxonomy.py # 10 observable fault classes, evidence, reproduction
│   ├── dataset/              # Reproducible experiment schemas & fixtures
│   │   ├── __init__.py
│   │   ├── schema.py         # DiagnosticCase, CaseFeatures, GroundTruthLabel schemas
│   │   └── fixtures.py       # Illustrative synthetic cases for schema validation
│   ├── experiments/          # Evaluation methodology & tracking
│   │   ├── __init__.py
│   │   ├── splitting.py      # Project-aware & scenario-aware data splitters
│   │   ├── evaluation.py     # Top-k ranking, ECE, abstention, cost metrics
│   │   └── tracking.py       # Local tracking config & secret redaction
│   ├── baselines/            # Baseline models progression
│   │   ├── __init__.py
│   │   └── specs.py          # Formal specifications for 6 baseline approaches
│   └── benchmark/            # Controlled fault-injection benchmark engine
│       ├── __init__.py
│       ├── schema.py         # DiagnosticEvidence, BenchmarkScenario, GroundTruthManifest
│       ├── scenarios.py      # 10 controlled scenarios & isolated ground-truth definitions
│       └── runner.py         # Deterministic benchmark runner & metric aggregator
└── testing/                  # All automated testing suites & fixtures
    ├── __init__.py
    ├── pytest.ini            # Pytest runner configuration with markers
    ├── conftest.py           # Shared test fixtures & sys.path environment bootstrap
    ├── fixtures/             # Controlled fixture projects for benchmark evaluation
    │   └── benchmark/        # 10 isolated fixture projects (proj_01 to proj_10)
    ├── backend/              # Backend test suite (pytest)
    │   ├── __init__.py
    │   ├── test_alembic.py      # Alembic configuration & offline SQL generation tests
    │   ├── test_config.py       # Configuration model unit tests
    │   ├── test_db.py           # Database connectivity & session handling tests
    │   ├── test_execution.py    # Sandbox policy, preflight, worker & dynamic API tests
    │   ├── test_health.py       # Endpoint integration tests
    │   ├── test_inspection.py   # Snapshot, ecosystem detector, AST parsing & API tests
    │   └── test_repositories.py # Repository CRUD & validation test suite
    ├── frontend/             # Frontend test suite (node:test)
    │   └── test_api_client.mjs  # API client & schema verification tests
    └── ml/                   # Machine learning test suite (pytest)
        ├── __init__.py
        ├── test_taxonomy.py       # Fault taxonomy coverage & documentation tests
        ├── test_dataset_schema.py  # Dataset schema & target leakage prevention tests
        ├── test_experiments.py     # Project-aware splitting, ECE, abstention & baseline tests
        └── test_benchmark.py       # Benchmark manifest, isolation, runner & metrics tests
```

---

## 4. PostgreSQL Database & Migration Lifecycle Architecture

The database architecture is designed for operational resilience, strict type enforcement, and verifiable schema evolution:

1. **Driver & Protocol**: Python interacts with PostgreSQL using `psycopg 3` (`postgresql+psycopg://`), taking advantage of binary parameters, native data type parsing, and client-side connection timeouts.
2. **Session Lifecycle**: Requests obtain a database session via [`get_db()`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/db/session.py#L25-L35), which yields an isolated SQLAlchemy `Session` bound to the engine pool and guarantees that the session is closed in a `finally` block upon completion.
3. **Fail-Fast Probing**: [`check_db_connectivity()`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/db/session.py#L38-L50) explicitly configures a short socket timeout (`connect_timeout=2s`) and executes a lightweight `SELECT 1`. This prevents the entire API from blocking or becoming unresponsive if the database daemon is unreachable.
4. **Dual-Mode Alembic Architecture**:
   - **Offline Mode (`alembic upgrade head --sql`)**: Alembic reads model metadata and emits pure PostgreSQL DDL statements (`BEGIN; ... COMMIT;`) without requiring an active database socket. This allows schema changes to be audited and tested in CI/CD without live infrastructure.
   - **Online Mode (`alembic upgrade head`)**: Connects to the target PostgreSQL instance via the configured `database_url` with bounded connection timeouts, applies versioned migrations within transactions, and records the revision in the `alembic_version` table.
5. **No Silent Fallbacks**: If PostgreSQL is unreachable, the system will never fall back to SQLite or in-memory persistence. The failure is recorded transparently in logs and diagnostics.

---

## 5. Frontend Architecture & API Contracts

The frontend is structured around explicit contracts, type safety, and clean component isolation:

1. **Next.js App Router**: Built with Next.js 16 and React 19. Root layout provides metadata and viewport shells, while page components consume client-side hooks for live diagnostics.
2. **Component Separation**:
   - UI presentation is isolated from network fetch logic. Components receive typed data props or invoke centralized client functions.
   - Distinct components exist for navigation status ([`Navbar`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/frontend/src/components/Navbar.tsx)), live system diagnostic presentation ([`StatusCard`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/frontend/src/components/StatusCard.tsx)), on-demand probes ([`HealthCheckAction`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/frontend/src/components/HealthCheckAction.tsx)), and roadmap visualization ([`DiagnosticWorkflowPreview`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/frontend/src/components/DiagnosticWorkflowPreview.tsx)).
3. **Strict Contract Alignment**:
   - TypeScript interfaces in [`frontend/src/types/api.ts`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/frontend/src/types/api.ts) directly mirror the backend Pydantic models in [`backend/oracle/api/v1/endpoints/health.py`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/api/v1/endpoints/health.py).
   - Discriminated union [`AsyncState<T>`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/frontend/src/types/api.ts#L22-L28) cleanly models `idle`, `loading`, `success`, and `error` states without implicit `any` or ambiguous nullable properties.
4. **CORS Security Boundary**:
   - Browser requests originate from `http://localhost:3000` to `http://localhost:8000`.
   - FastAPI's `CORSMiddleware` in [`oracle.main`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/main.py#L29-L35) explicitly allows `http://localhost:3000` and `http://127.0.0.1:3000` with credential support. Wildcard origins (`*`) with credentials enabled are strictly prohibited.

---

## 6. Diagnostic Target Domain Architecture (`Repository`)

A diagnostic target is a codebase or software project registered within ORACLE for upcoming diagnostic analysis.

### Canonical Entity Name: `Repository`
- **Rationale**: The core unit of inspection in software systems is the code repository. Terminology such as `DiagnosticTarget` is overly abstract, while `Project` or `Workspace` obscures the VCS boundaries. `Repository` (mapped to PostgreSQL table `repositories`) accurately identifies the entity across backend models, database schema, REST API, and frontend components.

### Data Model & Persistence Architecture
- **Table Name**: `repositories`
- **Primary Key**: UUIDv4 (`id`) generated server-side or by database default, preventing sequential enumeration attacks and cross-environment ID collision.
- **Attributes**:
  - `name`: VARCHAR(255), human-readable label, indexed for sorting and query filtering.
  - `url`: VARCHAR(1024), remote VCS URL or local directory URI.
  - `source_type`: VARCHAR(32), discriminator enum (`git` or `local_directory`). Defaults to `git`.
  - `status`: VARCHAR(32), lifecycle status (`registered`, `archived`). Defaults to `registered`.
  - `created_at`: TIMESTAMPTZ, automatic UTC creation timestamp.
  - `updated_at`: TIMESTAMPTZ, automatic UTC update timestamp.
- **Migration**: Controlled via Alembic revision `backend/alembic/versions/001_create_repositories.py`.

### Strict URL Validation & Security Guarantees
- Supported URL schemes: `https://`, `http://`, `git://`, `ssh://`, and `file://`.
- Scheme-only inputs (e.g. `https://`) and whitespace strings are rejected with HTTP 422 Unprocessable Entity.
- **Zero Premature Execution**: Registering a repository stores metadata only. ORACLE does NOT clone, fetch, parse, or execute code during registration.
- **Safe Metadata Deletion**: Deleting a repository (`DELETE /api/v1/repositories/{id}`) deletes only the ORACLE catalog entry. Local or remote source code is never deleted or modified.

---

## 7. Target Code Ingestion & Static Inspection Architecture

ORACLE inspects target software systems by acquiring controlled snapshots of codebases and analyzing their static structure without executing untrusted project code.

```mermaid
sequenceDiagram
    autonumber
    actor Client as API Client / Frontend
    participant API as Inspection Endpoint (/repositories/{id}/inspect)
    participant Service as InspectionService
    participant Snapshot as Snapshot Adapter (Local / Git)
    participant Policy as Policy & Resource Limiter
    participant Detector as Ecosystem Detector
    participant AST as Safe AST Parser
    participant Graph as Dependency Graph Builder
    participant Cache as In-Memory Report Cache

    Client->>API: POST /api/v1/repositories/{id}/inspect
    API->>Service: inspect_repository(repo, options)
    Service->>Snapshot: acquire_snapshot(url, source_type)
    alt Local Directory Target
        Snapshot->>Policy: Verify Path Containment (commonpath) & Symlink Safety
        Snapshot-->>Service: Yield Validated Local Path Context
    else Remote Git Target
        Snapshot->>Snapshot: Bounded Shallow Clone (depth=1, no hooks, no prompt)
        Snapshot-->>Service: Yield Ephemeral Directory Context
    end
    Service->>Policy: Filter Excluded Dirs (.git, node_modules) & Binaries
    Service->>Policy: Enforce Resource Limits (Count, Size, Total Bytes)
    Service->>Detector: detect_ecosystems(snapshot_dir)
    Detector-->>Service: Detected Languages & Confidence
    Service->>AST: parse_python_files(snapshot_dir)
    AST-->>Service: Imports (stdlib/internal/external), Syntax Errors
    Service->>Graph: build_dependency_graph(parsed_files)
    Graph-->>Service: Dependency Nodes, Edges & Provenance
    Service->>Cache: Store InspectionReport(id)
    Service-->>API: Return InspectionReport
    API-->>Client: HTTP 200 OK (InspectionReport JSON)
```

### 7.1 Sandboxed Snapshot Acquisition

1. **Local Directory Ingestion**:
   - Strictly enforced path containment: validates that `os.path.commonpath([permitted_root, target_path]) == permitted_root` against configured `permitted_local_roots`.
   - Traversal protection: paths with `../` attempting to escape permitted directories are rejected with `InspectionSecurityError`.
   - Symlink escape protection: target directories resolving outside the permitted boundary via symbolic links are rejected prior to scanning.
2. **Remote Git Ingestion**:
   - Bounded shallow clone: `git clone --depth 1 --no-tags --no-recurse-submodules -c core.hooksPath=NUL` (Windows) or `/dev/null` (POSIX). Disabling hooks prevents arbitrary script execution during cloning.
   - Bounded execution: invoked via direct argument lists (`subprocess.run(["git", ...])`) without shell interpolation.
   - Non-interactive: `GIT_TERMINAL_PROMPT=0` environment setting prevents git from hanging on credential prompts.
   - Pinned revision: records snapshot commit SHA via `git rev-parse HEAD`.
   - Automatic cleanup: cloned snapshots reside in temporary directories deleted upon context exit.

### 7.2 Ingestion Policy & Resource Boundaries

To safeguard ORACLE host resources against malicious or oversized repositories:
- **Directory Exclusions**: Automatically skips `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.tox`, `.mypy_cache`, and build output directories.
- **Binary File Exclusions**: Skips non-source files (`.pyc`, `.so`, `.dll`, `.exe`, `.tar`, `.zip`, `.png`, `.jpg`, etc.).
- **Resource Limits**: Configurable boundaries enforced by [`ResourceLimiter`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/inspection/policy.py):
  - Maximum files: 1,000 files per scan.
  - Maximum single file size: 1,000,000 bytes (1 MB).
  - Maximum cumulative bytes: 50,000,000 bytes (50 MB).
  - Ingestion timeout: 30 seconds.
- **Secret Redaction**: [`redact_secrets()`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/inspection/policy.py) masks embedded tokens (`ghp_`, `AKIA`, private keys, bearer tokens) and credentials within URLs (`user:pass@host`) before persisting or returning diagnostic metadata.

### 7.3 Static Language and Ecosystem Detection

The detector identifies software ecosystems purely through deterministic filesystem inspection without running project scripts:
- **Python**: Identified via `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg`, `Pipfile`, `poetry.lock`.
- **JavaScript / TypeScript**: Identified via `package.json`, `tsconfig.json`, `yarn.lock`, `package-lock.json`, `pnpm-lock.yaml`.
- **Java / JVM**: Identified via `pom.xml`, `build.gradle`, `build.gradle.kts`.
- **C / C++**: Identified via `CMakeLists.txt`, `Makefile`, `meson.build`, `configure.ac`.
- **Polyglot Repositories**: Multiple ecosystems can be detected concurrently in mixed codebases.

### 7.4 Zero-Execution AST Parsing & Dependency Representation

1. **Zero Untrusted Execution**: Source code is parsed exclusively via Python's standard library `ast.parse()`. No project modules are ever imported (`importlib`), evaluated (`eval`), or executed (`exec`).
2. **Import Provenance & Categorization**:
   - `stdlib`: Evaluated against Python 3.10+ `sys.stdlib_module_names` (zero third-party dependencies required).
   - `internal`: Resolved against discovered repository source files (including relative import resolution, e.g. `from .core import config`).
   - `external`: Third-party packages imported by target code (e.g. `pydantic`, `fastapi`).
   - `unresolved`: Imports that cannot be located within repo source or known standard library.
3. **Resilient Error Capture**: If a source file contains invalid syntax, `ast.parse()` raises `SyntaxError`. The parser catches this cleanly, records a [`FileSyntaxError`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/inspection/ast_parser.py) containing line number and message, and allows inspection of remaining files to proceed. Scan status reflects `partial` rather than crashing.
4. **Dependency Graph**: Generates nodes (files, external packages, standard libraries) and edges (provenance, line numbers, imported names).

---

## 8. Controlled Fault-Injection Benchmark Architecture

ORACLE includes a reproducible, controlled benchmark engine designed to measure diagnostic discrimination, false-positive rates on healthy codebases, and deliberate abstention under uncertainty.

```mermaid
flowchart TD
    subgraph BenchmarkEngine["Benchmark Engine (ml/benchmark/)"]
        Runner["BenchmarkRunner (runner.py)"]
        Scenarios["BenchmarkScenarios (CASE-001 to 010)"]
        Manifest["GroundTruthManifest (scenarios.py)"]
    end

    subgraph TargetFixtures["Controlled Fixtures (testing/fixtures/benchmark/)"]
        Clean["proj_01 (Clean Reference)"]
        SyntaxErr["proj_02 (Syntax Error)"]
        Unresolved["proj_03 (Missing Module)"]
        ExtDep["proj_04 (External Import)"]
        MissingEnv["proj_05 (Runtime Env Req)"]
        DBCli["proj_06 (DB Socket Req)"]
        IOContract["proj_07 (API Schema Req)"]
        DataVal["proj_08 (Transform Req)"]
        Misleading["proj_09 (Misleading Comment)"]
        Empty["proj_10 (Empty Stub)"]
    end

    subgraph InspectionPipeline["ORACLE Static Inspector"]
        Inspector["InspectionService (backend/oracle/inspection/)"]
        Report["InspectionReport"]
    end

    subgraph EvaluationPipeline["Evaluation & Leakage Isolation Boundary"]
        Evidence["DiagnosticEvidence (schema.py)"]
        Evaluator["Evaluation Logic (runner.py)"]
        Metrics["Honest Metrics (Top-k: None, FPR: 0%)"]
        Artifact["JSON Summary (run-summary.json)"]
    end

    Runner --> Scenarios
    Scenarios --> TargetFixtures
    TargetFixtures --> Inspector
    Inspector --> Report
    Report --> Evidence
    Evidence --> Evaluator
    Manifest -.->|"Separately Queried (Never in Input)"| Evaluator
    Evaluator --> Metrics
    Metrics --> Artifact
```

### 8.1 Ground-Truth Isolation & Target Leakage Prevention

- **Separation Invariant**: Ground truth is maintained in an independent [`GroundTruthManifest`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/ml/benchmark/schema.py#L170-L190). Public [`BenchmarkScenario`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/ml/benchmark/schema.py#L90-L120) objects presented to the diagnostic pipeline contain zero ground-truth labels, root-cause descriptions, or expected remediation outcomes.
- **Neutral Identifiers**: All scenarios and projects utilize neutral identifiers (`CASE-001` through `CASE-010`, `PRJ-001` through `PRJ-010`). Neither identifiers nor fixture paths disclose injected defect classes.
- **Serialization Audit**: [`DiagnosticEvidence.to_diagnostic_input()`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/ml/benchmark/schema.py#L70-L85) enforces programmatic regex validation, rejecting any payload containing forbidden tokens (`root_cause`, `ground_truth`, `injected_fault`).

### 8.2 Observable Evidence Contract & State Tracking

The evidence contract [`DiagnosticEvidence`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/ml/benchmark/schema.py#L30-L85) strictly records what the static inspector can genuinely observe, categorizing evidence states:
- `OBSERVED`: Evidence verified directly through static parsing (e.g. syntax errors with line numbers, unresolved imports).
- `INFERRED`: Rule-based hypotheses derived from observed signals.
- `MISSING`: Signals queried but absent (e.g. uninspected files).
- `UNSUPPORTED`: Analysis requiring capabilities not present in static inspection (e.g. runtime socket connectivity).
- `FAILED`: Inspection failures or corrupted fixture directories.

> [!IMPORTANT]
> **Zero Evidence Fabrication**: For scenarios requiring dynamic execution (such as database connectivity or API contract violations), the benchmark marks them as `unsupported_analysis` and notes missing runtime probes. ORACLE never fabricates synthetic stack traces or fake socket error outputs.

### 8.3 Ten Controlled Benchmark Scenarios

| Scenario ID | Project ID | Category | Static Scope | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **CASE-001** | `PRJ-001` | Healthy Control | Supported | `correct_control` (Clean reference, 0% FPR) |
| **CASE-002** | `PRJ-002` | `RUNTIME_EXCEPTION` | Supported | `correct` (Syntax error on line 6 detected) |
| **CASE-003** | `PRJ-003` | `DEPENDENCY_IMPORT_FAILURE` | Supported | `correct` (Unresolved relative import detected) |
| **CASE-004** | `PRJ-004` | `DEPENDENCY_IMPORT_FAILURE` | Supported | `correct` (External package imports extracted) |
| **CASE-005** | `PRJ-005` | `CONFIG_MISSING_OR_INVALID` | Unsupported (Dynamic) | `unsupported_analysis` (Runtime env var required) |
| **CASE-006** | `PRJ-006` | `DATABASE_CONNECTIVITY_SCHEMA` | Unsupported (Dynamic) | `unsupported_analysis` (TCP socket probe required) |
| **CASE-007** | `PRJ-007` | `IO_CONTRACT_VIOLATION` | Unsupported (Dynamic) | `unsupported_analysis` (Contract test required) |
| **CASE-008** | `PRJ-008` | `DATA_VALIDATION_TRANSFORMATION` | Unsupported (Dynamic) | `unsupported_analysis` (Runtime test payload required) |
| **CASE-009** | `PRJ-009` | Healthy Control (Misleading) | Supported | `correct_control` (Historical comment ignored, 0% FPR) |
| **CASE-010** | `PRJ-010` | `UNKNOWN_INSUFFICIENT_EVIDENCE` | Supported | `correct_abstention` (Empty stub triggers deliberate abstention) |

### 8.4 Honest Evaluation Metrics

The benchmark runner computes empirical metrics without inflating claims:
- **Static Diagnostic Accuracy**: Evaluated exclusively on supported scenarios.
- **False Positive Rate**: Evaluated on healthy control codebases (verified at 0.0%).
- **Abstention Correctness**: Evaluated when evidence is insufficient.
- **Top-k Ranking Accuracy**: Explicitly reported as `None` since no production ranking model is deployed.

---

## 9. Sandboxed Dynamic Test Execution Architecture

ORACLE extends static inspection toward active diagnostic probing via container-isolated test execution. Dynamic execution is strictly bounded to explicitly approved workload profiles, enforces defense-in-depth isolation, and never executes untrusted target code directly on the host machine.

```mermaid
sequenceDiagram
    autonumber
    actor Client as API Client / Benchmark Runner
    participant Endpoint as Execution Endpoint (/execute)
    participant Worker as DynamicExecutionWorker
    participant Policy as Policy Validator (WORKLOAD_PROFILES)
    participant Preflight as IsolationPreflight Prober
    participant Provider as DockerExecutionProvider
    participant Sandbox as Hardened Docker Container

    Client->>Endpoint: POST /api/v1/repositories/{id}/execute (profile_id)
    Endpoint->>Worker: execute_workload(repo, request, snapshot_path)
    Worker->>Policy: Validate profile_id in WORKLOAD_PROFILES
    alt Unknown Profile / Arbitrary Command
        Policy-->>Worker: Reject with REJECTED_BY_POLICY
        Worker-->>Endpoint: Return ExecutionReport(rejected_by_policy)
    else Approved Profile
        Worker->>Preflight: check_isolation_preflight()
        alt Docker Unavailable / Daemon Down
            Preflight-->>Worker: is_available = False
            Worker-->>Endpoint: Return ExecutionReport(isolation_unavailable)
            Note over Worker,Endpoint: Host execution is strictly forbidden
        else Isolation Available
            Worker->>Provider: execute(profile, snapshot, policy)
            Provider->>Sandbox: docker run --rm --read-only --network none --cap-drop ALL ...
            Sandbox-->>Provider: RawExecutionResult (exit_code, stdout, stderr, duration)
            Provider-->>Worker: RawExecutionResult
            Worker->>Worker: Enforce Max Output Bytes (Truncate if needed)
            Worker->>Worker: Redact Secrets (Tokens, Passwords, URIs)
            Worker-->>Endpoint: Return ExecutionReport(completed / failed / timed_out)
            Endpoint-->>Client: HTTP 200 OK (ExecutionReport JSON)
        end
    end
```

### 9.1 The Fundamental Security Invariant: Never Fall Back to Host Execution

- **Security Precedes Diagnostic Coverage**: A standard Python subprocess, virtual environment, or local shell is NOT a security sandbox.
- **Preflight Gating**: Before any dynamic execution, [`IsolationPreflight`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/execution/preflight.py) verifies that a container runtime (Docker) is installed, responding, and supports required security flags.
- **Fail-Safe Invariant**: If Docker is unavailable or misconfigured, the worker immediately aborts and returns lifecycle state [`ISOLATION_UNAVAILABLE`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/execution/policy.py). Target code is **never** executed directly on the host machine under any circumstances.

### 9.2 Immutable Workload Profile Allowlist

To eliminate arbitrary remote code execution risks:
- The execution worker accepts **only** pre-registered profile IDs from the ORACLE-owned allowlist [`WORKLOAD_PROFILES`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/execution/policy.py):
  1. `health-probe`: Minimal Python execution verifying sandbox initialization and process boundaries.
  2. `benchmark-env-audit`: Bounded execution testing module configuration loading when mandatory environment variables are absent (`CASE-005`).
  3. `benchmark-db-probe`: Active socket connection probe verifying database connection refusal (`CASE-006`).
  4. `benchmark-contract-check`: Type assertions verifying API contract payload structures (`CASE-007`).
  5. `benchmark-transform-test`: Bounded transformation parsing of invalid input payloads (`CASE-008`).
- **Zero Arbitrary Execution**: Neither repository code, README instructions, nor API callers can supply custom shell commands, arguments, or environment variables. Requests with unknown profiles are immediately marked `REJECTED_BY_POLICY`.

### 9.3 Hardened Container Sandbox Isolation Controls

When dynamic execution runs via [`DockerExecutionProvider`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/execution/provider.py), it enforces defense-in-depth isolation:
1. **Read-Only Root Filesystem**: `--read-only` prevents processes from writing to container system directories or modifying binaries.
2. **Network Isolation**: `--network none` cuts off all external socket connections by default, preventing data exfiltration, command-and-control communication, or unauthorized network scanning.
3. **Capability Dropping**: `--cap-drop ALL` strips all Linux capabilities from the container process, eliminating raw socket creation, ptrace, and root escalation paths.
4. **No Privilege Escalation**: `--security-opt no-new-privileges` prevents processes from gaining additional privileges via `setuid` binaries.
5. **Read-Only Target Mount**: Source code is mounted strictly read-only (`-v <snapshot>:/workspace:ro`), guaranteeing that running tests cannot mutate target repository files.
6. **Ephemeral Writable Storage**: A temporary scratch directory is mounted read-write (`-v <tmp_dir>:/tmp:rw`) for temporary process files and is deleted immediately upon container exit.
7. **Resource Quotas**: Hard boundaries enforced via `-m 256m` (memory limit), `--cpus 1.0` (CPU limit), and `--pids-limit 64` (process limit preventing fork bombs).
8. **Immutable Pinned Image**: Executes inside a pinned base image (e.g. `python:3.11-slim`), never building untrusted Dockerfiles supplied by target repositories.

### 9.4 Bounded Output & Secret Redaction

- **Output Capping**: Worker enforces hard byte ceilings ([`max_execution_output_bytes`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/core/config.py), default 100KB). Excessive stdout/stderr is truncated and flagged with `output_truncated = True` and status `PARTIAL`.
- **Secret Scrubbing**: All output streams and forensic error messages pass through [`redact_secrets()`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/inspection/policy.py) to mask credentials, tokens (`ghp_`, `AKIA`), and password-bearing connection strings before storage or HTTP transmission.

---

## 10. Machine Learning Research & Diagnostic Intelligence Foundation

The diagnostic intelligence of ORACLE is developed on a strict research-first methodology. No model is deployed or trained without formal problem formulation, target-leakage prevention, and project-aware evaluation.

### Conceptual Distinctions in Diagnostic Intelligence
1. **Anomaly Detection (Is something wrong?)**:
   - Detects deviations from baseline operational telemetry (latency, memory, CPU, error rates) in continuous multidimensional space (e.g. via Isolation Forest).
   - Identifies *that* a system is failing, but cannot determine *why*.
2. **Fault Classification (What kind of failure is this?)**:
   - Categorizes an observed failure into one of the 10 taxonomy classes based on symptoms, stack traces, and exit codes.
3. **Root-Cause Ranking (Which specific component or defect is responsible?)**:
   - Generates a prioritized, probability-calibrated ranking of candidate root-cause hypotheses (Top-1 and Top-3 accuracy).
4. **Adaptive Diagnostic Planning (What should the system test next?)**:
   - An active sequential decision-making agent that selects subsequent diagnostic probes or unit tests to maximize Expected Information Gain (EIG) relative to test execution cost and safety.

### Why Data Quality & Evaluation Design Must Precede Model Training
1. **Target Leakage Prevention**: In software diagnostics, stack traces and test logs frequently contain hints or error strings that directly reveal the injected root cause. If ground-truth labels or post-incident repairs leak into feature vectors, models achieve 99% training accuracy but fail in production.
2. **Group Data Leakage**: Codebases share distinctive naming conventions, file paths, and logging formats. If incidents from the same repository appear in both train and test sets, models memorize project-specific surface tokens instead of generalizable diagnostic rules.
3. **Calibrated Abstention**: In real-world software engineering, telemetry is often incomplete or missing. An effective diagnostic system must know when to say "insufficient evidence" rather than hallucinating plausible but incorrect root causes.

### Versioned Fault Taxonomy (v1.0.0)
The taxonomy provides 10 observable fault classes:
1. `CONFIG_MISSING_OR_INVALID`: Missing or malformed configuration, absent environment variables, out-of-range settings.
2. `DEPENDENCY_IMPORT_FAILURE`: Unresolvable packages, circular imports, missing C-extensions or shared libraries.
3. `IO_CONTRACT_VIOLATION`: Schema mismatches, missing required payload fields, type mismatches across service boundaries.
4. `RUNTIME_EXCEPTION`: Unhandled language exceptions, ZeroDivisionError, KeyError, AttributeError, unexpected NoneType.
5. `DATA_VALIDATION_TRANSFORMATION`: Serialization/deserialization failures, timezone bugs, Unicode encoding/decoding errors.
6. `API_COMMUNICATION_FAILURE`: Network timeouts, HTTP 5xx responses, connection reset, SSL/TLS handshake failures, rate limits (429).
7. `DATABASE_CONNECTIVITY_SCHEMA`: Connection refused, timeout, missing tables/columns, unapplied migration revisions, deadlocks.
8. `MODEL_LOADING_INFERENCE_FAILURE`: Missing weights/checkpoints, tensor shape mismatch, CUDA out-of-memory, NaN forward output.
9. `PERFORMANCE_ANOMALY`: P95 latency spikes (>3 sigma), CPU pegging (100%), memory leaks, thread starvation.
10. `UNKNOWN_INSUFFICIENT_EVIDENCE`: Telemetry missing or truncated, uninstrumented failure modes, requiring deliberate abstention.

### Six-Stage Baseline Progression
Models are evaluated sequentially against strictly defined baselines:
1. **Deterministic Diagnostic Rules**: Exact regex and boolean signature matching (0ms, 100% precision on exact matches, 0% recall on novel faults).
2. **Statistical Frequency (Naive Bayes / TF-IDF)**: Word-frequency conditional probability distributions over tokenized symptoms.
3. **Isolation Forest**: Unsupervised tree ensemble on continuous telemetry metrics for triage gating.
4. **Gradient Boosted Decision Trees (XGBoost)**: Supervised ranking model on structured tabular features and categorical indicators.
5. **Adaptive Test Selector**: Active diagnostic planner balancing information gain against execution latency and compute cost.
6. **Pretrained Semantic Embeddings & Deep Learning**: Deep neural models (e.g. CodeBERT) justified only if empirical gains exceed +5% over XGBoost to offset high inference latency.

---

## 11. Architectural Rules & Invariants

1. **Subfolder Strictness**: Files must not be created loose in the main repository root. Every file has an explicit domain subfolder.
2. **Modular Monolith**: All backend services reside within the `backend/oracle` package initially. Microservices are prohibited without demonstrated scale or deployment necessity.
3. **Frontend-to-Backend Separation**: The frontend communicates with the backend exclusively via explicit RESTful JSON HTTP contracts. The frontend never connects directly to the database.
4. **Decoupled Diagnostics**: Diagnostic algorithms and fault-isolation workflows must remain decoupled from HTTP request handling so they can be triggered from CLI, background jobs, or web requests alike.
5. **First-Class PostgreSQL**: PostgreSQL via psycopg 3 is the sole database persistence engine. SQLite or in-memory replacements are strictly forbidden, even for testing.
6. **Alembic Schema Evolution**: All database tables and schema migrations are tracked and applied strictly via Alembic revisions. Direct manual database alterations are not permitted.
7. **No Secret Commits**: Configuration is injected via environment variables (`.env`). Secrets are never committed to version control.
8. **ML Research Isolation**: ML research code lives strictly within `ml/`. No uncalibrated model may be mounted in production backend endpoints.
9. **Zero Untrusted Execution in Static Ingestion**: Target codebase static inspection must never execute untrusted code. No `importlib`, `exec`, `eval`, or invocation of target test runners/scripts during repository ingestion or AST parsing.
10. **Strict Ground-Truth Isolation in Benchmarks**: Ground-truth labels, injected-defect descriptions, and expected outcomes must remain in isolated manifests (`GroundTruthManifest`) and must never be serialized into diagnostic inputs or passed to diagnostic inference code.
11. **No Host Fallback for Dynamic Execution**: Dynamic test execution must never execute target code directly on the host machine. If container isolation is unavailable, the system must report `ISOLATION_UNAVAILABLE` rather than degrading to an insecure host subprocess.

---

## 12. Security Architecture

1. **Untrusted Repositories**: Source repositories analyzed by ORACLE are treated as untrusted data. ORACLE will not execute arbitrary repository code directly on the host machine.
2. **Filesystem Containment**: Local repository targets must reside within explicitly whitelisted directories (`permitted_local_roots`). Path traversal (`../`) and symbolic links escaping the boundary are rejected before file scanning begins.
3. **Git Sandboxing**: Remote git clones disable git hooks (`core.hooksPath=NUL`), submodules, and credential prompts, running with bounded depth (`--depth 1`) and strict process timeouts.
4. **Resource Quotas**: Ingestion workers enforce hard ceilings on file count (1000), single file size (1MB), and cumulative byte size (50MB) to prevent denial-of-service via zip bombs or unbounded repository trees.
5. **Dynamic Sandbox Isolation**: Dynamic test execution runs exclusively in containerized environments with read-only root filesystems, dropped Linux capabilities (`--cap-drop ALL`), disabled networking (`--network none`), `no-new-privileges`, read-only source mounts, and ephemeral scratch directories.
6. **Least Privilege**: Database roles for ORACLE follow least-privilege principles, restricting administrative table creation to migration execution.
7. **Input Validation**: All incoming requests pass through Pydantic models with strict typing, boundary validation, and schema enforcement before reaching business logic.
8. **Secret Redaction**: All experiment logging, target inspection reports, and dynamic execution outputs automatically redact database credentials, access tokens, and private keys before persisting to disk or returning over HTTP.

---

## 13. Unified Diagnostic Engine & End-to-End Evidence Pipeline

The core product capability of ORACLE connects static ingestion, dependency mapping, discrete evidence collection, deterministic causal reasoning, independent verification, and forensic reporting into an automated, verifiable pipeline.

```mermaid
flowchart TD
    Target["Target Repository (Git / Local)"] -->|"1. Validate & Ingest"| Ingestion["Safe Snapshot Ingestion (SnapshotContext)"]
    Ingestion -->|"2. Static Parse"| AST["AST Parser & Multi-Ecosystem Detector"]
    AST -->|"3. Graph Extraction"| SysMap["System Map (Components & Dependency Edges)"]
    SysMap -->|"4. Extract Signals"| Evidence["Evidence Set (Provenance, Line Coordinates)"]
    Evidence -->|"5. Deterministic Rules"| Hypo["Fault Hypotheses (Taxonomy Categories)"]
    Hypo -->|"6. Independent Checks"| Verif{"Verification Gating"}
    Verif -->|"Static AST Confirmation"| Verified["Verified Hypotheses"]
    Verif -->|"Preflight OK & Authorized"| Dynamic["Container Sandbox Workload"]
    Verif -->|"Isolation Unavailable"| Blocked["Unsupported Dynamic Stage (Zero Host Run)"]
    Verified --> Report["Diagnostic Report & Recommendations"]
    Dynamic --> Report
    Blocked --> Report
    Report -->|"REST API / Web UI"| Frontend["Next.js Diagnostic Dashboard"]
```

### 13.1 Eight-Stage Diagnostic Workflow
1. **Target Validation (`validate_target`)**:
   - Confirms registered repository exists in catalog.
   - Validates requested capabilities and execution policy.
   - Rejects unapproved workload profiles with HTTP 400.
2. **Safe Snapshot Ingestion (`acquire_snapshot`)**:
   - Acquires bounded shallow clone or validates local path containment within `permitted_local_roots`.
   - Records commit SHA and target metadata.
   - Guarantees zero code execution during ingestion.
3. **Static Inspection (`static_inspection`)**:
   - Scans files under strict file-count and byte limits (`ResourceLimiter`).
   - Detects ecosystems (`python`, `javascript`, etc.).
   - Parses Python files with `ast.parse`, capturing syntax errors and import declarations.
4. **System Map Construction (`build_system_map`)**:
   - Normalizes components into typed nodes: `source_file`, `internal_module`, `external_package`, `stdlib_module`, `unresolved_reference`.
   - Normalizes edges with line numbers, import statements, and provenance metadata.
   - Calculates summary metrics (internal, external, unresolved, syntax errors).
5. **Discrete Evidence Collection (`collect_evidence`)**:
   - Generates provenance-tracked `DiagnosticEvidenceRecord` objects (`EVID-SYNTAX-xxx`, `EVID-IMPORT-xxx`, `EVID-EXTDEP-xxx`, `EVID-EMPTY-xxx`, `EVID-PREFLIGHT-xxx`).
   - Reads manifest files (`pyproject.toml`, `requirements.txt`, `setup.cfg`) using built-in `tomllib` to audit declared dependencies.
   - Redacts all secrets and tokens before record creation.
6. **Deterministic Fault Hypothesis Generation (`generate_hypotheses`)**:
   - Evaluates empirical evidence using deterministic diagnostic rules:
     - *Rule A (Syntax Error)*: Generates `FaultCategory.RUNTIME_EXCEPTION` with `high` confidence and file/line provenance.
     - *Rule B (Unresolved Internal Import)*: Generates `FaultCategory.DEPENDENCY_IMPORT_FAILURE` with `high` confidence.
     - *Rule C (Undeclared External Package)*: Generates `FaultCategory.DEPENDENCY_IMPORT_FAILURE` with `medium` confidence.
     - *Rule D (Empty Codebase)*: Generates `FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE` with deliberate abstention.
     - *Rule E (Clean Codebase)*: Emits zero fault hypotheses, guaranteeing zero false positives on healthy projects.
7. **Hypothesis Verification & Security Gating (`verify_hypotheses`)**:
   - Statically confirmed findings are marked `verified` via `static_ast_validation`.
   - Dynamic verification requires explicit `allow_dynamic=True` authorization.
   - Dynamic execution checks host container isolation preflight: if Docker is unavailable, the stage is recorded as `unsupported` and host execution is strictly prohibited.
8. **Forensic Report Assembly (`generate_report`)**:
   - Assembles immutable `DiagnosticReport`.
   - Persists run metadata to PostgreSQL `diagnostic_runs` table when available and caches in-memory for immediate query.

---

## 14. Evidence-Based Diagnostic Intelligence & Adaptive Probe Planning

The ORACLE Diagnostic Engine features an active, evidence-driven investigation system that formulates competing causal hypotheses, reasons about uncertainty and upstream/downstream dependencies, generates safe candidate diagnostic probes, optimizes probe selection by utility and information gain, executes approved probes via isolated adapters, and stops cleanly under clear termination policies.

```mermaid
flowchart TD
    Obs["Initial Static & Dynamic Observations"] --> HypoGen["Multi-Hypothesis Generation\n(Assumptions & Alternatives)"]
    HypoGen --> Ranker["Heuristic Ranker\n(Diminishing Returns & Relative Score)"]
    Ranker --> DecisionCheck{"Sufficient Evidence or\nStopping Criteria Met?"}
    DecisionCheck -->|"Yes (Stop)"| Report["Assemble Forensic Report &\nRecord Investigation History"]
    DecisionCheck -->|"No (Continue)"| GenProbes["Generate Candidate Probes\n(AST, Import, Manifest, Downstream, Container)"]
    GenProbes --> UtilityOpt["Utility Optimization\n(Discrimination Heuristic / Cost^w)"]
    UtilityOpt --> SafetyGate{"Safety & Availability Gate"}
    SafetyGate -->|"Dynamic & Docker Absent"| RejectProbe["Reject Probe & Halt\n(further_investigation_unsafe_or_unsupported)"]
    RejectProbe --> Report
    SafetyGate -->|"Safe Adapter Approved"| ExecuteProbe["Execute Approved Probe via Safe Adapter\n(AST Check / Import Resolution / Manifest / Downstream)"]
    ExecuteProbe --> UpdateState["Update System Map & Evidence\n(Downstream marked 'blocked' if upstream faulty)"]
    UpdateState --> LoopIter["Increment Iteration &\nRecord Decision"]
    LoopIter --> Ranker
```

### 14.1 Competing Hypotheses and Explicit Assumptions
Rather than producing a single deterministic conclusion, the diagnostic engine constructs multiple competing explanations for observed anomalies:
- Every hypothesis records explicit `assumptions` required for the hypothesis to hold (e.g. "Missing module is not provided via dynamic PYTHONPATH modification").
- Plausible `alternative_explanations` are generated to account for confounding factors.
- `relative_ranking_score` [0.0 - 100.0] transparently reflects heuristic evidentiary weight.
- `score_rationale` provides human-readable mathematical provenance of how the score was calculated.

### 14.2 Transparent Heuristic Ranking (`ml.ranking.heuristic_ranker`)
To avoid misleading probabilistic claims on uncalibrated models, ORACLE strictly distinguishes relative heuristic scores from calibrated Bayesian probabilities:
- **Direct Observation Weight (+35)**: Credited for primary empirical evidence (e.g. AST parse error, failed import).
- **Diminishing Marginal Evidence (+5)**: Subsequent observations of the identical category receive diminishing weight to prevent artificially inflating partial static evidence into spurious certainty.
- **Corroborating Evidence Bonus (+15)**: Added when distinct components independently corroborate the fault.
- **Contradiction Penalty (-40)**: Applied when contradicting evidence is detected.
- **Verification Status Weight**:
  - `verified`: +35 bonus
  - `partially_verified`: +15 bonus
  - `candidate`: +5 bonus
- **Uncertainty Penalty (-10)**: Applied when unverified assumptions remain.
- **Deliberate Abstention**: Produces a score of 0.0 with confidence `uncertain` and explicit `abstention_reason`.

### 14.3 Adaptive Probe Planning & Utility Optimization (`ml.planning.probe_planner`)
ORACLE evaluates candidate diagnostic checks through a dual-mode information gain framework:
1. **Shannon Entropy Mode (Calibrated Probabilities)**:
   $$H(p) = -\sum_{i} p_i \log_2(p_i)$$
   Expected Information Gain:
   $$\text{EIG}(T) = H(p) - \sum_{k} P(O_k) H(p \mid O_k)$$
   Requires normalized, mutually exclusive probability distributions summing to $1.0 \pm 10^{-5}$.
2. **Discrimination Heuristic Mode (Relative Heuristic Scores)**:
   When working with uncalibrated heuristic scores, ORACLE calculates discriminatory power:
   $$\text{DiscriminationScore} = N_{\text{discriminated}} \times 0.5 + N_{\text{targeted}} \times 0.25$$
3. **Cost-Aware Utility Optimization**:
   $$\text{Utility} = \frac{\text{DiscriminationScore}}{\text{EstimatedCost}^{\text{cost\_weight}}}$$
   Lower-cost static AST probes ($\text{cost}=1.0$) are prioritized over expensive dynamic executions ($\text{cost}=10.0$) when discriminatory power is comparable.

### 14.4 Downstream Component Reasoning
When an upstream component has a verified defect (e.g. syntax error or missing package), downstream components that depend on it are not assumed to be faulty or healthy:
- An independent static probe (`downstream_independent_check`) verifies the downstream component's internal code in isolation.
- If the downstream component is syntactically valid and has no internal defects of its own, its runtime state in the `SystemMap` is marked as **`blocked`** (rather than `analyzed` or `syntax_error`), accurately reflecting that its failure at runtime is a cascade from the upstream fault.

### 14.5 Host Safety & Container Gating
All probes undergo safety gating before execution:
- Probes classified as `safe_read_only` (AST checks, internal module checks, manifest audits) run in-process without code execution.
- Probes requiring dynamic execution (`controlled_dynamic`) verify container preflight. If Docker is unavailable on the host development environment, the probe is rejected (`unavailable_missing_adapter`), and investigation stops safely (`further_investigation_unsafe_or_unsupported`). Host execution of untrusted repository code is strictly prohibited.

### 14.6 Stopping Policies
The investigation loop runs up to `max_iterations` (default: 5) and terminates deterministically under one of five explainable conditions:
1. `sufficient_evidence_verified`: High-confidence hypothesis ($\ge 70.0$) verified by an approved adapter.
2. `further_investigation_unsafe_or_unsupported`: Best candidate probe requires unavailable container infrastructure.
3. `deliberate_abstention`: Clean control project or empty codebase where fault hypotheses are zero or unsupportable.
4. `no_useful_probe_available`: All candidate probes have been executed or no discriminating probes exist.
5. `budget_exhausted`: Maximum allowed investigation loop iterations reached.

---

## 15. Diagnostic Reliability, Multiple-Fault Isolation, and Adversarial Validation

To ensure diagnostic conclusions reflect real-world software behavior rather than overfitting to synthetic single-fault fixtures, ORACLE incorporates comprehensive reliability controls, causal separation rules, and an expanded 20-scenario adversarial benchmark suite.

```mermaid
flowchart TD
    Repo["Target Repository"] --> AST["Multi-Component AST Parsing"]
    AST --> EvidGroup["Evidence Partitioning by Component"]
    EvidGroup --> MultiHypo["Independent Fault Hypotheses\n(Multiple Defects Handled Separately)"]
    MultiHypo --> OrderRanker["Order-Invariant Heuristic Ranker\n(Deduplication & Commutative Scoring)"]
    OrderRanker --> ProbeGen["Candidate Probes Generation\n(AST, Import, Manifest, Downstream)"]
    ProbeGen --> SafetyCheck{"Container Preflight Check"}
    SafetyCheck -->|"Docker Absent"| SafeHalt["Safe Halt without Host Fallback\n(further_investigation_unsafe_or_unsupported)"]
    SafetyCheck -->|"Safe Adapter Approved"| ProbeExec["Execute Probes Sequentially"]
    ProbeExec --> CascadeLogic{"Downstream Check Outcome"}
    CascadeLogic -->|"Syntax Valid"| Blocked["Mark Component 'blocked' in SystemMap"]
    CascadeLogic -->|"Syntax Broken"| Broken["Mark Component 'syntax_error'"]
    Blocked --> Report["Diagnostic Report & Baseline Comparison"]
    Broken --> Report
    SafeHalt --> Report
```

### 15.1 Architectural Invariants for Diagnostic Reliability
1. **Causal Separation of Multiple Simultaneous Faults**:
   - The diagnostic orchestrator partitions observations by source component (`source_component`).
   - Rather than collapsing all syntax violations or import failures into a single hypothesis for the first discovered file, each independently broken component generates its own causal hypothesis.
   - Probes are dispatched to verify each fault independently (`CASE-012`, `CASE-013`, `CASE-016`).
2. **Order Invariance & Commutativity in Heuristic Scoring**:
   - Additive heuristic scoring sorts evidence by `evidence_type` and selects the primary observation by reliability priority (`direct_observation` > `inferred_signal` > `limited_context`).
   - Subsequent observations of the identical category receive diminishing marginal weight (+5.0).
   - Scoring is mathematically commutative: reversing or shuffling the order of evidence IDs yields the exact same numerical score and breakdown rationale.
3. **Evidence Deduplication**:
   - Duplicate evidence IDs are deduplicated prior to scoring.
   - Repeated references to the same finding cannot artificially inflate confidence scores beyond target bounds.
4. **Immunity to Misleading & Non-Causal Signals**:
   - AST parsing ignores comments, docstrings, and string literals containing error keywords (e.g. historical incident notes referencing `SyntaxError` in `CASE-015`).
   - Configuration lookups with safe default fallbacks (e.g. `os.getenv("PORT", "8000")` in `CASE-020`) are recognized as healthy patterns and do not trigger false-positive configuration faults.
5. **Downstream Cascade Reasoning**:
   - When upstream module `A` fails and downstream module `B` imports `A`:
     - If `B` has valid internal syntax, its runtime state in the `SystemMap` is marked **`blocked`** (`CASE-011`).
     - If `B` also has an internal syntax defect, it is marked **`syntax_error`** (`CASE-016`).
     - Downstream health is never assumed without independent verification.
6. **Deliberate Abstention on Polyglot / Unsupported Targets**:
   - Repositories lacking Python source code (e.g. C++ and Java codebases in `CASE-019`, or empty directories in `CASE-010`) trigger deliberate abstention with `UNKNOWN_INSUFFICIENT_EVIDENCE` without false-positive fault manufacture.
7. **Adversarial Benchmark & Baseline Comparison**:
   - 20 controlled scenarios evaluated against a Naive 1-Shot Baseline.
   - All metrics reported with explicit numerators and denominators ($x/y = z\%$).
   - JSON and Markdown reports persisted under `testing/reports/`.

---

## 16. TypeScript/JavaScript AST & Cross-Module Semantic Analysis

To diagnose modern polyglot web platforms, ORACLE extends its static inspection engine to analyze TypeScript and JavaScript repositories with the identical evidence-driven discipline, sandboxing rigor, and uncertainty guarantees established for Python.

```mermaid
flowchart TD
    TSFiles["Target Snapshot (*.ts, *.tsx, *.js, *.jsx, etc.)"] --> BatchPrep["Batch Manifest Preparation (ts_parser.py)"]
    BatchPrep -->|"stdin JSON streaming"| NodeWorker["Isolated AST Worker (ts_ast_worker.mjs)"]
    NodeWorker -->|"ts.createSourceFile (Zero Execution)"| TSCompiler["Official Microsoft TypeScript Compiler API"]
    TSCompiler --> Diagnostics["Capture Parse Diagnostics (Line, Column, Offset)"]
    TSCompiler --> ASTNodes["Extract Imports, Exports & Re-exports"]
    Diagnostics --> WorkerOut["Structured JSON Result Payload"]
    ASTNodes --> WorkerOut
    WorkerOut -->|"stdout JSON streaming"| PythonAdapter["Python Adapter (ts_parser.py)"]
    PythonAdapter --> ConfigLoad["Load tsconfig.json (paths, baseUrl) & package.json"]
    ConfigLoad --> ModResolver["Deterministic Module Resolution Algorithm"]
    ModResolver --> BoundaryCheck{"Repository Containment Check"}
    BoundaryCheck -->|"Escaping Path"| UnsupRef["Classify as 'unsupported_reference'"]
    BoundaryCheck -->|"Within Snapshot"| GraphBuilder["Construct DependencyNode & DependencyEdge"]
    UnsupRef --> GraphBuilder
    GraphBuilder --> SysMap["Unified DiagnosticSystemMap"]
    SysMap --> EvidencePipe["Emit DiagnosticEvidenceRecords"]
    EvidencePipe --> DiagOrch["DiagnosticOrchestrator & Probe Planner"]
```

### 16.1 Isolated AST Parser Worker Architecture
To inspect JavaScript and TypeScript code safely and deterministically:
1. **Windows Application Control (WDAC) Discovery & Worker Selection**:
   - Native C-extension parsers (such as `tree-sitter` Python bindings) are blocked on Windows 11 under Application Control policies when loaded from user-writable directories.
   - Rather than relying on unsigned binary DLLs or fragile regex heuristics, ORACLE uses an isolated Node.js worker (`backend/oracle/inspection/ts_ast_worker.mjs`) leveraging the official Microsoft TypeScript Compiler API (`typescript >= 5.0`).
2. **Strict Zero-Execution Boundary**:
   - Source files are parsed purely as text strings using `ts.createSourceFile(filePath, content, ts.ScriptTarget.Latest, true)`.
   - Code is never compiled, evaluated, imported, or executed.
3. **High-Throughput Batch Processing Protocol**:
   - Spawning a separate Node.js process for each file adds 200–400ms startup latency per file.
   - The worker accepts an entire repository snapshot's files in a single JSON payload over `stdin`: `{"files": [{"path": "...", "content": "..."}]}`.
   - Structured parse diagnostics, imported identifiers, dynamic import types, and export statements are streamed to `stdout` in one pass, completing analysis of a 38-scenario benchmark in ~280ms.

### 16.2 Extension Coverage & Syntax Extraction
The TypeScript inspector provides full coverage across 8 file extensions:
- `.ts`, `.tsx`, `.mts`, `.cts`, `.js`, `.jsx`, `.mjs`, `.cjs`.

Extracted semantic structures include:
- **Import Statements**: Named (`import { A, B }`), default (`import React`), namespace (`import * as path`), side-effect (`import "./style.css"`), type-only (`import type { User }`), CommonJS (`require()`), and dynamic `import()` expressions.
- **Export Statements**: Named exports, default exports, and re-export barrel patterns (`export { Button } from "./button"`, `export * from "./types"`).
- **Dynamic Imports**: Distinguishes static string literals (`import("./modal")`) from unsupported computed expressions (`import("./plugins/" + name)`).
- **Exact Coordinates**: All imports, exports, and syntax diagnostics record exact line numbers, columns, and character offsets.

### 16.3 Bounded Deterministic Module Resolution
Module resolution implements a strict probe hierarchy:
1. **Repository Containment Boundary**:
   - Any relative import path that attempts directory traversal outside the repository snapshot root (e.g. `../../../../outside_repo`) is caught immediately.
   - It is marked as an `unsupported_reference` and prevented from resolving to or exposing host filesystem files.
2. **TypeScript Path Mapping (`tsconfig.json`)**:
   - Parses `compilerOptions.baseUrl` and `compilerOptions.paths` (e.g. `@/*` -> `src/*`).
   - Uses `strip_json_comments_and_trailing_commas()` to tolerate non-standard comments and trailing commas prevalent in tsconfig files.
3. **Relative Import Probing**:
   - Exact path if file exists.
   - Extension probes: `.ts`, `.tsx`, `.d.ts`, `.js`, `.jsx`, `.mts`, `.mjs`, `.cts`, `.cjs`.
   - Directory index probes: `<dir>/index.ts`, `<dir>/index.tsx`, `<dir>/index.js`, etc.
4. **Package Classification & Manifest Audit**:
   - Distinguishes Node built-in modules (`fs`, `path`, `crypto`, etc.) from external npm packages (`pkg:<name>`).
   - Audits `package.json` manifests (`dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies`).
   - Flags imported npm packages missing from `package.json` as `DEPENDENCY_IMPORT_FAILURE` (`CASE-031`) while preventing false positives on declared packages (`CASE-022`, `CASE-030`, `CASE-038`).

### 16.4 Unified Diagnostic Pipeline Integration
The TypeScript/JavaScript analysis seamlessly feeds the existing diagnostic engine without creating a duplicate pipeline:
- Components and dependencies are recorded using canonical `DependencyNode` and `DependencyEdge` dataclasses in `DiagnosticSystemMap`.
- Syntax errors, unresolved relative imports, undeclared packages, and unsupported dynamic expressions emit canonical `DiagnosticEvidenceRecord` models.
- The adaptive probe planner (`ProbePlanner`) dispatches `static_ast_syntax_check` and `downstream_independent_check` to the TypeScript parser when evaluating JS/TS files.
- The 38-scenario adversarial benchmark suite tests both single-language and polyglot repositories (`CASE-036`), achieving 100% accuracy and 0% false positives across healthy controls.

---

## 17. Java AST Analysis & Polyglot Dependency Intelligence (Implementation 014)

### 17.1 Safe, In-Process Compiler Tree Worker (`JavaAstWorker.java`)
ORACLE utilizes the standard OpenJDK 21 Compiler Tree API (`javax.tools.JavaCompiler` and `com.sun.source.tree.*`) implemented in `backend/oracle/inspection/JavaAstWorker.java` to perform exact syntax parsing of Java source files:
1. **Zero Untrusted Code Execution Invariant**:
   - The worker parses in-memory source strings wrapped in `SimpleJavaFileObject` by invoking `task.parse()`.
   - Only the syntactic and lexical analysis phase of the Java compiler executes.
   - Target code is never compiled to bytecode, loaded into any ClassLoader, evaluated, or executed on the host.
2. **Zero External Dependencies**:
   - To eliminate external JAR supply chain vulnerabilities and version mismatches, `JavaAstWorker.java` implements a self-contained, minimal JSON parser and serializer with zero third-party dependencies.
   - It communicates with the Python inspection adapter over standard input and output streams (`stdin`/`stdout`).
3. **High-Throughput Batch Processing Protocol**:
   - Compiling the Java worker once to `backend/oracle/inspection/JavaAstWorker.class` allows batch analysis of entire repository snapshots in a single JVM invocation.
   - Batch payloads transmit all repository Java source files in one JSON envelope, returning structured syntax diagnostics, declared packages, imported symbols, and type declarations within ~60–100ms.

### 17.2 Java Syntax Parsing & Coordinate Extraction
The Java AST worker supports modern Java syntax up through Java 21:
- **Type Declarations**: Standard classes, abstract classes, interfaces, enums, records (`record Point(int x, int y)`), nested static classes, and inner classes.
- **Import Statements**: Single-type imports (`import com.example.model.User;`), static member imports (`import static com.example.util.MathUtils.clamp;`), wildcard package imports (`import com.example.model.*;`), and wildcard static imports (`import static java.lang.Math.*;`).
- **Exact Coordinates**: Line numbers (1-indexed) and character offsets (1-indexed) are extracted for all syntax diagnostics and import declarations via `DiagnosticListener<JavaFileObject>` and `SourcePositions`.

### 17.3 Bounded Deterministic Module Resolution
Cross-module Java dependency resolution is performed by `backend/oracle/inspection/java_parser.py`:
1. **Global Symbol Table Construction**:
   - Scans all discovered Java files to map fully qualified class names (`com.example.service.UserService`) and simple type names to their declaring source files.
   - Maps package paths to member source files for fast containment queries.
2. **Standard Library Classification**:
   - Strict prefix matching against `JAVA_STDLIB_PREFIXES` (`java.`, `javax.`, `org.w3c.dom`, `org.xml.sax`, `sun.`, `jdk.`) guarantees zero false-positive undeclared package alerts for JDK APIs.
3. **Repository Namespace Inference**:
   - Extracts multi-segment package namespace prefixes (e.g. `com.example.*`) from declared packages across the repository.
   - Distinguishes broken internal project references (e.g. `import com.example.model.MissingAccount;` -> `unresolved_reference`) from external third-party library dependencies.
4. **Conservative Wildcard Handling**:
   - Wildcard package imports matching known internal packages are linked directly to the package module without manufacturing synthetic unresolved symbol errors.
5. **Cyclic Dependency Safety**:
   - Circular imports between Java classes (`ClassA` <-> `ClassB`) are recorded as valid cyclic dependency graph edges without infinite recursion or loop lockup.

### 17.4 Maven & Gradle Read-Only Manifest Inspection
Java dependency management metadata is extracted statically without invoking `mvn` or `gradle`:
1. **Maven `pom.xml` Static Parser (`parse_maven_pom`)**:
   - Read-only XML parsing extracting coordinates (`groupId`, `artifactId`, `version`), parent POM coordinates, packaging type, submodules, and declared `<dependencies>`.
   - Deterministic property expansion: resolves simple `${property.name}` values defined in `<properties>` or parent coordinates.
   - Preserves uncertainty: unresolvable properties (e.g. `${external.repo.version}`) are recorded in `unresolved_metadata` and flagged as diagnostic warnings without failing repository inspection.
2. **Gradle Build Script Static Parser (`parse_gradle_build`)**:
   - Analyzes `build.gradle` and `build.gradle.kts` using targeted static pattern extraction.
   - Identifies configuration scopes: `implementation`, `api`, `compileOnly`, `runtimeOnly`, `testImplementation`.
   - Preserves uncertainty: complex Groovy/Kotlin DSL constructs, external build plugins, or computed project dependencies (`implementation project(':core')`) are recorded as diagnostic uncertainty notes.
3. **Published Dependency-to-Package Mapping**:
   - Implements `KNOWN_JAVA_DEP_PREFIXES` to map common published Maven artifacts to their root runtime package namespaces (e.g. `com.google.guava:guava` -> `com.google.common.*`, `commons-lang3` -> `org.apache.commons.lang3.*`).

### 17.5 System Map & Diagnostic Pipeline Integration
The Java analysis engine seamlessly integrates into ORACLE's unified architecture:
- **Canonical Graph Representation**: Java source files become `source_file` components; package and class dependencies become `DiagnosticDependencyEdge` records.
- **Evidence Generation**: Syntax violations emit `syntax_error` evidence; missing internal types emit `unresolved_import` evidence; undeclared Maven/Gradle packages emit `undeclared_external_dependency` evidence.
- **Adaptive Probe Dispatch**: `ProbePlanner` routes `.java` probe targets to `parse_java_file` during `static_ast_syntax_check` and `downstream_independent_check` actions.
- **Adversarial Benchmark Expansion**: Evaluated across 22 new Java adversarial scenarios (`CASE-039` to `CASE-060`), bringing the benchmark suite to 60 scenarios with 100% Top-1 accuracy and 0% false positives on healthy controls.

---

## 18. End-to-End Product Validation, Persistence Fidelity, and Real-World Diagnostic Readiness (Implementation 015)

Implementation 015 proves that ORACLE operates as a complete, integrated diagnostic platform rather than a collection of isolated modules.

```mermaid
flowchart TD
    subgraph Client["Next.js Presentation Layer"]
        UI["Dashboard & Timeline UI"]
        API_CLIENT["Typed API Client (lib/api.ts)"]
        STATUS_CARD["Live Diagnostics (StatusCard.tsx)"]
    end

    subgraph API["FastAPI Routing & Contract Layer"]
        EP_HEALTH["GET /api/v1/health & /status"]
        EP_REPO["POST/GET/DELETE /api/v1/repositories"]
        EP_INSPECT["POST /api/v1/repositories/{id}/inspect"]
        EP_DIAG["POST /api/v1/repositories/{id}/diagnose"]
        EP_RUNS["GET /api/v1/diagnostics/runs & /{id}"]
        EP_PROBES["GET /api/v1/diagnostics/{id}/probes"]
        EP_DECISIONS["GET /api/v1/diagnostics/{id}/decisions"]
    end

    subgraph Core["Unified Diagnostic Orchestrator"]
        INGEST["Safe Ingestion & Path Containment"]
        POLY_PARSER["Polyglot AST Engine (Python, TS, Java)"]
        MANIFEST["Polyglot Manifest Resolver (Root & Subdirs)"]
        MAPPER["System Map & Dependency Graph"]
        EVID["Evidence Collector & Secret Redactor"]
        RANKER["Multi-Hypothesis Bayesian Ranker"]
        PLANNER["Adaptive Probe Planner & Bounded Loop"]
    end

    subgraph Persistence["Dual Persistence Architecture"]
        MEM["In-Memory Cache (_runs_by_id)"]
        PG[("PostgreSQL 16 + Alembic (DiagnosticRunRecord)")]
    end

    UI --> API_CLIENT
    STATUS_CARD --> API_CLIENT
    API_CLIENT --> API
    API --> Core
    EP_DIAG --> Core
    EP_RUNS --> Persistence
    Core --> Persistence
```

### 18.1 Multi-Layer Contract Synchronization
ORACLE enforces strict end-to-end contract parity between the Python backend schemas and TypeScript frontend interfaces:
1. **Investigation History & Decisions Dual-Alias**:
   - Backend `DiagnosticDecisionsResponse` exposes both `decisions` and `investigation_history` using automated Pydantic model validators, ensuring full interoperability with frontend components.
2. **Flexible Probe Outcomes & Details**:
   - `ProbeResult.details` supports string forensic summaries and structured metadata dictionaries (`string | Record<string, unknown>`).
   - `DiagnosticProbe.expected_outcomes` accepts lists of observable outcomes matching planner representations (`string[] | Record<string, string>`).
3. **Execution Gating & Status Reporting**:
   - `GET /api/v1/status` returns comprehensive diagnostic metadata:
     - `persistence_mode`: Transparently declares `"durable_postgresql"` when the database is operational, or `"in_memory_transient"` when running offline.
     - `docker_isolation_available`: Boolean status reflecting container engine readiness.
     - `supported_languages` & `supported_ecosystems`: Enumerates active analysis engines (`python`, `typescript`, `javascript`, `java`).

### 18.2 Persistence Semantics Across Process Restarts
ORACLE explicitly separates durable storage from transient caching:
1. **Durable Database Queries**:
   - `GET /api/v1/diagnostics/runs` queries `DiagnosticRunRecord` from PostgreSQL, ordered by `created_at DESC`, merging with active in-memory reports.
   - When the server process restarts (clearing in-memory caches), previously persisted diagnostic runs remain retrievable by UUID.
2. **Transparent Offline Demarcation**:
   - If PostgreSQL is uncontactable, ORACLE reports `"in_memory_transient"` persistence mode and never claims durable persistence.
   - Database schema migrations are verified offline via `alembic upgrade head --sql` using the PostgreSQL dialect.

### 18.3 Polyglot Manifest Intelligence in Complex Architectures
Real-world systems rarely locate all manifests at the repository root. ORACLE's manifest resolution:
- **Recursive First-Level Subdirectory Scanning**:
  - `extract_declared_dependencies()` and `load_package_json()` scan both the repository root and first-level subdirectories (e.g. `backend/pyproject.toml`, `frontend/package.json`).
  - Eliminates false positive `DEPENDENCY_IMPORT_FAILURE` alerts in monorepo and polyglot fullstack layouts.

### 18.4 Subprocess Isolation & Parser Resilience
Static inspection of TypeScript and Java involves external workers running Node.js and the JVM. ORACLE isolates these processes with multi-tiered safeguards:
- **Subprocess Timeout Recovery**:
  - Worker subprocesses execute under strict 30-second timeouts. If a worker hangs, the parser catches `subprocess.TimeoutExpired`, logs a diagnostic failure, and marks the component `analysis_failed` rather than crashing the orchestrator.
- **Malformed JSON Recovery**:
  - If a worker outputs non-JSON content (e.g. JVM warnings, Node out-of-memory logs), the parser catches `json.JSONDecodeError` and wraps the diagnostic into a `FileSyntaxError`.
- **URL Path Hygiene**:
  - Local repository URLs containing query parameters (`file:///path?token=xyz`) are sanitized to strip query strings and fragments before filesystem resolution, while preserving full token redaction in reporting.

---

## 19. Production Deployment Architecture, Containerization, and Operational Readiness (Implementation 016)

Implementation 016 packages ORACLE into a hardened, three-tier containerized production topology, establishing reproducible environment management, operational procedures, and defense-in-depth isolation.

```mermaid
flowchart TD
    subgraph Host["Production Deployment Boundary"]
        subgraph ExtNet["oracle_external (Bridge Network)"]
            FE["Frontend Container: oracle-frontend\nImage: node:20-alpine\nUser: nextjs (UID 1001)\nPort: 3000"]
            BE["Backend Container: oracle-backend\nImage: python:3.12-slim (Polyglot)\nUser: oracle (UID 10001)\nPort: 8000"]
        end

        subgraph IntNet["oracle_internal (Internal Only, Non-Routable)"]
            DB["Database Container: oracle-db\nImage: postgres:16-alpine\nHealthcheck: pg_isready\nVolume: oracle_pgdata"]
        end
    end

    FE -->|HTTP API Requests| BE
    BE -->|PostgreSQL Connection (Psycopg 3)| DB

    classDef secure fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef isolate fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    class FE,BE secure;
    class DB isolate;
```

### 19.1 Defense-in-Depth Security Invariants

1. **Network Segregation (`oracle_internal`)**:
   - The PostgreSQL 16 database resides exclusively within an internal, non-routable Docker bridge network (`internal: true`).
   - External ingress to the database is prohibited; only the backend container on `oracle_internal` can open connections to port 5432.
2. **Unprivileged Non-Root Execution**:
   - Backend processes execute under dedicated system user `oracle` (`UID 10001:GID 10001`).
   - Frontend processes execute under dedicated system user `nextjs` (`UID 1001:GID 1001`).
   - Root user execution is completely disallowed inside production containers.
3. **Protected Docker Host Boundary**:
   - The FastAPI backend container **never** mounts `/var/run/docker.sock`. Unrestricted daemon access from an API-facing container represents a critical root privilege escalation risk.
   - Dynamic test execution is gated: when Docker is unavailable or when dynamic execution is disabled, the system honestly marks dynamic probes unsupported and falls back safely to static AST evidence without executing target repository code on the host.
4. **Boot-Time Production Invariant Validation**:
   - In `ENVIRONMENT=production`, [`Settings`](file:///C:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/backend/oracle/core/config.py) strictly validates:
     - `debug=False` is mandatory; setting `debug=True` raises a fatal configuration exception.
     - Default unhardened database credentials (`postgres:postgres@localhost`) are rejected.
     - Wildcard CORS origins (`*`) are strictly prohibited.

### 19.2 Polyglot Runtime Packaging in Backend Container

The backend static analysis engine requires Python, Node.js (for the TypeScript Compiler API worker), and OpenJDK (for the Java Compiler Tree API worker):
- **Base Image**: `python:3.12-slim` (Debian Bookworm).
- **Embedded Polyglot Toolchains**:
  - `nodejs` and `npm` with global `typescript` package installation for `ts_ast_worker.mjs`.
  - `openjdk-17-jdk-headless` providing both `java` runtime and `javac` compiler.
- **Ahead-of-Time Class Compilation**:
  - `JavaAstWorker.java` is compiled during the Docker build stage (`javac /app/oracle/inspection/JavaAstWorker.java`), ensuring instant AST execution without runtime compilation lag.

### 19.3 Production Frontend Packaging with Next.js Standalone Runner

- **Multi-Stage Build**:
  - Stage 1 (`deps`): Installs dependencies with `npm ci`.
  - Stage 2 (`builder`): Compiles Next.js application with `output: "standalone"`, extracting only necessary dependencies.
  - Stage 3 (`runner`): Minimal `node:20-alpine` image copying `.next/standalone` and `.next/static`.
- **Footprint Reduction**:
  - Container image size reduced by >80% compared to full development node_modules, with zero build tooling present in the final runner.

### 19.4 Lifecycle Synchronization & Automated Migrations

- **Database Polling**:
  - Backend entrypoint (`deploy/entrypoint-backend.sh`) polls PostgreSQL connectivity using SQLAlchemy/psycopg with timeout loops before launching services.
- **Automated Alembic Migrations**:
  - Automatically runs `alembic upgrade head` upon verified database reachability.
- **Graceful Shutdown**:
  - Application lifespan handler traps termination signals (`SIGTERM` / `SIGINT`) and cleanly disposes the SQLAlchemy connection pool (`engine.dispose()`), preventing hanging socket locks.

### 19.5 Health & Status Monitoring

- **Liveness Probe**: `GET /api/v1/health` returns `HTTP 200` with service metadata (`app_name`, `version`, `environment`).
- **Readiness Probe**: `GET /api/v1/status` returns comprehensive subsystem status:
  - Database connectivity, driver, and active persistence mode (`durable_postgresql` vs `in_memory_transient`).
  - Docker sandbox isolation availability.
  - Polyglot static AST parser operational status (`python`, `typescript`, `java`, `go`).

---

## 20. Multi-Domain Generalization, Go Static Analysis, Telemetry Ingestion, and Calibrated ML Hypothesis Ranking (Implementation 017)

Implementation 017 expands ORACLE beyond static-first benchmarks and beyond its initial Python/TypeScript/Java language boundaries. It introduces native Go static analysis, polyglot runtime telemetry ingestion, calibrated probabilistic machine learning ranking, and empirical validation across 20 independently defined generalization scenarios.

```mermaid
flowchart TD
    TargetRepo["Target Repository (.py, .ts, .java, .go)"]
    RuntimeSymptom["Runtime Telemetry & Tracebacks (Python / Node / Java / Go)"]
    
    subgraph InspectionLayer["Polyglot Static & Telemetry Ingestion"]
        PyParser["Python AST Parser"]
        TSWorker["TypeScript Compiler API Worker"]
        JavaWorker["OpenJDK Compiler Tree Worker"]
        GoParser["Zero-Execution Go AST & go.mod Adapter"]
        TelemetryAnalyzer["Telemetry & Stack Trace Analyzer"]
    end

    TargetRepo --> PyParser & TSWorker & JavaWorker & GoParser
    RuntimeSymptom --> TelemetryAnalyzer

    subgraph EvidencePipeline["Discrete Evidence & System Map"]
        SystemMap["Polyglot System Map (Nodes & Edges)"]
        EvidenceSet["Discrete Evidence Records (Provenance & Limitations)"]
    end

    PyParser & TSWorker & JavaWorker & GoParser --> SystemMap
    PyParser & TSWorker & JavaWorker & GoParser & TelemetryAnalyzer --> EvidenceSet

    subgraph FeatureEngineering["Leak-Free Feature Extraction"]
        FeatureExtractor["extract_hypothesis_features (NUM_FEATURES=24)"]
        NoLabels["Zero Ground Truth / Scenario ID Leakage Guarantee"]
    end

    SystemMap & EvidenceSet --> FeatureExtractor

    subgraph CandidateRankers["Candidate Diagnostic Hypothesis Rankers"]
        Heuristic["Heuristic Ranker (Deterministic Baseline)"]
        CalibratedLogistic["Calibrated Logistic Regression (Platt Scaling)"]
        CalibratedRF["Calibrated Random Forest Ensemble (Isotonic/Sigmoid)"]
    end

    FeatureExtractor --> Heuristic & CalibratedLogistic & CalibratedRF

    subgraph AdaptivePlanning["Adaptive Uncertainty Reduction Loop"]
        ProbePlanner["Adaptive Probe Planner (Max EIG / Cost)"]
        EntropyMonitor["Shannon Entropy Monitor H(P)"]
        ContradictionEngine["Contradiction Refutation & Mass Redistribution"]
    end

    CalibratedRF --> ProbePlanner
    ProbePlanner --> EntropyMonitor
    EntropyMonitor --> ContradictionEngine
```

### 20.1 Zero-Execution Go Static Analysis Adapter

ORACLE inspects Go source files (`.go`) and module manifests (`go.mod`) with zero host binary dependencies, maintaining absolute WDAC compliance and defense-in-depth security:
- **Manifest Parser (`parse_go_mod`)**: Extracts module directives, Go version constraints, direct dependencies, indirect dependencies, and module `replace` directives without executing `go mod` binaries.
- **Go Standard Library Classification**: Distinguishes 60+ core standard library packages (`fmt`, `net/http`, `crypto`, `encoding/json`, `os`, `sync`, etc.) from third-party and local packages.
- **Lexical and Syntax Balance Diagnostics**: Captures unclosed token boundaries (`{`, `(`, `[`), unmatched closing tokens, and unclosed multi-line comments (`/* ... */`) with exact line and column coordinate provenance.
- **Dependency Resolution**: Maps imported Go packages to `resolved_stdlib`, `resolved_internal` (local repository packages), or `external_package` (verified against `go.mod`), emitting `unresolved_reference` when undeclared external packages are imported.

### 20.2 Polyglot Runtime Telemetry and Non-Static Fault Ingestion

Many real-world software defects (database connection timeouts, network routing failures, API contract validation mismatches, configuration omissions, and JSON deserialization errors) cannot be established by static AST analysis alone.
- **Polyglot Traceback Parser (`parse_runtime_traceback`)**: Parses and extracts innermost root frames from:
  - Python tracebacks (`File "...", line X, in ...`)
  - Node.js / TypeScript stack traces (`at func (path/file.ts:123:45)`)
  - Java exception traces (`at com.example.Class.method(File.java:88)`)
  - Go runtime panic traces (`panic: ... goroutine 1 [running]: \n /path/file.go:45`)
- **Deterministic Symptom Classifier (`classify_symptom_category`)**: Categorizes error messages and exception classes into the ORACLE Fault Taxonomy with high precision:
  - `DATABASE_CONNECTIVITY_SCHEMA`: Socket refusal, port 5432/3306 timeouts, deadlocks, and migration mismatches.
  - `API_COMMUNICATION_FAILURE`: HTTP 502/503/504, client `ConnectTimeout`, TLS handshake failures, and HTTP 429 rate limits.
  - `IO_CONTRACT_VIOLATION`: Pydantic/JSONSchema validation errors, HTTP 422, and missing required payload keys.
  - `DATA_VALIDATION_TRANSFORMATION`: `JSONDecodeError`, `UnicodeDecodeError`, zero division, and timezone conversion defects.
  - `CONFIG_MISSING_OR_INVALID`: Missing mandatory environment variables, unreadable `.env`, and YAML/TOML syntax defects.
- **Environment Configuration Auditing (`audit_environment_configuration`)**: Cross-references declared configuration templates (`.env.example`, `.env.template`) against local `.env` files and environment variables, emitting discrete configuration evidence before runtime crashes occur.

### 20.3 Leak-Free Machine Learning Feature Representation

The ML feature extractor (`extract_hypothesis_features`) generates dense 24-dimensional feature vectors strictly from observable evidence signals, graph structural properties, and telemetry confidences:
- **No Ground Truth Leakage**: Ground truth labels, scenario IDs, project titles, and file contents are strictly barred from feature vectors.
- **Feature Schema**:
  1. Counts of supporting evidence by reliability (`direct_observation`, `inferred_signal`, `limited_context`).
  2. Number of contradicting evidence records from active probes.
  3. Binary flags for evidence types (`syntax_error`, `unresolved_import`, `undeclared_dependency`, `runtime_telemetry`).
  4. Telemetry maximum confidence score.
  5. Verification status indicators (`verified`, `partially_verified`, `supported`, `candidate`, `contradicted`, `insufficient_evidence`).
  6. Graph structural metrics (node count, edge count, unresolved edge ratio).
  7. Evidence diversity and target component localization flags.

### 20.4 Calibrated ML Diagnostic Ranking Models

Candidate ML ranking models replace raw heuristic point systems with well-calibrated posterior probabilities:
- **Calibrated Logistic Regression**: Linear model with Platt scaling (`CalibratedClassifierCV(LogisticRegression(), method="sigmoid")`).
- **Calibrated Random Forest Ensemble**: Non-linear ensemble (`CalibratedClassifierCV(RandomForestClassifier(n_estimators=50), method="sigmoid")`) capturing interaction effects between conflicting evidence signals.
- **Contradiction Refutation**: Negative probe findings apply severe exponential penalties ($0.2^k$) to refuted candidates, naturally redistributing probability mass to surviving hypotheses.
- **Deliberate Abstention Quality**: When the highest predicted probability falls below the confidence threshold ($\max P < 0.25$) or when inspecting healthy / out-of-distribution repositories, the engine explicitly marks `verification_status="insufficient_evidence"` and abstains rather than manufacturing false-positive diagnoses.

### 20.5 Adaptive Probe Efficiency & Information Gain Evaluation

The adaptive probe evaluation framework (`evaluate_probe_policies`) mathematically validates the probe planner against fixed sequence policies:
- **Shannon Entropy Metric**: $H(P) = -\sum_{i} P(h_i) \log_2 P(h_i)$.
- **Empirical Superiority**: Adaptive planning achieves higher probe efficiency ($\Delta H / \text{Cost}$) by prioritizing high Expected Information Gain (EIG) probes and terminating early upon root-cause verification, avoiding up to 60% of redundant probes compared to brute-force sequences.

---

## 21. Independent Audit, Verification Framework & Polyglot Lexical Invariants (Implementation 018)

Implementation 018 conducted an independent evidence-based audit of ORACLE's static inspection, telemetry parsing, and machine learning pipelines, resolving confirmed defects and establishing defensible evaluation standards.

```mermaid
flowchart TD
    RawCode["Target Source Code (.go, .py, .ts, .java)"]
    Lexer["6-State Lexical Scanner (Zero Host Execution)"]
    SafeDelim["Delimiter Stack (Strings & Comments Masked)"]
    SafeImports["Package & Import Declarations Extracted"]
    
    RawTelemetry["Runtime Telemetry & Tracebacks"]
    Redactor["Secret Sanitizer (redact_secrets)"]
    CausalChain["Nested & Chained Traceback Parser"]
    
    FeatureExtractor["24-Dimensional Leak-Free Feature Vector"]
    
    subgraph EvaluationProtocols["Defensible ML Evaluation Protocols"]
        ZeroShot["Zero-Shot Domain Transfer (Synthetic Trained)"]
        CV5Fold["5-Fold Scenario-Family Cross-Validation"]
        Calib10Bin["10-Bin Expected Calibration Error (ECE)"]
    end
    
    RawCode --> Lexer
    Lexer --> SafeDelim & SafeImports
    RawTelemetry --> Redactor --> CausalChain
    SafeDelim & SafeImports & CausalChain --> FeatureExtractor
    FeatureExtractor --> EvaluationProtocols
```

### 21.1 6-State Lexical Scanner & Delimiter Balancing

Prior to Implementation 018, delimiter balancing (`{}`, `()`, `[]`) evaluated characters across raw lines without tracking literal state boundaries, causing false syntax errors when delimiters appeared in strings, struct tags, runes, or comments.
ORACLE now implements a zero-execution 6-state lexical scanner in `backend/oracle/inspection/go_parser.py`:
- `STATE_NORMAL`: Tracks delimiter balance and transitions into comments, strings, or runes.
- `STATE_LINE_COMMENT`: Ignores characters until newline (`\n`).
- `STATE_BLOCK_COMMENT`: Scans until `*/`; detects unclosed comments at EOF with start coordinates.
- `STATE_INTERPRETED_STR`: Ignores delimiters inside `"..."`; handles escape sequences (`\"`, `\\`); flags unescaped newlines.
- `STATE_RAW_STR`: Handles multiline backtick literals (`` `...` ``); ignores all delimiters; flags unclosed raw literals at EOF.
- `STATE_RUNE`: Ignores rune delimiters like `'{'` or `'\''`.

### 21.2 Privacy Sanitization & Telemetry Run-Scoping

Runtime tracebacks frequently contain sensitive connection strings or bearer tokens. ORACLE establishes two privacy invariants in `telemetry_analyzer.py`:
1. **Mandatory Secret Redaction**: All tracebacks, symptom strings, and exception messages pass through `oracle.inspection.policy.redact_secrets` before tokenization, ensuring credentials (`postgres://user:pass@host`, bearer tokens, AWS keys) are scrubbed to `[REDACTED]`.
2. **Run-Scoped Evidence Identifiers**: Evidence records generated from telemetry are scoped to the specific diagnostic run (`EVID-TELEM-{run_id[:8]}-{seq:03d}`), preventing evidence ID collisions in multi-tenant or concurrent operations.
3. **Chained Causal Analysis**: Python chained exceptions (`The above exception was the direct cause...`) and Java nested exceptions (`Caused by:`) are recursively traversed to extract the innermost fault origin.

### 21.3 Defensible Machine Learning Evaluation Protocol

To prevent overfitting claims and ensure methodological integrity, ORACLE separates evaluation into two complementary regimes:
1. **Zero-Shot Domain Transfer**: Models trained strictly on synthetic physics-based signal distributions are evaluated on 20 held-out generalization scenarios, testing out-of-domain transfer without scenario fine-tuning.
2. **Scenario-Family 5-Fold Cross-Validation**: The 20 generalization scenarios are partitioned into 5 thematic families (Go Ecosystem, Runtime Faults, Telemetry/Config, Polyglot Monorepo, Robustness/OOD). In each fold, the model trains on 4 families (16 scenarios) and tests on the 5th unseen family (4 scenarios).
3. **Documented 10-Bin Calibration**: Expected Calibration Error (ECE) is computed across 10 uniform probability bins on $[0.0, 1.0]$:
   $$\text{ECE} = \sum_{b=1}^{10} \frac{|B_b|}{N} |\text{acc}(B_b) - \text{conf}(B_b)|$$
   Demonstrating an ECE reduction from 0.6500 (heuristic points) to 0.3548 (Calibrated Random Forest).









