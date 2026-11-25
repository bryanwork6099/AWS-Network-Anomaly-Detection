import csv
import math

from pathlib import Path


DATASET_DIR = Path("dataset")

INPUT_FILES = {
    "train": DATASET_DIR / "train_normal_v3.csv",
    "validation": DATASET_DIR / "validation_v3.csv",
    "test": DATASET_DIR / "test_v3.csv"
}

FEATURE_FILES = {
    "train": DATASET_DIR / "train_rcf_features_v3.csv",
    "validation": DATASET_DIR / "validation_rcf_features_v3.csv",
    "test": DATASET_DIR / "test_rcf_features_v3.csv"
}

METADATA_FILES = {
    "validation": DATASET_DIR / "validation_metadata_v3.csv",
    "test": DATASET_DIR / "test_metadata_v3.csv"
}


FEATURE_COLUMNS = [
    "total_connections",
    "unique_destination_ips",
    "unique_destination_ports",
    "log_bytes_sent",
    "log_bytes_received",
    "failed_connections",
    "failed_connection_rate",
    "destination_ip_ratio",
    "destination_port_ratio",
    "udp_ratio"
]


METADATA_COLUMNS = [
    "timestamp",
    "source_ip",
    "ground_truth_label"
]


def transform_row(row):

    total = int(row["total_connections"])

    if total <= 0:
        raise ValueError("Connection count must be positive.")

    failed = int(row["failed_connections"])
    unique_ips = int(row["unique_destination_ips"])
    unique_ports = int(row["unique_destination_ports"])
    udp = int(row["udp_connections"])

    return {
        "total_connections": total,
        "unique_destination_ips": unique_ips,
        "unique_destination_ports": unique_ports,

        "log_bytes_sent": math.log1p(
            int(row["total_bytes_sent"])
        ),

        "log_bytes_received": math.log1p(
            int(row["total_bytes_received"])
        ),

        "failed_connections": failed,

        "failed_connection_rate": failed / total,

        "destination_ip_ratio": unique_ips / total,

        "destination_port_ratio": unique_ports / total,

        "udp_ratio": udp / total
    }


def main():

    print("Starting V3 Feature Engineering...\n")

    for dataset_name, input_path in INPUT_FILES.items():

        features = []
        metadata = []

        with input_path.open(
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                features.append(transform_row(row))

                if dataset_name in METADATA_FILES:

                    metadata.append({
                        column: row[column]
                        for column in METADATA_COLUMNS
                    })

        with FEATURE_FILES[dataset_name].open(
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=FEATURE_COLUMNS
            )

            writer.writeheader()
            writer.writerows(features)

        if dataset_name in METADATA_FILES:

            with METADATA_FILES[dataset_name].open(
                "w",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=METADATA_COLUMNS
                )

                writer.writeheader()
                writer.writerows(metadata)

        print(f"{dataset_name.upper()} DATASET")
        print("Observations:", len(features))
        print("Features:", len(FEATURE_COLUMNS))
        print("Feature file:", FEATURE_FILES[dataset_name])

        if dataset_name in METADATA_FILES:
            print("Metadata file:", METADATA_FILES[dataset_name])

        print()

    print("Feature engineering completed.")

    print(
        "\nGround-truth labels, timestamps and source IPs "
        "are excluded from model feature files."
    )


if __name__ == "__main__":
    main()
