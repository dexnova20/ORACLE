"""Formal specifications for the ORACLE diagnostic model baseline progression.

Documents the architectural progression from deterministic rules to learned rankers,
specifying inputs, outputs, assumptions, comparisons, and expected failure modes
without implementing premature or placeholder algorithms.
"""

from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, ConfigDict, Field


class BaselineType(str, Enum):
    """Canonical model and algorithm baselines in the planned diagnostic progression."""

    DETERMINISTIC_RULES = "deterministic_rules"
    STATISTICAL_FREQUENCY = "statistical_frequency"
    ISOLATION_FOREST_ANOMALY = "isolation_forest_anomaly"
    XGBOOST_FAULT_RANKER = "xgboost_fault_ranker"
    ADAPTIVE_TEST_SELECTOR = "adaptive_test_selector"
    PRETRAINED_EMBEDDINGS_DL = "pretrained_embeddings_dl"


class BaselineSpecification(BaseModel):
    """Comprehensive design specification for a diagnostic baseline algorithm."""

    model_config = ConfigDict(frozen=True)

    baseline_type: BaselineType = Field(..., description="Canonical baseline identifier")
    name: str = Field(..., description="Human-readable algorithm title")
    description: str = Field(..., description="Detailed architectural purpose")
    input_features: List[str] = Field(..., description="Exact feature set consumed by this model")
    output_format: str = Field(..., description="Output structure and probability/ranking contract")
    underlying_assumptions: List[str] = Field(..., description="Core assumptions required for validity")
    baseline_comparison: str = Field(..., description="How this model is evaluated against preceding steps")
    expected_failure_modes: List[str] = Field(..., description="Anticipated blind spots and error states")
    training_requirements: str = Field(..., description="Data, compute, and supervisor requirements")
    evaluation_role: str = Field(..., description="Role in overall evaluation methodology")


BASELINE_REGISTRY: Dict[BaselineType, BaselineSpecification] = {
    BaselineType.DETERMINISTIC_RULES: BaselineSpecification(
        baseline_type=BaselineType.DETERMINISTIC_RULES,
        name="Deterministic Diagnostic Rule Engine",
        description=(
            "Expert rule engine using exact regex matching, HTTP status codes, and deterministic boolean logic. "
            "Maps explicit signatures (e.g. ECONNREFUSED on 5432) to known root-cause categories."
        ),
        input_features=[
            "Exact exception class names (e.g. ModuleNotFoundError, psycopg.OperationalError)",
            "HTTP response status codes (e.g. 422, 502, 503)",
            "Process exit codes (e.g. 0, 1, 137)",
            "Known regex patterns in error logs",
        ],
        output_format="Deterministic diagnosis or abstain: (FaultCategory, confidence=1.0) or (UNKNOWN, confidence=0.0)",
        underlying_assumptions=[
            "Known failure modes exhibit static, repeatable string signatures",
            "Error messages are not corrupted, localized into unknown languages, or truncated",
        ],
        baseline_comparison="The zero-learning baseline. Sets the minimum benchmark for precision and latency (<1ms).",
        expected_failure_modes=[
            "Zero recall (complete silence) on previously unseen error messages or novel software frameworks",
            "Brittle against minor log formatting changes or dependency version upgrades",
        ],
        training_requirements="Zero training data required. Curated by domain engineers.",
        evaluation_role="Establishes absolute lower-bound latency and baseline precision for known faults.",
    ),
    BaselineType.STATISTICAL_FREQUENCY: BaselineSpecification(
        baseline_type=BaselineType.STATISTICAL_FREQUENCY,
        name="Statistical N-Gram & Frequency Baseline (Naive Bayes / TF-IDF)",
        description=(
            "Statistical frequency model calculating conditional probability P(FaultCategory | SymptomTokens) "
            "over tokenized log messages and component identifiers using term frequencies."
        ),
        input_features=[
            "TF-IDF unigrams and bigrams extracted from log message patterns",
            "Bag of component and dependency identifier indicators",
            "Test pass/fail boolean summary vectors",
        ],
        output_format="Probability distribution vector over all 10 FaultCategory classes with Top-k ranking",
        underlying_assumptions=[
            "Symptoms and vocabulary words are conditionally independent given the fault category",
            "Vocabulary distributions in training projects overlap partially with target projects",
        ],
        baseline_comparison="Must outperform deterministic rules on fuzzy string matches and paraphrased errors.",
        expected_failure_modes=[
            "Out-of-vocabulary (OOV) tokens on unseen libraries receive zero weight",
            "Poor probability calibration (tends toward overconfidence near 0.0 and 1.0)",
        ],
        training_requirements="Requires labelled dataset (>100 cases). CPU training in seconds.",
        evaluation_role="Provides minimum viable learned ranking baseline for Top-1 and Top-3 accuracy.",
    ),
    BaselineType.ISOLATION_FOREST_ANOMALY: BaselineSpecification(
        baseline_type=BaselineType.ISOLATION_FOREST_ANOMALY,
        name="Isolation Forest Anomaly Detector",
        description=(
            "Unsupervised tree ensemble that isolates numeric telemetry anomalies (latency, memory, CPU, error rate) "
            "by partitioning feature space. Detects whether a system is failing before root-cause classification."
        ),
        input_features=[
            "telemetry.latency_p50_ms",
            "telemetry.latency_p95_ms",
            "telemetry.error_rate",
            "telemetry.cpu_utilization_pct",
            "telemetry.memory_rss_mb",
        ],
        output_format="Binary anomaly score: [-1.0 (anomalous), +1.0 (normal)] with continuous anomaly depth",
        underlying_assumptions=[
            "Faulty states occupy low-density regions in continuous multi-dimensional telemetry space",
            "Normal operating telemetry is sufficiently clustered",
        ],
        baseline_comparison="Evaluated on precision/recall of anomaly detection without requiring fault class labels.",
        expected_failure_modes=[
            "Cannot diagnose root-cause category (identifies *that* a fault occurred, not *why*)",
            "High false-positive rate during legitimate seasonal traffic spikes or batch jobs",
        ],
        training_requirements="Unsupervised: trained purely on unlabelled historical telemetry runs.",
        evaluation_role="Acts as first-stage triage gate deciding whether to trigger expensive diagnostic probes.",
    ),
    BaselineType.XGBOOST_FAULT_RANKER: BaselineSpecification(
        baseline_type=BaselineType.XGBOOST_FAULT_RANKER,
        name="Gradient Boosted Decision Trees (XGBoost / LightGBM)",
        description=(
            "Supervised gradient-boosted decision tree ensemble trained on engineered tabular features "
            "combining numeric telemetry, categorical indicators, test results, and missing evidence flags."
        ),
        input_features=[
            "Quantitative telemetry features (latency, error rate, CPU, memory)",
            "One-hot / target encoded component and dependency identifiers",
            "Aggregated test failure counts and execution durations",
            "Binary presence indicators for missing evidence signals",
            "Top-50 TF-IDF symptom vocabulary components",
        ],
        output_format="Calibrated probability distribution across all 10 FaultCategory classes with Top-k ranking",
        underlying_assumptions=[
            "Non-linear interactions between telemetry and component flags are strong discriminators",
            "Tabular representation captures the essential diagnostic state without full raw log parsing",
        ],
        baseline_comparison="Primary structured learning baseline. Expected to achieve superior tabular classification.",
        expected_failure_modes=[
            "Cannot easily parse arbitrary unstructured stack traces or long text narratives",
            "Susceptible to project overfitting if evaluated without project-aware cross-validation",
        ],
        training_requirements="Supervised: requires balanced dataset (>500 cases) across taxonomy categories.",
        evaluation_role="Standard benchmark for Top-1/Top-3 ranking accuracy and macro F1 on structured features.",
    ),
    BaselineType.ADAPTIVE_TEST_SELECTOR: BaselineSpecification(
        baseline_type=BaselineType.ADAPTIVE_TEST_SELECTOR,
        name="Adaptive Test Selector (Cost-Sensitive Active Diagnostic Planner)",
        description=(
            "Sequential decision-making agent that iteratively selects the next diagnostic probe or test to execute. "
            "Optimizes the ratio of Expected Information Gain (EIG) to diagnostic execution cost (time, compute), "
            "subject to safety constraints."
        ),
        input_features=[
            "Current diagnostic belief state (posterior probability distribution over FaultCategory)",
            "Set of available unexecuted diagnostic probes and tests",
            "Historical duration and compute cost per probe",
            "Safety constraint flags (e.g. read-only probe vs mutating test)",
        ],
        output_format="Selected next probe identifier to execute, or TERMINATE_DIAGNOSIS when confidence > threshold",
        underlying_assumptions=[
            "Executing all diagnostic probes simultaneously is prohibitively slow or costly",
            "A small subset of targeted probes resolves entropy in the diagnostic posterior rapidly",
        ],
        baseline_comparison="Evaluated on Total Diagnostic Cost (latency + compute) to reach >=95% diagnostic confidence.",
        expected_failure_modes=[
            "Greedy selection trap (suboptimal multi-step probe planning under myopic information gain)",
            "Inability to plan when probe execution outcomes are noisy or non-deterministic",
        ],
        training_requirements="Reinforcement learning or Bayesian experimental design with simulated probe environments.",
        evaluation_role="Evaluates diagnostic efficiency, minimizing Mean Time to Diagnosis (MTTD) under budget.",
    ),
    BaselineType.PRETRAINED_EMBEDDINGS_DL: BaselineSpecification(
        baseline_type=BaselineType.PRETRAINED_EMBEDDINGS_DL,
        name="Pretrained Semantic Embeddings & Deep Learning (CodeBERT / Sentence-Transformers)",
        description=(
            "Deep neural network utilizing pretrained code/text embeddings to map raw stack traces, error messages, "
            "and source code diffs into dense vector space, evaluated only if experiments demonstrate measurable advantage."
        ),
        input_features=[
            "Dense 768-dimensional embedding vectors of raw stack traces and exception messages",
            "Source code context window snippets surrounding the failing line of code",
            "Numeric telemetry vector concatenated at classification head",
        ],
        output_format="Softmax probability distribution over FaultCategory with cosine similarity to reference prototypes",
        underlying_assumptions=[
            "Semantic meaning of error messages transfers across programming languages and frameworks",
            "The accuracy gain justifies 10x-50x higher inference latency and GPU compute requirements",
        ],
        baseline_comparison="Must demonstrate statistically significant (>5%) gain over XGBoost to be justified.",
        expected_failure_modes=[
            "High inference latency (100ms-500ms vs <5ms for XGBoost)",
            "Susceptible to adversarial perturbation or hallucination when prompted with unseen tokens",
        ],
        training_requirements="Fine-tuning requires GPU resources and large-scale diagnostic corpora (>2,000 cases).",
        evaluation_role="Evaluated as potential Phase 2 high-capacity model; rejected if latency penalty exceeds gain.",
    ),
}


def get_baseline_specification(baseline_type: BaselineType) -> BaselineSpecification:
    """Retrieve full design specification for a baseline algorithm."""
    if baseline_type not in BASELINE_REGISTRY:
        raise KeyError(f"Baseline '{baseline_type}' is not registered.")
    return BASELINE_REGISTRY[baseline_type]


def list_baseline_specifications() -> List[BaselineSpecification]:
    """List all registered baseline specifications in progression order."""
    return list(BASELINE_REGISTRY.values())
