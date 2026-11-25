import json
import csv

from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path("dataset/advanced_network_traffic.jsonl")
OUTPUT_FILE = Path("dataset/network_features.csv")


FEATURE_COLUMNS = [
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


def load_events():
    events = []

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    return events


def extract_features(events):
    hosts = defaultdict(list)

    for event in events:
        hosts[event["source_ip"]].append(event)

    feature_rows = []

    for source_ip, host_events in hosts.items():

        destination_ips = {
            event["destination_ip"]
            for event in host_events
        }

        destination_ports = {
            event["destination_port"]
            for event in host_events
        }

        total_connections = len(host_events)

        total_bytes_sent = sum(
            event["bytes_sent"] for event in host_events
        )

        total_bytes_received = sum(
            event["bytes_received"] for event in host_events
        )

        failed_connections = sum(
            1 for event in host_events
            if event["connection_status"] == "failed"
        )

        tcp_connections = sum(
            1 for event in host_events
            if event["protocol"] == "TCP"
        )

        udp_connections = sum(
            1 for event in host_events
            if event["protocol"] == "UDP"
        )

        # Evaluation label only.
        # This field must NOT be passed to Random Cut Forest.
        ground_truth_label = (
            "suspicious"
            if any(event["label"] == "suspicious"
                   for event in host_events)
            else "normal"
        )

        feature_rows.append({
            "source_ip": source_ip,
            "total_connections": total_connections,
            "unique_destination_ips": len(destination_ips),
            "unique_destination_ports": len(destination_ports),
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
            "failed_connections": failed_connections,
            "tcp_connections": tcp_connections,
            "udp_connections": udp_connections,
            "ground_truth_label": ground_truth_label
        })

    return feature_rows


def save_features(feature_rows):
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
        writer.writerows(feature_rows)


def main():
    print("Starting Network Feature Extraction...")

    events = load_events()
    features = extract_features(events)

    save_features(features)

    normal_hosts = sum(
        1 for row in features
        if row["ground_truth_label"] == "normal"
    )

    suspicious_hosts = sum(
        1 for row in features
        if row["ground_truth_label"] == "suspicious"
    )

    print("\nFeature extraction completed.")
    print("Total network events:", len(events))
    print("Unique source IPs:", len(features))
    print("Normal source IPs:", normal_hosts)
    print("Suspicious source IPs:", suspicious_hosts)
    print("Output file:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
