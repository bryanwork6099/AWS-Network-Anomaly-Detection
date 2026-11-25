import csv

from pathlib import Path


DATASET_DIR = Path("dataset")

OUTPUT_DIR = DATASET_DIR / "sagemaker_rcf"

FEATURE_FILES = {
    "train": "train_rcf_model_v3.csv",
    "validation": "validation_rcf_model_v3.csv",
    "test": "test_rcf_model_v3.csv"
}

METADATA_FILES = {
    "validation": "validation_metadata_v3.csv",
    "test": "test_metadata_v3.csv"
}


def load_csv(path):

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        return reader.fieldnames, list(reader)


def write_csv(path, rows):

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerows(rows)


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Preparing SageMaker RCF datasets...\n")

    for split in ["train", "validation", "test"]:

        feature_columns, feature_rows = load_csv(
            DATASET_DIR / FEATURE_FILES[split]
        )

        if not feature_rows:
            raise ValueError(f"{split}: feature dataset is empty")

        output_rows = [
            [row[column] for column in feature_columns]
            for row in feature_rows
        ]

        if split in METADATA_FILES:

            metadata_columns, metadata_rows = load_csv(
                DATASET_DIR / METADATA_FILES[split]
            )

            if len(feature_rows) != len(metadata_rows):
                raise ValueError(
                    f"{split}: feature and metadata row counts differ"
                )

            if "ground_truth_label" not in metadata_columns:
                raise ValueError(
                    f"{split}: ground-truth label is missing"
                )

            suspicious_count = sum(
                row["ground_truth_label"] == "suspicious"
                for row in metadata_rows
            )

            print(f"{split.upper()} DATA")
            print("Observations:", len(output_rows))
            print("Features:", len(feature_columns))
            print("Suspicious observations:", suspicious_count)
            print("Normal observations:", len(output_rows) - suspicious_count)

        else:

            print("TRAINING DATA")
            print("Observations:", len(output_rows))
            print("Features:", len(feature_columns))

        output_path = OUTPUT_DIR / f"{split}.csv"

        write_csv(output_path, output_rows)

        print("Labels included in model input: No")
        print("Output:", output_path)
        print()

    print("SageMaker dataset preparation completed.")


if __name__ == "__main__":
    main()
