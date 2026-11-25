import base64
import json
import logging
import os

import boto3

from dynamodb_store import store_event


logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = "network-anomaly-aggregation-v3"
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")

dynamodb_client = boto3.client(
    "dynamodb",
    region_name=AWS_REGION,
)

REQUIRED_FIELDS = [
    "event_id",
    "timestamp",
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "protocol",
    "bytes_sent",
    "bytes_received",
    "connection_status",
    "scenario",
]


def lambda_handler(event, context):
    records = event.get("Records", [])

    if not records:
        logger.info("No Kinesis records received.")

        return {
            "processed": 0,
            "duplicates": 0,
        }

    processed = 0
    duplicates = 0

    for record in records:

        # Decode the Base64-encoded Kinesis payload.
        encoded_data = record["kinesis"]["data"]
        decoded_data = base64.b64decode(encoded_data)

        # Parse the original network event.
        network_event = json.loads(decoded_data)

        # Validate required fields.
        missing_fields = [
            field for field in REQUIRED_FIELDS
            if field not in network_event
        ]

        if missing_fields:
            raise ValueError(
                f"Event is missing required fields: {missing_fields}"
            )

        # Basic validation.
        if network_event["protocol"].upper() not in ("TCP", "UDP"):
            raise ValueError("Unsupported network protocol.")

        if network_event["connection_status"] not in (
            "success",
            "failed",
        ):
            raise ValueError("Invalid connection status.")

        # Persist the event and update its minute aggregation.
        result = store_event(
            dynamodb_client=dynamodb_client,
            event=network_event,
            table_name=TABLE_NAME,
        )

        if result["status"] == "processed":
            processed += 1

        elif result["status"] == "duplicate":
            duplicates += 1

        else:
            raise ValueError(
                f"Unexpected storage result: {result}"
            )

        # Ground-truth label is deliberately excluded.
        logger.info(
            "Network event handled: %s",
            json.dumps({
                "event_id": network_event["event_id"],
                "source_ip": network_event["source_ip"],
                "destination_ip": network_event["destination_ip"],
                "protocol": network_event["protocol"],
                "scenario": network_event["scenario"],
                "connection_status": network_event[
                    "connection_status"
                ],
                "storage_status": result["status"],
            })
        )

    logger.info(
        "Kinesis batch completed: processed=%s duplicates=%s",
        processed,
        duplicates,
    )

    return {
        "processed": processed,
        "duplicates": duplicates,
    }
