"""Evaluation metrics and methodology for ORACLE diagnostic models.

Provides rigorous, dependency-free implementations of:
- Top-1 and Top-3 Root-Cause Ranking Accuracy
- Precision, Recall, Macro-F1, and False-Positive Rate
- Expected Calibration Error (ECE) for confidence assessment
- Deliberate Abstention metrics for insufficient evidence
- Diagnostic latency and probe execution cost tracking
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set


def top_k_ranking_accuracy(
    ranked_predictions: List[List[str]],
    ground_truth: List[str],
    k: int = 1,
) -> float:
    """Calculate the proportion of cases where the true root-cause is within the top-k ranked predictions.

    Args:
        ranked_predictions: List of lists containing predicted labels ordered by model confidence (highest first).
        ground_truth: True target labels for each case.
        k: Maximum rank depth to evaluate (e.g. k=1 for Top-1, k=3 for Top-3).

    Returns:
        Fraction of predictions where the true label appears in the top-k predictions (between 0.0 and 1.0).
    """
    if len(ranked_predictions) != len(ground_truth):
        raise ValueError(
            f"Length mismatch: {len(ranked_predictions)} predictions vs {len(ground_truth)} ground truth labels."
        )
    if not ground_truth:
        return 0.0
    if k < 1:
        raise ValueError("k must be >= 1.")

    hits = 0
    for preds, true_label in zip(ranked_predictions, ground_truth):
        top_k_candidates = preds[:k]
        if true_label in top_k_candidates:
            hits += 1

    return hits / len(ground_truth)


def classification_metrics(
    predictions: List[str],
    ground_truth: List[str],
    all_classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute overall accuracy, per-class metrics, and macro-averaged Precision, Recall, and F1.

    Pure-Python implementation avoiding external library dependencies.
    """
    if len(predictions) != len(ground_truth):
        raise ValueError("Length mismatch between predictions and ground_truth.")
    if not ground_truth:
        return {
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "per_class": {},
        }

    classes: Set[str] = set(ground_truth).union(predictions)
    if all_classes:
        classes.update(all_classes)

    total_samples = len(ground_truth)
    total_correct = sum(1 for p, y in zip(predictions, ground_truth) if p == y)
    overall_accuracy = total_correct / total_samples

    per_class: Dict[str, Dict[str, float]] = {}
    precisions: List[float] = []
    recalls: List[float] = []
    f1_scores: List[float] = []

    for c in sorted(classes):
        tp = sum(1 for p, y in zip(predictions, ground_truth) if p == c and y == c)
        fp = sum(1 for p, y in zip(predictions, ground_truth) if p == c and y != c)
        fn = sum(1 for p, y in zip(predictions, ground_truth) if p != c and y == c)
        tn = sum(1 for p, y in zip(predictions, ground_truth) if p != c and y != c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        per_class[c] = {
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "tn": float(tn),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
            "support": float(tp + fn),
        }

        # Include classes that have support in ground truth for macro averaging
        if (tp + fn) > 0:
            precisions.append(precision)
            recalls.append(recall)
            f1_scores.append(f1)

    macro_p = sum(precisions) / len(precisions) if precisions else 0.0
    macro_r = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    return {
        "accuracy": round(overall_accuracy, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
    }


def false_positive_rate(predictions: List[str], ground_truth: List[str], target_label: str) -> float:
    """Calculate the False Positive Rate (FPR = FP / (FP + TN)) for a specific target class."""
    if len(predictions) != len(ground_truth):
        raise ValueError("Length mismatch between predictions and ground_truth.")
    fp = sum(1 for p, y in zip(predictions, ground_truth) if p == target_label and y != target_label)
    tn = sum(1 for p, y in zip(predictions, ground_truth) if p != target_label and y != target_label)
    denominator = fp + tn
    if denominator == 0:
        return 0.0
    return fp / denominator


def expected_calibration_error(
    confidences: List[float],
    correct_flags: List[bool],
    num_bins: int = 10,
) -> float:
    """Calculate Expected Calibration Error (ECE) across confidence bins.

    A well-calibrated model produces confidence scores that equal the empirical probability
    of being correct (e.g. 80% confidence implies an 80% empirical accuracy).

    Formula:
        ECE = sum_{b=1}^{B} (|B_b| / N) * |acc(B_b) - conf(B_b)|
    """
    if len(confidences) != len(correct_flags):
        raise ValueError("Length mismatch between confidences and correct_flags.")
    if not confidences:
        return 0.0
    if num_bins < 2:
        raise ValueError("num_bins must be >= 2.")

    n = len(confidences)
    bin_size = 1.0 / num_bins
    total_ece = 0.0

    for i in range(num_bins):
        bin_lower = i * bin_size
        bin_upper = (i + 1) * bin_size

        # Find items belonging to this confidence bin
        in_bin_indices = [
            j
            for j, c in enumerate(confidences)
            if (bin_lower <= c < bin_upper) or (i == num_bins - 1 and c == 1.0)
        ]

        bin_count = len(in_bin_indices)
        if bin_count > 0:
            bin_acc = sum(1 for idx in in_bin_indices if correct_flags[idx]) / bin_count
            bin_conf = sum(confidences[idx] for idx in in_bin_indices) / bin_count
            total_ece += (bin_count / n) * abs(bin_acc - bin_conf)

    return round(total_ece, 4)


def abstention_metrics(
    predictions: List[str],
    ground_truth: List[str],
    abstention_label: str = "unknown_insufficient_evidence",
) -> Dict[str, float]:
    """Evaluate model performance on deliberate abstention when evidence is insufficient."""
    if len(predictions) != len(ground_truth):
        raise ValueError("Length mismatch between predictions and ground_truth.")
    if not ground_truth:
        return {"abstention_precision": 0.0, "abstention_recall": 0.0, "coverage": 1.0}

    total = len(ground_truth)
    tp = sum(1 for p, y in zip(predictions, ground_truth) if p == abstention_label and y == abstention_label)
    fp = sum(1 for p, y in zip(predictions, ground_truth) if p == abstention_label and y != abstention_label)
    fn = sum(1 for p, y in zip(predictions, ground_truth) if p != abstention_label and y == abstention_label)
    
    total_abstained = sum(1 for p in predictions if p == abstention_label)
    coverage = (total - total_abstained) / total if total > 0 else 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "abstention_precision": round(precision, 4),
        "abstention_recall": round(recall, 4),
        "abstention_f1": round(f1, 4),
        "coverage": round(coverage, 4),
    }


def diagnostic_cost_metrics(
    latencies_ms: List[float],
    probe_costs: Optional[List[float]] = None,
) -> Dict[str, float]:
    """Summarize diagnostic run latency and probe execution cost."""
    if not latencies_ms:
        return {"mean_latency_ms": 0.0, "p95_latency_ms": 0.0, "mean_probe_cost": 0.0}

    sorted_latencies = sorted(latencies_ms)
    n = len(sorted_latencies)
    mean_lat = sum(sorted_latencies) / n
    p95_idx = min(int(n * 0.95), n - 1)
    p95_lat = sorted_latencies[p95_idx]

    mean_cost = sum(probe_costs) / len(probe_costs) if probe_costs else 0.0

    return {
        "mean_latency_ms": round(mean_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "mean_probe_cost": round(mean_cost, 4),
    }
