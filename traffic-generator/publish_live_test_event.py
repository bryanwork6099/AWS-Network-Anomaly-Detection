import json
import uuid

from datetime import datetime, timezone

import boto3


REGION = "ap-southeast-1"
STREAM_NAME = "network-traffic-stream-v3"


def main():
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": "192.168.1.250",
        "destination_ip": "203.0.113.10",
        "source_port": 51500,
        "destination_port": 443,
        "protocol": "TCP",
        "bytes_sent": 1200,
        "bytes_received": 4500,
        "connection_status": "success",
        "scenario": "normal_browsing",
        "label": "normal"
    }

    client = boto3.client("kinesis", region_name=REGION)

    response = client.put_record(
        StreamName=STREAM_NAME,
        Data=json.dumps(event).encode("utf-8"),
        PartitionKey=event["source_ip"]
    )

    print("LIVE TEST EVENT PUBLISHED")
    print("Event ID:", event["event_id"])
    print("Timestamp:", event["timestamp"])
    print("Source IP:", event["source_ip"])
    print("Stream:", STREAM_NAME)
    print("Shard ID:", response["ShardId"])
    print("Sequence Number:", response["SequenceNumber"])


if __name__ == "__main__":
    main()
