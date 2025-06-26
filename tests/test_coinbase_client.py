"""Unit tests for the CoinbaseClient class."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, ANY, call
import uuid
from requests.exceptions import HTTPError, RequestException

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now that the path is set, we can import the class to be tested
from coinbase_client import CoinbaseClient


class TestCoinbaseClient(unittest.TestCase):
    """Test suite for the CoinbaseClient."""

    def setUp(self):
        """Set up test environment for each test."""
        patcher_rest_client = patch('coinbase_client.RESTClient')
        patcher_config = patch('coinbase_client.config')
        patcher_logger = patch('coinbase_client.logger')

        self.mock_rest_client_class = patcher_rest_client.start()
        self.mock_config_module = patcher_config.start()
        self.mock_logger_module = patcher_logger.start()

        self.addCleanup(patcher_rest_client.stop)
        self.addCleanup(patcher_config.stop)
        self.addCleanup(patcher_logger.stop)

        self.mock_logger_instance = self.mock_logger_module.get_logger.return_value
        self.mock_rest_client_instance = self.mock_rest_client_class.return_value

        self.mock_config_module.COINBASE_API_KEY = "test_api_key"
        self.mock_config_module.COINBASE_API_SECRET = "test_api_secret"
        self.mock_config_module.COINBASE_SANDBOX_API_URL = "https://api.sandbox.coinbase.com"

        # Common HTTP/Request exception mocks
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        self.mock_http_error = HTTPError("Test HTTP Error", response=mock_response)
        self.mock_request_exception = RequestException("Test Request Exception")

    def _test_api_call_http_error(self, method_name, api_args, log_message):
        """Helper to test HTTPError handling for a given client method."""
        getattr(self.mock_rest_client_instance, method_name).side_effect = self.mock_http_error
        client = CoinbaseClient()
        result = getattr(client, method_name)(**api_args)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(log_message, exc_info=True)

    def _test_api_call_request_exception(self, method_name, api_args, log_message):
        """Helper to test RequestException handling for a given client method."""
        getattr(self.mock_rest_client_instance, method_name).side_effect = self.mock_request_exception
        client = CoinbaseClient()
        result = getattr(client, method_name)(**api_args)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(log_message, exc_info=True)

    def _test_api_call_unexpected_error(self, method_name, api_args, log_message):
        """Helper to test unexpected error handling for a given client method."""
        getattr(self.mock_rest_client_instance, method_name).side_effect = Exception("Chaos")
        client = CoinbaseClient()
        result = getattr(client, method_name)(**api_args)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(log_message, exc_info=True)

    # --- Test Initialization ---

    def test_initialization_success(self):
        """Test successful initialization of CoinbaseClient uses config values."""
        CoinbaseClient()
        self.mock_rest_client_class.assert_called_once_with(
            api_key="test_api_key",
            api_secret="test_api_secret",
            base_url="https://api.sandbox.coinbase.com",
            rate_limit_headers=True
        )
        self.mock_logger_instance.info.assert_called_with(
            "Coinbase RESTClient initialized successfully for https://api.sandbox.coinbase.com URL."
        )

    def test_initialization_with_arguments(self):
        """Test successful initialization with direct arguments."""
        CoinbaseClient(api_key="arg_key", api_secret="arg_secret", api_url="https://custom.url")
        self.mock_rest_client_class.assert_called_once_with(
            api_key="arg_key",
            api_secret="arg_secret",
            base_url="https://custom.url",
            rate_limit_headers=True
        )

    def test_initialization_failure(self):
        """Test initialization failure if RESTClient instantiation fails."""
        self.mock_rest_client_class.side_effect = Exception("Connection Failed")
        with self.assertRaisesRegex(RuntimeError, "Coinbase RESTClient initialization failed: Connection Failed"):
            CoinbaseClient()
        self.mock_logger_instance.error.assert_called_with(
            "Failed to initialize Coinbase RESTClient: Connection Failed", exc_info=True
        )

    def test_initialization_no_api_key(self):
        """Test initialization fails if API key is missing."""
        self.mock_config_module.COINBASE_API_KEY = None
        with self.assertRaisesRegex(AssertionError, "API key must be a non-empty string."):
            CoinbaseClient()

    def test_initialization_empty_api_key(self):
        """Test initialization fails if API key is an empty string."""
        with self.assertRaisesRegex(AssertionError, "API key must be a non-empty string."):
            CoinbaseClient(api_key="", api_secret="a-secret")

    def test_initialization_no_api_secret(self):
        """Test initialization fails if API secret is missing."""
        self.mock_config_module.COINBASE_API_SECRET = None
        with self.assertRaisesRegex(AssertionError, "API secret must be a non-empty string."):
            CoinbaseClient()

    def test_initialization_empty_api_secret(self):
        """Test initialization fails if API secret is an empty string."""
        with self.assertRaisesRegex(AssertionError, "API secret must be a non-empty string."):
            CoinbaseClient(api_key="an-api-key", api_secret="")

    def test_generate_client_order_id(self):
        """Test the generation of a unique client order ID."""
        client = CoinbaseClient()
        order_id = client._generate_client_order_id()
        self.assertIsInstance(order_id, str)
        self.assertTrue(len(order_id) > 0)

    # --- Test get_accounts ---

    def test_get_accounts_success(self):
        """Test successful retrieval of accounts."""
        mock_accounts = [{'id': '1', 'name': 'BTC Wallet', 'balance': '1.0'}]
        self.mock_rest_client_instance.get_accounts.return_value = {'accounts': mock_accounts}
        client = CoinbaseClient()
        result = client.get_accounts()
        self.assertEqual(result, mock_accounts)
        self.mock_logger_instance.debug.assert_called_with("Attempting to retrieve accounts.")
        self.mock_logger_instance.info.assert_called_with(f"Successfully retrieved {len(mock_accounts)} accounts.")
        self.mock_rest_client_instance.get_accounts.assert_called_once()

    def test_get_accounts_error_handling(self):
        """Test all error handling for get_accounts."""
        api_args = {}
        self._test_api_call_http_error('get_accounts', api_args, f"Network error retrieving accounts: {self.mock_http_error}")
        self._test_api_call_request_exception('get_accounts', api_args, f"Network error retrieving accounts: {self.mock_request_exception}")
        self._test_api_call_unexpected_error('get_accounts', api_args, "An unexpected error occurred while retrieving accounts: Chaos")

    def test_get_accounts_malformed_response_not_dict(self):
        """Test get_accounts handles a response that is not a dictionary."""
        self.mock_rest_client_instance.get_accounts.return_value = "not_a_dict"
        client = CoinbaseClient()
        result = client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving accounts: get_accounts response should be a dictionary.",
            exc_info=True
        )

    def test_get_accounts_malformed_response_no_accounts_key(self):
        """Test get_accounts handles a response missing the 'accounts' key."""
        self.mock_rest_client_instance.get_accounts.return_value = {'data': []}
        client = CoinbaseClient()
        result = client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving accounts: 'accounts' key is missing in the response.",
            exc_info=True
        )

    def test_get_accounts_malformed_response_accounts_not_list(self):
        """Test get_accounts handles a response where 'accounts' is not a list."""
        self.mock_rest_client_instance.get_accounts.return_value = {'accounts': 'not_a_list'}
        client = CoinbaseClient()
        result = client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving accounts: 'accounts' key should be a list.",
            exc_info=True
        )

    def test_get_accounts_invalid_json_response(self):
        """Test get_accounts handles a response that is an invalid JSON string."""
        invalid_json_string = "{'bad': 'json'"
        self.mock_rest_client_instance.get_accounts.return_value = invalid_json_string
        client = CoinbaseClient()
        result = client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_any_call(
            "Failed to decode JSON from response: %s", invalid_json_string
        )
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving accounts: get_accounts response should be a dictionary.",
            exc_info=True
        )

    # --- Test get_product_candles ---

    def test_get_product_candles_success(self):
        """Test successful retrieval of product candles."""
        mock_candles = [{'time': 123, 'price': '100'}]
        self.mock_rest_client_instance.get_product_candles.return_value = {'candles': mock_candles}
        client = CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "ONE_MINUTE")
        self.assertEqual(candles, mock_candles)
        self.mock_logger_instance.info.assert_called_with(f"Successfully retrieved {len(mock_candles)} candles for BTC-USD.")

    def test_get_product_candles_error_handling(self):
        """Test all error handling for get_product_candles."""
        api_args = {'product_id': 'BTC-USD', 'granularity': 'ONE_MINUTE'}
        self._test_api_call_http_error('get_product_candles', api_args, f"Network error retrieving candles for BTC-USD: {self.mock_http_error}")
        self._test_api_call_request_exception('get_product_candles', api_args, f"Network error retrieving candles for BTC-USD: {self.mock_request_exception}")
        self._test_api_call_unexpected_error('get_product_candles', api_args, "An unexpected error occurred while retrieving candles for BTC-USD: Chaos")

    def test_get_product_candles_malformed_response_not_dict(self):
        """Test get_product_candles handles a response that is not a dictionary."""
        self.mock_rest_client_instance.get_product_candles.return_value = "not_a_dict"
        client = CoinbaseClient()
        result = client.get_product_candles(product_id='BTC-USD', granularity='ONE_MINUTE')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving candles for BTC-USD: get_product_candles response should be a dictionary.",
            exc_info=True
        )

    def test_get_product_candles_malformed_response_no_candles_key(self):
        """Test get_product_candles handles a response missing the 'candles' key."""
        self.mock_rest_client_instance.get_product_candles.return_value = {'data': []}
        client = CoinbaseClient()
        result = client.get_product_candles(product_id='BTC-USD', granularity='ONE_MINUTE')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving candles for BTC-USD: 'candles' key missing in response.",
            exc_info=True
        )

    def test_get_product_candles_malformed_response_candles_not_list(self):
        """Test get_product_candles handles a response where 'candles' is not a list."""
        self.mock_rest_client_instance.get_product_candles.return_value = {'candles': 'not_a_list'}
        client = CoinbaseClient()
        result = client.get_product_candles(product_id='BTC-USD', granularity='ONE_MINUTE')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving candles for BTC-USD: 'candles' key must be a list.",
            exc_info=True
        )

    # --- Test get_product_book ---

    def test_get_product_book_success(self):
        """Test successful retrieval of product book."""
        mock_book = {'bids': [], 'asks': []}
        self.mock_rest_client_instance.get_product_book.return_value = {'pricebook': mock_book}
        client = CoinbaseClient()
        book = client.get_product_book("BTC-USD")
        self.assertEqual(book, mock_book)
        self.mock_logger_instance.info.assert_called_with("Successfully retrieved order book for BTC-USD.")

    def test_get_product_book_error_handling(self):
        """Test all error handling for get_product_book."""
        api_args = {'product_id': 'BTC-USD'}
        self._test_api_call_http_error('get_product_book', api_args, f"Network error retrieving order book for BTC-USD: {self.mock_http_error}")
        self._test_api_call_request_exception('get_product_book', api_args, f"Network error retrieving order book for BTC-USD: {self.mock_request_exception}")
        self._test_api_call_unexpected_error('get_product_book', api_args, "An unexpected error occurred while retrieving order book for BTC-USD: Chaos")

    def test_get_product_book_malformed_response_not_dict(self):
        """Test get_product_book handles a response that is not a dictionary."""
        self.mock_rest_client_instance.get_product_book.return_value = "not_a_dict"
        client = CoinbaseClient()
        result = client.get_product_book(product_id='BTC-USD')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving order book for BTC-USD: get_product_book response should be a dictionary.",
            exc_info=True
        )

    def test_get_product_book_malformed_response_no_pricebook_key(self):
        """Test get_product_book handles a response missing the 'pricebook' key."""
        self.mock_rest_client_instance.get_product_book.return_value = {'data': {}}
        client = CoinbaseClient()
        result = client.get_product_book(product_id='BTC-USD')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving order book for BTC-USD: 'pricebook' key missing in response.",
            exc_info=True
        )

    def test_get_product_book_malformed_response_pricebook_not_dict(self):
        """Test get_product_book handles a response where 'pricebook' is not a dict."""
        self.mock_rest_client_instance.get_product_book.return_value = {'pricebook': 'not_a_dict'}
        client = CoinbaseClient()
        result = client.get_product_book(product_id='BTC-USD')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving order book for BTC-USD: 'pricebook' must be a dictionary.",
            exc_info=True
        )

    # --- Test get_product ---

    def test_get_product_success(self):
        """Test successful retrieval of a product."""
        mock_product = {'product_id': 'BTC-USD'}
        self.mock_rest_client_instance.get_product.return_value = mock_product
        client = CoinbaseClient()
        product = client.get_product("BTC-USD")
        self.assertEqual(product, mock_product)
        self.mock_logger_instance.info.assert_called_with("Successfully retrieved product details for BTC-USD.")

    def test_get_product_error_handling(self):
        """Test all error handling for get_product."""
        api_args = {'product_id': 'BTC-USD'}
        self._test_api_call_http_error('get_product', api_args, f"Network error retrieving product BTC-USD: {self.mock_http_error}")
        self._test_api_call_request_exception('get_product', api_args, f"Network error retrieving product BTC-USD: {self.mock_request_exception}")
        self._test_api_call_unexpected_error('get_product', api_args, "An unexpected error occurred while retrieving product BTC-USD: Chaos")

    def test_get_product_malformed_response_not_dict(self):
        """Test get_product handles a response that is not a dictionary."""
        self.mock_rest_client_instance.get_product.return_value = "not_a_dict"
        client = CoinbaseClient()
        result = client.get_product(product_id='BTC-USD')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving product BTC-USD: get_product response should be a dictionary.",
            exc_info=True
        )

    def test_get_product_malformed_response_no_product_key(self):
        """Test get_product handles a response missing the 'product' key."""
        self.mock_rest_client_instance.get_product.return_value = {'data': {}}
        client = CoinbaseClient()
        result = client.get_product(product_id='BTC-USD')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving product BTC-USD: 'product_id' missing from product data.",
            exc_info=True
        )

    def test_get_product_malformed_response_product_not_dict(self):
        """Test get_product handles a response where 'product' is not a dict."""
        self.mock_rest_client_instance.get_product.return_value = {'product': 'not_a_dict'}
        client = CoinbaseClient()
        result = client.get_product(product_id='BTC-USD')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving product BTC-USD: 'product_id' missing from product data.",
            exc_info=True
        )

    # --- Test limit_order ---

    def test_limit_order_success(self):
        """Test successful placement of a limit order."""
        self.mock_rest_client_instance.limit_order_buy.return_value = {'success': True, 'order_id': 'order-123'}
        client = CoinbaseClient()
        response = client.limit_order(side="BUY", product_id="BTC-USD", size="1", price="10000")
        self.assertIsNotNone(response)
        self.assertTrue(response['success'])
        self.assertEqual(response['order_id'], 'order-123')
        self.mock_logger_instance.info.assert_called_with("Successfully placed limit buy order order-123.")
        self.mock_rest_client_instance.limit_order_buy.assert_called_with(
            client_order_id=ANY,
            product_id="BTC-USD",
            base_size="1",
            limit_price="10000"
        )

    def test_limit_order_failure(self):
        """Test failed placement of a limit order."""
        self.mock_rest_client_instance.limit_order_sell.return_value = {'success': False, 'failure_reason': 'Insufficient funds'}
        client = CoinbaseClient()
        response = client.limit_order(side="SELL", product_id="BTC-USD", size="1", price="10000")
        self.assertIsNotNone(response)
        self.assertFalse(response['success'])
        self.assertEqual(response['failure_reason'], 'Insufficient funds')
        self.mock_logger_instance.error.assert_called_with("Failed to place limit sell order for BTC-USD. Reason: Insufficient funds")
        self.mock_rest_client_instance.limit_order_sell.assert_called_with(
            client_order_id=ANY,
            product_id="BTC-USD",
            base_size="1",
            limit_price="10000"
        )

    def test_limit_order_error_handling(self):
        """Test all error handling for limit_order."""
        # Test HTTPError
        self.mock_rest_client_instance.limit_order_buy.side_effect = self.mock_http_error
        client = CoinbaseClient()
        result = client.limit_order(side='BUY', product_id='BTC-USD', size='1', price='10000')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(f"Network error on limit buy for BTC-USD: {self.mock_http_error}", exc_info=True)

        # Test RequestException
        self.mock_rest_client_instance.limit_order_sell.side_effect = self.mock_request_exception
        result = client.limit_order(side='SELL', product_id='BTC-USD', size='1', price='10000')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(f"Network error on limit sell for BTC-USD: {self.mock_request_exception}", exc_info=True)

        # Test Unexpected Error
        self.mock_rest_client_instance.limit_order_buy.side_effect = Exception("Chaos")
        result = client.limit_order(side='BUY', product_id='BTC-USD', size='1', price='10000')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with("An unexpected error occurred on limit buy for BTC-USD: Chaos", exc_info=True)

    def test_limit_order_malformed_response_not_dict(self):
        """Test limit_order handles a response that is not a dictionary."""
        self.mock_rest_client_instance.limit_order_buy.return_value = "not_a_dict"
        client = CoinbaseClient()
        result = client.limit_order(side="BUY", product_id="BTC-USD", size="1", price="10000")
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred on limit buy for BTC-USD: limit_order_buy response should be a dictionary.",
            exc_info=True
        )

    # --- Test get_order ---

    def test_get_order_success(self):
        """Test successful retrieval of an order."""
        mock_order = {'order_id': 'order-123'}
        self.mock_rest_client_instance.get_order.return_value = {'order': mock_order}
        client = CoinbaseClient()
        order = client.get_order('order-123')
        self.assertEqual(order, mock_order)
        self.mock_logger_instance.info.assert_called_with("Successfully retrieved order order-123.")

    def test_get_order_error_handling(self):
        """Test all error handling for get_order."""
        api_args = {'order_id': 'order-123'}
        self._test_api_call_http_error('get_order', api_args, f"Network error retrieving order order-123: {self.mock_http_error}")
        self._test_api_call_request_exception('get_order', api_args, f"Network error retrieving order order-123: {self.mock_request_exception}")
        self._test_api_call_unexpected_error('get_order', api_args, "An unexpected error occurred while retrieving order order-123: Chaos")

    def test_get_order_malformed_response_not_dict(self):
        """Test get_order handles a response that is not a dictionary."""
        self.mock_rest_client_instance.get_order.return_value = "not_a_dict"
        client = CoinbaseClient()
        result = client.get_order(order_id='order-123')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving order order-123: get_order response should be a dictionary.",
            exc_info=True
        )

    def test_get_order_malformed_response_no_order_key(self):
        """Test get_order handles a response missing the 'order' key."""
        self.mock_rest_client_instance.get_order.return_value = {'data': {}}
        client = CoinbaseClient()
        result = client.get_order(order_id='order-123')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving order order-123: 'order' key missing in response.",
            exc_info=True
        )

    def test_get_order_malformed_response_order_not_dict(self):
        """Test get_order handles a response where 'order' is not a dict."""
        self.mock_rest_client_instance.get_order.return_value = {'order': 'not_a_dict'}
        client = CoinbaseClient()
        result = client.get_order(order_id='order-123')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving order order-123: 'order' must be a dictionary.",
            exc_info=True
        )

    # --- Test cancel_orders ---

    def test_cancel_orders_success(self):
        """Test successful cancellation of orders."""
        order_ids = ['order1', 'order2']
        response_data = {'results': [{'success': True, 'order_id': 'order1'}, {'success': True, 'order_id': 'order2'}]}
        self.mock_rest_client_instance.cancel_orders.return_value = response_data
        client = CoinbaseClient()
        response = client.cancel_orders(order_ids)
        self.assertEqual(response, response_data)
        self.mock_logger_instance.info.assert_has_calls([
            call("Successfully cancelled order order1."),
            call("Successfully cancelled order order2.")
        ])

    def test_cancel_orders_partial_failure(self):
        """Test partial failure when cancelling multiple orders."""
        response_data = {
            'results': [
                {'success': True, 'order_id': 'order-123'},
                {'success': False, 'order_id': 'order-456', 'failure_reason': 'Order not found'}
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = response_data
        client = CoinbaseClient()
        response = client.cancel_orders(order_ids=['order-123', 'order-456'])
        self.assertIsNotNone(response)
        self.assertEqual(len(response['results']), 2)
        self.mock_logger_instance.info.assert_any_call("Successfully cancelled order order-123.")
        self.mock_logger_instance.error.assert_called_with("Failed to cancel order order-456. Reason: Order not found")

    def test_cancel_orders_error_handling(self):
        """Test all error handling for cancel_orders."""
        api_args = {'order_ids': ['order-123']}
        self._test_api_call_http_error('cancel_orders', api_args, f"Network error cancelling orders {api_args['order_ids']}: {self.mock_http_error}")
        self._test_api_call_request_exception('cancel_orders', api_args, f"Network error cancelling orders {api_args['order_ids']}: {self.mock_request_exception}")
        self._test_api_call_unexpected_error('cancel_orders', api_args, "An unexpected error occurred while cancelling orders ['order-123']: Chaos")

    def test_cancel_orders_malformed_response_not_dict(self):
        """Test cancel_orders handles a response that is not a dictionary."""
        self.mock_rest_client_instance.cancel_orders.return_value = "not_a_dict"
        client = CoinbaseClient()
        result = client.cancel_orders(order_ids=['order-123'])
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while cancelling orders ['order-123']: cancel_orders response should be a dictionary.",
            exc_info=True
        )

    def test_cancel_orders_malformed_response_results_not_list(self):
        """Test cancel_orders handles a response where 'results' is not a list."""
        self.mock_rest_client_instance.cancel_orders.return_value = {'results': 'not_a_list'}
        client = CoinbaseClient()
        result = client.cancel_orders(order_ids=['order-123'])
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while cancelling orders ['order-123']: 'results' key should be a list.",
            exc_info=True
        )

    def test_cancel_orders_malformed_response_results_item_not_dict(self):
        """Test cancel_orders handles a response where an item in 'results' is not a dict."""
        self.mock_rest_client_instance.cancel_orders.return_value = {'results': ['not_a_dict']}
        client = CoinbaseClient()
        result = client.cancel_orders(order_ids=['order-123'])
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while cancelling orders ['order-123']: Each item in 'results' should be a dictionary.",
            exc_info=True
        )

    def test_cancel_orders_malformed_response_no_results_or_success(self):
        """Test cancel_orders handles a response with no 'results' or 'success' key."""
        response_data = {'other_key': 'some_value'}
        self.mock_rest_client_instance.cancel_orders.return_value = response_data
        client = CoinbaseClient()
        result = client.cancel_orders(order_ids=['order-123'])
        self.assertEqual(result, response_data)
        self.mock_logger_instance.warning.assert_called_with(f"Cancel orders response format not as expected: {response_data}")


if __name__ == "__main__":
    unittest.main()