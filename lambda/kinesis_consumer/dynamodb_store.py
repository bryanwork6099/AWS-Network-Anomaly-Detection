import logging
import time

from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

TABLE_NAME = "network-anomaly-aggregation-v3"

# Allow two minutes for late-arriving events.
ALLOWED_LATENESS_SECONDS = 120

# Keep deduplication records for 48 hours.
DEDUP_TTL_SECONDS = 48 * 60 * 60


def parse_event_timestamp(timestamp):
    """Parse an ISO timestamp and normalize it to UTC."""

    parsed = datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        raise ValueError("Event timestamp must include a timezone.")

    return parsed.astimezone(timezone.utc)


def validate_event(event):
    """Validate the fields needed for persistent aggregation."""

    required_fields = [
        "event_id",
        "timestamp",
        "source_ip",
        "destination_ip",
        "destination_port",
        "bytes_sent",
        "bytes_received",
        "connection_status",
        "protocol",
    ]

    missing = [
        field for field in required_fields
        if field not in event
    ]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    if not isinstance(event["event_id"], str) or not event["event_id"]:
        raise ValueError("Invalid event_id.")

    if not isinstance(event["source_ip"], str) or not event["source_ip"]:
        raise ValueError("Invalid source_ip.")

    if not isinstance(event["destination_ip"], str) or not event["destination_ip"]:
        raise ValueError("Invalid destination_ip.")

    port = event["destination_port"]
    bytes_sent = event["bytes_sent"]
    bytes_received = event["bytes_received"]

    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError("destination_port must be an integer.")

    if not 1 <= port <= 65535:
        raise ValueError("destination_port must be between 1 and 65535.")

    for field, value in (
        ("bytes_sent", bytes_sent),
        ("bytes_received", bytes_received),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field} must be an integer.")

        if value < 0:
            raise ValueError(f"{field} cannot be negative.")

    protocol = event["protocol"].upper()

    if protocol not in ("TCP", "UDP"):
        raise ValueError("Unsupported network protocol.")

    status = event["connection_status"]

    if status not in ("success", "failed"):
        raise ValueError("Invalid connection_status.")

    event_time = parse_event_timestamp(event["timestamp"])

    return event_time, protocol


def store_event(
    dynamodb_client,
    event,
    table_name=TABLE_NAME,
):
    """
    Atomically deduplicate an event and update its minute window.

    Returns:
        {"status": "processed"}
        {"status": "duplicate"}
    """

    event_time, protocol = validate_event(event)

    # Identify the UTC minute containing this event.
    minute_start = event_time.replace(
        second=0,
        microsecond=0,
    )

    window_end = minute_start + timedelta(minutes=1)

    finalize_at = (
        window_end.timestamp() + ALLOWED_LATENESS_SECONDS
    )

    now = int(time.time())

    dedup_expiry = now + DEDUP_TTL_SECONDS

    source_ip = event["source_ip"]
    event_id = event["event_id"]

    window_pk = f"WINDOW#{source_ip}"
    window_sk = f"MINUTE#{minute_start.isoformat()}"

    dedup_pk = f"EVENT#{event_id}"

    # Each event contributes one unique destination IP and port.
    destination_ips = {event["destination_ip"]}
    destination_ports = {event["destination_port"]}

    expression_values = {
        ":open": {"S": "OPEN"},
        ":open_pk": {"S": "WINDOW#OPEN"},
        ":finalize_at": {"S": f"{int(finalize_at):020d}"},
        ":window_start": {"S": minute_start.isoformat()},
        ":window_end": {"S": window_end.isoformat()},
        ":one": {"N": "1"},
        ":bytes_sent": {"N": str(event["bytes_sent"])},
        ":bytes_received": {"N": str(event["bytes_received"])},
        ":zero_or_one": {
            "N": str(
                1 if event["connection_status"] == "failed" else 0
            )
        },
        ":tcp": {"N": str(1 if protocol == "TCP" else 0)},
        ":udp": {"N": str(1 if protocol == "UDP" else 0)},
        ":destination_ips": {"SS": list(destination_ips)},
        ":destination_ports": {
            "NS": [str(port) for port in destination_ports]
        },
    }

    transaction = [
        {
            "Put": {
                "TableName": table_name,
                "Item": {
                    "PK": {"S": dedup_pk},
                    "SK": {"S": "DEDUP"},
                    "event_id": {"S": event_id},
                    "expires_at": {"N": str(dedup_expiry)},
                },
                "ConditionExpression": (
                    "attribute_not_exists(PK)"
                ),
            }
        },
        {
            "Update": {
                "TableName": table_name,
                "Key": {
                    "PK": {"S": window_pk},
                    "SK": {"S": window_sk},
                },
                "UpdateExpression": (
                    "SET #status = if_not_exists(#status, :open), "
                    "GSI1PK = if_not_exists(GSI1PK, :open_pk), "
                    "GSI1SK = if_not_exists(GSI1SK, :finalize_at), "
                    "window_start = if_not_exists(window_start, :window_start), "
                    "window_end = if_not_exists(window_end, :window_end) "
                    "ADD total_connections :one, "
                    "total_bytes_sent :bytes_sent, "
                    "total_bytes_received :bytes_received, "
                    "failed_connections :zero_or_one, "
                    "tcp_connections :tcp, "
                    "udp_connections :udp, "
                    "destination_ips :destination_ips, "
                    "destination_ports :destination_ports"
                ),
                "ConditionExpression": (
                    "attribute_not_exists(#status) OR #status = :open"
                ),
                "ExpressionAttributeNames": {
                    "#status": "status",
                },
                "ExpressionAttributeValues": expression_values,
            }
        },
    ]

    try:
        dynamodb_client.transact_write_items(
            TransactItems=transaction
        )

        logger.info(
            "Event stored: event_id=%s source_ip=%s window=%s",
            event_id,
            source_ip,
            minute_start.isoformat(),
        )

        return {"status": "processed"}

    except ClientError as error:
        logger.error(
            "DynamoDB error response: %s",
            error.response,
        )

        error_code = error.response.get(
            "Error", {}
        ).get("Code")

        if error_code == "TransactionCanceledException":
            # Determine whether this was a previously processed event.
            response = dynamodb_client.get_item(
                TableName=table_name,
                Key={
                    "PK": {"S": dedup_pk},
                    "SK": {"S": "DEDUP"},
                },
                ConsistentRead=True,
            )

            if "Item" in response:
                logger.info(
                    "Duplicate event ignored: %s",
                    event_id,
                )

                return {"status": "duplicate"}

            # No dedup record means another transaction condition failed,
            # such as the window already being finalized.
            logger.error(
                "Aggregation transaction rejected for event %s",
                event_id,
            )

        raise
