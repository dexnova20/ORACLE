# ORACLE Real-World Diagnostic Trials Report

**Generated:** 2026-10-26T20:19:20.797249+00:00  
**Overall Accuracy:** 8/8 (100.0%)  
**Healthy Control Clean Rate:** 5/5 (100.0%)  
**Defective Scenario Identification:** 3/3 (100.0%)  

## Trial Summary Table

| Trial ID | Target Name | Ecosystem | Type | Expected Category | Actual Category | Matched | Duration (ms) |
|---|---|---|---|---|---|:---:|---:|
| `TRIAL-001` | FastAPI Microservice | `python` | Healthy Control | `None (Clean)` | `None (Clean)` | **PASS** | 39.7 |
| `TRIAL-002` | Next.js / TypeScript App | `typescript` | Healthy Control | `None (Clean)` | `None (Clean)` | **PASS** | 2326.9 |
| `TRIAL-003` | Spring Boot Java Maven Service | `java` | Healthy Control | `None (Clean)` | `None (Clean)` | **PASS** | 1908.4 |
| `TRIAL-004` | Mixed Polyglot Fullstack App | `polyglot (python + typescript)` | Healthy Control | `None (Clean)` | `None (Clean)` | **PASS** | 2776.4 |
| `TRIAL-005` | Multi-Module Python Utility Library | `python` | Healthy Control | `None (Clean)` | `None (Clean)` | **PASS** | 15.6 |
| `TRIAL-006` | TypeScript Syntax Defect Scenario | `typescript` | Defective | `Syntax error identified in transform.ts` | `runtime_exception` | **PASS** | 6170.0 |
| `TRIAL-007` | Polyglot Multi-Defect System | `polyglot (python + typescript)` | Defective | `Separation of Python syntax fault in auth_service.py and TypeScript undeclared axios dependency into distinct hypotheses` | `runtime_exception` | **PASS** | 1892.1 |
| `TRIAL-008` | Java Ambiguous Dependency Resolution | `java` | Defective | `Undeclared dependency hypothesis with uncertainty clearly stated` | `dependency_import_failure` | **PASS** | 1478.4 |

## Detailed Trial Results

### TRIAL-001: FastAPI Microservice (PASSED)
- **Ecosystem:** `python`
- **Provenance / License:** Synthetic production-grade FastAPI service layout with APIRouter and pyproject.toml (Apache-2.0)
- **Expected Findings:** Healthy service, 0 fault hypotheses
- **Hypotheses Generated:** 0
- **Top-1 Category:** `None` (confidence: None, status: None)
- **Probes Executed:** 0
- **Stopping Reason:** `sufficient_evidence_verified`
- **Execution Time:** 39.7ms

### TRIAL-002: Next.js / TypeScript App (PASSED)
- **Ecosystem:** `typescript`
- **Provenance / License:** Synthetic Next.js frontend utility layout with package.json and React dependencies (MIT)
- **Expected Findings:** Healthy frontend utility, 0 fault hypotheses
- **Hypotheses Generated:** 0
- **Top-1 Category:** `None` (confidence: None, status: None)
- **Probes Executed:** 0
- **Stopping Reason:** `sufficient_evidence_verified`
- **Execution Time:** 2326.9ms

### TRIAL-003: Spring Boot Java Maven Service (PASSED)
- **Ecosystem:** `java`
- **Provenance / License:** Synthetic Maven enterprise service with pom.xml, Spring Web, and Jackson (Apache-2.0)
- **Expected Findings:** Healthy Java service, 0 fault hypotheses
- **Hypotheses Generated:** 0
- **Top-1 Category:** `None` (confidence: None, status: None)
- **Probes Executed:** 0
- **Stopping Reason:** `sufficient_evidence_verified`
- **Execution Time:** 1908.4ms

### TRIAL-004: Mixed Polyglot Fullstack App (PASSED)
- **Ecosystem:** `polyglot (python + typescript)`
- **Provenance / License:** Synthetic fullstack project containing Python Flask backend and TypeScript frontend (MIT)
- **Expected Findings:** Multi-ecosystem detection, 0 fault hypotheses
- **Hypotheses Generated:** 0
- **Top-1 Category:** `None` (confidence: None, status: None)
- **Probes Executed:** 0
- **Stopping Reason:** `sufficient_evidence_verified`
- **Execution Time:** 2776.4ms

### TRIAL-005: Multi-Module Python Utility Library (PASSED)
- **Ecosystem:** `python`
- **Provenance / License:** Synthetic clean Python utility library with relative imports and pyproject.toml (MIT)
- **Expected Findings:** Zero false positive hypotheses
- **Hypotheses Generated:** 0
- **Top-1 Category:** `None` (confidence: None, status: None)
- **Probes Executed:** 0
- **Stopping Reason:** `sufficient_evidence_verified`
- **Execution Time:** 15.6ms

### TRIAL-006: TypeScript Syntax Defect Scenario (PASSED)
- **Ecosystem:** `typescript`
- **Provenance / License:** Synthetic TypeScript data transformation module with breaking syntax error (MIT)
- **Expected Findings:** Syntax error identified in transform.ts, Verified via static AST validation
- **Hypotheses Generated:** 2
- **Top-1 Category:** `runtime_exception` (confidence: high, status: verified)
- **Probes Executed:** 1
- **Stopping Reason:** `further_investigation_unsafe_or_unsupported`
- **Execution Time:** 6170.0ms

  - **Executed Probes:**
    - `PROBE-SYNTAX-src_transform_ts: static_ast_syntax_check on file:src/transform.ts -> confirmed`

### TRIAL-007: Polyglot Multi-Defect System (PASSED)
- **Ecosystem:** `polyglot (python + typescript)`
- **Provenance / License:** Synthetic polyglot system with independent Python syntax error and TS undeclared package (Apache-2.0)
- **Expected Findings:** Separation of Python syntax fault in auth_service.py and TypeScript undeclared axios dependency into distinct hypotheses
- **Hypotheses Generated:** 3
- **Top-1 Category:** `runtime_exception` (confidence: high, status: verified)
- **Probes Executed:** 2
- **Stopping Reason:** `further_investigation_unsafe_or_unsupported`
- **Execution Time:** 1892.1ms

  - **Executed Probes:**
    - `PROBE-SYNTAX-auth_service_py: static_ast_syntax_check on file:auth_service.py -> confirmed`
    - `PROBE-MANIFEST-axios: static_manifest_audit on axios -> confirmed`

### TRIAL-008: Java Ambiguous Dependency Resolution (PASSED)
- **Ecosystem:** `java`
- **Provenance / License:** Synthetic Java Maven project importing undeclared third-party utility class (MIT)
- **Expected Findings:** Undeclared dependency hypothesis with uncertainty clearly stated
- **Hypotheses Generated:** 2
- **Top-1 Category:** `dependency_import_failure` (confidence: high, status: verified)
- **Probes Executed:** 1
- **Stopping Reason:** `sufficient_evidence_verified`
- **Execution Time:** 1478.4ms

  - **Executed Probes:**
    - `PROBE-IMPORT-src_main_java_com_example_demo_App_java: static_import_resolution_check on file:src/main/java/com/example/demo/App.java -> confirmed`
