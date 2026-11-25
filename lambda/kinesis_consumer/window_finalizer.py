import logging
import time

from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

TABLE_NAME = "network-anomaly-aggregation-v3"
INDEX_NAME = "GSI1-OpenWindowsByFinalizeAt"
OPEN_WINDOW_KEY = "WINDOW#OPEN"


def finalize_expired_windows(
    dynamodb_client,
    table_name=TABLE_NAME,
    index_name=INDEX_NAME,
    current_time=None,
):
    """
    Find expired windows first, then finalize them.

    Collecting keys before updating avoids modifying the GSI
    while its query pagination is still in progress.
    """

    if current_time is None:
        current_time = int(time.time())

    result = {
        "found": 0,
        "finalized": 0,
        "skipped": 0,
    }

    query_parameters = {
        "TableName": table_name,
        "IndexName": index_name,
        "KeyConditionExpression": (
            "GSI1PK = :open_pk AND GSI1SK <= :now"
        ),
        "ExpressionAttributeValues": {
            ":open_pk": {"S": OPEN_WINDOW_KEY},
            ":now": {"S": f"{current_time:020d}"},
        },
    }

    # Phase 1: Collect eligible window keys.
    expired_windows = []

    while True:
        response = dynamodb_client.query(**query_parameters)

        expired_windows.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")

        if not last_key:
            break

        query_parameters["ExclusiveStartKey"] = last_key

    result["found"] = len(expired_windows)

    # Phase 2: Finalize the collected windows.
    for item in expired_windows:

        pk = item["PK"]["S"]
        sk = item["SK"]["S"]

        try:
            dynamodb_client.update_item(
                TableName=table_name,
                Key={
                    "PK": {"S": pk},
                    "SK": {"S": sk},
                },
                UpdateExpression=(
                    "SET #status = :finalized, "
                    "finalized_at = :finalized_at "
                    "REMOVE GSI1PK, GSI1SK"
                ),
                ConditionExpression=(
                    "#status = :open "
                    "AND GSI1PK = :open_pk "
                    "AND GSI1SK <= :now"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                },
                ExpressionAttributeValues={
                    ":open": {"S": "OPEN"},
                    ":finalized": {"S": "FINALIZED"},
                    ":open_pk": {"S": OPEN_WINDOW_KEY},
                    ":now": {"S": f"{current_time:020d}"},
                    ":finalized_at": {"N": str(current_time)},
                },
            )

            result["finalized"] += 1

            logger.info(
                "Window finalized: PK=%s SK=%s",
                pk,
                sk,
            )

        except ClientError as error:

            error_code = error.response.get(
                "Error", {}
            ).get("Code")

            if error_code == "ConditionalCheckFailedException":
                result["skipped"] += 1

                logger.info(
                    "Window skipped because its condition changed: "
                    "PK=%s SK=%s",
                    pk,
                    sk,
                )

                continue

            raise

    logger.info(
        "Finalization completed: found=%s finalized=%s skipped=%s",
        result["found"],
        result["finalized"],
        result["skipped"],
    )

    return result
