import csv
import json
import math
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCORE_FILE = PROJECT_ROOT / "dataset" / "test.csv.out"
METADATA_FILE = PROJECT_ROOT / "dataset" / "test_metadata_v3.csv"
OUTPUT_FILE = PROJECT_ROOT / "dataset" / "test_scored_v3.csv"

THRESHOLD = 2.980612


def calculate_auc(labels, scores):
    """Calculate ROC-AUC using the rank-sum method."""
    positives = sum(labels)
    negatives = len(labels) - positives

    if positives == 0 or negatives == 0:
        return float("nan")

    ranked = sorted(
        zip(scores, labels),
        key=lambda item: item[0]
    )

    rank_sum = 0
    i = 0

    while i < len(ranked):
        j = i + 1

        while j < len(ranked) and ranked[j][0] == ranked[i][0]:
            j += 1

        average_rank = ((i + 1) + j) / 2

        for k in range(i, j):
            if ranked[k][1] == 1:
                rank_sum += average_rank

        i = j

    return (
        rank_sum - positives * (positives + 1) / 2
    ) / (positives * negatives)


def main():
    print("RANDOM CUT FOREST TEST EVALUATION")
    print("=" * 55)

    with open(SCORE_FILE, "r", encoding="utf-8") as file:
        inference = json.load(file)

    scores = [
        float(item["score"])
        for item in inference["scores"]
    ]

    with open(METADATA_FILE, "r", newline="", encoding="utf-8") as file:
        metadata = list(csv.DictReader(file))

    if len(scores) != len(metadata):
        raise ValueError("Score and metadata counts do not match.")

    if not all(math.isfinite(score) for score in scores):
        raise ValueError("Non-finite inference score detected.")

    labels = []

    for row in metadata:
        label = row["ground_truth_label"].strip().lower()

        if label not in ("normal", "suspicious"):
            raise ValueError(f"Unexpected label: {label}")

        labels.append(1 if label == "suspicious" else 0)

    print(f"Total observations: {len(scores)}")
    print(f"Normal observations: {labels.count(0)}")
    print(f"Suspicious observations: {labels.count(1)}")
    print(f"Threshold: {THRESHOLD}")

    predictions = [
        1 if score >= THRESHOLD else 0
        for score in scores
    ]

    tp = sum(p == 1 and y == 1 for p, y in zip(predictions, labels))
    tn = sum(p == 0 and y == 0 for p, y in zip(predictions, labels))
    fp = sum(p == 1 and y == 0 for p, y in zip(predictions, labels))
    fn = sum(p == 0 and y == 1 for p, y in zip(predictions, labels))

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )
    fpr = fp / (fp + tn) if fp + tn else 0

    auc = calculate_auc(labels, scores)

    print("\nCONFUSION MATRIX")
    print("-" * 55)
    print(f"True Positives:  {tp}")
    print(f"True Negatives:  {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")

    print("\nCLASSIFICATION METRICS")
    print("-" * 55)
    print(f"ROC-AUC:           {auc:.6f}")
    print(f"Precision:         {precision:.6f}")
    print(f"Recall:            {recall:.6f}")
    print(f"F1-score:          {f1:.6f}")
    print(f"False Positive Rate: {fpr:.6f}")

    print("\nSCORE DISTRIBUTION")
    print("-" * 55)
    print(f"Minimum: {min(scores):.6f}")
    print(f"Maximum: {max(scores):.6f}")
    print(f"Mean:    {sum(scores) / len(scores):.6f}")

    print("\nTOP 20 HIGHEST ANOMALY SCORES")
    print("-" * 75)

    results = []

    for row, score, label, prediction in zip(
        metadata, scores, labels, predictions
    ):
        results.append({
            "timestamp": row["timestamp"],
            "source_ip": row["source_ip"],
            "ground_truth_label": (
                "suspicious" if label else "normal"
            ),
            "anomaly_score": score,
            "predicted_label": (
                "suspicious" if prediction else "normal"
            ),
        })

    results.sort(
        key=lambda item: item["anomaly_score"],
        reverse=True
    )

    for rank, item in enumerate(results[:20], start=1):
        print(
            f"{rank:2} | "
            f"{item['anomaly_score']:.6f} | "
            f"{item['source_ip']} | "
            f"{item['ground_truth_label']} | "
            f"{item['timestamp']}"
        )

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "source_ip",
                "ground_truth_label",
                "anomaly_score",
                "predicted_label",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nScored dataset saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
