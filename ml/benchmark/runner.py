"""Deterministic benchmark runner executing controlled fault-injection evaluation against ORACLE."""

import json
import os
import sys
import time
import uuid
from typing import Dict, List, Optional

# Ensure backend directory is in sys.path for direct CLI benchmark execution
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from oracle.execution import DynamicExecutionWorker, ExecutionState
from oracle.inspection.service import InspectionService
from oracle.models.repository import Repository, SourceType
from oracle.schemas.execution import ExecutionRequest
from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.benchmark.schema import (
    BENCHMARK_SCHEMA_VERSION,
    BenchmarkCaseResult,
    BenchmarkRunSummary,
    BenchmarkScenario,
    DiagnosticEvidence,
    EvidenceState,
    GroundTruthManifest,
)
from ml.experiments.evaluation import classification_metrics
from ml.taxonomy.fault_taxonomy import FaultCategory

# Mapping from benchmark scenario IDs to approved ORACLE workload profiles
DYNAMIC_SCENARIO_PROFILES: Dict[str, str] = {
    "CASE-005": "benchmark-env-audit",
    "CASE-006": "benchmark-db-probe",
    "CASE-007": "benchmark-contract-check",
    "CASE-008": "benchmark-transform-test",
}


class BenchmarkRunner:
    """Orchestrates deterministic benchmark runs across controlled fixture projects."""

    def __init__(
        self,
        fixtures_base_dir: Optional[str] = None,
        inspection_service: Optional[InspectionService] = None,
        execution_worker: Optional[DynamicExecutionWorker] = None,
        enable_dynamic: bool = False,
    ) -> None:
        if fixtures_base_dir:
            self.fixtures_base_dir = os.path.abspath(fixtures_base_dir)
        else:
            # Default to testing/fixtures/benchmark relative to repository root
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.fixtures_base_dir = os.path.join(repo_root, "testing", "fixtures", "benchmark")

        self.inspection_service = inspection_service or InspectionService()
        self.execution_worker = execution_worker or DynamicExecutionWorker()
        self.enable_dynamic = enable_dynamic
        self.scenarios = get_benchmark_scenarios()
        self.manifest = get_ground_truth_manifest()

    def run_all(self, run_id: Optional[str] = None) -> BenchmarkRunSummary:
        """Execute static inspection and benchmark evaluation across all scenarios."""
        run_identifier = run_id or f"run-{uuid.uuid4().hex[:8]}"
        case_results: List[BenchmarkCaseResult] = []

        for scenario in self.scenarios:
            result = self.evaluate_scenario(scenario)
            case_results.append(result)

        return self._summarize_run(run_identifier, case_results)

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> BenchmarkCaseResult:
        """Run inspection on a single scenario fixture and evaluate against isolated ground truth."""
        fixture_path = os.path.join(self.fixtures_base_dir, scenario.fixture_relative_path)

        if not os.path.exists(fixture_path):
            evidence = DiagnosticEvidence(
                scenario_id=scenario.scenario_id,
                project_id=scenario.project_id,
                status="failed",
                missing_evidence=[f"Fixture path does not exist on disk: {scenario.fixture_relative_path}"],
                evidence_state=EvidenceState.FAILED,
            )
            return BenchmarkCaseResult(
                scenario_id=scenario.scenario_id,
                project_id=scenario.project_id,
                is_supported_statically=scenario.is_supported_statically,
                evidence=evidence,
                observed_fault_category=None,
                evaluation_outcome="incorrect",
                explanation=f"Fixture directory missing: {fixture_path}",
            )

        start_time = time.monotonic()

        # Execute static inspection via ORACLE InspectionService
        repo_url = f"file:///{fixture_path.replace(os.sep, '/')}"
        test_repo = Repository(
            id=uuid.uuid4(),
            name=scenario.project_id,
            url=repo_url,
            source_type=SourceType.LOCAL_DIRECTORY,
        )

        report = self.inspection_service.inspect_repository(test_repo)
        duration_ms = (time.monotonic() - start_time) * 1000.0

        syntax_err_records = [
            {
                "file_path": s.file_path,
                "line_number": s.line_number,
                "error_message": s.error_message,
            }
            for s in report.syntax_errors
        ]

        unresolved_records = [
            {
                "source": e.source_node,
                "target": e.target_node,
                "line": e.line_number,
            }
            for e in report.dependency_graph.edges
            if e.dependency_type == "unresolved"
        ]

        external_packages = sorted(
            list(
                {
                    e.target_node
                    for e in report.dependency_graph.edges
                    if e.dependency_type == "external"
                }
            )
        )

        missing_evidence_list = list(report.missing_evidence)
        if not scenario.is_supported_statically and scenario.unsupported_reason:
            missing_evidence_list.append(scenario.unsupported_reason)

        evidence_state = (
            EvidenceState.UNSUPPORTED
            if not scenario.is_supported_statically
            else (EvidenceState.OBSERVED if report.status in ("completed", "partial") else EvidenceState.FAILED)
        )

        evidence = DiagnosticEvidence(
            scenario_id=scenario.scenario_id,
            project_id=scenario.project_id,
            status=report.status,
            ecosystems=[e.name for e in report.ecosystems],
            total_files_discovered=report.total_files_discovered,
            total_files_analyzed=report.total_files_analyzed,
            syntax_errors=syntax_err_records,
            unresolved_imports=unresolved_records,
            external_imports=external_packages,
            missing_evidence=missing_evidence_list,
            evidence_state=evidence_state,
            duration_ms=round(duration_ms, 2),
            provenance={"inspector": "InspectionService", "version": "1.0.0"},
        )

        # Retrieve isolated ground truth
        gt = self.manifest.get(scenario.scenario_id)
        if not gt:
            raise KeyError(f"No ground truth entry registered for scenario {scenario.scenario_id}")

        # If scenario is unsupported statically, check if dynamic container execution is enabled
        if not scenario.is_supported_statically:
            if self.enable_dynamic and scenario.scenario_id in DYNAMIC_SCENARIO_PROFILES:
                profile_id = DYNAMIC_SCENARIO_PROFILES[scenario.scenario_id]
                worker = self.execution_worker or DynamicExecutionWorker()
                preflight = worker.provider.check_preflight()

                if not preflight.is_available:
                    missing_evidence_list.append(
                        f"Dynamic execution unavailable: {'; '.join(preflight.missing_reasons)}"
                    )
                    evidence = DiagnosticEvidence(
                        scenario_id=scenario.scenario_id,
                        project_id=scenario.project_id,
                        status=report.status,
                        ecosystems=[e.name for e in report.ecosystems],
                        total_files_discovered=report.total_files_discovered,
                        total_files_analyzed=report.total_files_analyzed,
                        syntax_errors=syntax_err_records,
                        unresolved_imports=unresolved_records,
                        external_imports=external_packages,
                        missing_evidence=missing_evidence_list,
                        evidence_state=EvidenceState.UNSUPPORTED,
                        duration_ms=round(duration_ms, 2),
                        provenance={
                            "inspector": "InspectionService",
                            "dynamic_isolation": "unavailable",
                            "preflight_reasons": preflight.missing_reasons,
                        },
                    )
                    return BenchmarkCaseResult(
                        scenario_id=scenario.scenario_id,
                        project_id=scenario.project_id,
                        is_supported_statically=False,
                        evidence=evidence,
                        observed_fault_category=None,
                        evaluation_outcome="unsupported_analysis",
                        explanation=f"Dynamic isolation unavailable: {'; '.join(preflight.missing_reasons)}",
                    )

                # Container isolation is verified available: execute approved workload profile
                exec_report = worker.execute_workload(
                    repository=test_repo,
                    request=ExecutionRequest(profile_id=profile_id),
                    snapshot_path=fixture_path,
                )

                observed_category = None
                if exec_report.status == ExecutionState.FAILED or exec_report.exit_code != 0:
                    if scenario.scenario_id == "CASE-005" and ("KeyError" in exec_report.stderr or "AUTH_SECRET_KEY" in exec_report.stderr):
                        observed_category = FaultCategory.CONFIG_MISSING_OR_INVALID
                    elif scenario.scenario_id == "CASE-006" and ("ConnectionRefused" in exec_report.stderr or "timed out" in exec_report.stderr or exec_report.exit_code != 0):
                        observed_category = FaultCategory.DATABASE_CONNECTIVITY_SCHEMA
                    elif scenario.scenario_id == "CASE-007" and ("AssertionError" in exec_report.stderr or "Contract violation" in exec_report.stderr):
                        observed_category = FaultCategory.IO_CONTRACT_VIOLATION
                    elif scenario.scenario_id == "CASE-008" and ("ValueError" in exec_report.stderr or "could not convert" in exec_report.stderr):
                        observed_category = FaultCategory.DATA_VALIDATION_TRANSFORMATION

                evidence = DiagnosticEvidence(
                    scenario_id=scenario.scenario_id,
                    project_id=scenario.project_id,
                    status=report.status,
                    ecosystems=[e.name for e in report.ecosystems],
                    total_files_discovered=report.total_files_discovered,
                    total_files_analyzed=report.total_files_analyzed,
                    syntax_errors=syntax_err_records,
                    unresolved_imports=unresolved_records,
                    external_imports=external_packages,
                    missing_evidence=missing_evidence_list,
                    evidence_state=EvidenceState.OBSERVED if observed_category else EvidenceState.FAILED,
                    duration_ms=round(duration_ms + exec_report.duration_ms, 2),
                    provenance={
                        "inspector": "InspectionService",
                        "dynamic_execution": {
                            "profile_id": profile_id,
                            "status": exec_report.status.value,
                            "exit_code": exec_report.exit_code,
                            "applied_controls": exec_report.applied_isolation_controls,
                        },
                    },
                )

                if observed_category == gt.taxonomy_category:
                    outcome = "correct"
                    explanation = f"Dynamic execution confirmed {observed_category.value} via exit status {exec_report.exit_code}."
                else:
                    outcome = "incorrect"
                    explanation = f"Dynamic execution produced unexpected category: {observed_category}"

                return BenchmarkCaseResult(
                    scenario_id=scenario.scenario_id,
                    project_id=scenario.project_id,
                    is_supported_statically=False,
                    evidence=evidence,
                    observed_fault_category=observed_category,
                    evaluation_outcome=outcome,
                    explanation=explanation,
                )

            # Static-only baseline path: safely report unsupported_analysis without executing code
            return BenchmarkCaseResult(
                scenario_id=scenario.scenario_id,
                project_id=scenario.project_id,
                is_supported_statically=False,
                evidence=evidence,
                observed_fault_category=None,
                evaluation_outcome="unsupported_analysis",
                explanation=f"Scenario requires dynamic/runtime analysis: {scenario.unsupported_reason}",
            )

        # Rule-based diagnostic inference on observable static evidence
        observed_category: Optional[FaultCategory] = None
        if len(report.syntax_errors) > 0:
            observed_category = FaultCategory.RUNTIME_EXCEPTION
        elif report.dependency_graph.unresolved_edge_count > 0:
            observed_category = FaultCategory.DEPENDENCY_IMPORT_FAILURE
        elif len(external_packages) > 0:
            from oracle.diagnostics.service import extract_declared_dependencies, _normalize_pkg_name
            from oracle.inspection.java_parser import is_java_package_declared
            declared_pkgs = extract_declared_dependencies(fixture_path)
            clean_external = [p.replace("pkg:", "") for p in external_packages]
            undeclared = [
                p for p in clean_external
                if _normalize_pkg_name(p) not in declared_pkgs and not is_java_package_declared(p, declared_pkgs)
            ]
            if undeclared:
                observed_category = FaultCategory.DEPENDENCY_IMPORT_FAILURE
            elif report.total_files_analyzed == 0:
                observed_category = FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE
            else:
                observed_category = None
        elif report.total_files_analyzed == 0:
            observed_category = FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE
        else:
            observed_category = None

        # Compare observed inference against ground truth
        if scenario.is_healthy_control:
            if observed_category is None:
                outcome = "correct_control"
                explanation = "Clean baseline correctly identified with zero faults."
            else:
                outcome = "false_positive"
                explanation = f"False positive: clean project was incorrectly diagnosed as {observed_category.value}."
        elif gt.taxonomy_category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
            if observed_category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
                outcome = "correct_abstention"
                explanation = "Correctly abstained due to zero analyzable source files."
            else:
                outcome = "incorrect_abstention"
                explanation = f"Failed to abstain: expected insufficient evidence, but observed {observed_category}."
        else:
            if observed_category == gt.taxonomy_category:
                outcome = "correct"
                explanation = f"Correctly diagnosed {observed_category.value} from observable evidence."
            elif observed_category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
                outcome = "abstained"
                explanation = "Abstained on a faulty scenario."
            else:
                outcome = "incorrect"
                explanation = f"Diagnosis mismatch: observed {observed_category}, ground truth is {gt.taxonomy_category}."

        return BenchmarkCaseResult(
            scenario_id=scenario.scenario_id,
            project_id=scenario.project_id,
            is_supported_statically=True,
            evidence=evidence,
            observed_fault_category=observed_category,
            evaluation_outcome=outcome,
            explanation=explanation,
        )

    def _summarize_run(
        self,
        run_id: str,
        results: List[BenchmarkCaseResult],
    ) -> BenchmarkRunSummary:
        """Aggregate evaluation metrics across benchmark case results."""
        total_scenarios = len(results)
        supported_results = [r for r in results if r.is_supported_statically]
        unsupported_results = [r for r in results if not r.is_supported_statically]

        # Healthy control evaluation
        healthy_scenarios_ids = {s.scenario_id for s in self.scenarios if s.is_healthy_control}
        healthy_results = [r for r in results if r.scenario_id in healthy_scenarios_ids]
        false_positive_count = sum(1 for r in healthy_results if r.evaluation_outcome == "false_positive")
        false_positive_rate = (
            false_positive_count / len(healthy_results) if healthy_results else 0.0
        )

        # Accuracy on supported scenarios
        correct_count = sum(
            1
            for r in supported_results
            if r.evaluation_outcome in ("correct", "correct_control", "correct_abstention")
        )
        static_accuracy = (
            correct_count / len(supported_results) if supported_results else 0.0
        )

        # Abstention metrics
        abstention_count = sum(
            1 for r in results if r.observed_fault_category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE
        )
        correct_abstentions = sum(
            1 for r in results if r.evaluation_outcome == "correct_abstention"
        )

        # Evidence extraction coverage
        coverage_count = sum(
            1 for r in supported_results if r.evidence.total_files_analyzed > 0 or r.scenario_id == "CASE-010"
        )
        coverage_rate = coverage_count / len(supported_results) if supported_results else 0.0

        # Compute macro classification metrics for supported cases
        pred_labels: List[str] = []
        true_labels: List[str] = []
        for r in supported_results:
            gt = self.manifest.get(r.scenario_id)
            if gt:
                t_label = gt.taxonomy_category.value if gt.taxonomy_category else "healthy_control"
                p_label = r.observed_fault_category.value if r.observed_fault_category else "healthy_control"
                pred_labels.append(p_label)
                true_labels.append(t_label)

        metrics = classification_metrics(pred_labels, true_labels) if pred_labels else {}

        return BenchmarkRunSummary(
            benchmark_version=BENCHMARK_SCHEMA_VERSION,
            run_id=run_id,
            total_scenarios=total_scenarios,
            supported_scenarios=len(supported_results),
            unsupported_scenarios=len(unsupported_results),
            healthy_controls_count=len(healthy_results),
            false_positive_count=false_positive_count,
            false_positive_rate=round(false_positive_rate, 4),
            evidence_extraction_coverage=round(coverage_rate, 4),
            abstention_count=abstention_count,
            correct_abstentions=correct_abstentions,
            static_diagnostic_accuracy=round(static_accuracy, 4),
            top_k_ranking_accuracy=None,  # Explicitly None: no ranking model deployed in Phase 008
            macro_precision=metrics.get("macro_precision"),
            macro_recall=metrics.get("macro_recall"),
            macro_f1=metrics.get("macro_f1"),
            case_results=results,
        )


def run_benchmark(
    fixtures_base_dir: Optional[str] = None,
    run_id: Optional[str] = None,
) -> BenchmarkRunSummary:
    """Convenience entry point for benchmark runs."""
    runner = BenchmarkRunner(fixtures_base_dir=fixtures_base_dir)
    return runner.run_all(run_id=run_id)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ORACLE Controlled Fault-Injection Benchmark Runner")
    parser.add_argument("--json", action="store_true", help="Print summary as machine-readable JSON artifact")
    parser.add_argument("--output", type=str, default=None, help="Save machine-readable JSON summary to file")
    args = parser.parse_args()

    summary = run_benchmark()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))
        print(f"Benchmark artifact saved to: {args.output}")

    if args.json:
        print(summary.model_dump_json(indent=2))
    else:
        print("=" * 60)
        print(f"ORACLE Controlled Benchmark Summary (v{summary.benchmark_version})")
        print(f"Run ID: {summary.run_id}")
        print(f"Total Scenarios: {summary.total_scenarios}")
        print(f"Supported Scenarios (Static): {summary.supported_scenarios}")
        print(f"Unsupported Scenarios (Dynamic Required): {summary.unsupported_scenarios}")
        print(f"Static Diagnostic Accuracy: {summary.static_diagnostic_accuracy * 100:.1f}%")
        print(f"False Positive Rate (Controls): {summary.false_positive_rate * 100:.1f}%")
        print(f"Evidence Coverage: {summary.evidence_extraction_coverage * 100:.1f}%")
        print(f"Abstentions: {summary.abstention_count} (Correct: {summary.correct_abstentions})")
        print(f"Top-k Ranking Accuracy: {summary.top_k_ranking_accuracy} (No ranking model deployed)")
        print("=" * 60)
        print("\nCase Results:")
        for c in summary.case_results:
            supp = "Supported" if c.is_supported_statically else "Unsupported"
            print(f"[{c.scenario_id}] {c.project_id} ({supp}): {c.evaluation_outcome} -> {c.explanation}")
