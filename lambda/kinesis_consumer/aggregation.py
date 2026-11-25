import math

from collections import defaultdict
from datetime import datetime


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


def get_minute_window(timestamp):
    """
    Convert an event timestamp into its UTC minute window.
    """

    event_time = datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

    if event_time.tzinfo is None:
        raise ValueError("Event timestamp must include a timezone.")

    window_time = event_time.replace(
        second=0,
        microsecond=0
    )

    return window_time.isoformat()


def create_window():
    """
    Create an empty aggregation window.
    """

    return {
        "total_connections": 0,
        "destination_ips": set(),
        "destination_ports": set(),
        "total_bytes_sent": 0,
        "total_bytes_received": 0,
        "failed_connections": 0,
        "tcp_connections": 0,
        "udp_connections": 0
    }


def add_event(window, event):
    """
    Add one network event to an aggregation window.
    """

    required_fields = [
        "timestamp",
        "source_ip",
        "destination_ip",
        "destination_port",
        "bytes_sent",
        "bytes_received",
        "connection_status",
        "protocol"
    ]

    missing_fields = [
        field for field in required_fields
        if field not in event
    ]

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {missing_fields}"
        )

    if event["connection_status"] not in ("success", "failed"):
        raise ValueError("Invalid connection status.")

    protocol = event["protocol"].upper()

    if protocol not in ("TCP", "UDP"):
        raise ValueError("Unsupported network protocol.")

    destination_port = int(event["destination_port"])
    bytes_sent = int(event["bytes_sent"])
    bytes_received = int(event["bytes_received"])

    if not 0 <= destination_port <= 65535:
        raise ValueError("Invalid destination port.")

    if bytes_sent < 0 or bytes_received < 0:
        raise ValueError("Byte counts cannot be negative.")

    window["total_connections"] += 1

    window["destination_ips"].add(
        event["destination_ip"]
    )

    window["destination_ports"].add(
        destination_port
    )

    window["total_bytes_sent"] += bytes_sent
    window["total_bytes_received"] += bytes_received

    if event["connection_status"] == "failed":
        window["failed_connections"] += 1

    if protocol == "TCP":
        window["tcp_connections"] += 1
    else:
        window["udp_connections"] += 1


def transform_window(window):
    """
    Convert an aggregated window into the exact
    10 numerical features expected by the V3 RCF model.
    """

    total = window["total_connections"]

    if total <= 0:
        raise ValueError("Connection count must be positive.")

    failed = window["failed_connections"]
    unique_ips = len(window["destination_ips"])
    unique_ports = len(window["destination_ports"])
    udp = window["udp_connections"]

    features = {
        "total_connections": total,

        "unique_destination_ips": unique_ips,

        "unique_destination_ports": unique_ports,

        "log_bytes_sent": math.log1p(
            window["total_bytes_sent"]
        ),

        "log_bytes_received": math.log1p(
            window["total_bytes_received"]
        ),

        "failed_connections": failed,

        "failed_connection_rate": failed / total,

        "destination_ip_ratio": unique_ips / total,

        "destination_port_ratio": unique_ports / total,

        "udp_ratio": udp / total
    }

    return features


def aggregate_events(events):
    """
    Aggregate a collection of events by source IP and minute.

    This is a local testing helper. It does not provide
    persistent storage or streaming window finalization.
    """

    windows = defaultdict(create_window)

    for event in events:

        window_time = get_minute_window(
            event["timestamp"]
        )

        key = (
            event["source_ip"],
            window_time
        )

        add_event(windows[key], event)

    results = []

    for (source_ip, timestamp), window in windows.items():

        results.append({
            "timestamp": timestamp,
            "source_ip": source_ip,
            "features": transform_window(window)
        })

    results.sort(
        key=lambda row: (
            row["timestamp"],
            row["source_ip"]
        )
    )

    return results
