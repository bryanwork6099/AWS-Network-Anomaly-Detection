import json
import random
import uuid

from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = Path("dataset/advanced_network_traffic_v3.jsonl")

SIMULATION_DAYS = 3
MINUTES_PER_DAY = 24 * 60
SIMULATION_MINUTES = SIMULATION_DAYS * MINUTES_PER_DAY

SIMULATION_START = (
    datetime.now(timezone.utc).replace(second=0, microsecond=0)
    - timedelta(days=SIMULATION_DAYS)
)

# Twelve normal network devices.
NORMAL_HOSTS = [
    f"192.168.1.{ip}" for ip in range(10, 22)
]

# Three devices used for controlled anomaly simulation.
SUSPICIOUS_HOSTS = [
    "192.168.1.200",
    "192.168.1.210",
    "192.168.1.220",
]

ALL_HOSTS = NORMAL_HOSTS + SUSPICIOUS_HOSTS


# ============================================================
# EVENT CREATION
# ============================================================

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
        "bytes_sent": (
            bytes_sent if bytes_sent is not None
            else random.randint(100, 5000)
        ),
        "bytes_received": (
            bytes_received if bytes_received is not None
            else random.randint(500, 15000)
        ),
        "connection_status": status,
        "scenario": scenario,
        "label": label
    }


# ============================================================
# NORMAL BASELINE TRAFFIC
# ============================================================

def generate_baseline_event(source_ip, event_time):
    """
    Generate ordinary network activity for one device.
    Every device, including anomaly-capable devices,
    receives normal baseline traffic.
    """

    scenario = random.choices(
        ["normal_browsing", "dns_activity", "ssh_activity"],
        weights=[65, 25, 10],
        k=1
    )[0]

    if scenario == "normal_browsing":
        return create_event(
            source_ip,
            f"10.0.1.{random.randint(1, 254)}",
            random.choice([80, 443]),
            scenario,
            event_time,
            bytes_sent=random.randint(300, 12000),
            bytes_received=random.randint(1000, 50000)
        )

    if scenario == "dns_activity":
        return create_event(
            source_ip,
            "10.0.0.53",
            53,
            scenario,
            event_time,
            protocol="UDP",
            bytes_sent=random.randint(30, 200),
            bytes_received=random.randint(50, 500)
        )

    return create_event(
        source_ip,
        "10.0.2.10",
        22,
        scenario,
        event_time,
        bytes_sent=random.randint(100, 2000),
        bytes_received=random.randint(100, 3000)
    )


def generate_baseline_traffic():
    """
    Generate 1-3 ordinary events per device per minute.
    This creates a continuous three-day baseline.
    """

    events = []

    for minute_offset in range(SIMULATION_MINUTES):

        minute_start = (
            SIMULATION_START + timedelta(minutes=minute_offset)
        )

        for source_ip in ALL_HOSTS:

            event_count = random.randint(1, 3)

            for _ in range(event_count):

                event_time = minute_start + timedelta(
                    seconds=random.randint(0, 59)
                )

                events.append(
                    generate_baseline_event(source_ip, event_time)
                )

    return events


# ============================================================
# ANOMALOUS TRAFFIC
# ============================================================

def generate_port_scan(source_ip, event_time):
    events = []

    ports = random.sample(range(1, 1025), 30)

    for index, port in enumerate(ports):

        events.append(
            create_event(
                source_ip,
                "10.0.5.10",
                port,
                "port_scanning",
                event_time + timedelta(seconds=index),
                label="suspicious",
                bytes_sent=random.randint(40, 150),
                bytes_received=0,
                status="failed"
            )
        )

    return events


def generate_ip_scan(source_ip, event_time):
    events = []

    for index in range(1, 31):

        events.append(
            create_event(
                source_ip,
                f"10.0.10.{index}",
                443,
                "ip_scanning",
                event_time + timedelta(seconds=index),
                label="suspicious",
                bytes_sent=random.randint(40, 150),
                bytes_received=0,
                status="failed"
            )
        )

    return events


def generate_unusual_outbound(source_ip, event_time):
    events = []

    for index in range(5):

        events.append(
            create_event(
                source_ip,
                "203.0.113.50",
                443,
                "unusual_outbound",
                event_time + timedelta(seconds=index * 10),
                label="suspicious",
                bytes_sent=random.randint(500000, 2000000),
                bytes_received=random.randint(100, 5000)
            )
        )

    return events


def generate_failed_connections(source_ip, event_time):
    events = []

    for index in range(20):

        events.append(
            create_event(
                source_ip,
                "10.0.2.20",
                random.choice([22, 3389, 445]),
                "failed_connections",
                event_time + timedelta(seconds=index * 2),
                label="suspicious",
                bytes_sent=random.randint(40, 200),
                bytes_received=0,
                status="failed"
            )
        )

    return events


# ============================================================
# ANOMALY SCHEDULING
# ============================================================

def generate_anomaly_schedule():
    """
    Schedule four anomaly types per day.
    Each attack is assigned to a suspicious host and a
    unique host/minute combination.
    """

    schedule = []

    generators = [
        ("port_scanning", generate_port_scan),
        ("ip_scanning", generate_ip_scan),
        ("unusual_outbound", generate_unusual_outbound),
        ("failed_connections", generate_failed_connections),
    ]

    used_host_minutes = set()

    for day in range(SIMULATION_DAYS):

        for scenario, generator in generators:

            source_ip = random.choice(SUSPICIOUS_HOSTS)

            minute_offset = (
                day * MINUTES_PER_DAY
                + random.randint(0, MINUTES_PER_DAY - 1)
            )

            while (source_ip, minute_offset) in used_host_minutes:

                source_ip = random.choice(SUSPICIOUS_HOSTS)

                minute_offset = (
                    day * MINUTES_PER_DAY
                    + random.randint(0, MINUTES_PER_DAY - 1)
                )

            used_host_minutes.add((source_ip, minute_offset))

            attack_time = (
                SIMULATION_START + timedelta(minutes=minute_offset)
            )

            schedule.append(
                (source_ip, attack_time, scenario, generator)
            )

    return schedule


def generate_anomalous_traffic(schedule):
    events = []

    for source_ip, event_time, scenario, generator in schedule:

        attack_events = generator(source_ip, event_time)

        events.extend(attack_events)

    return events


# ============================================================
# DATASET GENERATION
# ============================================================

def generate_dataset():

    print("Generating normal baseline traffic...")

    events = generate_baseline_traffic()

    print("Generating scheduled anomaly traffic...")

    schedule = generate_anomaly_schedule()

    anomaly_events = generate_anomalous_traffic(schedule)

    events.extend(anomaly_events)

    events.sort(key=lambda event: event["timestamp"])

    return events, schedule


# ============================================================
# MAIN
# ============================================================

def main():

    print("Starting V3 Network Traffic Generator...")
    print("Simulation duration:", SIMULATION_DAYS, "days")
    print("Normal devices:", len(NORMAL_HOSTS))
    print("Anomaly-capable devices:", len(SUSPICIOUS_HOSTS))
    print("Total devices:", len(ALL_HOSTS))

    events, schedule = generate_dataset()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:

        for event in events:
            file.write(json.dumps(event) + "\n")

    normal_count = sum(
        1 for event in events
        if event["label"] == "normal"
    )

    suspicious_count = sum(
        1 for event in events
        if event["label"] == "suspicious"
    )

    scenario_counts = Counter(
        event["scenario"] for event in events
    )

    timestamps = [
        datetime.fromisoformat(event["timestamp"])
        for event in events
    ]

    print("\nGeneration completed.")
    print("Total events:", len(events))
    print("Normal events:", normal_count)
    print("Suspicious events:", suspicious_count)
    print("Scheduled anomaly windows:", len(schedule))

    print("\nScenario counts:")

    for scenario, count in sorted(scenario_counts.items()):
        print(f"{scenario}: {count}")

    print("\nSimulation start:", min(timestamps).isoformat())
    print("Simulation end:", max(timestamps).isoformat())

    print("\nOutput file:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
