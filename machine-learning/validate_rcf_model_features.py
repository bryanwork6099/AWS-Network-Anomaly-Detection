import csv
import math
import statistics

from pathlib import Path


DATASET_DIR = Path("dataset")

FILES = {
    "train": "train_rcf_model_v3.csv",
    "validation": "validation_rcf_model_v3.csv",
    "test": "test_rcf_model_v3.csv"
}


def load_csv(path):

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames
        rows = [
            {key: float(value) for key, value in row.items()}
            for row in reader
        ]

    return columns, rows


def main():

    datasets = {}

    print("VALIDATING RCF MODEL DATASETS\n")

    for split, filename in FILES.items():

        columns, rows = load_csv(DATASET_DIR / filename)

        datasets[split] = rows

        valid = all(
            math.isfinite(value)
            for row in rows
            for value in row.values()
        )

        print(f"{split.upper()}")
        print("-" * 50)
        print("Observations:", len(rows))
        print("Features:", len(columns))
        print("All values finite:", valid)

    train = datasets["train"]

    print("\nTRAINING FEATURE STATISTICS")
    print("-" * 85)

    print(
        f"{'FEATURE':<30}"
        f"{'MEAN':>15}"
        f"{'STD DEV':>15}"
    )

    for column in train[0]:

        values = [row[column] for row in train]

        print(
            f"{column:<30}"
            f"{statistics.mean(values):>15.6f}"
            f"{statistics.pstdev(values):>15.6f}"
        )

    print("\nFEATURE CONSISTENCY")

    train_columns = list(train[0].keys())

    for split, rows in datasets.items():

        consistent = (
            all(list(row.keys()) == train_columns for row in rows)
            and all(len(row) == len(train_columns) for row in rows)
        )

        print(f"{split.upper()} feature order consistent:", consistent)

    print("\nValidation completed.")


if __name__ == "__main__":
    main()
