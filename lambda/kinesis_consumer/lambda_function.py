import logging
import os

import boto3

from window_finalizer import finalize_expired_windows


logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_client = boto3.client("dynamodb")


def lambda_handler(event, context):

    result = finalize_expired_windows(
        dynamodb_client=dynamodb_client,
        table_name=os.environ.get(
            "TABLE_NAME",
            "network-anomaly-aggregation-v3",
        ),
        index_name=os.environ.get(
            "INDEX_NAME",
            "GSI1-OpenWindowsByFinalizeAt",
        ),
    )

    logger.info("Lambda finalizer result: %s", result)

    return result
