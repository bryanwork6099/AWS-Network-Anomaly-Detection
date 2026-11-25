import json
import random
import uuid

from datetime import datetime, timezone, timedelta
from pathlib import Path


OUTPUT_FILE = Path("dataset/advanced_network_traffic_v2.jsonl")

NORMAL_HOSTS = [
    "192.168.1.10",
    "192.168.1.20",
    "192.168.1.30",
    "192.168.1.40",
]

SUSPICIOUS_HOSTS = [
    "192.168.1.200",
    "192.168.1.210",
    "192.168.1.220",
]

# Simulate one hour of network activity.
SIMULATION_START = (
    datetime.now(timezone.utc).replace(second=0, microsecond=0)
    - timedelta(hours=1)
)


def random_session_time():
    """Choose a random minute within the simulated hour."""
    minute = random.randint(0, 59)
    return SIMULATION_START + timedelta(minutes=minute)


def create_event(
    source_ip,
    destination_ip,
    destination_port,
    scenario,
    event_time,
    label="normal",
    protocol="TCP",
    bytes_sent=None,
    bytes_received=None,
    status="success"
):
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": event_time.isoformat(),
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "source_port": random.randint(1024, 65535),
        "destination_port": destination_port,
        "protocol": protocol,
        "bytes_sent": bytes_sent if bytes_sent is not None
        else random.randint(100, 5000),
        "bytes_received": bytes_received if bytes_received is not None
        else random.randint(500, 15000),
        "connection_status": status,
        "scenario": scenario,
        "label": label
    }


def generate_normal_browsing():
    events = []
    source = random.choice(NORMAL_HOSTS)
    session_time = random_session_time()

    for i in range(random.randint(5, 10)):
        events.append(
            create_event(
                source,
                f"10.0.1.{random.randint(1, 254)}",
                random.choice([80, 443]),
                "normal_browsing",
                session_time + timedelta(seconds=i * 2)
            )
        )

    return events


def generate_dns_activity():
    events = []
    source = random.choice(NORMAL_HOSTS)
    session_time = random_session_time()

    for i in range(random.randint(3, 6)):
        events.append(
            create_event(
                source,
                "10.0.0.53",
                53,
                "dns_activity",
                session_time + timedelta(seconds=i * 2),
                protocol="UDP",
                bytes_sent=random.randint(30, 200),
                bytes_received=random.randint(50, 500)
            )
        )

    return events


def generate_ssh_activity():
    source = random.choice(NORMAL_HOSTS)
    session_time = random_session_time()

    return [
        create_event(
            source,
            "10.0.2.10",
            22,
            "ssh_activity",
            session_time + timedelta(seconds=i * 5),
            bytes_sent=random.randint(100, 2000),
            bytes_received=random.randint(100, 3000)
        )
        for i in range(random.randint(1, 3))
    ]


def generate_port_scan():
    events = []
    source = random.choice(SUSPICIOUS_HOSTS)
    destination = "10.0.5.10"
    session_time = random_session_time()

    ports = random.sample(range(1, 1025), 30)

    for i, port in enumerate(ports):
        events.append(
            create_event(
                source,
                destination,
                port,
                "port_scanning",
                session_time + timedelta(seconds=i),
                label="suspicious",
                bytes_sent=random.randint(40, 150),
                bytes_received=0,
                status="failed"
            )
        )

    return events


def generate_ip_scan():
    events = []
    source = random.choice(SUSPICIOUS_HOSTS)
    session_time = random_session_time()

    for i in range(1, 31):
        events.append(
            create_event(
                source,
                f"10.0.10.{i}",
                443,
                "ip_scanning",
                session_time + timedelta(seconds=i),
                label="suspicious",
                bytes_sent=random.randint(40, 150),
                bytes_received=0,
                status="failed"
            )
        )

    return events


def generate_unusual_outbound():
    events = []
    source = random.choice(SUSPICIOUS_HOSTS)
    session_time = random_session_time()

    for i in range(5):
        events.append(
            create_event(
                source,
                "203.0.113.50",
                443,
                "unusual_outbound",
                session_time + timedelta(seconds=i * 10),
                label="suspicious",
                bytes_sent=random.randint(500000, 2000000),
                bytes_received=random.randint(100, 5000)
            )
        )

    return events


def generate_failed_connections():
    events = []
    source = random.choice(SUSPICIOUS_HOSTS)
    session_time = random_session_time()

    for i in range(10):
        events.append(
            create_event(
                source,
                "10.0.2.20",
                random.choice([22, 3389, 445]),
                "failed_connections",
                session_time + timedelta(seconds=i * 3),
                label="suspicious",
                bytes_sent=random.randint(40, 200),
                bytes_received=0,
                status="failed"
            )
        )

    return events


def generate_dataset():
    events = []

    # Generate normal traffic sessions.
    for _ in range(5):
        events.extend(generate_normal_browsing())
        events.extend(generate_dns_activity())
        events.extend(generate_ssh_activity())

    # Generate suspicious traffic sessions.
    events.extend(generate_port_scan())
    events.extend(generate_ip_scan())
    events.extend(generate_unusual_outbound())
    events.extend(generate_failed_connections())

    # Sort chronologically for easier inspection.
    events.sort(key=lambda event: event["timestamp"])

    return events


def main():
    print("Starting Time-Based Network Traffic Generator...")

    events = generate_dataset()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event) + "\n")

    normal = sum(
        1 for event in events if event["label"] == "normal"
    )

    suspicious = sum(
        1 for event in events if event["label"] == "suspicious"
    )

    timestamps = [
        datetime.fromisoformat(event["timestamp"])
        for event in events
    ]

    print("\nGeneration completed.")
    print("Total events:", len(events))
    print("Normal events:", normal)
    print("Suspicious events:", suspicious)
    print("Simulation start:", min(timestamps).isoformat())
    print("Simulation end:", max(timestamps).isoformat())
    print("Output file:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
