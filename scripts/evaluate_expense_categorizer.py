"""Evaluate the deterministic expense rules against a fixed held-out dataset."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from utils.ai_categorizer import AICategorizer, CATEGORIES


DEFAULT_DATASET = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "expense_categorization_eval.json"
)


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate(dataset_path: Path = DEFAULT_DATASET) -> dict[str, Any]:
    examples = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(examples, list) or not examples:
        raise ValueError("Evaluation dataset must be a non-empty JSON array")

    categories = tuple(CATEGORIES)
    unknown_labels = {
        example.get("expected")
        for example in examples
        if not isinstance(example, dict) or example.get("expected") not in categories
    }
    if unknown_labels:
        raise ValueError(f"Unknown evaluation labels: {sorted(map(str, unknown_labels))}")

    matrix = {actual: {predicted: 0 for predicted in categories} for actual in categories}
    predictions = []
    for example in examples:
        actual = example["expected"]
        predicted = AICategorizer().categorize(example.get("description"))["category"]
        matrix[actual][predicted] += 1
        predictions.append((actual, predicted))

    per_category = {}
    total = len(predictions)
    correct = sum(actual == predicted for actual, predicted in predictions)
    for category in categories:
        true_positive = matrix[category][category]
        false_positive = sum(matrix[actual][category] for actual in categories if actual != category)
        false_negative = sum(matrix[category][predicted] for predicted in categories if predicted != category)
        support = sum(matrix[category].values())
        precision = _safe_ratio(true_positive, true_positive + false_positive)
        recall = _safe_ratio(true_positive, true_positive + false_negative)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        per_category[category] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    macro_precision = sum(item["precision"] for item in per_category.values()) / len(categories)
    macro_recall = sum(item["recall"] for item in per_category.values()) / len(categories)
    macro_f1 = sum(item["f1"] for item in per_category.values()) / len(categories)
    weighted_precision = sum(item["precision"] * item["support"] for item in per_category.values()) / total
    weighted_recall = sum(item["recall"] * item["support"] for item in per_category.values()) / total
    weighted_f1 = sum(item["f1"] * item["support"] for item in per_category.values()) / total
    other_count = sum(predicted == "Other" for _, predicted in predictions)

    return {
        "dataset_size": total,
        "accuracy": correct / total,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_precision": weighted_precision,
        "weighted_recall": weighted_recall,
        "weighted_f1": weighted_f1,
        "other_predictions": other_count,
        "other_rate": other_count / total,
        "per_category": per_category,
        "confusion_matrix": matrix,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()

    results = evaluate(args.dataset)
    print("Expense categorizer held-out evaluation (rule-based; no training split)")
    print(f"Dataset size: {results['dataset_size']}")
    for metric in (
        "accuracy", "macro_precision", "macro_recall", "macro_f1",
        "weighted_precision", "weighted_recall", "weighted_f1", "other_rate",
    ):
        print(f"{metric.replace('_', ' ').title()}: {results[metric]:.4f}")
    print(f"Other predictions: {results['other_predictions']}/{results['dataset_size']}")
    print("\nPer-category metrics:")
    for category, metrics in results["per_category"].items():
        print(
            f"{category:14} n={metrics['support']:2} "
            f"P={metrics['precision']:.3f} R={metrics['recall']:.3f} F1={metrics['f1']:.3f}"
        )
    print("\nConfusion matrix (rows=actual, columns=predicted):")
    categories = tuple(CATEGORIES)
    print("actual\\pred " + " ".join(f"{category[:5]:>5}" for category in categories))
    for actual in categories:
        values = " ".join(f"{results['confusion_matrix'][actual][predicted]:5}" for predicted in categories)
        print(f"{actual[:12]:12} {values}")


if __name__ == "__main__":
    main()