import json
import uuid
import random

from datetime import datetime, timezone

import boto3


REGION = "ap-southeast-1"
STREAM_NAME = "network-traffic-stream-v3"

SOURCE_IP = "192.168.1.210"
DESTINATION_IP = "10.0.5.10"

EVENT_COUNT = 30


def main():
    client = boto3.client("kinesis", region_name=REGION)

    # Keep all events inside the same UTC minute.
    now = datetime.now(timezone.utc)
    event_time = now.replace(microsecond=0).isoformat()

    ports = random.sample(range(1, 1025), EVENT_COUNT)

    records = []

    for port in ports:
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": event_time,
            "source_ip": SOURCE_IP,
            "destination_ip": DESTINATION_IP,
            "source_port": random.randint(1024, 65535),
            "destination_port": port,
            "protocol": "TCP",
            "bytes_sent": random.randint(40, 150),
            "bytes_received": 0,
            "connection_status": "failed",
            "scenario": "port_scanning",
            "label": "suspicious"
        }

        records.append({
            "Data": json.dumps(event).encode("utf-8"),
            "PartitionKey": SOURCE_IP
        })

    response = client.put_records(
        StreamName=STREAM_NAME,
        Records=records
    )

    failed_count = response["FailedRecordCount"]

    print("LIVE PORT SCAN TEST")
    print("Source IP:", SOURCE_IP)
    print("Destination IP:", DESTINATION_IP)
    print("Events submitted:", EVENT_COUNT)
    print("Successful:", EVENT_COUNT - failed_count)
    print("Failed:", failed_count)
    print("Timestamp:", event_time)

    if failed_count:
        print("WARNING: Some events failed. Do not blindly rerun.")


if __name__ == "__main__":
    main()
