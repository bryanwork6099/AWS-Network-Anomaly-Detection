import csv

from pathlib import Path


DATASET_DIR = Path("dataset")

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


def load_csv(path):
    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def main():

    print("Inspecting Suspicious Feature Observations...\n")

    for split in ["validation", "test"]:

        feature_rows = load_csv(
            DATASET_DIR / f"{split}_rcf_features_v3.csv"
        )

        metadata_rows = load_csv(
            DATASET_DIR / f"{split}_metadata_v3.csv"
        )

        print(f"\n{split.upper()} SUSPICIOUS OBSERVATIONS")
        print("=" * 90)

        suspicious_count = 0

        for features, metadata in zip(
            feature_rows,
            metadata_rows
        ):

            if metadata["ground_truth_label"] != "suspicious":
                continue

            suspicious_count += 1

            print("\nTimestamp:", metadata["timestamp"])
            print("Source IP:", metadata["source_ip"])

            for column in FEATURE_COLUMNS:
                print(f"{column}: {features[column]}")

        print("\nSuspicious observations:", suspicious_count)

    print("\nInspection completed.")


if __name__ == "__main__":
    main()
