import json
import boto3

from pathlib import Path
from botocore.exceptions import ClientError


# Configuration
REGION = "ap-southeast-1"
STREAM_NAME = "network-traffic-stream-v3"

INPUT_FILE = Path("dataset/advanced_network_traffic_v3.jsonl")

TEST_EVENT_COUNT = 10


def publish_events():
    print("KINESIS NETWORK TRAFFIC PRODUCER")
    print("=" * 50)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}"
        )

    # Read only the first 10 events for initial testing
    events = []

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if len(events) >= TEST_EVENT_COUNT:
                break

            if line.strip():
                events.append(json.loads(line))

    if not events:
        raise ValueError("No events found in dataset.")

    # Initialize Kinesis client
    client = boto3.client(
        "kinesis",
        region_name=REGION
    )

    records = []

    for event in events:
        if not event.get("source_ip"):
            raise ValueError("Event missing source_ip.")

        records.append({
            "Data": json.dumps(event).encode("utf-8"),
            "PartitionKey": event["source_ip"]
        })

    print(f"Stream: {STREAM_NAME}")
    print(f"Events prepared: {len(records)}")

    # Publish events
    try:
        response = client.put_records(
            StreamName=STREAM_NAME,
            Records=records
        )

        failed_count = response["FailedRecordCount"]

        print("\nPUBLISH RESULTS")
        print("-" * 50)
        print(f"Total records: {len(records)}")
        print(f"Successful: {len(records) - failed_count}")
        print(f"Failed: {failed_count}")

        if failed_count:
            print("\nFailed record details:")

            for index, result in enumerate(response["Records"]):
                if "ErrorCode" in result:
                    print(
                        f"Record {index + 1}: "
                        f"{result['ErrorCode']} - "
                        f"{result.get('ErrorMessage', '')}"
                    )

            raise RuntimeError(
                "Some records were not published. "
                "Do not rerun blindly; check the failed records first."
            )

        print("\nAll test events published successfully.")

    except ClientError as error:
        print("\nAWS ERROR")
        print(error)
        raise


if __name__ == "__main__":
    publish_events()
