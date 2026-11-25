import csv
import json

from collections import defaultdict
from datetime import datetime
from pathlib import Path


INPUT_FILE = Path("dataset/advanced_network_traffic_v3.jsonl")
OUTPUT_FILE = Path("dataset/time_window_features_v3.csv")


FEATURE_COLUMNS = [
    "timestamp",
    "source_ip",
    "total_connections",
    "unique_destination_ips",
    "unique_destination_ports",
    "total_bytes_sent",
    "total_bytes_received",
    "failed_connections",
    "tcp_connections",
    "udp_connections",
    "ground_truth_label"
]


def main():
    print("Starting V3 Time-Window Feature Extraction...\n")

    # Each key represents one source IP during one minute.
    windows = defaultdict(lambda: {
        "total_connections": 0,
        "destination_ips": set(),
        "destination_ports": set(),
        "total_bytes_sent": 0,
        "total_bytes_received": 0,
        "failed_connections": 0,
        "tcp_connections": 0,
        "udp_connections": 0,
        "labels": set()
    })

    total_events = 0

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            event = json.loads(line)
            total_events += 1

            event_time = datetime.fromisoformat(event["timestamp"])

            window_time = event_time.replace(
                second=0,
                microsecond=0
            ).isoformat()

            source_ip = event["source_ip"]

            key = (source_ip, window_time)
            features = windows[key]

            features["total_connections"] += 1
            features["destination_ips"].add(
                event["destination_ip"]
            )
            features["destination_ports"].add(
                event["destination_port"]
            )

            features["total_bytes_sent"] += event["bytes_sent"]
            features["total_bytes_received"] += event["bytes_received"]

            if event["connection_status"] == "failed":
                features["failed_connections"] += 1

            if event["protocol"].upper() == "TCP":
                features["tcp_connections"] += 1

            elif event["protocol"].upper() == "UDP":
                features["udp_connections"] += 1

            features["labels"].add(event["label"])

    rows = []

    for (source_ip, timestamp), features in windows.items():

        # A window is suspicious if it contains any suspicious event.
        ground_truth = (
            "suspicious"
            if "suspicious" in features["labels"]
            else "normal"
        )

        rows.append({
            "timestamp": timestamp,
            "source_ip": source_ip,
            "total_connections": features["total_connections"],
            "unique_destination_ips": len(
                features["destination_ips"]
            ),
            "unique_destination_ports": len(
                features["destination_ports"]
            ),
            "total_bytes_sent": features["total_bytes_sent"],
            "total_bytes_received": features["total_bytes_received"],
            "failed_connections": features["failed_connections"],
            "tcp_connections": features["tcp_connections"],
            "udp_connections": features["udp_connections"],
            "ground_truth_label": ground_truth
        })

    rows.sort(
        key=lambda row: (
            row["timestamp"],
            row["source_ip"]
        )
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FEATURE_COLUMNS
        )

        writer.writeheader()
        writer.writerows(rows)

    normal_count = sum(
        1 for row in rows
        if row["ground_truth_label"] == "normal"
    )

    suspicious_count = sum(
        1 for row in rows
        if row["ground_truth_label"] == "suspicious"
    )

    print("Feature extraction completed.")
    print("Total network events:", total_events)
    print("Source IP / minute observations:", len(rows))
    print("Normal observations:", normal_count)
    print("Suspicious observations:", suspicious_count)
    print("Output file:", OUTPUT_FILE)

    print(
        "\nIMPORTANT: Exclude timestamp, source_ip, and "
        "ground_truth_label from Random Cut Forest model inputs."
    )


if __name__ == "__main__":
    main()
