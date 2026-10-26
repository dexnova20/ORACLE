"""Automated regression test suite for real-world repository trials (Implementation 015)."""

import os
import pytest
from ml.benchmark.real_world_trials import REAL_WORLD_TRIALS, run_real_world_trials


def test_real_world_trials_manifest_complete() -> None:
    """Verify that 8 distinct real-world trials are specified covering all required categories."""
    assert len(REAL_WORLD_TRIALS) == 8
    healthy_count = sum(1 for t in REAL_WORLD_TRIALS if t.is_healthy_control)
    defective_count = sum(1 for t in REAL_WORLD_TRIALS if not t.is_healthy_control)
    assert healthy_count == 5
    assert defective_count == 3

    ecosystems = {t.ecosystem for t in REAL_WORLD_TRIALS}
    assert "python" in ecosystems
    assert "typescript" in ecosystems
    assert "java" in ecosystems
    assert "polyglot (python + typescript)" in ecosystems


def test_real_world_trials_execution_and_accuracy() -> None:
    """Execute all 8 real-world trials and assert 100% accuracy and zero healthy control false positives."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    fixtures_dir = os.path.join(repo_root, "testing", "fixtures", "real_world")

    results = run_real_world_trials(fixtures_dir=fixtures_dir)
    assert len(results) == 8

    for r in results:
        assert r.findings_matched_expectations, (
            f"Trial {r.trial_id} ({r.target_name}) failed expectations! "
            f"Expected: {r.expected_findings}, Top-1 Category: {r.top1_hypothesis_category}, "
            f"Hypotheses count: {r.actual_hypotheses_count}, Duration: {r.duration_ms:.1f}ms"
        )
        if r.is_healthy_control:
            assert not r.false_positives_detected, (
                f"Healthy control trial {r.trial_id} ({r.target_name}) produced false positive hypotheses!"
            )
