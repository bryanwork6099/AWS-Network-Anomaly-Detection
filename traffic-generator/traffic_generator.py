import json
import random
import time
import uuid

from datetime import datetime, timezone


NORMAL_SCENARIOS = [
    "normal_browsing",
    "dns_activity",
    "ssh_activity",
]

SUSPICIOUS_SCENARIOS = [
    "port_scanning",
    "unusual_outbound",
    "failed_connections",
]


def generate_event(scenario):
    source_ip = "192.168.1.{}".format(random.randint(10, 250))
    destination_ip = "10.0.{}.{}".format(
        random.randint(1, 20),
        random.randint(1, 254)
    )

    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "source_port": random.randint(1024, 65535),
        "destination_port": 443,
        "protocol": "TCP",
        "bytes_sent": random.randint(100, 5000),
        "bytes_received": random.randint(500, 15000),
        "connection_status": "success",
        "scenario": scenario,
        "label": "normal"
    }

    if scenario == "normal_browsing":
        event["destination_port"] = random.choice([80, 443])
        event["bytes_sent"] = random.randint(100, 3000)
        event["bytes_received"] = random.randint(1000, 20000)

    elif scenario == "dns_activity":
        event["destination_port"] = 53
        event["protocol"] = "UDP"
        event["bytes_sent"] = random.randint(30, 200)
        event["bytes_received"] = random.randint(50, 500)

    elif scenario == "ssh_activity":
        event["destination_port"] = 22
        event["bytes_sent"] = random.randint(100, 2000)
        event["bytes_received"] = random.randint(100, 3000)

    elif scenario == "port_scanning":
        event["destination_port"] = random.randint(1, 1024)
        event["bytes_sent"] = random.randint(40, 150)
        event["bytes_received"] = random.randint(0, 50)
        event["connection_status"] = "failed"
        event["label"] = "suspicious"

    elif scenario == "unusual_outbound":
        event["destination_port"] = random.choice([80, 443, 8080])
        event["bytes_sent"] = random.randint(500000, 2000000)
        event["bytes_received"] = random.randint(100, 5000)
        event["label"] = "suspicious"

    elif scenario == "failed_connections":
        event["destination_port"] = random.choice([22, 3389, 445])
        event["connection_status"] = "failed"
        event["bytes_sent"] = random.randint(40, 200)
        event["bytes_received"] = 0
        event["label"] = "suspicious"

    return event


def generate_traffic(total_events=100):
    events = []

    for _ in range(total_events):
        # Generate normal traffic more frequently.
        if random.random() < 0.8:
            scenario = random.choice(NORMAL_SCENARIOS)
        else:
            scenario = random.choice(SUSPICIOUS_SCENARIOS)

        event = generate_event(scenario)
        events.append(event)

    return events


def main():
    print("Starting Network Traffic Generator...")

    total_events = 100

    events = generate_traffic(total_events)

    output_file = "dataset/network_traffic.jsonl"

    with open(output_file, "w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event) + "\n")

    normal_count = sum(
        1 for event in events if event["label"] == "normal"
    )

    suspicious_count = sum(
        1 for event in events if event["label"] == "suspicious"
    )

    print("\nTraffic generation completed.")
    print("Total events:", len(events))
    print("Normal events:", normal_count)
    print("Suspicious events:", suspicious_count)
    print("Output file:", output_file)


if __name__ == "__main__":
    main()
