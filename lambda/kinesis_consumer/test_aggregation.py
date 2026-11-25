import math

from aggregation import aggregate_events, FEATURE_COLUMNS


events = [
    {
        "timestamp": "2026-11-24T10:15:03+00:00",
        "source_ip": "192.168.1.10",
        "destination_ip": "10.0.1.51",
        "destination_port": 443,
        "bytes_sent": 1000,
        "bytes_received": 5000,
        "connection_status": "success",
        "protocol": "TCP"
    },
    {
        "timestamp": "2026-11-24T10:15:27+00:00",
        "source_ip": "192.168.1.10",
        "destination_ip": "10.0.1.52",
        "destination_port": 443,
        "bytes_sent": 2000,
        "bytes_received": 6000,
        "connection_status": "failed",
        "protocol": "UDP"
    },
    {
        "timestamp": "2026-11-24T10:15:49+00:00",
        "source_ip": "192.168.1.10",
        "destination_ip": "10.0.1.51",
        "destination_port": 22,
        "bytes_sent": 3000,
        "bytes_received": 7000,
        "connection_status": "success",
        "protocol": "TCP"
    },
    {
        "timestamp": "2026-11-24T10:16:05+00:00",
        "source_ip": "192.168.1.10",
        "destination_ip": "10.0.1.53",
        "destination_port": 53,
        "bytes_sent": 400,
        "bytes_received": 800,
        "connection_status": "success",
        "protocol": "UDP"
    },
    {
        "timestamp": "2026-11-24T10:15:35+00:00",
        "source_ip": "192.168.1.20",
        "destination_ip": "10.0.1.60",
        "destination_port": 80,
        "bytes_sent": 500,
        "bytes_received": 1500,
        "connection_status": "success",
        "protocol": "TCP"
    }
]


def main():

    results = aggregate_events(events)

    assert len(results) == 3

    first = next(
        row for row in results
        if row["source_ip"] == "192.168.1.10"
        and row["timestamp"] == "2026-11-24T10:15:00+00:00"
    )

    features = first["features"]

    assert list(features.keys()) == FEATURE_COLUMNS

    assert features["total_connections"] == 3
    assert features["unique_destination_ips"] == 2
    assert features["unique_destination_ports"] == 2

    assert features["log_bytes_sent"] == math.log1p(6000)
    assert features["log_bytes_received"] == math.log1p(18000)

    assert features["failed_connections"] == 1
    assert features["failed_connection_rate"] == 1 / 3

    assert features["destination_ip_ratio"] == 2 / 3
    assert features["destination_port_ratio"] == 2 / 3

    assert features["udp_ratio"] == 1 / 3

    second_minute = next(
        row for row in results
        if row["source_ip"] == "192.168.1.10"
        and row["timestamp"] == "2026-11-24T10:16:00+00:00"
    )

    assert second_minute["features"]["total_connections"] == 1

    other_source = next(
        row for row in results
        if row["source_ip"] == "192.168.1.20"
    )

    assert other_source["features"]["total_connections"] == 1

    print("AGGREGATION TEST PASSED")
    print("Total observations:", len(results))
    print("First window features:")

    for name, value in features.items():
        print(f"{name}: {value}")

    print("\nAll aggregation assertions passed.")


if __name__ == "__main__":
    main()
