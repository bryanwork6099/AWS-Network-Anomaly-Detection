import base64
import json
import unittest
from unittest.mock import patch

from app import lambda_handler


def create_kinesis_record(event):
    encoded_data = base64.b64encode(
        json.dumps(event).encode("utf-8")
    ).decode("utf-8")

    return {
        "kinesis": {
            "data": encoded_data
        }
    }


class TestLambdaHandler(unittest.TestCase):

    def setUp(self):
        self.network_event = {
            "event_id": "test-event-001",
            "timestamp": "2026-11-24T08:00:00+00:00",
            "source_ip": "192.168.1.10",
            "destination_ip": "10.0.1.51",
            "source_port": 21486,
            "destination_port": 443,
            "protocol": "TCP",
            "bytes_sent": 3156,
            "bytes_received": 39448,
            "connection_status": "success",
            "scenario": "normal_browsing",
            "label": "normal",
        }

    @patch("app.store_event")
    def test_new_event_processed(self, mock_store):
        mock_store.return_value = {
            "status": "processed"
        }

        event = {
            "Records": [
                create_kinesis_record(self.network_event)
            ]
        }

        result = lambda_handler(event, None)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["duplicates"], 0)
        mock_store.assert_called_once()

    @patch("app.store_event")
    def test_duplicate_event(self, mock_store):
        mock_store.return_value = {
            "status": "duplicate"
        }

        event = {
            "Records": [
                create_kinesis_record(self.network_event)
            ]
        }

        result = lambda_handler(event, None)

        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["duplicates"], 1)

    @patch("app.store_event")
    def test_multiple_events(self, mock_store):
        mock_store.side_effect = [
            {"status": "processed"},
            {"status": "duplicate"},
        ]

        second_event = self.network_event.copy()
        second_event["event_id"] = "test-event-002"

        event = {
            "Records": [
                create_kinesis_record(self.network_event),
                create_kinesis_record(second_event),
            ]
        }

        result = lambda_handler(event, None)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(mock_store.call_count, 2)

    @patch("app.store_event")
    def test_missing_required_field(self, mock_store):
        invalid_event = self.network_event.copy()
        del invalid_event["source_ip"]

        event = {
            "Records": [
                create_kinesis_record(invalid_event)
            ]
        }

        with self.assertRaises(ValueError):
            lambda_handler(event, None)

        mock_store.assert_not_called()

    @patch("app.store_event")
    def test_empty_batch(self, mock_store):
        result = lambda_handler({"Records": []}, None)

        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["duplicates"], 0)
        mock_store.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
