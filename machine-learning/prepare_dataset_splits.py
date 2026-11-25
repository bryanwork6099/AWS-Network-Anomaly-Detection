import csv

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


INPUT_FILE = Path("dataset/time_window_features_v3.csv")

TRAIN_FILE = Path("dataset/train_normal_v3.csv")
VALIDATION_FILE = Path("dataset/validation_v3.csv")
TEST_FILE = Path("dataset/test_v3.csv")


def main():
    print("Preparing chronological dataset splits...\n")

    with INPUT_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not rows:
        raise ValueError("Input dataset is empty.")

    rows.sort(key=lambda row: row["timestamp"])

    timestamps = [
        datetime.fromisoformat(row["timestamp"])
        for row in rows
    ]

    start_time = min(timestamps)
    end_time = max(timestamps)

    # Each observation represents one minute.
    total_duration = end_time - start_time + timedelta(minutes=1)

    training_boundary = start_time + total_duration * 0.60
    validation_boundary = start_time + total_duration * 0.80

    training_rows = []
    validation_rows = []
    test_rows = []

    for row in rows:
        timestamp = datetime.fromisoformat(row["timestamp"])

        if timestamp < training_boundary:
            # Only normal observations are used for training.
            if row["ground_truth_label"] == "normal":
                training_rows.append(row)

        elif timestamp < validation_boundary:
            validation_rows.append(row)

        else:
            test_rows.append(row)

    def write_csv(path, dataset_rows):
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )
            writer.writeheader()
            writer.writerows(dataset_rows)

    write_csv(TRAIN_FILE, training_rows)
    write_csv(VALIDATION_FILE, validation_rows)
    write_csv(TEST_FILE, test_rows)

    def report(name, dataset_rows):
        labels = Counter(
            row["ground_truth_label"]
            for row in dataset_rows
        )

        print(name)
        print("Total observations:", len(dataset_rows))
        print("Normal:", labels["normal"])
        print("Suspicious:", labels["suspicious"])

        if dataset_rows:
            print("First timestamp:", dataset_rows[0]["timestamp"])
            print("Last timestamp:", dataset_rows[-1]["timestamp"])

        print()

    print("Simulation start:", start_time.isoformat())
    print("Simulation end:", end_time.isoformat())
    print("Training boundary:", training_boundary.isoformat())
    print("Validation boundary:", validation_boundary.isoformat())
    print()

    report("TRAINING DATASET", training_rows)
    report("VALIDATION DATASET", validation_rows)
    report("TEST DATASET", test_rows)

    print("Output files:")
    print(TRAIN_FILE)
    print(VALIDATION_FILE)
    print(TEST_FILE)

    print("\nDataset splitting completed.")


if __name__ == "__main__":
    main()
