"""Unit tests for the CoinbaseClient class."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import uuid

# Add the project root to sys.path to allow for absolute imports of project modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Global imports that will be mocked or used in class setup
CoinbaseClient = None
config = None
logger = None


class TestCoinbaseClient(unittest.TestCase):
    """Test suite for the CoinbaseClient class."""

    @classmethod
    def setUpClass(cls):
        """Set up a dummy environment and import modules under test."""
        cls.original_environ = dict(os.environ)
        os.environ["COINBASE_API_KEY"] = "dummy_key_for_import"
        os.environ["COINBASE_API_SECRET"] = "dummy_secret_for_import"

        global CoinbaseClient, config, logger
        # We must import the modules here AFTER the environment is set up
        from coinbase_client import CoinbaseClient as Client
        import config as conf
        import logger as log

        # Assign to class attributes so tests can use them
        cls.CoinbaseClient = Client
        cls.config = conf
        cls.logger = log

    @classmethod
    def tearDownClass(cls):
        """Restore the original environment."""
        os.environ.clear()
        os.environ.update(cls.original_environ)

    def setUp(self):
        """Set up a clean, mocked environment for each test."""
        patcher_rest_client = patch("coinbase_client.RESTClient")
        patcher_config = patch("coinbase_client.config")
        patcher_logger = patch("coinbase_client.logger")

        self.mock_rest_client_class = patcher_rest_client.start()
        self.mock_config_module = patcher_config.start()
        self.mock_logger_module = patcher_logger.start()

        self.addCleanup(patcher_rest_client.stop)
        self.addCleanup(patcher_config.stop)
        self.addCleanup(patcher_logger.stop)

        self.mock_rest_client_instance = self.mock_rest_client_class.return_value
        self.mock_logger_instance = self.mock_logger_module.get_logger.return_value

        self.mock_config_module.COINBASE_API_KEY = "test_api_key"
        self.mock_config_module.COINBASE_API_SECRET = "test_api_secret"

    # --- Test Initialization ---

    def test_initialization_success(self):
        """Test successful initialization of CoinbaseClient."""
        self.CoinbaseClient()
        self.mock_rest_client_class.assert_called_once_with(
            api_key="test_api_key",
            api_secret="test_api_secret",
            rate_limit_headers=True,
        )
        self.mock_logger_instance.info.assert_called_with(
            "Coinbase RESTClient initialized successfully for production URL."
        )

    def test_initialization_rest_client_exception(self):
        """Test initialization failure if RESTClient instantiation fails."""
        self.mock_rest_client_class.side_effect = Exception("Connection Failed")
        with self.assertRaisesRegex(RuntimeError, "initialization failed: Connection Failed"):
            self.CoinbaseClient()
        self.mock_logger_instance.error.assert_called_with(
            "Failed to initialize Coinbase RESTClient: Connection Failed", exc_info=True
        )

    # --- Test Core Methods ---

    def test_get_accounts_success(self):
        """Test get_accounts successfully returns a list of accounts."""
        expected_accounts = [{"id": "acc1"}]
        self.mock_rest_client_instance.get_accounts.return_value = {"accounts": expected_accounts}
        client = self.CoinbaseClient()
        self.mock_rest_client_instance.get_accounts.return_value = {'accounts': expected_accounts}
        accounts = client.get_accounts()
        self.assertEqual(accounts, expected_accounts)
        self.mock_rest_client_instance.get_accounts.assert_called_once()
        self.mock_logger_instance.info.assert_called_with(
            f"Successfully retrieved {len(expected_accounts)} accounts."
        )

    def test_get_accounts_api_exception(self):
        """Test get_accounts handles API exceptions gracefully."""
        self.mock_rest_client_instance.get_accounts.side_effect = Exception("API Error")
        client = self.CoinbaseClient()
        accounts = client.get_accounts()
        self.assertIsNone(accounts)
        self.mock_rest_client_instance.get_accounts.assert_called_once()
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving accounts: API Error", exc_info=True
        )

    def test_get_product_candles_success(self):
        """Test get_product_candles successfully retrieves candles."""
        expected_candles = [
            {
                "start": "1672531200",
                "low": "20000",
                "high": "21000",
                "open": "20500",
                "close": "20800",
                "volume": "100",
            }
        ]
        self.mock_rest_client_instance.get_public_candles.return_value = {
            "candles": expected_candles
        }
        client = self.CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "ONE_HOUR")
        self.assertEqual(candles, expected_candles)

    def test_get_product_candles_api_exception(self):
        """Test get_product_candles handles API exceptions gracefully."""
        self.mock_rest_client_instance.get_public_candles.side_effect = Exception(
            "API Error"
        )
        client = self.CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "ONE_HOUR")
        self.assertIsNone(candles)
        self.mock_logger_instance.error.assert_called_with(
            'An unexpected error occurred while retrieving candles for BTC-USD: API Error',
            exc_info=True,
        )

    def test_get_product_book_success(self):
        """Test get_product_book successfully retrieves the order book."""
        expected_book = {"bids": [], "asks": []}
        self.mock_rest_client_instance.get_product_book.return_value = expected_book
        client = self.CoinbaseClient()
        book = client.get_product_book("BTC-USD", limit=1)
        self.assertEqual(book, expected_book)
        self.mock_logger_instance.info.assert_called_with(
            "Successfully retrieved product book for BTC-USD."
        )

    def test_get_product_book_no_pricebook_key(self):
        """Test get_product_book when 'pricebook' key is missing or data is not a dict."""
        self.mock_rest_client_instance.get_product_book.return_value = {
            "not_pricebook": {}
        }
        self.mock_rest_client_instance.get_product_book.return_value = {
            "not_pricebook": {}
        }
        client = self.CoinbaseClient()
        book = client.get_product_book("BTC-USD")
        self.assertIsNone(book)
        self.mock_logger_instance.warning.assert_called_with(
            "get_product_book for BTC-USD response format not recognized or key data missing: {'not_pricebook': {}}"
        )

    def test_get_product_book_api_exception(self):
        """Test get_product_book handles API exceptions."""
        client = self.CoinbaseClient()
        product_id = "LTC-USD"
        self.mock_rest_client_instance.get_product_book.side_effect = Exception(
            "API Error"
        )
        book = client.get_product_book("BTC-USD")
        self.assertIsNone(book)
        self.mock_logger_instance.error.assert_called_with(
            'An unexpected error occurred while retrieving order book for BTC-USD: API Error',
            exc_info=True,
        )

    # --- Tests for limit_order_buy ---
    @patch("coinbase_client.CoinbaseClient._generate_client_order_id")
    def test_limit_order_buy_success(self, mock_generate_id):
        """Test successful limit buy order placement."""
        client = self.CoinbaseClient()
        mock_generate_id.return_value = "test_client_order_id_buy"
        product_id = "BTC-USD"
        base_size = "0.001"
        limit_price = "30000.00"
        mock_api_response = {
            "success": True,
            "order_id": "server_order_id_buy",
            "failure_reason": None,  # Example fields, adjust to actual API
            "client_order_id": "test_client_order_id_buy",
        }
        self.mock_rest_client_instance.limit_order_gtc_buy.return_value = (
            mock_api_response
        )

        expected_processed_response = {
            "success": True,
            "order_id": "server_order_id_buy",
            "client_order_id": "test_client_order_id_buy",
            "product_id": product_id,
            "side": "BUY",
            "size": base_size,
            "price": limit_price,
        }

        result = client.limit_order_buy(
            product_id, base_size, limit_price
        )
        self.assertEqual(result, expected_processed_response)

        self.mock_rest_client_instance.limit_order_gtc_buy.assert_called_once_with(
            client_order_id="test_client_order_id_buy",
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price,
            post_only=True,
        )
        expected_log_message = (
            "Limit buy order placed successfully for %s. Order ID: %s"
            % (product_id, mock_api_response.get("order_id"))
        )
        self.mock_logger_instance.info.assert_any_call(expected_log_message)
        self.mock_logger_instance.error.assert_not_called()

    @patch("coinbase_client.CoinbaseClient._generate_client_order_id")
    def test_limit_order_buy_api_exception(self, mock_generate_id):
        """Test limit buy order handles API exceptions."""
        client = self.CoinbaseClient()
        mock_generate_id.return_value = "test_client_order_id_buy_fail"
        product_id = "BTC-USD"
        base_size = "0.001"
        limit_price = "30000.00"
        self.mock_rest_client_instance.limit_order_gtc_buy.side_effect = Exception(
            "Buy Order API Error"
        )

        response = client.limit_order_buy(
            product_id, base_size, limit_price
        )
        self.assertIsNone(response)
        self.mock_logger_instance.error.assert_any_call(
            f"An unexpected error occurred while placing limit buy order for {product_id}: Buy Order API Error",
            exc_info=True,
        )

    # --- Tests for limit_order_sell ---
    @patch("coinbase_client.CoinbaseClient._generate_client_order_id")
    def test_limit_order_sell_success(self, mock_generate_id):
        """Test successful limit sell order placement."""
        client = self.CoinbaseClient()
        mock_generate_id.return_value = "test_client_order_id_sell"
        product_id = "ETH-USD"
        base_size = "0.01"
        limit_price = "2100.00"
        mock_api_response = {
            "success": True,
            "order_id": "server_order_id_sell",
            "failure_reason": None,
            "client_order_id": "test_client_order_id_sell",
        }
        self.mock_rest_client_instance.limit_order_gtc_sell.return_value = (
            mock_api_response
        )

        expected_processed_response = {
            "success": True,
            "order_id": "server_order_id_sell",
            "client_order_id": "test_client_order_id_sell",
            "product_id": product_id,
            "side": "SELL",
            "size": base_size,
            "price": limit_price,
        }

        result = client.limit_order_sell(
            product_id, base_size, limit_price
        )
        self.assertEqual(result, expected_processed_response)

        self.mock_rest_client_instance.limit_order_gtc_sell.assert_called_once_with(
            client_order_id="test_client_order_id_sell",
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price,
            post_only=True,
        )
        expected_log_message = (
            "Limit sell order placed successfully for %s. Order ID: %s"
            % (product_id, mock_api_response.get("order_id"))
        )
        self.mock_logger_instance.info.assert_any_call(expected_log_message)
        self.mock_logger_instance.error.assert_not_called()

    @patch("coinbase_client.CoinbaseClient._generate_client_order_id")
    def test_limit_order_sell_api_exception(self, mock_generate_id):
        """Test limit sell order handles API exceptions."""
        mock_generate_id.return_value = "test_client_order_id_sell_fail"
        product_id = "BTC-USD"
        base_size = "0.001"
        limit_price = "31000.00"
        self.mock_rest_client_instance.limit_order_gtc_sell.side_effect = Exception(
            "Sell Order API Error"
        )

        client = self.CoinbaseClient()
        client = self.CoinbaseClient()
        response = client.limit_order_sell(
            product_id, base_size, limit_price
        )
        self.assertIsNone(response)
        self.mock_logger_instance.error.assert_any_call(
            f"An unexpected error occurred while placing limit sell order for {product_id}: Sell Order API Error",
            exc_info=True,
        )

    # --- Tests for cancel_orders ---
    def test_cancel_orders_success(self):
        """Test successful order cancellation."""
        order_ids = ["order1", "order2"]
        expected_response = {
            "results": [
                {"success": True, "order_id": "order1"},
                {"success": False, "order_id": "order2"},
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = expected_response

        client = self.CoinbaseClient()
        response = client.cancel_orders(order_ids)
        self.assertEqual(response, expected_response)
        self.mock_rest_client_instance.cancel_orders.assert_called_once_with(
            order_ids=order_ids
        )
        calls = [
            call(f"Attempting to cancel orders: {order_ids}"),
            call(f"Cancel orders response: {expected_response}"),
            call(
                f"Successfully processed cancel_orders request for {len(order_ids)} order(s). Checking individual results."
            ),
            call("Order order1 cancelled successfully."),
            # Assuming the mock for order2 implies a failure reason of None or it's handled by a default
        ]
        self.mock_logger_instance.info.assert_has_calls(calls, any_order=False)
        # Check for the error log for the failed order
        # The failure_reason for order2 in mock_response is None. The client code defaults to "Unknown reason".
        self.mock_logger_instance.error.assert_any_call(
            "Failed to cancel order order2. Reason: Unknown reason"
        )

    def test_cancel_orders_api_exception(self):
        """Test cancel_orders handles API exceptions."""
        order_ids = ["order_err1"]
        self.mock_rest_client_instance.cancel_orders.side_effect = Exception(
            "Cancel API Error"
        )

        client = self.CoinbaseClient()
        response = client.cancel_orders(order_ids)
        self.assertIsNone(response)
        self.mock_logger_instance.error.assert_any_call(
            f"An unexpected error occurred while cancelling orders {order_ids}: Cancel API Error",
            exc_info=True,
        )

    def test_cancel_orders_empty_list(self):
        """Test cancel_orders with an empty list of orders."""
        # This should ideally be caught by assertions in cancel_orders before API call
        client = self.CoinbaseClient()
        with self.assertRaises(AssertionError):  # Or appropriate custom exception
            client.cancel_orders([])
        # Check that no API call was made if an assertion fails early
        self.mock_rest_client_instance.cancel_orders.assert_not_called()
        # Depending on implementation, a log might occur before assertion
        # self.mock_logger_instance.warning.assert_any_call("No orders provided for cancellation.")


if __name__ == "__main__":
    unittest.main()
