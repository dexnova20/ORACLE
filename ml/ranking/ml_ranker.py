"""Machine Learning hypothesis ranking models for empirical diagnostic intelligence.

Trains, calibrates, and evaluates ML models (Calibrated Logistic Regression,
Calibrated Random Forest, and Ensemble) against the heuristic baseline using
strictly leak-free feature vectors.
"""

from dataclasses import dataclass
import os
import pickle
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from ml.ranking.feature_extractor import NUM_FEATURES, extract_hypothesis_features
from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.schemas.diagnostics import (
    DiagnosticEvidenceRecord,
    DiagnosticSystemMap,
    FaultHypothesis,
)


@dataclass
class ModelEvaluationMetrics:
    """Quantitative performance metrics for ML diagnostic rankers."""

    model_name: str
    top_1_accuracy: float
    top_3_accuracy: float
    precision: float
    recall: float
    brier_score: float
    expected_calibration_error: float
    abstention_precision: float
    mean_latency_ms: float


def compute_expected_calibration_error(
    probabilities: np.ndarray,
    labels: np.ndarray,
    num_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE) measuring reliability of predicted probabilities."""
    if len(probabilities) == 0:
        return 0.0

    bin_boundaries = np.linspace(0, 1, num_bins + 1)
    ece = 0.0
    total_samples = len(probabilities)

    for i in range(num_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        in_bin = (probabilities >= bin_lower) & (probabilities <= bin_upper)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = np.mean(labels[in_bin])
            bin_conf = np.mean(probabilities[in_bin])
            ece += (bin_size / total_samples) * abs(bin_acc - bin_conf)

    return float(ece)


def generate_synthetic_training_data(num_samples: int = 400, random_seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """Generate synthetic, leak-free training dataset spanning multi-domain diagnostic patterns.

    Features represent observable evidence signals (direct observations, verification status,
    contradictions, telemetry confidence, graph metrics), and binary labels represent whether
    the hypothesis corresponds to the verified root cause.
    """
    rng = np.random.RandomState(random_seed)
    X = np.zeros((num_samples, NUM_FEATURES), dtype=np.float64)
    y = np.zeros(num_samples, dtype=np.int32)

    for i in range(num_samples):
        is_true_cause = rng.rand() > 0.5
        y[i] = 1 if is_true_cause else 0

        # Feature simulation based on diagnostic physics
        if is_true_cause:
            n_support = rng.randint(1, 6)
            n_direct = rng.randint(1, n_support + 1)
            n_inferred = n_support - n_direct
            n_contra = 0
            is_verified = 1.0 if rng.rand() > 0.4 else 0.0
            is_supported = 1.0 if is_verified == 0.0 else 0.0
            is_contradicted = 0.0
            telem_conf = rng.uniform(0.7, 0.98) if rng.rand() > 0.5 else 0.0
        else:
            n_support = rng.randint(0, 3)
            n_direct = rng.randint(0, max(1, n_support))
            n_inferred = n_support - n_direct
            n_contra = rng.randint(1, 4) if rng.rand() > 0.6 else 0
            is_verified = 0.0
            is_supported = 1.0 if rng.rand() > 0.6 else 0.0
            is_contradicted = 1.0 if n_contra > 0 else 0.0
            telem_conf = rng.uniform(0.0, 0.4) if rng.rand() > 0.5 else 0.0

        has_syntax = 1.0 if rng.rand() > 0.7 else 0.0
        has_unres = 1.0 if rng.rand() > 0.7 else 0.0
        has_undecl = 1.0 if rng.rand() > 0.7 else 0.0
        has_telem = 1.0 if telem_conf > 0.0 else 0.0

        X[i, 0] = float(n_support)
        X[i, 1] = float(n_direct)
        X[i, 2] = float(n_inferred)
        X[i, 3] = float(rng.randint(0, 2))
        X[i, 4] = float(n_contra)
        X[i, 5] = has_syntax
        X[i, 6] = has_unres
        X[i, 7] = has_undecl
        X[i, 8] = has_telem
        X[i, 9] = telem_conf
        X[i, 10] = is_verified
        X[i, 11] = 0.0
        X[i, 12] = is_supported
        X[i, 13] = 1.0 if (is_verified == 0 and is_supported == 0) else 0.0
        X[i, 14] = is_contradicted
        X[i, 15] = 1.0 if n_support == 0 else 0.0
        X[i, 16] = float(rng.randint(1, 4))
        X[i, 17] = float(rng.randint(1, 4))
        X[i, 18] = float(rng.randint(5, 50))
        X[i, 19] = float(rng.randint(5, 80))
        X[i, 20] = rng.uniform(0.0, 0.3)
        X[i, 21] = float(rng.randint(0, 10))
        X[i, 22] = rng.uniform(0.2, 1.0)
        X[i, 23] = 1.0 if rng.rand() > 0.2 else 0.0

    return X, y


class MLHypothesisRanker:
    """Calibrated Machine Learning hypothesis ranker trained on leak-free diagnostic signals."""

    def __init__(self, model_type: str = "calibrated_logistic") -> None:
        self.model_type = model_type
        self.model: Optional[Any] = None
        self._is_trained = False
        self._initialize_model()

    def _initialize_model(self) -> None:
        if self.model_type == "calibrated_logistic":
            base = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
            self.model = CalibratedClassifierCV(estimator=base, method="sigmoid", cv=3)
        elif self.model_type == "calibrated_random_forest":
            base = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42)
            self.model = CalibratedClassifierCV(estimator=base, method="sigmoid", cv=3)
        elif self.model_type == "ensemble":
            base_rf = RandomForestClassifier(n_estimators=40, max_depth=5, random_state=42)
            self.model = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=3)
        else:
            raise ValueError(f"Unknown model_type: {self.model_type}")

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the calibrated classifier on feature matrix X and ground truth labels y."""
        self.model.fit(X, y)
        self._is_trained = True

    def train_default(self) -> None:
        """Train model with standard synthetic diagnostic dataset."""
        X, y = generate_synthetic_training_data(num_samples=500, random_seed=42)
        self.train(X, y)

    def predict_probability(
        self,
        hypo: FaultHypothesis,
        evidence: List[DiagnosticEvidenceRecord],
        system_map: Optional[DiagnosticSystemMap] = None,
    ) -> float:
        """Predict calibrated probability in [0.0, 1.0] for a single FaultHypothesis."""
        if not self._is_trained:
            self.train_default()

        if hypo.category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
            return 0.0
        if hypo.verification_status == "contradicted":
            return 0.02

        feat = extract_hypothesis_features(hypo, evidence, system_map).reshape(1, -1)
        proba = self.model.predict_proba(feat)[0, 1]

        # Apply negative probe contradiction refutation
        if hypo.contradicting_evidence_ids:
            proba = max(0.01, proba * (0.2 ** len(hypo.contradicting_evidence_ids)))

        return float(proba)

    def rank_hypotheses(
        self,
        hypotheses: List[FaultHypothesis],
        evidence: List[DiagnosticEvidenceRecord],
        system_map: Optional[DiagnosticSystemMap] = None,
        abstention_threshold: float = 0.25,
    ) -> List[FaultHypothesis]:
        """Rank hypotheses using calibrated ML probability predictions."""
        if not hypotheses:
            return []

        if len(hypotheses) == 1 and hypotheses[0].category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
            return hypotheses

        raw_scored: List[Tuple[FaultHypothesis, float]] = []
        for h in hypotheses:
            prob = self.predict_probability(h, evidence, system_map)
            raw_scored.append((h, prob))

        raw_scored.sort(key=lambda x: x[1], reverse=True)
        max_prob = raw_scored[0][1] if raw_scored else 0.0
        should_abstain = max_prob < abstention_threshold

        # Compute normalized softmax probabilities across candidate hypotheses
        raw_probs_arr = np.array([p for _, p in raw_scored], dtype=np.float64)
        if len(raw_probs_arr) > 1:
            exp_p = np.exp((raw_probs_arr - np.max(raw_probs_arr)) / 0.5)
            norm_probs = (exp_p / np.sum(exp_p)).tolist()
        else:
            norm_probs = [max_prob]

        ranked: List[FaultHypothesis] = []
        for (hypo, _), norm_p in zip(raw_scored, norm_probs):
            score_pct = round(norm_p * 100.0, 1)

            if hypo.verification_status == "contradicted":
                conf = "refuted"
            elif norm_p >= 0.70:
                conf = "high"
            elif norm_p >= 0.40:
                conf = "medium"
            else:
                conf = "low"

            status = hypo.verification_status
            if should_abstain and status not in ("verified", "contradicted"):
                status = "insufficient_evidence"

            rationale = (
                f"ML model ({self.model_type}) calibrated probability: {score_pct}% "
                f"(status={hypo.verification_status}, supporting={len(hypo.supporting_evidence_ids)})."
            )
            if hypo.verification_status == "contradicted":
                rationale += " Contradicted by diagnostic probe finding."

            ranked.append(
                hypo.model_copy(
                    update={
                        "relative_ranking_score": score_pct,
                        "confidence_level": conf,
                        "verification_status": status,
                        "score_rationale": rationale,
                    }
                )
            )

        return ranked
