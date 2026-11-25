import unittest
from unittest.mock import Mock

from botocore.exceptions import ClientError

from dynamodb_store import store_event


class TestDynamoDBStore(unittest.TestCase):

    def setUp(self):
        self.client = Mock()

        self.event = {
            "event_id": "test-event-001",
            "timestamp": "2026-11-24T09:15:30+00:00",
            "source_ip": "192.168.1.10",
            "destination_ip": "10.0.1.50",
            "destination_port": 443,
            "bytes_sent": 1500,
            "bytes_received": 3500,
            "connection_status": "success",
            "protocol": "TCP",
        }

    def test_valid_event(self):
        result = store_event(self.client, self.event)

        self.assertEqual(result["status"], "processed")
        self.client.transact_write_items.assert_called_once()

        transaction = (
            self.client.transact_write_items.call_args.kwargs[
                "TransactItems"
            ]
        )

        self.assertEqual(len(transaction), 2)

        dedup_item = transaction[0]["Put"]["Item"]

        self.assertEqual(
            dedup_item["PK"]["S"],
            "EVENT#test-event-001",
        )

        window_update = transaction[1]["Update"]

        self.assertEqual(
            window_update["Key"]["PK"]["S"],
            "WINDOW#192.168.1.10",
        )

        self.assertIn(
            "destination_ips",
            window_update["UpdateExpression"],
        )

    def test_duplicate_event(self):
        self.client.transact_write_items.side_effect = ClientError(
            {
                "Error": {
                    "Code": "TransactionCanceledException",
                    "Message": "Transaction cancelled",
                }
            },
            "TransactWriteItems",
        )

        self.client.get_item.return_value = {
            "Item": {
                "PK": {"S": "EVENT#test-event-001"},
                "SK": {"S": "DEDUP"},
            }
        }

        result = store_event(self.client, self.event)

        self.assertEqual(result["status"], "duplicate")
        self.client.get_item.assert_called_once()

    def test_invalid_event(self):
        invalid_event = self.event.copy()
        del invalid_event["source_ip"]

        with self.assertRaises(ValueError):
            store_event(self.client, invalid_event)

        self.client.transact_write_items.assert_not_called()

    def test_finalized_window_rejected(self):
        self.client.transact_write_items.side_effect = ClientError(
            {
                "Error": {
                    "Code": "TransactionCanceledException",
                    "Message": "Window is finalized",
                }
            },
            "TransactWriteItems",
        )

        self.client.get_item.return_value = {}

        with self.assertRaises(ClientError):
            store_event(self.client, self.event)


if __name__ == "__main__":
    unittest.main(verbosity=2)
