"""ORACLE Controlled Fault-Injection Benchmark package."""

from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.benchmark.schema import (
    BENCHMARK_SCHEMA_VERSION,
    BenchmarkCaseResult,
    BenchmarkRunSummary,
    BenchmarkScenario,
    DiagnosticEvidence,
    EvidenceState,
    GroundTruthManifest,
    ScenarioGroundTruth,
)


def __getattr__(name: str):
    if name in ("BenchmarkRunner", "run_benchmark"):
        from ml.benchmark.runner import BenchmarkRunner, run_benchmark

        if name == "BenchmarkRunner":
            return BenchmarkRunner
        return run_benchmark
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BENCHMARK_SCHEMA_VERSION",
    "BenchmarkCaseResult",
    "BenchmarkRunner",
    "BenchmarkRunSummary",
    "BenchmarkScenario",
    "DiagnosticEvidence",
    "EvidenceState",
    "GroundTruthManifest",
    "ScenarioGroundTruth",
    "get_benchmark_scenarios",
    "get_ground_truth_manifest",
    "run_benchmark",
]
