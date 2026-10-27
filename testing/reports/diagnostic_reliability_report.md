# ORACLE Diagnostic Reliability & Real-World Validation Report

**Generated:** 2026-10-27T00:06:13.976309+00:00  
**Benchmark Version:** 1.0.0  
**Taxonomy Version:** 1.0.0  
**Total Scenarios Evaluated:** 60  
**Supported Scenarios:** 56 | **Healthy Controls:** 34 | **Unsupported (Dynamic-Only):** 4

---

## 1. Executive Summary & Baseline Comparison

| Evaluation Metric | Naive 1-Shot Baseline | ORACLE Adaptive Engine | Delta / Improvement |
| :--- | :--- | :--- | :--- |
| **Top-1 Supported Accuracy** | 100.0% (56/56) | **100.0% (56/56)** | +0.0% (parity on primary fault) |
| **Top-3 Supported Accuracy** | 100.0% (56/56) | **100.0% (56/56)** | +0.0% (parity) |
| **Healthy Control False Positives** | 0.0% (0/34) | **0.0% (0/34)** | 0% FPR across all 34 controls |
| **Deliberate Abstention** | 100.0% (3/3) | **100.0% (3/3)** | 100% on empty & unsupported codebases |
| **Multiple-Fault Separation** | 0.0% (0/8) | **100.0% (8/8)** | **+100.0% (separated independent faults)** |
| **Downstream Blocked Detection** | 0.0% (0/1) | **100.0% (1/1)** | **+100.0% (cascade reasoning)** |
| **Unsafe Probe Rejection** | N/A (no probes) | **100.0% (4/4)** | **100.0% (zero host fallback)** |
| **Repeated Probes Prevented** | N/A (1-shot) | **100.0% (60/60)** | **100.0% (deduplicated loop)** |
| **Mean Investigation Iterations** | 1.0 | **1.47** | Adaptive bounded planning |
| **Total Execution Duration** | 78846.5ms | **77497.4ms** | Across all 60 projects |

---

## 2. Granular Scenario Breakdown (All 60 Cases)

| Scenario | Project | Class | Ground Truth Root Cause | Baseline Top-1 | Adaptive Top-1 | Score | Probes Executed | Stopping Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CASE-001` | `PRJ-001` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-002` | `PRJ-002` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-003` | `PRJ-003` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 70.0 | `static_import_resolution_check` | `sufficient_evidence_verified` |
| `CASE-004` | `PRJ-004` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 55.0 | `static_manifest_audit` | `no_useful_probe_available` |
| `CASE-005` | `PRJ-005` | Fault | `config_missing_or_invalid` | ✗ `None` | ✗ `None` | 0.0 | `none` | `further_investigation_unsafe_or_unsupported` |
| `CASE-006` | `PRJ-006` | Fault | `database_connectivity_schema` | ✗ `None` | ✗ `None` | 0.0 | `none` | `further_investigation_unsafe_or_unsupported` |
| `CASE-007` | `PRJ-007` | Fault | `io_contract_violation` | ✗ `None` | ✗ `None` | 0.0 | `none` | `further_investigation_unsafe_or_unsupported` |
| `CASE-008` | `PRJ-008` | Fault | `data_validation_transformation` | ✗ `None` | ✗ `None` | 0.0 | `none` | `further_investigation_unsafe_or_unsupported` |
| `CASE-009` | `PRJ-009` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-010` | `PRJ-010` | Fault | `unknown_insufficient_evidence` | ✓ `unknown_insufficient_evidence` | ✓ `unknown_insufficient_evidence` | 0.0 | `none` | `deliberate_abstention` |
| `CASE-011` | `PRJ-011` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, downstream_independent_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-012` | `PRJ-012` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, static_ast_syntax_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-013` | `PRJ-013` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, static_import_resolution_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-014` | `PRJ-014` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-015` | `PRJ-015` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-016` | `PRJ-016` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, static_ast_syntax_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-017` | `PRJ-017` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 50.0 | `static_manifest_audit` | `no_useful_probe_available` |
| `CASE-018` | `PRJ-018` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 50.0 | `static_manifest_audit` | `no_useful_probe_available` |
| `CASE-019` | `PRJ-019` | Fault | `unknown_insufficient_evidence` | ✓ `unknown_insufficient_evidence` | ✓ `unknown_insufficient_evidence` | 0.0 | `none` | `deliberate_abstention` |
| `CASE-020` | `PRJ-020` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-021` | `PRJ-021` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-022` | `PRJ-022` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-023` | `PRJ-023` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-024` | `PRJ-024` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-025` | `PRJ-025` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 70.0 | `static_import_resolution_check` | `sufficient_evidence_verified` |
| `CASE-026` | `PRJ-026` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-027` | `PRJ-027` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-028` | `PRJ-028` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-029` | `PRJ-029` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-030` | `PRJ-030` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-031` | `PRJ-031` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 50.0 | `static_manifest_audit` | `no_useful_probe_available` |
| `CASE-032` | `PRJ-032` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-033` | `PRJ-033` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-034` | `PRJ-034` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, static_ast_syntax_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-035` | `PRJ-035` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, static_import_resolution_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-036` | `PRJ-036` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-037` | `PRJ-037` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-038` | `PRJ-038` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-039` | `PRJ-039` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-040` | `PRJ-040` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-041` | `PRJ-041` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-042` | `PRJ-042` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-043` | `PRJ-043` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-044` | `PRJ-044` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 70.0 | `static_import_resolution_check` | `sufficient_evidence_verified` |
| `CASE-045` | `PRJ-045` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 70.0 | `static_import_resolution_check, static_import_resolution_check` | `sufficient_evidence_verified` |
| `CASE-046` | `PRJ-046` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, static_ast_syntax_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-047` | `PRJ-047` | Fault | `runtime_exception` | ✓ `runtime_exception` | ✓ `runtime_exception` | 70.0 | `static_ast_syntax_check, static_import_resolution_check` | `further_investigation_unsafe_or_unsupported` |
| `CASE-048` | `PRJ-048` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-049` | `PRJ-049` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-050` | `PRJ-050` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-051` | `PRJ-051` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-052` | `PRJ-052` | Fault | `dependency_import_failure` | ✓ `dependency_import_failure` | ✓ `dependency_import_failure` | 50.0 | `static_manifest_audit` | `no_useful_probe_available` |
| `CASE-053` | `PRJ-053` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-054` | `PRJ-054` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-055` | `PRJ-055` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-056` | `PRJ-056` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-057` | `PRJ-057` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-058` | `PRJ-058` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-059` | `PRJ-059` | Control | `CLEAN_CONTROL` | ✓ `None` | ✓ `None` | 0.0 | `none` | `sufficient_evidence_verified` |
| `CASE-060` | `PRJ-060` | Fault | `unknown_insufficient_evidence` | ✓ `unknown_insufficient_evidence` | ✓ `unknown_insufficient_evidence` | 0.0 | `none` | `deliberate_abstention` |

---

## 3. Key Findings, Weaknesses Discovered & Fixes

1. **Multiple Simultaneous Faults**: Previously, the orchestrator collapsed all syntax errors into a single hypothesis for the first discovered file. We refactored hypothesis generation to group evidence by source component, allowing `CASE-012` (two syntax errors), `CASE-013` (syntax error + import failure), and `CASE-016` (upstream + downstream syntax errors) to generate independent, verified fault hypotheses.
2. **Hypothesis Ranker Order Invariance**: Additive scoring previously evaluated evidence in arbitrary arrival order. We implemented reliability-priority sorting (`direct_observation` > `inferred_signal` > `limited_context`), guaranteeing mathematically commutative and order-invariant scores.
3. **Evidence Deduplication**: Duplicate observations are deduplicated prior to scoring, ensuring repeated signals do not artificially inflate confidence beyond target bounds.
4. **Downstream Dependency Reasoning**: In `CASE-011`, the upstream syntax error is verified, and the downstream component is verified as syntactically clean in isolation, marking its state in the `SystemMap` as `blocked` at runtime.
5. **Host Safety Invariant**: In unisolated environments lacking Docker (`CASE-005`, `CASE-006`, `CASE-007`, `CASE-008`), dynamic probes are rejected (`unavailable_missing_adapter`) and investigation cleanly halts with `further_investigation_unsafe_or_unsupported`. Zero host execution fallback occurs.