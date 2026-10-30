# ORACLE

**Open-source Resilience & Adaptive Causal Localization Engine**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#technology-stack)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](#technology-stack)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.4-black.svg)](#technology-stack)
[![React 19](https://img.shields.io/badge/React-19.3-61dafb.svg)](#technology-stack)
[![TypeScript 5](https://img.shields.io/badge/TypeScript-5.0%2B-3178c6.svg)](#technology-stack)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](#technology-stack)

ORACLE is an adaptive technical diagnostic engine and evidence localization platform for distributed software systems. It investigates software failures by combining zero-untrusted-execution static AST analysis, sanitized runtime telemetry ingestion, calibrated machine learning hypothesis ranking, and Shannon entropy-driven probe planning.

Instead of guessing a single root cause or executing untrusted code on the host, ORACLE constructs a directed dependency graph of the target codebase, extracts discrete empirical evidence, formulates competing causal hypotheses, and produces an audit-ready diagnostic report with explicit uncertainty boundaries.

---

## Table of Contents

- [The Problem](#the-problem)
- [System Overview](#system-overview)
- [Core Capabilities](#core-capabilities)
- [How ORACLE Works](#how-oracle-works)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
  - [Running Backend & Frontend](#running-backend--frontend)
  - [Verified Endpoints](#verified-endpoints)
- [Project Structure](#project-structure)
- [User Workflows](#user-workflows)
- [Machine Learning & Diagnostic Evaluation](#machine-learning--diagnostic-evaluation)
- [Security & Execution Safety](#security--execution-safety)
- [Testing & Verification](#testing--verification)
- [Deployment](#deployment)
- [Current Limitations & Roadmap](#current-limitations--roadmap)
- [Contributing](#contributing)
- [License & Legal Notice](#license--legal-notice)

---

## The Problem

Modern software architectures span multiple programming languages, polyglot build tools, and distributed cloud services. When an incident occurs, traditional monitoring tools face fundamental limitations:

1. **Symptom–Cause Disconnect:** An unhandled exception or crash in an edge service (e.g. HTTP 500 in an API gateway) is frequently caused by a failure multiple hops upstream, such as an unresolved relative export in a TypeScript service, a malformed build manifest, or an unreachable database socket.
2. **Untrusted Code Execution Risks:** Automated diagnostic tools that attempt to reproduce failures by dynamically running scripts or importing target modules directly on the host risk arbitrary code execution, credential exfiltration, and resource exhaustion.
3. **Premature Diagnostic Lock-in:** Heuristic tools typically lock onto the first visible symptom, ignoring competing explanations and failing to account for multiple interacting defects.
4. **Credential Leakage in Telemetry:** Stack traces and error logs submitted during an incident frequently contain raw database connection strings, JWT bearer tokens, or cloud API keys.

ORACLE addresses these challenges by enforcing a strict **zero-untrusted-execution boundary** during static inspection, automatically sanitizing telemetry credentials, evaluating competing hypotheses in parallel, and calculating information gain before proposing verification actions.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ORACLE WORKSPACE                               │
│  [ Gateway: 8000 (Live) ]   [ DB: PostgreSQL ]   [ Execution: Docker/Safe ] │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│    SYSTEM TOPOLOGY MAP   │   HYPOTHESIS EXPLORER    │   EVIDENCE INSPECTOR  │
│                          │                          │                       │
│    (SVG Graph Canvas)    │  ▶ H-01 [Rank 1 • 94%]   │  [STATIC_ANALYSIS]    │
│                          │    Auth Token Expiry     │  src/auth_service.ts  │
│    [Clean]    [Defect]   │    ΔH: -1.42 bits        │  Line: 42             │
│       ○ ───────▶ ●       │                          │  SyntaxError token    │
│    (api)       (auth)    │  ▷ H-02 [Rank 2 • 38%]   │                       │
│                          │    DB Socket Refusal     │  Reliability: Direct  │
│    [Chartreuse Edge]     │    ΔH: -0.32 bits        │  Secret Redacted: YES │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

The ORACLE interface is designed around an editorial engineering aesthetic:
- **Jet Black (`#09090B`)** technical foundations with Deep Charcoal (`#151519`) surfaces.
- **Hot Pink (`#F20B91`)** for critical fault indicators, primary actions, and localized defects.
- **Chartreuse (`#D4FF32`)** for active AST dependency paths, verification achievements, and technical highlights.
- **Warm White (`#F5F3EF`)** and **Muted Gray (`#85858D`)** typography for readability.

---

## Core Capabilities

### 1. Multi-Language Static Code Analysis
Parses source code into syntactic dependency representations without executing target files:
- **Python:** Pure standard-library `ast.parse()` inspection. No project modules are ever imported or evaluated.
- **TypeScript / JavaScript:** Isolated Node.js worker (`ts_ast_worker.mjs`) leveraging the official Microsoft TypeScript Compiler API (`ts.createSourceFile`). Handles `.ts`, `.tsx`, `.js`, `.jsx`, `.mts`, and `.cjs` across ES Modules and CommonJS.
- **Java:** OpenJDK Compiler Tree API worker (`JavaAstWorker.java`) executing exclusively the syntactic parse phase (`task.parse()`). Extracts packages, imports, classes, and Maven/Gradle dependencies without generating bytecode or loading classes.
- **Go:** Zero-host-dependency lexical scanner and AST parser (`go_parser.py`) isolating tokens, standard library imports (60+ packages), and `go.mod` dependencies.

### 2. Directed Dependency & System Mapping
Constructs a normalized, directed acyclic architectural graph (`DiagnosticSystemMap`):
- Classifies import edges into `stdlib`, `internal`, `external`, and `unresolved`.
- Maps relative imports across multi-level directory structures.
- Isolates escaping references attempting to break outside repository containment boundaries.

### 3. Runtime Telemetry Ingestion & Secret Redaction
Ingests runtime error messages, application logs, and multi-line stack traces:
- Parses Python tracebacks (including chained exceptions), Node.js/V8 errors, Java stack traces (with recursive `Caused by:` isolation), and Go panics.
- Automatically executes regex-based credential scrubbers (`redact_secrets()`) to strip database passwords, JWT tokens, AWS access keys (`AKIA...`), and GitHub tokens (`ghp_...`) before storage or analysis.

### 4. Empirical Evidence Collection
Generates typed evidence records (`DiagnosticEvidenceRecord`):
- Tags each evidence item with reliability tiers: `direct_observation` (AST syntax defects, exact stack traces) vs. `inferred_signal` (dependency heuristics, manifest mismatches).
- Preserves exact source location coordinates (file path, line number, column number).

### 5. Calibrated Machine Learning Hypothesis Ranking
Formulates competing causal explanations mapped to a 10-class versioned Fault Taxonomy:
- Extracts 24 dense, target-leakage-free features capturing AST graph topology, telemetry correlations, and manifest discrepancies.
- Computes calibrated probabilities via Platt/Sigmoid scaling over an ensemble ranking pipeline.

### 6. Adaptive Diagnostic Probe Planning
Optimizes next-step investigation using information theory:
- Calculates expected Shannon entropy reduction ($\Delta H / \text{Cost}$) to prioritize probes that yield maximum discriminatory power at lowest cost.
- Classifies candidate probes by Safety Tier (`Safe Host AST Check` vs. `Container Required`).
- Automatically halts investigation loops via formal stopping criteria (confident confirmation, diminishing returns, or iteration exhaustion).

### 7. Execution Safety & Docker Isolation Gating
Enforces isolation boundaries when dynamic verification is requested:
- Preflight validation verifies whether Docker isolation is reachable and safe.
- Dynamic test execution is restricted to ephemeral containers with `--read-only` root filesystems, dropped capabilities (`--cap-drop ALL`), network disconnection (`--network none`), and execution memory limits.
- If Docker is unavailable, dynamic probes are **strictly gated and skipped**. ORACLE never executes unisolated code on the host machine.

---

## How ORACLE Works

The diagnostic lifecycle follows an 8-stage pipeline from target intake to final report generation:

```mermaid
flowchart TD
    A[Target Intake<br/>Local Path or Git URI] --> B[Path Containment & Security Ingestion<br/>Snapshot Acquisition & Quota Check]
    B --> C[Polyglot AST Static Analysis<br/>Python • TypeScript • Java • Go]
    C --> D[System Dependency Graph<br/>Internal • External • Unresolved]
    
    T[Runtime Telemetry Input<br/>Logs & Stack Traces] --> S[Secret Redaction Engine<br/>Passwords, Bearer Tokens, Keys]
    S --> E[Empirical Evidence Extraction<br/>Direct Observations & Provenance Coordinates]
    D --> E
    
    E --> F[Causal Hypothesis Formulation<br/>Mapped to Versioned Fault Taxonomy]
    F --> G[ML Feature Extraction & Calibration<br/>24 Leak-Free Features • Platt Scaling]
    G --> H{Adaptive Probe Planning<br/>Shannon Entropy Gain vs Cost}
    
    H -->|Host Safe AST Probe| I[Static Verification Execution]
    H -->|Dynamic Probe & Docker Available| J[Isolated Container Worker<br/>--read-only • --cap-drop ALL • --network none]
    H -->|Docker Unavailable| K[Gated Safe Skip<br/>Preserve Uncertainty]
    
    I --> L[Stopping Policy Evaluation<br/>Confident Finding • Diminishing Returns • Max Loops]
    J --> L
    K --> L
    
    L --> M[Editorial Deliverable Report<br/>Executive Finding • Provenance • Uncertainty Disclosure]
    M --> N[Persistence Layer<br/>PostgreSQL Durable / In-Memory Transient]
```

---

## System Architecture

ORACLE is architected as a modular monolith with decoupled presentation, orchestration, analysis, and execution layers:

```mermaid
graph TB
    subgraph ClientLayer["Presentation Layer (Port 3000)"]
        UI["Next.js 16 App Router (React 19)"]
        Hero["Cinematic Hero & Scroll Story (/)"]
        Console["Operations Console (/dashboard)"]
        Dispatch["Dispatch Terminal (/diagnostics/new)"]
        Room["3-Panel Investigation Room (/workspace)"]
        Audit["Run History Audit (/history)"]
        ReportView["Editorial Deliverable (/reports/:id)"]
    end

    subgraph APILayer["API Gateway & Service Layer (Port 8000)"]
        FastAPI["FastAPI 0.115+ (oracle.main)"]
        Router["Versioned Router (/api/v1)"]
        HealthEP["/health & /status Probes"]
        RepoEP["/repositories Endpoints"]
        DiagEP["/diagnostics Endpoints"]
    end

    subgraph EngineLayer["Core Diagnostic Engine (backend/oracle)"]
        Orchestrator["DiagnosticOrchestrator (service.py)"]
        Snapshot["SnapshotManager (snapshot.py)"]
        Policy["ResourceLimiter & SecretRedactor (policy.py)"]
        Intelligence["Hypothesis & Probe Planner (intelligence.py)"]
        Stopping["StoppingCriteria (stopping.py)"]
        Telemetry["TelemetryAnalyzer (telemetry_analyzer.py)"]
    end

    subgraph InspectionLayer["Polyglot AST Parsers"]
        PyParser["Python ast.parse()"]
        TSWorker["ts_ast_worker.mjs (TypeScript Compiler API)"]
        JavaWorker["JavaAstWorker.java (OpenJDK Compiler Tree API)"]
        GoParser["go_parser.py (Zero-Dependency Go Lexer)"]
    end

    subgraph MLLayer["Machine Learning Pipeline (ml/)"]
        Taxonomy["Fault Taxonomy (v1.0.0, 10 Classes)"]
        FeatureExtractor["24-Feature Representation Extractor"]
        Ranker["Calibrated ML Ranker (Random Forest + Platt)"]
        ProbeEval["Shannon Entropy Evaluator (ΔH)"]
    end

    subgraph ExecutionLayer["Dynamic Isolation Boundary"]
        Preflight["IsolationPreflight (preflight.py)"]
        DockerWorker["DockerExecutionProvider (provider.py)"]
        Sandbox["Ephemeral Container (--read-only, --network none)"]
    end

    subgraph PersistenceLayer["Dual-Mode Persistence"]
        DBRouter["SessionRouter / Fallback Manager"]
        Postgres[("PostgreSQL 16 (Durable)")]
        Transient[("In-Memory State (Transient)")]
    end

    UI --> FastAPI
    FastAPI --> Router
    Router --> Orchestrator
    Orchestrator --> Snapshot
    Orchestrator --> Policy
    Orchestrator --> InspectionLayer
    Orchestrator --> Telemetry
    Orchestrator --> MLLayer
    Orchestrator --> Intelligence
    Intelligence --> Preflight
    Preflight -->|Docker Available| DockerWorker
    DockerWorker --> Sandbox
    Orchestrator --> DBRouter
    DBRouter -->|Online| Postgres
    DBRouter -->|Offline| Transient
```

---

## Technology Stack

| Layer | Technologies | Responsibility |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16.4.3, React 19.3.0, TypeScript 5, Tailwind CSS v4 | App Router routes, SVG interactive topology, 3-panel workspace, pure CSS keyframe animations. |
| **Backend API** | Python 3.11–3.14, FastAPI 0.115+, Pydantic v2, Uvicorn, AnyIO | REST endpoints, request validation, snapshot lifecycle management, CORS boundary. |
| **Static Inspection** | Python `ast`, TypeScript Compiler API (`ts.createSourceFile`), OpenJDK Compiler Tree API (`task.parse()`), native Go lexer | Safe zero-execution AST dependency graph extraction across four language ecosystems. |
| **Telemetry & Security** | Regex Credential Sanitizer, POSIX Path Containment (`os.path.commonpath`), Quota Enforcers | Automatic credential redaction (JWT, passwords, API keys) and resource boundary limits. |
| **Machine Learning** | Scikit-learn, NumPy, Platt Calibrator, Shannon Entropy Calculator | 24-dimensional feature extraction, 10-class taxonomy classification, expected information gain. |
| **Persistence** | PostgreSQL 16, SQLAlchemy 2.0, psycopg 3 (`postgresql+psycopg://`), Alembic 1.20 | Reversible database migrations, durable relational storage with automatic in-memory transient fallback. |
| **Execution Isolation** | Docker Engine, Docker Compose v2 | Capability-dropped, read-only ephemeral container execution with preflight isolation verification. |
| **Testing** | Pytest 9.1 (`testing/`), Node.js Test Runner (`node:test`) | Unit tests, AST parser validation, ML leakage invariance checks, API client tests, deployment smoke. |

---

## Getting Started

### Prerequisites

- **Python:** 3.11, 3.12, 3.13, or 3.14.
- **Node.js:** v20.x, v22.x, or v24.x and `npm`.
- **Git:** Installed and available on your system `PATH`.
- *(Optional for dynamic execution & durable persistence):* Docker 24+ with Docker Compose v2, or a running PostgreSQL 15/16 instance.

### Local Development Setup

#### 1. Clone the repository
```bash
git clone https://github.com/mshas/ORACLE.git
cd ORACLE
```

#### 2. Configure Python Virtual Environment (Backend)
```bash
# Create virtual environment at repo root
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS (Bash):
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements-dev.txt
```

#### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

#### 4. Configure Environment Variables
Copy the example environment template for the backend:
```bash
# Windows (PowerShell)
Copy-Item backend/.env.example backend/.env

# Linux / macOS
cp backend/.env.example backend/.env
```

Default `.env` configuration:
```ini
ORACLE_APP_NAME=ORACLE
ORACLE_ENVIRONMENT=development
ORACLE_DEBUG=True
ORACLE_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/oracle_db
ORACLE_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

> [!NOTE]
> If a local PostgreSQL instance is not running, ORACLE automatically operates in `in_memory_transient` mode. Target repositories, AST graphs, and diagnostic reports function normally in memory for development and demonstration without crashing.

---

### Running Backend & Frontend

For local development, run the backend and frontend in separate terminals:

#### Terminal 1: Backend Service
```bash
# From repository root (with .venv activated)
python -m uvicorn oracle.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

#### Terminal 2: Frontend Client
```bash
# From frontend/ directory
cd frontend
npm run dev
```

Open your browser to:
- **Frontend Application:** [http://localhost:3000](http://localhost:3000)
- **Interactive API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **System Status & Telemetry:** [http://localhost:8000/api/v1/status](http://localhost:8000/api/v1/status)

---

### Verified Endpoints

The FastAPI backend exposes the following versioned REST API:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health, version, and operational environment. |
| `GET` | `/api/v1/status` | Database connectivity, persistence mode (`durable_postgresql` vs `in_memory_transient`), and Docker host isolation status. |
| `GET` | `/api/v1/repositories` | List registered codebases and targets. |
| `POST` | `/api/v1/repositories` | Register a new target directory (`file:///...`) or remote Git repository (`https://...`). |
| `GET` | `/api/v1/repositories/{id}` | Retrieve metadata for a specific repository. |
| `DELETE`| `/api/v1/repositories/{id}` | Delete a repository registration and associated diagnostic runs. |
| `POST` | `/api/v1/repositories/{id}/inspect` | Execute safe zero-execution static inspection and return AST component graph. |
| `POST` | `/api/v1/repositories/{id}/diagnose` | Run the complete 8-stage diagnostic engine and generate a diagnostic report. |
| `GET` | `/api/v1/repositories/{id}/diagnostics/latest` | Retrieve the latest diagnostic report for a target repository. |
| `GET` | `/api/v1/diagnostics/runs` | List all historical diagnostic investigation runs. |
| `GET` | `/api/v1/diagnostics/{run_id}` | Retrieve complete diagnostic report for a run by UUID. |
| `GET` | `/api/v1/diagnostics/{run_id}/probes` | Inspect candidate and executed diagnostic probes. |
| `GET` | `/api/v1/diagnostics/{run_id}/decisions` | Inspect diagnostic probe planning iterations and Shannon entropy decisions. |

---

## Project Structure

```
ORACLE/
├── backend/                  # FastAPI Backend Service
│   ├── alembic/              # Database migration environment and revision scripts
│   ├── oracle/
│   │   ├── api/v1/           # REST endpoints (/health, /status, /repositories, /diagnostics)
│   │   ├── core/             # Pydantic Settings and logging configuration
│   │   ├── db/               # SQLAlchemy engine, session router, and in-memory transient fallback
│   │   ├── diagnostics/      # Orchestrator, hypothesis formulation, probe planning, stopping rules
│   │   ├── execution/        # Docker execution worker and preflight isolation checker
│   │   ├── inspection/       # AST parsers (Python, TypeScript worker, Java worker, Go lexer)
│   │   ├── models/           # SQLAlchemy ORM models (Repository, DiagnosticRun)
│   │   └── schemas/          # Pydantic request/response validation schemas
│   ├── pyproject.toml        # Backend build configuration
│   └── requirements-dev.txt  # Pinned backend dependencies
├── frontend/                 # Next.js 16 Web Application
│   ├── src/
│   │   ├── app/              # App Router routes (/, /dashboard, /diagnostics/new, /workspace, /history, /reports)
│   │   ├── components/       # UI components (CinematicHero, InteractiveSystemMap, Workspace, etc.)
│   │   ├── lib/              # Resilient, typed API client (api.ts)
│   │   └── types/            # TypeScript contract interfaces matching backend schemas
│   ├── package.json          # Node dependencies (Next.js 16, React 19, Tailwind CSS v4)
│   └── tsconfig.json         # Strict TypeScript configuration
├── ml/                       # Machine Learning & Diagnostic Evaluation
│   ├── baselines/            # Baseline classifier specifications
│   ├── benchmark/            # Controlled benchmark runner, scenarios (CASE-001 to 060), evaluation
│   ├── dataset/              # Generalization dataset fixtures and schema
│   ├── experiments/          # Cross-validation splitters and evaluation metrics
│   ├── planning/             # Shannon entropy probe selection and evaluation
│   ├── ranking/              # Calibrated ML ranker, heuristic ranker, 24-feature extractor
│   └── taxonomy/             # Versioned 10-class Fault Taxonomy (v1.0.0)
├── deploy/                   # Containerized & Cloud Deployment
│   ├── docker-compose.yml    # Production multi-container topology
│   ├── Dockerfile.backend    # Polyglot backend container (Python, Node.js, OpenJDK)
│   ├── Dockerfile.frontend   # Next.js standalone container
│   ├── scripts/              # Automated VM setup and persistence verification scripts
│   └── docs/                 # Cloud deployment and cost model documentation
├── doc/                      # Comprehensive Engineering Documentation
│   ├── ARCHITECTURE.md       # Full architecture specification
│   ├── COMMANDS.md           # Developer commands reference
│   └── IMPLEMENTATION_STATUS.md # Milestone tracking
└── testing/                  # Centralized Test Suites
    ├── backend/              # Pytest backend tests (config, db, parsers, diagnostics, execution)
    ├── ml/                   # Pytest ML tests (feature leakage, taxonomy, benchmarks)
    ├── deploy/               # Deployment smoke test
    ├── frontend/             # Native node:test API client tests
    └── fixtures/             # Controlled benchmark codebases (proj_01 to proj_38)
```

---

## User Workflows

### 1. Launching an Investigation (`/diagnostics/new`)
Navigate to **New Diagnosis**. Select a previously registered repository or enter a new URI:
- **Local Directory:** `file:///c:/path/to/project` (Windows) or `file:///path/to/project` (Linux/macOS).
- **Remote Git Repository:** `https://github.com/org/repo.git`.
- **Optional Runtime Telemetry:** Paste a runtime error traceback. The interface displays an active `🛡 Secret Redaction Active` notice.
- **Dynamic Container Probes:** Toggle dynamic execution. If Docker is unavailable, the backend safely enforces read-only static inspection.

### 2. Exploring System Topology (`/workspace` System Map)
The left panel renders the system's topological dependency graph:
- Green/Chartreuse nodes represent verified clean components.
- Hot Pink nodes indicate localized defects (e.g. syntax errors, broken imports).
- Amber nodes denote unresolved package imports or missing modules.
- Click any node to inspect callers, dependents, and metadata in the drawer.
- Toggle between **Canvas View** and **Matrix Table** for dense codebases.

### 3. Reviewing Hypotheses (`/workspace` Hypothesis Explorer)
The center panel lists competing causal hypotheses ranked by ML probability and information gain:
- Each hypothesis displays its rank, confidence level (`high`, `medium`, `low`, `uncertain`), and category.
- Evidence references are color-coded: **Chartreuse (`+ EVID`)** for supporting evidence; **Hot Pink (`- EVID`)** for contradictory evidence.
- Clicking a hypothesis illuminates the affected component on the System Map and pins its supporting evidence in the Evidence Inspector.

### 4. Reading Provenance Evidence (`/workspace` Evidence Inspector)
The right panel provides an monospaced evidence reader:
- Displays exact source coordinates (file path, line number).
- Tags evidence reliability (`Direct Observation` vs. `Inferred Signal`).
- Shows the sanitized code statement and context excerpt.

### 5. Reviewing the Deliverable Report (`/reports/[id]`)
Generates an audit-ready technical diagnosis report:
- **Executive Summary:** Plain-language causal attribution.
- **Ranked Findings:** Comprehensive hypothesis ranking with evidence provenance.
- **Diagnostic Boundaries Notice:** Explicit disclosure of uninspected components and remaining uncertainties (e.g. when dynamic container probes were skipped).

---

## Machine Learning & Diagnostic Evaluation

ORACLE utilizes machine learning to rank candidate fault hypotheses without human bias.

### 1. Versioned Fault Taxonomy (v1.0.0)
Diagnoses are categorized into 10 deterministic fault categories:
1. `SYNTAX_ERROR`: Unparseable source text.
2. `UNRESOLVED_INTERNAL_IMPORT`: Missing or invalid relative import.
3. `UNDECLARED_EXTERNAL_DEPENDENCY`: Third-party package absent from manifest.
4. `RUNTIME_EXCEPTION_DATABASE_SOCKET`: Database connection refused on port 5432/3306.
5. `RUNTIME_EXCEPTION_TIMEOUT`: Downstream HTTP/network timeout.
6. `RUNTIME_EXCEPTION_SCHEMA_VALIDATION`: Payload contract validation failure.
7. `RUNTIME_EXCEPTION_JSON_DECODE`: Malformed response payload.
8. `RUNTIME_EXCEPTION_MISSING_ENV`: Required environment variable unset.
9. `RUNTIME_EXCEPTION_GENERIC`: Other uncategorized runtime stack trace.
10. `HEALTHY_BASELINE`: Clean codebase with zero observable faults.

### 2. Feature Representation & Leakage Isolation Boundary
Hypotheses are evaluated across 24 dense features capturing:
- Structural AST metrics (inbound callers, outbound dependencies, error counts).
- Telemetry alignment (stack frame presence, exception message similarity).
- Manifest discrepancies (package declared in `pyproject.toml` or `package.json` vs. observed imports).

> [!IMPORTANT]
> To prevent data leakage, ground-truth labels and benchmark scenario IDs are strictly isolated from the feature extraction boundary. Dedicated invariance tests (`testing/ml/test_feature_leakage.py`) enforce zero group or scenario leakage.

### 3. Evaluation Protocol & Benchmark Results
Evaluated using **Scenario-Family 5-Fold Cross-Validation** over a controlled 20-scenario generalization dataset (`ml/benchmark/ml_evaluation.py`):

| Model | CV Top-1 Accuracy | Expected Calibration Error (ECE) | Brier Score | Mean Inference Latency |
| :--- | :---: | :---: | :---: | :---: |
| Uncalibrated Heuristic Baseline | 70.0% | 0.6500 | 0.3031 | < 1 ms |
| **Calibrated Random Forest Ensemble** | **80.0%** | **0.2976** | **0.1600** | **22.4 ms** |

*Note on Evaluation Scope:* The 80.0% Top-1 accuracy and 0.2976 ECE represent performance on the existing 20-scenario generalization benchmark suite. They demonstrate that Platt-calibrated ensembles outperform uncalibrated heuristics on controlled cross-validation folds. They do not constitute a claim of universal accuracy across arbitrary production codebases.

---

## Security & Execution Safety

ORACLE is engineered to analyze potentially broken or hostile code safely:

1. **Zero-Execution Static Analysis:**
   - Source code is never executed during ingestion.
   - Python code is parsed with `ast.parse()`, TypeScript with Microsoft's compiler AST factory, Java with OpenJDK compiler trees, and Go with a custom lexical scanner. No code is evaluated via `eval()`, `exec()`, or runtime import reflection.
2. **Filesystem Containment Boundaries:**
   - Ingestion enforces strict path traversal protection using `os.path.commonpath()`.
   - Symlinks resolving outside the target repository root are rejected as `escaping_reference`.
3. **Resource Boundaries:**
   - Scan quotas enforced by `ResourceLimiter`: max 1,000 files, max 1 MB per file, max 50 MB total, and 30-second timeout.
   - Automatically excludes `.git`, `.venv`, `node_modules`, `__pycache__`, and binary assets.
4. **Automated Credential Redaction:**
   - Pre-persistence regex scrubbers sanitize database URLs (`user:password@host`), JWT tokens, AWS access keys, and bearer tokens from runtime stack traces.
5. **Dynamic Execution Isolation Boundary:**
   - When dynamic probes are requested, `DockerExecutionProvider` requires preflight validation.
   - Containers run non-root with dropped capabilities (`--cap-drop ALL`), read-only root filesystems, `--network none`, and disabled privilege escalation (`no-new-privileges`).
   - If Docker is unavailable, dynamic execution is **safely gated and disabled**. ORACLE never falls back to unisolated host execution.

---

## Testing & Verification

The repository contains an automated multi-level test suite under [`testing/`](file:///c:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/testing):

```
testing/
├── backend/          # Backend API, database, AST parsers, and diagnostic engine tests (pytest)
├── ml/               # Taxonomy, dataset schema, feature leakage, and ML benchmark tests (pytest)
├── deploy/           # Deployment configuration and smoke tests (pytest)
├── frontend/         # Frontend API client tests (node:test)
└── demonstration/    # End-to-end multi-scenario demonstration runner
```

### Running Test Suites

#### 1. Backend & Machine Learning Test Suite
```bash
# Run all unit and integration tests (excluding live external daemon scenarios)
python -m pytest -k "not test_e2e_scenarios"
```

#### 2. Frontend Client Test Suite
```bash
cd frontend
npm test
```

#### 3. TypeScript Type-Check & ESLint
```bash
cd frontend
npm run type-check
npm run lint
```

#### 4. Next.js Production Standalone Build
```bash
cd frontend
npm run build
```

### Verified Test Results Summary

| Test Category | Test Command | Tests | Status | Scope / Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Backend & Parser Suite** | `pytest testing/backend/` | 175 | **PASS** | Validates Python, TS, Java, Go AST parsers, config, health, telemetry, and isolation preflight. |
| **ML & Benchmark Suite** | `pytest testing/ml/` | 83 | **PASS** | Validates taxonomy, feature leakage invariance, calibrated ranking, probe planning, and benchmarks. |
| **Deployment Smoke** | `pytest testing/deploy/` | 1 | **PASS** | Audits Docker Compose configuration and CLI contract endpoints. |
| **Frontend API Client** | `node --test` | 17 | **PASS** | Tests API client error handling, typing, and endpoint contracts. |
| **Frontend Static Typing** | `tsc --noEmit` | — | **0 Errors** | Strict TypeScript compilation across all components and routes. |
| **Frontend Linting** | `npm run lint` | — | **0 Warnings** | Clean ESLint compliance. |
| **Frontend Production Build**| `next build` | 8 routes | **PASS** | Standalone Turbopack build compiled in ~5.7s. |
| *Live Daemon Scenarios* | `pytest testing/demonstration/` | 6 | *Skipped* | Requires active live backend daemon and PostgreSQL instance. |

---

## Deployment

ORACLE provides two deployment configurations under [`deploy/`](file:///c:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/deploy):

### 1. Docker Compose (Local & Production Host)

The Compose deployment provisions three isolated containers:
- **`oracle-frontend`:** Multi-stage Next.js standalone container (Port 3000).
- **`oracle-backend`:** Polyglot container with Python 3.12, Node.js runtime, and OpenJDK 17 (Port 8000).
- **`oracle-db`:** PostgreSQL 16 database on private bridge network `oracle_internal` (Port 5432).

To start the containerized stack:
```bash
cd deploy
docker compose up -d --build
```

### 2. Dedicated Cloud VM Deployment (Ubuntu 22.04 / 24.04 LTS)

For running outside the local development environment, an automated setup script is provided in `deploy/scripts/setup_ubuntu_vm.sh`:
- Installs Docker Engine 26+ and Docker Compose plugin.
- Configures non-root user execution and UFW firewall boundaries (allowing ports 22, 80, 443).
- Generates high-entropy database credentials in `deploy/.env`.
- Automates container startup and persistence health checks.

> [!NOTE]
> Detailed cloud provisioning guides and VM cost models (AWS EC2, GCP, Azure, DigitalOcean) are documented in [`deploy/docs/cloud_vm_deployment_guide.md`](file:///c:/Users/mshas/OneDrive/Documents/GitHub/ORACLE/deploy/docs/cloud_vm_deployment_guide.md).

---

## Current Limitations & Roadmap

### Current Limitations
1. **Local Dynamic Execution Gating:** On hosts without a reachable Docker daemon, dynamic probe execution is disabled. ORACLE safely falls back to static-only analysis and transparently notes this boundary in the diagnostic report.
2. **Database Fallback:** If PostgreSQL is offline during development, ORACLE operates in `in_memory_transient` mode. State persists in memory for the duration of the process but does not survive application restarts.
3. **Language AST Coverage:** Static inspection currently covers Python, TypeScript, JavaScript, Java, and Go. C/C++, Rust, and Ruby static parsers are not yet implemented.
4. **Single-Node Execution:** The diagnostic engine runs as a single-process orchestrator and does not currently distribute probe execution across a Celery or Temporal cluster.

### Roadmap
- [ ] **Expanded AST Ecosystems:** Add static AST parsing and manifest inspection for Rust (`cargo`) and C/C++ (`CMake`).
- [ ] **Automated Remediation Code Diffs:** Synthesize concrete code patches for verified syntax defects and missing imports.
- [ ] **Distributed Telemetry Correlation:** Ingest OpenTelemetry distributed traces (`.otlp`) to map spans directly to AST component nodes.
- [ ] **Temporal / Celery Probe Dispatch:** Distribute dynamic container probes across multi-worker execution clusters.

---

## Contributing

Contributions to ORACLE are welcome. To maintain engineering rigor and security integrity:

1. **Development Setup:** Follow the [Local Development Setup](#local-development-setup) instructions.
2. **Branching:** Create a feature branch off `main` (`feature/your-feature-name` or `fix/issue-description`).
3. **Zero Untrusted Execution Invariant:** Any new static analysis feature must strictly parse source code without executing, evaluating, or dynamically importing target files.
4. **Mandatory Secret Redaction:** Any telemetry parser must pass all strings through `redact_secrets()`.
5. **Quality Gates:** All pull requests must pass:
   ```bash
   # Backend & ML test suites
   python -m pytest -k "not test_e2e_scenarios"
   
   # Frontend type-check, lint, and tests
   cd frontend
   npm run type-check
   npm run lint
   npm test
   npm run build
   ```

---

## License & Legal Notice

**Licensing Information:**  
Formal open-source licensing information for ORACLE has not yet been assigned. All rights are reserved pending official release license assignment.

*Notice:* This software is provided for research, testing, and evaluation purposes. When configured to inspect third-party repositories, ensure you have appropriate authorization to scan and analyze target codebases.

