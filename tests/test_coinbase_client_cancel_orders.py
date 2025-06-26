"""Tests for the cancel_orders method in the CoinbaseClient class."""

import sys
import unittest
from unittest.mock import patch, MagicMock, call
from requests.exceptions import HTTPError, RequestException


class TestCoinbaseClientCancelOrders(unittest.TestCase):
    """Test suite for the cancel_orders method."""

    def setUp(self):
        """Set up a clean, mocked environment for each test."""
        for module in ["coinbase_client", "config", "logger"]:
            if module in sys.modules:
                del sys.modules[module]

        self.patcher_config = patch("coinbase_client.config")
        self.patcher_logger = patch("coinbase_client.logger")
        self.patcher_rest_client = patch("coinbase_client.RESTClient")

        self.mock_config = self.patcher_config.start()
        self.mock_logger_module = self.patcher_logger.start()
        self.mock_rest_client_class = self.patcher_rest_client.start()

        self.addCleanup(self.patcher_config.stop)
        self.addCleanup(self.patcher_logger.stop)
        self.addCleanup(self.patcher_rest_client.stop)

        self.mock_config.COINBASE_API_KEY = "k"
        self.mock_config.COINBASE_API_SECRET = "s"
        self.mock_config.COINBASE_SANDBOX_API_URL = "https://api.sandbox.pro.coinbase.com"
        self.mock_logger_instance = self.mock_logger_module.get_logger.return_value
        self.mock_rest_client_instance = self.mock_rest_client_class.return_value

        from coinbase_client import CoinbaseClient
        self.client = CoinbaseClient()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        self.mock_http_error = HTTPError("HTTP Error")
        self.mock_http_error.response = mock_response

    def test_cancel_orders_success_single_order(self):
        """Test successful cancellation of a single order."""
        order_ids = ['order1']
        mock_response = {
            'results': [{'success': True, 'order_id': 'order1', 'failure_reason': None}]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        response = self.client.cancel_orders(order_ids)

        self.assertEqual(response, mock_response)
        self.mock_rest_client_instance.cancel_orders.assert_called_once_with(order_ids=order_ids)
        self.mock_logger_instance.info.assert_any_call("Order order1 cancelled successfully.")

    def test_cancel_orders_success_multiple_orders(self):
        """Test successful cancellation of multiple orders."""
        order_ids = ['order1', 'order2']
        mock_response = {
            'results': [
                {'success': True, 'order_id': 'order1', 'failure_reason': None},
                {'success': True, 'order_id': 'order2', 'failure_reason': None}
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        response = self.client.cancel_orders(order_ids)

        self.assertEqual(response, mock_response)
        self.mock_rest_client_instance.cancel_orders.assert_called_once_with(order_ids=order_ids)
        self.mock_logger_instance.info.assert_has_calls([
            call("Order order1 cancelled successfully."),
            call("Order order2 cancelled successfully.")
        ], any_order=True)

    def test_cancel_orders_partial_success(self):
        """Test partial success when cancelling multiple orders."""
        order_ids = ['order1', 'order2']
        mock_response = {
            'results': [
                {'success': True, 'order_id': 'order1', 'failure_reason': None},
                {'success': False, 'order_id': 'order2', 'failure_reason': 'Insufficient funds'}
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        self.client.cancel_orders(order_ids)

        self.mock_logger_instance.info.assert_any_call("Order order1 cancelled successfully.")
        self.mock_logger_instance.error.assert_any_call("Failed to cancel order order2. Reason: Insufficient funds")

    def test_cancel_orders_failure_reason_parsing(self):
        """Test failure reason parsing from different response fields."""
        order_ids = ['order1', 'order2', 'order3']
        mock_response = {
            'results': [
                {'success': False, 'order_id': 'order1', 'error_response': {'message': 'Error from error_response'}},
                {'success': False, 'order_id': 'order2', 'failure_reason': 'Error from failure_reason'},
                {'success': False, 'order_id': 'order3'}
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        self.client.cancel_orders(order_ids)

        self.mock_logger_instance.error.assert_has_calls([
            call("Failed to cancel order order1. Reason: Error from error_response"),
            call("Failed to cancel order order2. Reason: Error from failure_reason"),
            call("Failed to cancel order order3. Reason: Unknown reason")
        ], any_order=True)

    def test_cancel_orders_unexpected_response_no_results_key(self):
        """Test handling of a response without the 'results' key."""
        order_ids = ['order1']
        mock_response = {'success': False, 'message': 'Batch failed'}
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        self.client.cancel_orders(order_ids)

        self.mock_logger_instance.warning.assert_called_once_with(
            f"Cancel orders response format not as expected or indicates general failure: {mock_response}"
        )

    def test_cancel_orders_http_error(self):
        """Test that HTTPError is handled correctly."""
        order_ids = ['order1']
        self.mock_rest_client_instance.cancel_orders.side_effect = self.mock_http_error

        response = self.client.cancel_orders(order_ids)

        self.assertIsNone(response)
        self.mock_logger_instance.error.assert_called_once_with(
            f"HTTP error cancelling orders {order_ids}: 404 Not Found",
            exc_info=True
        )

    def test_cancel_orders_request_exception(self):
        """Test that RequestException is handled correctly."""
        order_ids = ['order1']
        error = RequestException("Connection failed")
        self.mock_rest_client_instance.cancel_orders.side_effect = error

        response = self.client.cancel_orders(order_ids)

        self.assertIsNone(response)
        self.mock_logger_instance.error.assert_called_once_with(
            f"Request exception cancelling orders {order_ids}: {error}", exc_info=True
        )

    def test_cancel_orders_unexpected_exception(self):
        """Test that a generic Exception is handled correctly."""
        order_ids = ['order1']
        error = Exception("Something went wrong")
        self.mock_rest_client_instance.cancel_orders.side_effect = error

        response = self.client.cancel_orders(order_ids)

        self.assertIsNone(response)
        self.mock_logger_instance.error.assert_called_once_with(
            f"An unexpected error occurred while cancelling orders {order_ids}: {error}", exc_info=True
        )

    def test_cancel_orders_input_validation(self):
        """Test input validation for the order_ids parameter."""
        with self.assertRaisesRegex(AssertionError, "order_ids must be a list."):
            self.client.cancel_orders('not-a-list')
        with self.assertRaisesRegex(AssertionError, "order_ids list cannot be empty."):
            self.client.cancel_orders([])
        with self.assertRaisesRegex(AssertionError, "All order_ids in the list must be non-empty strings."):
            self.client.cancel_orders(['order1', ''])

    def test_cancel_orders_response_not_a_dict(self):
        """Test assertion failure if the API response is not a dictionary."""
        order_ids = ['order1']
        self.mock_rest_client_instance.cancel_orders.return_value = "not-a-dict"

        with self.assertRaisesRegex(AssertionError, "cancel_orders response should be a dictionary."):
            self.client.cancel_orders(order_ids)

    def test_cancel_orders_results_item_not_a_dict(self):
        """Test assertion failure if an item in the 'results' list is not a dictionary."""
        order_ids = ['order1']
        mock_response = {
            'results': ["not-a-dict"]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        with self.assertRaisesRegex(AssertionError, "Each item in 'results' should be a dictionary."):
            self.client.cancel_orders(order_ids)


    def test_cancel_orders_result_missing_success_key(self):
        """Test that an error is logged if a result is missing the 'success' key."""
        order_ids = ['order1']
        mock_response = {
            'results': [
                {
                    'failure_reason': 'none',
                    'order_id': 'order1',
                }
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        self.client.cancel_orders(order_ids)

        self.mock_logger_instance.error.assert_called_once_with(
            "Failed to cancel order order1. Reason: none"
        )

    def test_cancel_orders_result_missing_order_id_key(self):
        """Test that the method handles a missing 'order_id' key gracefully."""
        order_ids = ['order1']
        mock_response = {
            'results': [
                {'success': False, 'failure_reason': 'some_reason'}
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        self.client.cancel_orders(order_ids)

        self.mock_logger_instance.error.assert_called_once_with(
            "Failed to cancel order N/A. Reason: some_reason"
        )

    def test_cancel_orders_no_results_key_success(self):
        """Test handling of a successful response that lacks a 'results' key."""
        order_ids = ["order1", "order2"]
        mock_response = {"success": True, "some_other_data": "value"}
        self.mock_rest_client_instance.cancel_orders.return_value = mock_response

        self.client.cancel_orders(order_ids)

        expected_log = f"Cancel orders request appears successful at a high level for orders: {order_ids}"
        self.mock_logger_instance.info.assert_any_call(expected_log)


if __name__ == '__main__':
    unittest.main()
