import csv
import math

from pathlib import Path


INPUT_FILE = Path("dataset/train_rcf_features_v3.csv")


def percentile(values, percentage):
    ordered = sorted(values)

    index = (len(ordered) - 1) * percentage
    lower = math.floor(index)
    upper = math.ceil(index)

    if lower == upper:
        return ordered[lower]

    fraction = index - lower

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


def main():

    print("Inspecting Training Feature Distributions...\n")

    with INPUT_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        columns = {
            name: [] for name in reader.fieldnames
        }

        for row in reader:
            for name, value in row.items():
                columns[name].append(float(value))

    print(
        f"{'FEATURE':<30}"
        f"{'MIN':>12}"
        f"{'MEDIAN':>12}"
        f"{'P95':>12}"
        f"{'P99':>12}"
        f"{'MAX':>12}"
    )

    print("-" * 90)

    for name, values in columns.items():

        print(
            f"{name:<30}"
            f"{min(values):>12.3f}"
            f"{percentile(values, 0.50):>12.3f}"
            f"{percentile(values, 0.95):>12.3f}"
            f"{percentile(values, 0.99):>12.3f}"
            f"{max(values):>12.3f}"
        )

    print("\nTotal observations:", len(next(iter(columns.values()))))
    print("Total numerical features:", len(columns))
    print("\nDistribution inspection completed.")


if __name__ == "__main__":
    main()
