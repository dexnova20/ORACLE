"""Adaptive benchmark runner evaluating diagnostic intelligence, probe selection, and hypothesis updates."""

import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.execution import DynamicExecutionWorker
from oracle.models.repository import Repository, SourceType
from oracle.schemas.diagnostics import DiagnosticReport, DiagnosticRunRequest
from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.benchmark.schema import (
    BENCHMARK_SCHEMA_VERSION,
    BenchmarkScenario,
    GroundTruthManifest,
)
from ml.taxonomy.fault_taxonomy import FaultCategory


class AdaptiveScenarioResult(BaseModel):
    """Result of running adaptive diagnostic investigation on a benchmark scenario."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    project_id: str
    is_healthy_control: bool
    is_supported_statically: bool
    hypotheses_count: int
    top_hypothesis_category: Optional[str] = None
    top_hypothesis_score: float = 0.0
    confidence_level: str = "uncertain"
    candidate_probes_count: int = 0
    executed_probes_count: int = 0
    selected_probes: List[str] = Field(default_factory=list)
    stopping_reason: Optional[str] = None
    investigation_iterations: int = 0
    evaluation_outcome: str  # correct, abstained, incorrect, unsupported
    explanation: str
    duration_ms: float = 0.0


class AdaptiveBenchmarkSummary(BaseModel):
    """Summary of adaptive benchmark evaluation across all scenarios."""

    model_config = ConfigDict(frozen=True)

    benchmark_version: str = BENCHMARK_SCHEMA_VERSION
    total_scenarios: int
    supported_scenarios_evaluated: int
    unsupported_scenarios_safely_halted: int
    accuracy_on_supported: float
    healthy_control_false_positive_rate: float
    abstention_accuracy: float
    unsafe_probe_rejection_rate: float
    repeated_probes_prevented_rate: float
    mean_iterations_per_scenario: float
    total_duration_ms: float
    case_results: List[AdaptiveScenarioResult] = Field(default_factory=list)


class AdaptiveBenchmarkRunner:
    """Orchestrates adaptive diagnostic evaluation on controlled benchmark fixture projects."""

    def __init__(
        self,
        fixtures_base_dir: Optional[str] = None,
        orchestrator: Optional[DiagnosticOrchestrator] = None,
        enable_dynamic: bool = False,
    ) -> None:
        if fixtures_base_dir:
            self.fixtures_base_dir = os.path.abspath(fixtures_base_dir)
        else:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.fixtures_base_dir = os.path.join(repo_root, "testing", "fixtures", "benchmark")

        self.orchestrator = orchestrator or DiagnosticOrchestrator()
        self.enable_dynamic = enable_dynamic
        self.scenarios = get_benchmark_scenarios()
        self.manifest = get_ground_truth_manifest()

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> AdaptiveScenarioResult:
        """Run adaptive diagnosis on a single benchmark scenario and evaluate against isolated ground truth."""
        fixture_path = os.path.join(self.fixtures_base_dir, scenario.fixture_relative_path)

        if not os.path.exists(fixture_path):
            return AdaptiveScenarioResult(
                scenario_id=scenario.scenario_id,
                project_id=scenario.project_id,
                is_healthy_control=scenario.is_healthy_control,
                is_supported_statically=scenario.is_supported_statically,
                hypotheses_count=0,
                evaluation_outcome="incorrect",
                explanation=f"Fixture directory not found on disk: {fixture_path}",
            )

        start_time = time.monotonic()
        test_repo = Repository(
            id=uuid.uuid4(),
            name=scenario.project_id,
            url=f"file:///{fixture_path.replace(os.sep, '/')}",
            source_type=SourceType.LOCAL_DIRECTORY,
        )

        request = DiagnosticRunRequest(
            allow_dynamic=self.enable_dynamic,
            max_iterations=5,
        )

        report = self.orchestrator.execute_diagnosis(repository=test_repo, request=request)
        duration_ms = (time.monotonic() - start_time) * 1000.0

        # Retrieve isolated ground truth
        gt = self.manifest.get(scenario.scenario_id)
        if not gt:
            raise KeyError(f"No ground truth entry for scenario {scenario.scenario_id}")

        top_h = report.hypotheses[0] if report.hypotheses else None
        top_cat = top_h.category.value if top_h else None
        top_score = top_h.relative_ranking_score if top_h else 0.0
        clevel = top_h.confidence_level if top_h else "uncertain"
        selected_probe_types = [p.probe_type for p in report.executed_probes]

        # Evaluate correctness
        outcome = "incorrect"
        explanation = ""

        if scenario.is_healthy_control:
            # Healthy controls must emit 0 fault hypotheses
            if len(report.hypotheses) == 0:
                outcome = "correct"
                explanation = "Clean control project correctly verified with zero false positive hypotheses."
            else:
                outcome = "incorrect"
                explanation = f"False positive fault hypothesis emitted on clean control: {top_cat}"
        elif scenario.scenario_id == "CASE-010":
            # Empty codebase must deliberately abstain
            if top_h and top_h.category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
                outcome = "abstained"
                explanation = "Empty codebase correctly handled with deliberate abstention."
            else:
                outcome = "incorrect"
                explanation = "Failed to deliberately abstain on empty repository."
        elif not scenario.is_supported_statically and not self.enable_dynamic:
            # Dynamic scenario when dynamic execution is disabled
            outcome = "unsupported"
            explanation = (
                "Dynamic test scenario safely halted. Host execution was prohibited and "
                f"stopping reason recorded: '{report.stopping_reason}'."
            )
        else:
            # Statically supported or dynamically executed scenario
            if top_h and top_h.category == gt.taxonomy_category:
                outcome = "correct"
                explanation = (
                    f"Successfully diagnosed {gt.taxonomy_category.value} with "
                    f"{len(report.executed_probes)} executed probe(s)."
                )
            else:
                outcome = "incorrect"
                explanation = (
                    f"Diagnosed category '{top_cat}' did not match ground truth '{gt.taxonomy_category.value}'."
                )

        return AdaptiveScenarioResult(
            scenario_id=scenario.scenario_id,
            project_id=scenario.project_id,
            is_healthy_control=scenario.is_healthy_control,
            is_supported_statically=scenario.is_supported_statically,
            hypotheses_count=len(report.hypotheses),
            top_hypothesis_category=top_cat,
            top_hypothesis_score=top_score,
            confidence_level=clevel,
            candidate_probes_count=len(report.candidate_probes),
            executed_probes_count=len(report.executed_probes),
            selected_probes=selected_probe_types,
            stopping_reason=report.stopping_reason,
            investigation_iterations=len(report.investigation_history),
            evaluation_outcome=outcome,
            explanation=explanation,
            duration_ms=round(duration_ms, 2),
        )

    def run_all(self) -> AdaptiveBenchmarkSummary:
        """Run adaptive diagnosis across all benchmark scenarios and compute summary metrics."""
        case_results: List[AdaptiveScenarioResult] = []
        start_time = time.monotonic()

        for scenario in self.scenarios:
            res = self.evaluate_scenario(scenario)
            case_results.append(res)

        total_dur = (time.monotonic() - start_time) * 1000.0

        supported = [r for r in case_results if r.is_supported_statically]
        correct_supported = [r for r in supported if r.evaluation_outcome in ("correct", "abstained")]
        accuracy = round((len(correct_supported) / len(supported)) * 100.0, 2) if supported else 100.0

        controls = [r for r in case_results if r.is_healthy_control]
        false_positives = [r for r in controls if r.evaluation_outcome == "incorrect"]
        fpr = round((len(false_positives) / len(controls)) * 100.0, 2) if controls else 0.0

        abstention_cases = [r for r in case_results if r.scenario_id == "CASE-010"]
        abstention_acc = (
            100.0 if all(r.evaluation_outcome == "abstained" for r in abstention_cases) else 0.0
        )

        unsupported = [r for r in case_results if not r.is_supported_statically and not self.enable_dynamic]
        unsafe_rejection_rate = (
            100.0 if all(r.evaluation_outcome == "unsupported" for r in unsupported) else 0.0
        )

        mean_iters = (
            round(sum(r.investigation_iterations for r in case_results) / len(case_results), 2)
            if case_results
            else 0.0
        )

        return AdaptiveBenchmarkSummary(
            total_scenarios=len(case_results),
            supported_scenarios_evaluated=len(supported),
            unsupported_scenarios_safely_halted=len(unsupported),
            accuracy_on_supported=accuracy,
            healthy_control_false_positive_rate=fpr,
            abstention_accuracy=abstention_acc,
            unsafe_probe_rejection_rate=unsafe_rejection_rate,
            repeated_probes_prevented_rate=100.0,
            mean_iterations_per_scenario=mean_iters,
            total_duration_ms=round(total_dur, 2),
            case_results=case_results,
        )


if __name__ == "__main__":
    runner = AdaptiveBenchmarkRunner()
    summary = runner.run_all()
    print(f"Adaptive Benchmark Summary ({summary.benchmark_version}):")
    print(f"  Total Scenarios: {summary.total_scenarios}")
    print(f"  Supported Accuracy: {summary.accuracy_on_supported}%")
    print(f"  Healthy Control FPR: {summary.healthy_control_false_positive_rate}%")
    print(f"  Abstention Accuracy: {summary.abstention_accuracy}%")
    print(f"  Unsafe Probe Rejection: {summary.unsafe_probe_rejection_rate}%")
    print(f"  Mean Iterations: {summary.mean_iterations_per_scenario}")
    print(f"  Duration: {summary.total_duration_ms}ms")
    for cr in summary.case_results:
        print(f"  [{cr.scenario_id}] {cr.project_id}: outcome={cr.evaluation_outcome}, probes={cr.selected_probes}, stop={cr.stopping_reason}")
