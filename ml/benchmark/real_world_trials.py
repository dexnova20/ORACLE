"""Controlled Real-Repository Trials and Product Validation Runner (Implementation 015).

Evaluates the ORACLE diagnostic engine across 8 realistic repository configurations
representing distinct technical stacks, architectures, and failure modes.
Generates structured JSON and Markdown validation reports.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
import uuid

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.models.repository import Repository, SourceType
from oracle.schemas.diagnostics import DiagnosticReport, DiagnosticRunRequest
from ml.taxonomy.fault_taxonomy import FaultCategory


@dataclass
class RealWorldTrialManifest:
    """Specification of a real-world repository trial."""

    trial_id: str
    target_name: str
    directory_name: str
    ecosystem: str
    provenance: str
    license: str
    description: str
    is_healthy_control: bool
    expected_findings: List[str]
    expected_top_category: Optional[str]


REAL_WORLD_TRIALS: List[RealWorldTrialManifest] = [
    RealWorldTrialManifest(
        trial_id="TRIAL-001",
        target_name="FastAPI Microservice",
        directory_name="real_01_python_fastapi",
        ecosystem="python",
        provenance="Synthetic production-grade FastAPI service layout with APIRouter and pyproject.toml",
        license="Apache-2.0",
        description="Clean Python FastAPI service with router and model separation",
        is_healthy_control=True,
        expected_findings=["Healthy service", "0 fault hypotheses"],
        expected_top_category=None,
    ),
    RealWorldTrialManifest(
        trial_id="TRIAL-002",
        target_name="Next.js / TypeScript App",
        directory_name="real_02_typescript_nextjs",
        ecosystem="typescript",
        provenance="Synthetic Next.js frontend utility layout with package.json and React dependencies",
        license="MIT",
        description="Clean TypeScript application with modular imports and package.json",
        is_healthy_control=True,
        expected_findings=["Healthy frontend utility", "0 fault hypotheses"],
        expected_top_category=None,
    ),
    RealWorldTrialManifest(
        trial_id="TRIAL-003",
        target_name="Spring Boot Java Maven Service",
        directory_name="real_03_java_maven_service",
        ecosystem="java",
        provenance="Synthetic Maven enterprise service with pom.xml, Spring Web, and Jackson",
        license="Apache-2.0",
        description="Clean Java Maven service with package hierarchy and multi-class architecture",
        is_healthy_control=True,
        expected_findings=["Healthy Java service", "0 fault hypotheses"],
        expected_top_category=None,
    ),
    RealWorldTrialManifest(
        trial_id="TRIAL-004",
        target_name="Mixed Polyglot Fullstack App",
        directory_name="real_04_mixed_polyglot_fullstack",
        ecosystem="polyglot (python + typescript)",
        provenance="Synthetic fullstack project containing Python Flask backend and TypeScript frontend",
        license="MIT",
        description="Mixed polyglot repository with concurrent Python and TypeScript ecosystems",
        is_healthy_control=True,
        expected_findings=["Multi-ecosystem detection", "0 fault hypotheses"],
        expected_top_category=None,
    ),
    RealWorldTrialManifest(
        trial_id="TRIAL-005",
        target_name="Multi-Module Python Utility Library",
        directory_name="real_05_healthy_control",
        ecosystem="python",
        provenance="Synthetic clean Python utility library with relative imports and pyproject.toml",
        license="MIT",
        description="Clean Python control library verifying zero false positives",
        is_healthy_control=True,
        expected_findings=["Zero false positive hypotheses"],
        expected_top_category=None,
    ),
    RealWorldTrialManifest(
        trial_id="TRIAL-006",
        target_name="TypeScript Syntax Defect Scenario",
        directory_name="real_06_source_defect_syntax",
        ecosystem="typescript",
        provenance="Synthetic TypeScript data transformation module with breaking syntax error",
        license="MIT",
        description="TypeScript module containing unclosed parenthesis syntax defect in transform.ts",
        is_healthy_control=False,
        expected_findings=["Syntax error identified in transform.ts", "Verified via static AST validation"],
        expected_top_category=FaultCategory.RUNTIME_EXCEPTION.value,
    ),
    RealWorldTrialManifest(
        trial_id="TRIAL-007",
        target_name="Polyglot Multi-Defect System",
        directory_name="real_07_multiple_defects",
        ecosystem="polyglot (python + typescript)",
        provenance="Synthetic polyglot system with independent Python syntax error and TS undeclared package",
        license="Apache-2.0",
        description="Independent Python auth_service.py syntax defect and TypeScript undeclared axios external dependency",
        is_healthy_control=False,
        expected_findings=["Separation of Python syntax fault in auth_service.py and TypeScript undeclared axios dependency into distinct hypotheses"],
        expected_top_category=FaultCategory.RUNTIME_EXCEPTION.value,
    ),
    RealWorldTrialManifest(
        trial_id="TRIAL-008",
        target_name="Java Ambiguous Dependency Resolution",
        directory_name="real_08_ambiguous_dependency",
        ecosystem="java",
        provenance="Synthetic Java Maven project importing undeclared third-party utility class",
        license="MIT",
        description="Java source importing com.example.common.utils.StringUtils without declared Maven artifact",
        is_healthy_control=False,
        expected_findings=["Undeclared dependency hypothesis with uncertainty clearly stated"],
        expected_top_category=FaultCategory.DEPENDENCY_IMPORT_FAILURE.value,
    ),
]


@dataclass
class RealWorldTrialResult:
    """Evaluation result for an individual real-world trial."""

    trial_id: str
    target_name: str
    ecosystem: str
    provenance: str
    license: str
    is_healthy_control: bool
    expected_findings: List[str]
    actual_hypotheses_count: int
    top1_hypothesis_category: Optional[str]
    top1_hypothesis_component: Optional[str]
    top1_hypothesis_confidence: Optional[str]
    top1_hypothesis_status: Optional[str]
    all_hypothesis_categories: List[str]
    probes_executed_count: int
    executed_probe_summaries: List[str]
    unsupported_stages: List[str]
    stopping_reason: Optional[str]
    false_positives_detected: bool
    findings_matched_expectations: bool
    duration_ms: float


def run_real_world_trials(fixtures_dir: Optional[str] = None) -> List[RealWorldTrialResult]:
    """Execute diagnostic evaluations across all real-world trial fixtures."""
    if not fixtures_dir:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        fixtures_dir = os.path.join(repo_root, "testing", "fixtures", "real_world")

    orchestrator = DiagnosticOrchestrator()
    results: List[RealWorldTrialResult] = []

    for manifest in REAL_WORLD_TRIALS:
        target_path = os.path.join(fixtures_dir, manifest.directory_name)
        if not os.path.isdir(target_path):
            raise FileNotFoundError(f"Fixture directory '{manifest.directory_name}' not found at {target_path}")

        file_url = f"file:///{target_path.replace(os.sep, '/')}"
        repo = Repository(
            id=uuid.uuid4(),
            name=manifest.target_name,
            url=file_url,
            source_type=SourceType.LOCAL_DIRECTORY.value,
        )

        start_time = time.monotonic()
        req = DiagnosticRunRequest(max_iterations=5, allow_dynamic=False)
        report: DiagnosticReport = orchestrator.execute_diagnosis(repository=repo, request=req)
        elapsed_ms = (time.monotonic() - start_time) * 1000.0

        actual_count = len(report.hypotheses)
        top1_cat = report.hypotheses[0].category.value if report.hypotheses else None
        top1_comp = report.hypotheses[0].affected_component if report.hypotheses else None
        top1_conf = report.hypotheses[0].confidence_level if report.hypotheses else None
        top1_stat = report.hypotheses[0].verification_status if report.hypotheses else None
        all_cats = [h.category.value for h in report.hypotheses]

        probe_summaries = [
            f"{p.probe_id}: {p.probe_type} on {p.target_component} -> {p.outcome}"
            for p in report.executed_probes
        ]

        # Check expectations
        if manifest.is_healthy_control:
            false_positives = actual_count > 0
            matched = actual_count == 0
        else:
            false_positives = False
            if manifest.trial_id == "TRIAL-007":
                # Multiple fault separation requires multiple hypotheses covering distinct components
                matched = (
                    actual_count >= 2
                    and FaultCategory.RUNTIME_EXCEPTION.value in all_cats
                    and FaultCategory.DEPENDENCY_IMPORT_FAILURE.value in all_cats
                )
            else:
                matched = top1_cat == manifest.expected_top_category

        results.append(
            RealWorldTrialResult(
                trial_id=manifest.trial_id,
                target_name=manifest.target_name,
                ecosystem=manifest.ecosystem,
                provenance=manifest.provenance,
                license=manifest.license,
                is_healthy_control=manifest.is_healthy_control,
                expected_findings=manifest.expected_findings,
                actual_hypotheses_count=actual_count,
                top1_hypothesis_category=top1_cat,
                top1_hypothesis_component=top1_comp,
                top1_hypothesis_confidence=top1_conf,
                top1_hypothesis_status=top1_stat,
                all_hypothesis_categories=all_cats,
                probes_executed_count=len(report.executed_probes),
                executed_probe_summaries=probe_summaries,
                unsupported_stages=report.unsupported_stages,
                stopping_reason=report.stopping_reason,
                false_positives_detected=false_positives,
                findings_matched_expectations=matched,
                duration_ms=elapsed_ms,
            )
        )

    return results


def generate_reports(results: List[RealWorldTrialResult], output_dir: Optional[str] = None) -> None:
    """Generate structured JSON and Markdown trial reports."""
    if not output_dir:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        output_dir = os.path.join(repo_root, "testing", "reports")

    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "real_world_trials_report.json")
    md_path = os.path.join(output_dir, "real_world_trials_report.md")

    total_trials = len(results)
    passed_trials = sum(1 for r in results if r.findings_matched_expectations)
    healthy_trials = [r for r in results if r.is_healthy_control]
    healthy_passed = sum(1 for r in healthy_trials if not r.false_positives_detected)
    defective_trials = [r for r in results if not r.is_healthy_control]
    defective_passed = sum(1 for r in defective_trials if r.findings_matched_expectations)

    summary_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_trials": total_trials,
        "passed_trials": passed_trials,
        "overall_accuracy_pct": round(passed_trials / total_trials * 100.0, 1),
        "healthy_control_trials": len(healthy_trials),
        "healthy_control_clean_pct": round(healthy_passed / len(healthy_trials) * 100.0, 1),
        "defective_scenario_trials": len(defective_trials),
        "defective_scenario_accuracy_pct": round(defective_passed / len(defective_trials) * 100.0, 1),
        "results": [asdict(r) for r in results],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Generate Markdown report
    md_lines = [
        "# ORACLE Real-World Diagnostic Trials Report",
        "",
        f"**Generated:** {summary_data['generated_at']}  ",
        f"**Overall Accuracy:** {passed_trials}/{total_trials} ({summary_data['overall_accuracy_pct']}%)  ",
        f"**Healthy Control Clean Rate:** {healthy_passed}/{len(healthy_trials)} ({summary_data['healthy_control_clean_pct']}%)  ",
        f"**Defective Scenario Identification:** {defective_passed}/{len(defective_trials)} ({summary_data['defective_scenario_accuracy_pct']}%)  ",
        "",
        "## Trial Summary Table",
        "",
        "| Trial ID | Target Name | Ecosystem | Type | Expected Category | Actual Category | Matched | Duration (ms) |",
        "|---|---|---|---|---|---|:---:|---:|",
    ]

    for r in results:
        trial_type = "Healthy Control" if r.is_healthy_control else "Defective"
        expected = "None (Clean)" if r.is_healthy_control else (r.expected_findings[0] if r.expected_findings else "Defect")
        actual = r.top1_hypothesis_category or "None (Clean)"
        status_icon = "PASS" if r.findings_matched_expectations else "FAIL"
        md_lines.append(
            f"| `{r.trial_id}` | {r.target_name} | `{r.ecosystem}` | {trial_type} | `{expected}` | `{actual}` | **{status_icon}** | {r.duration_ms:.1f} |"
        )

    md_lines.extend([
        "",
        "## Detailed Trial Results",
        "",
    ])

    for r in results:
        status_str = "PASSED" if r.findings_matched_expectations else "FAILED"
        md_lines.extend([
            f"### {r.trial_id}: {r.target_name} ({status_str})",
            f"- **Ecosystem:** `{r.ecosystem}`",
            f"- **Provenance / License:** {r.provenance} ({r.license})",
            f"- **Expected Findings:** {', '.join(r.expected_findings)}",
            f"- **Hypotheses Generated:** {r.actual_hypotheses_count}",
            f"- **Top-1 Category:** `{r.top1_hypothesis_category}` (confidence: {r.top1_hypothesis_confidence}, status: {r.top1_hypothesis_status})",
            f"- **Probes Executed:** {r.probes_executed_count}",
            f"- **Stopping Reason:** `{r.stopping_reason}`",
            f"- **Execution Time:** {r.duration_ms:.1f}ms",
            "",
        ])
        if r.executed_probe_summaries:
            md_lines.append("  - **Executed Probes:**")
            for ps in r.executed_probe_summaries:
                md_lines.append(f"    - `{ps}`")
            md_lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Real-World Trials complete: {passed_trials}/{total_trials} passed ({summary_data['overall_accuracy_pct']}%).")
    print(f"Reports saved to {json_path} and {md_path}")


if __name__ == "__main__":
    trials_results = run_real_world_trials()
    generate_reports(trials_results)
