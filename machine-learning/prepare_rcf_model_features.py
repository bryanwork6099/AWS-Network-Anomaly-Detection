import csv
import json
import math
import statistics

from pathlib import Path


DATASET_DIR = Path("dataset")

SPLITS = ["train", "validation", "test"]

INPUT_FILES = {
    "train": "train_rcf_features_v3.csv",
    "validation": "validation_rcf_features_v3.csv",
    "test": "test_rcf_features_v3.csv"
}

OUTPUT_FILES = {
    "train": "train_rcf_model_v3.csv",
    "validation": "validation_rcf_model_v3.csv",
    "test": "test_rcf_model_v3.csv"
}


def load_features(path):

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames

        rows = [
            {
                name: float(value)
                for name, value in row.items()
            }
            for row in reader
        ]

    return columns, rows


def transform_features(rows):

    transformed = []

    for row in rows:

        new_row = row.copy()

        # Reduce the scale of failed connection counts.
        new_row["failed_connections"] = math.log1p(
            new_row["failed_connections"]
        )

        # Give the transformed feature an explicit name.
        new_row["log_failed_connections"] = (
            new_row.pop("failed_connections")
        )

        transformed.append(new_row)

    return transformed


def calculate_scaler(columns, training_rows):

    scaler = {}

    for column in columns:

        values = [
            row[column]
            for row in training_rows
        ]

        mean = statistics.mean(values)
        std = statistics.pstdev(values)

        if std < 1e-12:

            scaler[column] = {
                "mean": mean,
                "scale": 1.0,
                "standardized": False
            }

        else:

            scaler[column] = {
                "mean": mean,
                "scale": std,
                "standardized": True
            }

    return scaler


def apply_scaler(rows, columns, scaler):

    scaled_rows = []

    for row in rows:

        scaled_row = {}

        for column in columns:

            parameters = scaler[column]

            value = row[column]

            if parameters["standardized"]:

                value = (
                    value - parameters["mean"]
                ) / parameters["scale"]

            scaled_row[column] = value

        scaled_rows.append(scaled_row)

    return scaled_rows


def save_features(path, columns, rows):

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(rows)


def main():

    print("Preparing RCF Model Features...\n")

    datasets = {}

    for split in SPLITS:

        input_path = DATASET_DIR / INPUT_FILES[split]

        columns, rows = load_features(input_path)

        datasets[split] = transform_features(rows)

        print(
            f"{split.upper()} observations: {len(rows)}"
        )

    # The scaler is fitted exclusively on training data.
    model_columns = list(datasets["train"][0].keys())

    scaler = calculate_scaler(
        model_columns,
        datasets["train"]
    )

    print("\nSCALING SUMMARY")
    print("-" * 65)

    for column, parameters in scaler.items():

        if parameters["standardized"]:
            method = "Standardized"
        else:
            method = "Left unchanged (zero variance)"

        print(f"{column:<30} {method}")

    # Apply the same training scaler to all three datasets.
    for split in SPLITS:

        scaled_rows = apply_scaler(
            datasets[split],
            model_columns,
            scaler
        )

        output_path = DATASET_DIR / OUTPUT_FILES[split]

        save_features(
            output_path,
            model_columns,
            scaled_rows
        )

        print(
            f"\n{split.upper()} output: {output_path}"
        )

    # Save the training scaler parameters for reproducibility.
    scaler_path = (
        DATASET_DIR / "rcf_scaler_parameters_v3.json"
    )

    with scaler_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            scaler,
            file,
            indent=4
        )

    print("\nScaler parameters:", scaler_path)

    print("\nFeature preparation completed.")


if __name__ == "__main__":
    main()
