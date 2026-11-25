import csv
import json
from pathlib import Path
from statistics import mean, median


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCORE_FILE = PROJECT_ROOT / "dataset" / "validation.csv.out"
METADATA_FILE = PROJECT_ROOT / "dataset" / "validation_metadata_v3.csv"
OUTPUT_FILE = PROJECT_ROOT / "dataset" / "validation_scored_v3.csv"


def percentile(values, percentage):
    ordered = sorted(values)

    if not ordered:
        return 0.0

    position = (len(ordered) - 1) * percentage / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


def main():
    print("AWS NETWORK ANOMALY DETECTION")
    print("VALIDATION MODEL EVALUATION")
    print("=" * 55)

    # Load SageMaker inference output
    with open(SCORE_FILE, "r", encoding="utf-8") as file:
        score_data = json.load(file)

    scores = [float(item["score"]) for item in score_data["scores"]]

    # Load validation metadata
    with open(METADATA_FILE, "r", newline="", encoding="utf-8") as file:
        metadata = list(csv.DictReader(file))

    # Verify record counts
    print("\nRECORD VALIDATION")
    print("-" * 55)
    print(f"Inference scores: {len(scores)}")
    print(f"Metadata records: {len(metadata)}")

    if len(scores) != len(metadata):
        raise ValueError("Score and metadata counts do not match!")

    if not scores:
        raise ValueError("No inference scores found.")

    if not all(
        label in {"normal", "suspicious"}
        for label in (row["ground_truth_label"] for row in metadata)
    ):
        raise ValueError("Unexpected ground-truth label found.")

    print("Record counts and labels verified.")

    # Combine scores and metadata in original input order
    results = []

    for row, score in zip(metadata, scores):
        results.append({
            "timestamp": row["timestamp"],
            "source_ip": row["source_ip"],
            "ground_truth_label": row["ground_truth_label"],
            "anomaly_score": score,
        })

    # Rank observations: highest score first
    ranked = sorted(
        results,
        key=lambda item: item["anomaly_score"],
        reverse=True
    )

    for rank, row in enumerate(ranked, start=1):
        row["anomaly_rank"] = rank

    # Score distributions
    normal_scores = [
        row["anomaly_score"]
        for row in results
        if row["ground_truth_label"] == "normal"
    ]

    suspicious_scores = [
        row["anomaly_score"]
        for row in results
        if row["ground_truth_label"] == "suspicious"
    ]

    print("\nDATASET SUMMARY")
    print("-" * 55)
    print(f"Total observations: {len(results)}")
    print(f"Normal observations: {len(normal_scores)}")
    print(f"Suspicious observations: {len(suspicious_scores)}")

    print("\nOVERALL ANOMALY SCORE DISTRIBUTION")
    print("-" * 55)
    all_scores = [row["anomaly_score"] for row in results]

    print(f"Minimum: {min(all_scores):.6f}")
    print(f"Mean:    {mean(all_scores):.6f}")
    print(f"Median:  {median(all_scores):.6f}")
    print(f"P95:     {percentile(all_scores, 95):.6f}")
    print(f"P99:     {percentile(all_scores, 99):.6f}")
    print(f"Maximum: {max(all_scores):.6f}")

    print("\nNORMAL VS SUSPICIOUS SCORES")
    print("-" * 55)

    if normal_scores:
        print(f"Normal mean:      {mean(normal_scores):.6f}")
        print(f"Normal median:    {median(normal_scores):.6f}")
        print(f"Normal P99:       {percentile(normal_scores, 99):.6f}")
        print(f"Normal maximum:   {max(normal_scores):.6f}")

    if suspicious_scores:
        print(f"Suspicious mean:  {mean(suspicious_scores):.6f}")
        print(f"Suspicious median:{median(suspicious_scores):.6f}")
        print(f"Suspicious min:   {min(suspicious_scores):.6f}")
        print(f"Suspicious max:   {max(suspicious_scores):.6f}")

    print("\nKNOWN SUSPICIOUS OBSERVATIONS")
    print("-" * 55)

    suspicious_results = [
        row for row in ranked
        if row["ground_truth_label"] == "suspicious"
    ]

    for row in suspicious_results:
        print(
            f"Rank: {row['anomaly_rank']:>5} | "
            f"Score: {row['anomaly_score']:.6f} | "
            f"IP: {row['source_ip']} | "
            f"Time: {row['timestamp']}"
        )

    print("\nTOP 20 HIGHEST ANOMALY SCORES")
    print("-" * 55)

    for row in ranked[:20]:
        print(
            f"Rank {row['anomaly_rank']:>5} | "
            f"{row['anomaly_score']:.6f} | "
            f"{row['ground_truth_label']:<10} | "
            f"{row['source_ip']}"
        )

    # Export combined results
    fieldnames = [
        "timestamp",
        "source_ip",
        "ground_truth_label",
        "anomaly_score",
        "anomaly_rank",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ranked)

    print("\nOUTPUT")
    print("-" * 55)
    print(f"Saved: {OUTPUT_FILE}")
    print("\nVALIDATION EVALUATION COMPLETED")


if __name__ == "__main__":
    main()
