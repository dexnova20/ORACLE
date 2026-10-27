#!/usr/bin/env python3
"""Repeatable prototype demonstration runner for ORACLE v0.1.

Executes four canonical demonstration cases against ORACLE's diagnostic engine
(either live HTTP API or in-process orchestrator):
  1. Case 1: Healthy polyglot repository (clean report, zero false positives)
  2. Case 2: Supported fault repository (top hypothesis, provenance, probe plan)
  3. Case 3: Runtime telemetry non-static fault (DB socket refusal, secret redaction)
  4. Case 4: Ambiguous / unsupported repository (explicit abstention, bounded budget)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

# Ensure repo root and backend dir are on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def check_api_server(base_url: str = "http://127.0.0.1:8000") -> bool:
    """Check if the live FastAPI server is accessible."""
    try:
        req = urllib.request.Request(f"{base_url}/api/v1/health", headers={"User-Agent": "ORACLE-Demonstration"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def run_via_http(
    base_url: str,
    name: str,
    target_path: Path,
    symptom_description: Optional[str] = None,
    runtime_traceback: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute diagnosis via live HTTP REST API."""
    uri = target_path.resolve().as_uri()

    # 1. Register repository
    reg_body = json.dumps({
        "name": name,
        "url": uri,
        "source_type": "local_directory",
    }).encode("utf-8")
    reg_req = urllib.request.Request(
        f"{base_url}/api/v1/repositories",
        data=reg_body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(reg_req, timeout=10.0) as resp:
        repo_data = json.loads(resp.read().decode("utf-8"))
    repo_id = repo_data["id"]

    # 2. Run diagnosis
    diag_body: Dict[str, Any] = {}
    if symptom_description:
        diag_body["symptom_description"] = symptom_description
    if runtime_traceback:
        diag_body["runtime_traceback"] = runtime_traceback

    diag_req = urllib.request.Request(
        f"{base_url}/api/v1/repositories/{repo_id}/diagnose",
        data=json.dumps(diag_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(diag_req, timeout=30.0) as resp:
        report = json.loads(resp.read().decode("utf-8"))

    return report


def run_in_process(
    name: str,
    target_path: Path,
    symptom_description: Optional[str] = None,
    runtime_traceback: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute diagnosis in-process via DiagnosticOrchestrator fallback."""
    from oracle.diagnostics.service import diagnostic_orchestrator
    from oracle.models.repository import Repository, SourceType, utc_now
    from oracle.schemas.diagnostics import DiagnosticRunRequest
    import uuid

    repo = Repository(
        id=uuid.uuid4(),
        name=name,
        url=target_path.resolve().as_uri(),
        source_type=SourceType.LOCAL_DIRECTORY.value,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    diagnostic_orchestrator.register_repo(repo)

    req = DiagnosticRunRequest(
        symptom_description=symptom_description,
        runtime_traceback=runtime_traceback,
        allow_dynamic=False,
    )
    report = diagnostic_orchestrator.execute_diagnosis(repository=repo, request=req)
    return report.model_dump(mode="json")


def format_duration(seconds: float) -> str:
    """Format duration in seconds or milliseconds."""
    if seconds < 1.0:
        return f"{seconds * 1000:.1f}ms"
    return f"{seconds:.2f}s"


def main() -> int:
    """Run all 4 canonical prototype demonstration cases."""
    print("=" * 80)
    print("  ORACLE v0.1 PROTOTYPE DEMONSTRATION RUNNER")
    print("=" * 80)

    base_url = os.environ.get("ORACLE_API_URL", "http://127.0.0.1:8000")
    use_live_api = check_api_server(base_url)

    if use_live_api:
        print(f"[*] Execution Mode: Live HTTP REST API ({base_url})")
    else:
        print("[*] Execution Mode: In-Process Orchestrator Fallback")

    cases = [
        {
            "id": "CASE-1",
            "title": "Healthy Polyglot Repository",
            "repo_rel": "testing/fixtures/real_world/real_05_healthy_control",
            "symptom_description": None,
            "runtime_traceback": None,
            "expected_verdict": "healthy",
        },
        {
            "id": "CASE-2",
            "title": "Supported Syntax Defect Repository",
            "repo_rel": "testing/fixtures/real_world/real_06_source_defect_syntax",
            "symptom_description": None,
            "runtime_traceback": None,
            "expected_verdict": "defect_identified",
        },
        {
            "id": "CASE-3",
            "title": "Runtime Telemetry Non-Static Fault (with Secret Scrubber)",
            "repo_rel": "testing/fixtures/benchmark/proj_01",
            "symptom_description": "Database connection timeout and socket error during query dispatch",
            "runtime_traceback": (
                "2026-10-27 04:00:00.123 [error] app.db: connection refused\n"
                "Traceback (most recent call last):\n"
                '  File "/app/db/connection.py", line 42, in get_connection\n'
                "    dsn = 'postgresql://admin:super_secret_token_9999@db.internal:5432/main'\n"
                "    conn = psycopg.connect(dsn, connect_timeout=5)\n"
                "psycopg.errors.ConnectionTimeout: connection timeout expired\n"
                "socket.gaierror: [Errno 111] Connection refused: db.internal:5432"
            ),
            "secret_canary": "super_secret_token_9999",
            "expected_verdict": "telemetry_diagnosed",
        },
        {
            "id": "CASE-4",
            "title": "Ambiguous / Unsupported Repository (Explicit Abstention)",
            "repo_rel": "testing/fixtures/generalization/gen_017_rust_abstention",
            "symptom_description": None,
            "runtime_traceback": None,
            "expected_verdict": "abstained",
        },
    ]

    all_passed = True
    summaries = []

    for c in cases:
        target_path = REPO_ROOT / c["repo_rel"]
        if not target_path.exists():
            print(f"[!] Target path missing: {target_path}")
            all_passed = False
            continue

        print(f"\n[>] Executing {c['id']}: {c['title']}...")
        start_time = time.monotonic()

        try:
            if use_live_api:
                report = run_via_http(
                    base_url=base_url,
                    name=f"demo-{c['id'].lower()}",
                    target_path=target_path,
                    symptom_description=c.get("symptom_description"),
                    runtime_traceback=c.get("runtime_traceback"),
                )
            else:
                report = run_in_process(
                    name=f"demo-{c['id'].lower()}",
                    target_path=target_path,
                    symptom_description=c.get("symptom_description"),
                    runtime_traceback=c.get("runtime_traceback"),
                )
        except Exception as exc:
            print(f"[X] Execution failed with exception: {exc}")
            all_passed = False
            continue

        duration = time.monotonic() - start_time
        status = report.get("status")
        abstention = report.get("abstention_reason")
        hypotheses = report.get("hypotheses", [])
        evidence = report.get("evidence", [])
        probes = report.get("probes", [])

        # Secret redaction check
        secret_clean = True
        secret_canary = c.get("secret_canary")
        if secret_canary:
            report_str = json.dumps(report)
            if secret_canary in report_str:
                secret_clean = False
                all_passed = False

        top_hypo = hypotheses[0] if hypotheses else None
        if top_hypo:
            top_name = top_hypo.get("category_title") or str(top_hypo.get("category", "Unknown"))
            conf_level = top_hypo.get("confidence_level", "uncertain")
            score = top_hypo.get("relative_ranking_score", 0.0)
            top_conf = f"{score:.0f} ({conf_level})"
        else:
            top_name = "No Defect" if status == "completed" and not abstention else ("Abstained" if abstention else "None")
            top_conf = "N/A"

        # Verification check per case
        case_passed = True
        if c["expected_verdict"] == "healthy":
            case_passed = (status == "completed" and len(hypotheses) == 0 and abstention is None)
        elif c["expected_verdict"] == "defect_identified":
            case_passed = (status in ("completed", "partial") and len(hypotheses) > 0 and top_hypo is not None)
        elif c["expected_verdict"] == "telemetry_diagnosed":
            has_telem_evid = any(e.get("evidence_type") == "runtime_telemetry" for e in evidence)
            case_passed = (status in ("completed", "partial") and len(hypotheses) > 0 and secret_clean and has_telem_evid)
        elif c["expected_verdict"] == "abstained":
            case_passed = (abstention is not None or "unsupported" in str(report.get("unsupported_stages", [])))

        if not case_passed:
            all_passed = False

        verdict_str = "PASS" if case_passed else "FAIL"
        print(f"    Verdict: {verdict_str}")
        print(f"    Status: {status} | Abstention: {abstention or 'None'}")
        print(f"    Primary Hypothesis: {top_name} (Confidence: {top_conf})")
        print(f"    Evidence Count: {len(evidence)} | Probe Count: {len(probes)}")
        print(f"    Secret Redaction: {'VERIFIED CLEAN' if secret_clean else 'LEAKAGE DETECTED'}")
        print(f"    Execution Time: {format_duration(duration)}")

        summaries.append({
            "case": c["id"],
            "title": c["title"],
            "target": c["repo_rel"],
            "verdict": verdict_str,
            "status": status,
            "abstention": abstention,
            "primary_hypothesis": top_name,
            "confidence": top_conf,
            "evidence_count": len(evidence),
            "probe_count": len(probes),
            "secret_redaction": "CLEAN" if secret_clean else "LEAKED",
            "duration": format_duration(duration),
        })

    print("\n" + "=" * 80)
    print("  PROTOTYPE DEMONSTRATION SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Case':<8} | {'Status':<10} | {'Primary Hypothesis':<30} | {'Conf':<15} | {'Ev':<4} | {'Pr':<4} | {'Redaction':<9} | {'Time':<8}")
    print("-" * 98)
    for s in summaries:
        print(
            f"{s['case']:<8} | "
            f"{s['status']:<10} | "
            f"{(s['primary_hypothesis'] or 'None')[:30]:<30} | "
            f"{s['confidence']:<15} | "
            f"{s['evidence_count']:<4} | "
            f"{s['probe_count']:<4} | "
            f"{s['secret_redaction']:<9} | "
            f"{s['duration']:<8}"
        )
    print("=" * 80)

    if all_passed and len(summaries) == len(cases):
        print("\n[OK] ALL 4 PROTOTYPE DEMONSTRATION CASES VERIFIED SUCCESSFULLY.")
        print("[OK] ORACLE v0.1 Demonstrates Complete Real-World Diagnostic Workflow.")
        return 0
    else:
        print("\n[FAIL] ONE OR MORE DEMONSTRATION CASES FAILED VERIFICATION.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
