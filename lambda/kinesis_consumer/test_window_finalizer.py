import unittest
from unittest.mock import Mock

from botocore.exceptions import ClientError

from window_finalizer import finalize_expired_windows


def make_window(source_ip, minute):
    return {
        "PK": {"S": f"WINDOW#{source_ip}"},
        "SK": {"S": f"MINUTE#{minute}"},
    }


class TestWindowFinalizer(unittest.TestCase):

    def setUp(self):
        self.client = Mock()
        self.now = 1795511820

    def test_expired_window_finalized(self):
        self.client.query.return_value = {
            "Items": [
                make_window("192.168.1.10", "2026-11-24T10:15:00+00:00")
            ]
        }

        result = finalize_expired_windows(
            self.client,
            current_time=self.now,
        )

        self.assertEqual(result["found"], 1)
        self.assertEqual(result["finalized"], 1)
        self.assertEqual(result["skipped"], 0)

        self.client.update_item.assert_called_once()

        update = self.client.update_item.call_args.kwargs

        self.assertEqual(
            update["Key"]["PK"]["S"],
            "WINDOW#192.168.1.10",
        )

        self.assertIn(
            "REMOVE GSI1PK, GSI1SK",
            update["UpdateExpression"],
        )

    def test_conditional_failure_skipped(self):
        self.client.query.return_value = {
            "Items": [
                make_window("192.168.1.20", "2026-11-24T10:15:00+00:00")
            ]
        }

        self.client.update_item.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ConditionalCheckFailedException",
                    "Message": "Condition failed",
                }
            },
            "UpdateItem",
        )

        result = finalize_expired_windows(
            self.client,
            current_time=self.now,
        )

        self.assertEqual(result["found"], 1)
        self.assertEqual(result["finalized"], 0)
        self.assertEqual(result["skipped"], 1)

    def test_multiple_query_pages(self):
        first_page = {
            "Items": [
                make_window("192.168.1.10", "2026-11-24T10:15:00+00:00")
            ],
            "LastEvaluatedKey": {
                "PK": {"S": "WINDOW#192.168.1.10"},
                "SK": {"S": "MINUTE#2026-11-24T10:15:00+00:00"},
            },
        }

        second_page = {
            "Items": [
                make_window("192.168.1.20", "2026-11-24T10:16:00+00:00")
            ]
        }

        self.client.query.side_effect = [
            first_page,
            second_page,
        ]

        result = finalize_expired_windows(
            self.client,
            current_time=self.now,
        )

        self.assertEqual(result["found"], 2)
        self.assertEqual(result["finalized"], 2)
        self.assertEqual(self.client.query.call_count, 2)
        self.assertEqual(self.client.update_item.call_count, 2)

    def test_unexpected_error_raised(self):
        self.client.query.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Access denied",
                }
            },
            "Query",
        )

        with self.assertRaises(ClientError):
            finalize_expired_windows(
                self.client,
                current_time=self.now,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
