import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


INPUT_FILE = Path("dataset/advanced_network_traffic_v3.jsonl")

REQUIRED_FIELDS = [
    "event_id",
    "timestamp",
    "source_ip",
    "destination_ip",
    "destination_port",
    "protocol",
    "bytes_sent",
    "bytes_received",
    "connection_status",
    "scenario",
    "label"
]


def main():
    print("Starting V3 Dataset Validation...\n")

    event_ids = set()
    scenarios = Counter()
    labels = Counter()
    source_counts = Counter()
    window_labels = defaultdict(set)
    timestamps = []

    total_events = 0
    malformed_events = 0
    missing_fields = 0
    duplicate_ids = 0

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed_events += 1
                continue

            total_events += 1

            missing = [
                field for field in REQUIRED_FIELDS
                if field not in event
            ]

            if missing:
                missing_fields += 1
                continue

            event_id = event["event_id"]

            if event_id in event_ids:
                duplicate_ids += 1

            event_ids.add(event_id)

            timestamp = datetime.fromisoformat(event["timestamp"])
            timestamps.append(timestamp)

            source = event["source_ip"]
            minute = timestamp.replace(
                second=0, microsecond=0
            ).isoformat()

            window_key = (source, minute)

            window_labels[window_key].add(event["label"])

            scenarios[event["scenario"]] += 1
            labels[event["label"]] += 1
            source_counts[source] += 1

    suspicious_windows = sum(
        1 for values in window_labels.values()
        if "suspicious" in values
    )

    normal_windows = sum(
        1 for values in window_labels.values()
        if values == {"normal"}
    )

    mixed_windows = sum(
        1 for values in window_labels.values()
        if len(values) > 1
    )

    print("DATA QUALITY")
    print("Total events:", total_events)
    print("Malformed events:", malformed_events)
    print("Events with missing fields:", missing_fields)
    print("Duplicate event IDs:", duplicate_ids)

    print("\nEVENT LABELS")
    for label, count in labels.items():
        print(f"{label}: {count}")

    print("\nTIME-WINDOW STATISTICS")
    print("Unique source-IP/minute observations:", len(window_labels))
    print("Normal observations:", normal_windows)
    print("Suspicious observations:", suspicious_windows)
    print("Mixed-label observations:", mixed_windows)

    print("\nDEVICE EVENT COUNTS")
    for source, count in sorted(source_counts.items()):
        print(f"{source}: {count}")

    print("\nSCENARIO COUNTS")
    for scenario, count in scenarios.items():
        print(f"{scenario}: {count}")

    if timestamps:
        print("\nTIMESTAMP RANGE")
        print("Start:", min(timestamps).isoformat())
        print("End:", max(timestamps).isoformat())

    print("\nValidation completed.")


if __name__ == "__main__":
    main()
