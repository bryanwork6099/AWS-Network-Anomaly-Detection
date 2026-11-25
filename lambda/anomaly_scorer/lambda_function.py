import json
import logging
import math
import os
import time

import boto3
from boto3.dynamodb.types import TypeDeserializer
from decimal import Decimal


logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
TABLE_NAME = os.environ["TABLE_NAME"]
ENDPOINT_NAME = os.environ["ENDPOINT_NAME"]
MODEL_VERSION = os.environ.get("MODEL_VERSION", "rcf-v3")
ANOMALY_THRESHOLD = float(os.environ["ANOMALY_THRESHOLD"])

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

runtime = boto3.client("sagemaker-runtime", region_name=REGION)
deserializer = TypeDeserializer()

# Training-derived scaling parameters.
SCALER = {
    "total_connections": (2.0002829654782115, 0.8194683935305673),
    "unique_destination_ips": (1.9090137366877604, 0.7949327218545988),
    "unique_destination_ports": (1.650331841333539, 0.6635072157597085),
    "log_bytes_sent": (8.381849036464663, 1.537934140380285),
    "log_bytes_received": (9.656914458563442, 1.7707316740105103),
    "destination_ip_ratio": (0.9655510967055958, 0.11662365770085238),
    "destination_port_ratio": (0.8680180411929138, 0.20141667736997096),
    "udp_ratio": (0.24802781636397936, 0.3385752714116792),
}

# Exact feature order used during RCF training.
FEATURE_ORDER = [
    "total_connections",
    "unique_destination_ips",
    "unique_destination_ports",
    "log_bytes_sent",
    "log_bytes_received",
    "failed_connection_rate",
    "destination_ip_ratio",
    "destination_port_ratio",
    "udp_ratio",
    "log_failed_connections",
]


def deserialize_image(image):
    return {
        key: deserializer.deserialize(value)
        for key, value in image.items()
    }


def standardize(feature_name, value):
    if feature_name not in SCALER:
        return value

    mean, scale = SCALER[feature_name]
    return (value - mean) / scale


def build_features(item):
    total = int(item.get("total_connections", 0))
    failed = int(item.get("failed_connections", 0))
    udp = int(item.get("udp_connections", 0))

    if total <= 0:
        raise ValueError("Cannot score a window with zero connections.")

    destination_ips = item.get("destination_ips", set())
    destination_ports = item.get("destination_ports", set())

    raw_features = {
        "total_connections": float(total),
        "unique_destination_ips": float(len(destination_ips)),
        "unique_destination_ports": float(len(destination_ports)),
        "log_bytes_sent": math.log1p(
            float(item.get("total_bytes_sent", 0))
        ),
        "log_bytes_received": math.log1p(
            float(item.get("total_bytes_received", 0))
        ),
        "failed_connection_rate": failed / total,
        "destination_ip_ratio": len(destination_ips) / total,
        "destination_port_ratio": len(destination_ports) / total,
        "udp_ratio": udp / total,
        "log_failed_connections": math.log1p(failed),
    }

    features = {
        name: standardize(name, raw_features[name])
        for name in FEATURE_ORDER
    }

    return [features[name] for name in FEATURE_ORDER]


def score_window(item):
    features = build_features(item)

    csv_payload = ",".join(
        format(value, ".15g") for value in features
    )

    response = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="text/csv",
        Accept="application/json",
        Body=csv_payload.encode("utf-8"),
    )

    result = json.loads(response["Body"].read().decode("utf-8"))
    score = float(result["scores"][0]["score"])

    anomaly_status = (
        "ANOMALY"
        if score > ANOMALY_THRESHOLD
        else "NORMAL"
    )

    return score, anomaly_status


def lambda_handler(event, context):
    result = {
        "scored": 0,
        "skipped": 0,
    }

    for record in event.get("Records", []):
        if record.get("eventName") != "MODIFY":
            result["skipped"] += 1
            continue

        dynamodb_record = record.get("dynamodb", {})
        new_image = dynamodb_record.get("NewImage")
        old_image = dynamodb_record.get("OldImage")

        if not new_image or not old_image:
            result["skipped"] += 1
            continue

        new_item = deserialize_image(new_image)
        old_item = deserialize_image(old_image)

        if (
            new_item.get("status") != "FINALIZED"
            or old_item.get("status") != "OPEN"
        ):
            result["skipped"] += 1
            continue

        pk = new_item["PK"]
        sk = new_item["SK"]

        # Avoid scoring a record that has already been processed.
        existing = table.get_item(
            Key={"PK": pk, "SK": sk},
            ConsistentRead=True,
        ).get("Item")

        if existing and existing.get("scored_at") is not None:
            result["skipped"] += 1
            continue

        score, anomaly_status = score_window(new_item)

        table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression=(
                "SET anomaly_score = :score, "
                "anomaly_status = :anomaly_status, "
                "model_version = :model_version, "
                "scored_at = :scored_at"
            ),
            ConditionExpression=(
                "#status = :finalized "
                "AND attribute_not_exists(scored_at)"
            ),
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":score": Decimal(str(score)),
                ":anomaly_status": anomaly_status,
                ":model_version": MODEL_VERSION,
                ":scored_at": int(time.time()),
                ":finalized": "FINALIZED",
            },
        )

        result["scored"] += 1

        logger.info(
            "Window scored: PK=%s SK=%s score=%s status=%s",
            pk,
            sk,
            score,
            anomaly_status,
        )

    logger.info("Scoring batch completed: %s", result)
    return result
