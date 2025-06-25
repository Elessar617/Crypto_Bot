"""Unit tests for the CoinbaseClient class."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import uuid
from requests.exceptions import HTTPError, RequestException

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

    def test_get_accounts_http_error(self):
        """Test get_accounts handles HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        http_error = HTTPError(response=mock_response)
        self.mock_rest_client_instance.get_accounts.side_effect = http_error
        client = self.CoinbaseClient()
        accounts = client.get_accounts()
        self.assertIsNone(accounts)
        self.mock_logger_instance.error.assert_called_with(
            f"HTTP error retrieving accounts: {mock_response.status_code} {mock_response.text}",
            exc_info=True,
        )

    def test_get_accounts_request_exception(self):
        """Test get_accounts handles RequestException."""
        request_exception = RequestException("Connection timeout")
        self.mock_rest_client_instance.get_accounts.side_effect = request_exception
        client = self.CoinbaseClient()
        accounts = client.get_accounts()
        self.assertIsNone(accounts)
        self.mock_logger_instance.error.assert_called_with(
            f"Request exception retrieving accounts: {request_exception}",
            exc_info=True,
        )

    def test_get_accounts_no_accounts_key(self):
        """Test get_accounts handles a response missing the 'accounts' key."""
        self.mock_rest_client_instance.get_accounts.return_value = {"data": "no accounts here"}
        client = self.CoinbaseClient()
        accounts = client.get_accounts()
        self.assertIsNone(accounts)
        self.mock_logger_instance.warning.assert_called_with(
            "Received unexpected format for accounts data: <class 'dict'>"
        )

    def test_get_product_candles_success(self):
        """Test get_product_candles successfully retrieves candles."""
        expected_candles = [
            {"start": "1672531200", "low": "16000", "high": "16100", "open": "16050", "close": "16080", "volume": "100"}
        ]
        self.mock_rest_client_instance.get_public_candles.return_value = {"candles": expected_candles}
        client = self.CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "ONE_HOUR")
        self.assertEqual(candles, expected_candles)
        self.mock_rest_client_instance.get_public_candles.assert_called_once_with(
            product_id="BTC-USD",
            start="0",
            end="0",
            granularity="ONE_HOUR",
        )
        self.mock_logger_instance.info.assert_called_with(
            f"Successfully retrieved {len(expected_candles)} candles for BTC-USD."
        )

    def test_get_product_candles_api_exception(self):
        """Test get_product_candles handles API exceptions gracefully."""
        self.mock_rest_client_instance.get_public_candles.side_effect = Exception("API Error")
        client = self.CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "ONE_HOUR")
        self.assertIsNone(candles)
        self.mock_logger_instance.error.assert_called_with(
            'An unexpected error occurred while retrieving candles for BTC-USD: API Error',
            exc_info=True,
        )

    def test_get_product_book_success(self):
        """Test successful retrieval of the product book."""
        expected_book = {'bids': [], 'asks': []}
        self.mock_rest_client_instance.get_product_book.return_value = {'pricebook': expected_book}
        client = self.CoinbaseClient()
        book = client.get_product_book('BTC-USD')
        self.assertEqual(book, expected_book)
        self.mock_rest_client_instance.get_product_book.assert_called_once_with(product_id='BTC-USD', limit=None)
        self.mock_logger_instance.info.assert_called_with('Successfully retrieved product book for BTC-USD.')

    def test_get_product_book_no_pricebook_key(self):
        """Test get_product_book handles a response missing the 'pricebook' key."""
        self.mock_rest_client_instance.get_product_book.return_value = {'data': 'no book here'}
        client = self.CoinbaseClient()
        book = client.get_product_book('BTC-USD')
        self.assertIsNone(book)
        self.mock_logger_instance.warning.assert_called_with(
            "get_product_book for BTC-USD response format not recognized or key data missing: {'data': 'no book here'}"
        )

    def test_get_product_book_http_error(self):
        """Test get_product_book handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        http_error = HTTPError("Server Error")
        http_error.response = mock_response

        self.mock_rest_client_instance.get_product_book.side_effect = http_error
        client = self.CoinbaseClient()
        book = client.get_product_book('BTC-USD')
        self.assertIsNone(book)
        self.mock_logger_instance.error.assert_called_with(
            'HTTP error retrieving order book for BTC-USD: 500 Internal Server Error',
            exc_info=True,
        )

    def test_get_product_book_request_exception(self):
        """Test get_product_book handles request exceptions."""
        self.mock_rest_client_instance.get_product_book.side_effect = RequestException('Request Exception')
        client = self.CoinbaseClient()
        book = client.get_product_book('BTC-USD')
        self.assertIsNone(book)
        self.mock_logger_instance.error.assert_called_with(
            'Request exception retrieving order book for BTC-USD: Request Exception',
            exc_info=True,
        )

    # Tests for get_product
    def test_get_product_success(self):
        """Test successful retrieval of a single product."""
        # Create a mock product object that mimics the structure of the SDK's Product object
        mock_product = MagicMock()
        mock_product.product_id = 'BTC-USD'
        mock_product.price = '50000.00'
        mock_product.price_percentage_change_24h = '0.05'
        mock_product.volume_24h = '1000'
        mock_product.volume_percentage_change_24h = '0.10'
        mock_product.base_increment = '0.00000001'
        mock_product.quote_increment = '0.01'
        mock_product.quote_min_size = '1.00'
        mock_product.quote_max_size = '1000000.00'
        mock_product.base_min_size = '0.0001'
        mock_product.base_max_size = '100'
        mock_product.base_name = 'Bitcoin'
        mock_product.quote_name = 'US Dollar'
        mock_product.watched = False
        mock_product.is_disabled = False
        mock_product.new = False
        mock_product.status = 'online'
        mock_product.cancel_only = False
        mock_product.limit_only = False
        mock_product.post_only = False
        mock_product.trading_disabled = False
        mock_product.auction_mode = False
        mock_product.product_type = 'SPOT'
        mock_product.quote_currency_id = 'USD'
        mock_product.base_currency_id = 'BTC'
        mock_product.fcm_trading_session_details = None
        mock_product.mid_market_price = '50000.50'

        self.mock_rest_client_instance.get_products.return_value = {'products': [mock_product]}
        client = self.CoinbaseClient()
        product = client.get_product('BTC-USD')

        self.assertIsNotNone(product)
        self.assertEqual(product['product_id'], 'BTC-USD')
        self.assertEqual(product['price'], '50000.00')
        self.mock_logger_instance.info.assert_called_with('Successfully found and formatted product details for BTC-USD.')

    def test_get_product_not_found(self):
        """Test get_product when the product is not in the response."""
        self.mock_rest_client_instance.get_products.return_value = {'products': []}
        client = self.CoinbaseClient()
        product = client.get_product('ETH-USD')
        self.assertIsNone(product)
        self.mock_logger_instance.warning.assert_called_with('Could not find product details for ETH-USD in API response.')

    def test_get_product_malformed_response(self):
        """Test get_product with a malformed API response."""
        self.mock_rest_client_instance.get_products.return_value = {'data': 'wrong format'}
        client = self.CoinbaseClient()
        product = client.get_product('BTC-USD')
        self.assertIsNone(product)
        # The method should log two warnings: one for the format, one for not finding the product.
        # We will check that both were called.
        calls = [
            call("Unexpected format for get_products response: <class 'dict'>"),
            call('Could not find product details for BTC-USD in API response.')
        ]
        self.mock_logger_instance.warning.assert_has_calls(calls, any_order=True)

    def test_get_product_http_error(self):
        """Test get_product handles HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        http_error = HTTPError("Not Found")
        http_error.response = mock_response

        self.mock_rest_client_instance.get_products.side_effect = http_error
        client = self.CoinbaseClient()
        product = client.get_product('BTC-USD')
        self.assertIsNone(product)
        self.mock_logger_instance.error.assert_called_with(
            'HTTP error retrieving product BTC-USD: 404 Not Found',
            exc_info=True
        )

    def test_get_product_request_exception(self):
        """Test get_product handles RequestException."""
        self.mock_rest_client_instance.get_products.side_effect = RequestException('Connection Error')
        client = self.CoinbaseClient()
        product = client.get_product('BTC-USD')
        self.assertIsNone(product)
        self.mock_logger_instance.error.assert_called_with(
            'Request exception retrieving product BTC-USD: Connection Error',
            exc_info=True
        )

    def test_get_product_unexpected_exception(self):
        """Test get_product handles a generic Exception."""
        self.mock_rest_client_instance.get_products.side_effect = Exception('Unexpected Error')
        client = self.CoinbaseClient()
        product = client.get_product('BTC-USD')
        self.assertIsNone(product)
        self.mock_logger_instance.error.assert_called_with(
            'An unexpected error occurred while retrieving product BTC-USD: Unexpected Error',
            exc_info=True
        )

    # Tests for limit_order_buy
    def test_limit_order_buy_success(self):
        """Test successful placement of a limit buy order."""
        self.mock_rest_client_instance.limit_order_gtc_buy.return_value = {
            'success': True,
            'order_id': 'test_order_id_123'
        }
        client = self.CoinbaseClient()
        # Mock the internal client_order_id generation to have a predictable value
        with patch.object(client, '_generate_client_order_id', return_value='test_client_order_id_456'):
            result = client.limit_order_buy(product_id='BTC-USD', size='0.1', price='50000')

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertEqual(result['order_id'], 'test_order_id_123')
        self.mock_rest_client_instance.limit_order_gtc_buy.assert_called_once_with(
            client_order_id='test_client_order_id_456',
            product_id='BTC-USD',
            base_size='0.1',
            limit_price='50000',
            post_only=True
        )
        self.mock_logger_instance.info.assert_called_with('Limit buy order placed successfully for BTC-USD. Order ID: test_order_id_123')

    def test_limit_order_buy_api_failure(self):
        """Test API failure during limit buy order placement."""
        self.mock_rest_client_instance.limit_order_gtc_buy.return_value = {
            'success': False,
            'failure_reason': 'INSUFFICIENT_FUNDS'
        }
        client = self.CoinbaseClient()
        result = client.limit_order_buy(product_id='BTC-USD', size='1000', price='50000')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with('Limit buy order failed for BTC-USD. Reason: INSUFFICIENT_FUNDS')

    def test_limit_order_buy_invalid_price(self):
        """Test limit_order_buy with an invalid price (e.g., non-positive)."""
        client = self.CoinbaseClient()
        with self.assertRaises(ValueError) as cm:
            client.limit_order_buy(product_id='BTC-USD', size='0.1', price='-100')
        self.assertEqual(str(cm.exception), 'price must be a string representing a positive number.')
        self.mock_logger_instance.error.assert_called_with('Non-positive price for limit_order_buy: -100.')

    def test_limit_order_buy_http_error(self):
        """Test limit_order_buy handles HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Server Error'
        http_error = HTTPError('Server Error')
        http_error.response = mock_response

        self.mock_rest_client_instance.limit_order_gtc_buy.side_effect = http_error
        client = self.CoinbaseClient()
        result = client.limit_order_buy(product_id='BTC-USD', size='0.1', price='50000')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            'HTTP error placing limit buy order for BTC-USD: 500 Server Error',
            exc_info=True
        )

    def test_limit_order_buy_invalid_size_type(self):
        """Test limit_order_buy with a non-string size."""
        client = self.CoinbaseClient()
        with self.assertRaises(ValueError) as cm:
            client.limit_order_buy(product_id='BTC-USD', size=123, price='50000')
        self.assertEqual(str(cm.exception), 'size must be a string representing a positive number.')
        self.mock_logger_instance.error.assert_called_with("Invalid size type for limit_order_buy: <class 'int'>. Must be a string.")

    def test_limit_order_buy_invalid_price_format(self):
        """Test limit_order_buy with a non-numeric string price."""
        client = self.CoinbaseClient()
        with self.assertRaises(ValueError) as cm:
            client.limit_order_buy(product_id='BTC-USD', size='0.1', price='invalid')
        self.assertEqual(str(cm.exception), 'price must be a string representing a positive number.')
        self.mock_logger_instance.error.assert_called_with("Invalid price format for limit_order_buy: invalid. Not a valid number string.")

    # Tests for limit_order_sell
    def test_limit_order_sell_success(self):
        """Test successful placement of a limit sell order."""
        self.mock_rest_client_instance.limit_order_gtc_sell.return_value = {
            'success': True,
            'order_id': 'test_sell_order_id_123'
        }
        client = self.CoinbaseClient()
        with patch.object(client, '_generate_client_order_id', return_value='test_client_sell_id_456'):
            result = client.limit_order_sell(product_id='BTC-USD', size='0.1', price='51000')

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertEqual(result['order_id'], 'test_sell_order_id_123')
        self.mock_rest_client_instance.limit_order_gtc_sell.assert_called_once_with(
            client_order_id='test_client_sell_id_456',
            product_id='BTC-USD',
            base_size='0.1',
            limit_price='51000',
            post_only=True
        )
        self.mock_logger_instance.info.assert_called_with('Limit sell order placed successfully for BTC-USD. Order ID: test_sell_order_id_123')

    def test_limit_order_sell_api_failure(self):
        """Test API failure during limit sell order placement."""
        self.mock_rest_client_instance.limit_order_gtc_sell.return_value = {
            'success': False,
            'failure_reason': 'PRODUCT_NOT_FOUND'
        }
        client = self.CoinbaseClient()
        result = client.limit_order_sell(product_id='FAKE-COIN', size='10', price='100')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with('Limit sell order failed for FAKE-COIN. Reason: PRODUCT_NOT_FOUND')

    def test_limit_order_sell_invalid_size(self):
        """Test limit_order_sell with an invalid size (e.g., zero)."""
        client = self.CoinbaseClient()
        with self.assertRaises(ValueError) as cm:
            client.limit_order_sell(product_id='BTC-USD', size='0', price='51000')
        self.assertEqual(str(cm.exception), 'size must be a string representing a positive number.')
        self.mock_logger_instance.error.assert_called_with('Non-positive size for limit_order_sell: 0.')

    def test_limit_order_sell_http_error(self):
        """Test limit_order_sell handles HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        http_error = HTTPError('Bad Request')
        http_error.response = mock_response

        self.mock_rest_client_instance.limit_order_gtc_sell.side_effect = http_error
        client = self.CoinbaseClient()
        result = client.limit_order_sell(product_id='BTC-USD', size='0.1', price='51000')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            'HTTP error placing limit sell order for BTC-USD: 400 Bad Request',
            exc_info=True
        )

    def test_limit_order_sell_request_exception(self):
        """Test limit_order_sell handles RequestException."""
        self.mock_rest_client_instance.limit_order_gtc_sell.side_effect = RequestException('Network Error')
        client = self.CoinbaseClient()
        result = client.limit_order_sell(product_id='BTC-USD', size='0.1', price='51000')
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            'Request exception placing limit sell order for BTC-USD: Network Error',
            exc_info=True
        )

    def test_limit_order_sell_invalid_price_type(self):
        """Test limit_order_sell with a non-string price."""
        client = self.CoinbaseClient()
        with self.assertRaises(ValueError) as cm:
            client.limit_order_sell(product_id='BTC-USD', size='0.1', price=51000)
        self.assertEqual(str(cm.exception), 'price must be a string representing a positive number.')
        self.mock_logger_instance.error.assert_called_with("Invalid price type for limit_order_sell: <class 'int'>. Must be a string.")

    def test_limit_order_sell_invalid_size_format(self):
        """Test limit_order_sell with a non-numeric string size."""
        client = self.CoinbaseClient()
        with self.assertRaises(ValueError) as cm:
            client.limit_order_sell(product_id='BTC-USD', size='abc', price='51000')
        self.assertEqual(str(cm.exception), 'size must be a string representing a positive number.')
        self.mock_logger_instance.error.assert_called_with("Invalid size format for limit_order_sell: abc. Not a valid number string.")

    # Tests for cancel_orders
    def test_cancel_orders_success_and_failure_mix(self):
        """Test cancelling a mix of successful and failed orders in one batch."""
        self.mock_rest_client_instance.cancel_orders.return_value = {
            'results': [
                {'success': True, 'order_id': 'order_1', 'failure_reason': None},
                {'success': False, 'order_id': 'order_2', 'failure_reason': 'NOT_FOUND'}
            ]
        }
        client = self.CoinbaseClient()
        result = client.cancel_orders(order_ids=['order_1', 'order_2'])

        self.assertIsNotNone(result)
        self.assertEqual(len(result['results']), 2)
        # Check logs for both success and failure
        self.mock_logger_instance.info.assert_any_call('Order order_1 cancelled successfully.')
        self.mock_logger_instance.error.assert_any_call('Failed to cancel order order_2. Reason: NOT_FOUND')

    def test_cancel_orders_malformed_response(self):
        """Test cancel_orders with a response missing the 'results' key."""
        self.mock_rest_client_instance.cancel_orders.return_value = {'status': 'error'}
        client = self.CoinbaseClient()
        client.cancel_orders(order_ids=['order_1'])
        self.mock_logger_instance.warning.assert_called_with(
            "Cancel orders response format not as expected or indicates general failure: {'status': 'error'}"
        )

    def test_cancel_orders_invalid_input(self):
        """Test cancel_orders with invalid input (e.g., empty list)."""
        client = self.CoinbaseClient()
        with self.assertRaises(AssertionError) as cm:
            client.cancel_orders(order_ids=[])
        self.assertEqual(str(cm.exception), 'order_ids list cannot be empty.')

    def test_cancel_orders_http_error(self):
        """Test cancel_orders handles HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = 'Service Unavailable'
        http_error = HTTPError('Service Unavailable')
        http_error.response = mock_response

        self.mock_rest_client_instance.cancel_orders.side_effect = http_error
        client = self.CoinbaseClient()
        result = client.cancel_orders(order_ids=['order_1'])
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "HTTP error cancelling orders ['order_1']: 503 Service Unavailable",
            exc_info=True
        )

    def test_cancel_orders_request_exception(self):
        """Test cancel_orders handles RequestException."""
        self.mock_rest_client_instance.cancel_orders.side_effect = RequestException('Timeout')
        client = self.CoinbaseClient()
        result = client.cancel_orders(order_ids=['order_1'])
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "Request exception cancelling orders ['order_1']: Timeout",
            exc_info=True
        )

    def test_cancel_orders_unexpected_exception(self):
        """Test cancel_orders handles a generic Exception."""
        self.mock_rest_client_instance.cancel_orders.side_effect = Exception('Something broke')
        client = self.CoinbaseClient()
        result = client.cancel_orders(order_ids=['order_1'])
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while cancelling orders ['order_1']: Something broke",
            exc_info=True
        )

    def test_cancel_orders_no_results_key_success(self):
        """Test cancel_orders with a response that has success: True but no 'results' key."""
        self.mock_rest_client_instance.cancel_orders.return_value = {'success': True}
        client = self.CoinbaseClient()
        client.cancel_orders(order_ids=['order_1'])
        self.mock_logger_instance.info.assert_called_with(
            "Cancel orders request appears successful at a high level for orders: ['order_1']"
        )

    # Tests for get_order
    def test_get_order_success(self):
        """Test successful retrieval of a single order."""
        mock_order_data = {'order_id': 'test_order_1', 'status': 'FILLED'}
        mock_response = MagicMock()
        mock_response.order = mock_order_data
        self.mock_rest_client_instance.get_order.return_value = mock_response

        client = self.CoinbaseClient()
        result = client.get_order(order_id='test_order_1')

        self.assertEqual(result, mock_order_data)
        self.mock_rest_client_instance.get_order.assert_called_once_with(order_id='test_order_1')
        self.mock_logger_instance.info.assert_called_with('Successfully retrieved order test_order_1.')

    def test_get_order_not_found(self):
        """Test get_order for a non-existent order (HTTP 404)."""
        mock_http_response = MagicMock()
        mock_http_response.status_code = 404
        mock_http_response.text = 'Order not found'
        http_error = HTTPError('Not Found')
        http_error.response = mock_http_response

        self.mock_rest_client_instance.get_order.side_effect = http_error
        client = self.CoinbaseClient()
        result = client.get_order(order_id='non_existent_order')

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "HTTP error retrieving order non_existent_order: 404 Order not found",
            exc_info=True
        )

    def test_get_order_malformed_response(self):
        """Test get_order with a response missing the 'order' attribute."""
        self.mock_rest_client_instance.get_order.return_value = {'unexpected': 'data'}
        client = self.CoinbaseClient()
        result = client.get_order(order_id='test_order_1')

        self.assertIsNone(result)
        self.mock_logger_instance.warning.assert_called_with(
            "Received unexpected format for order data: <class 'dict'>"
        )

    def test_get_order_request_exception(self):
        """Test get_order handles RequestException."""
        self.mock_rest_client_instance.get_order.side_effect = RequestException('Connection failed')
        client = self.CoinbaseClient()
        result = client.get_order(order_id='test_order_1')

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "Request exception retrieving order test_order_1: Connection failed",
            exc_info=True
        )

    def test_get_order_unexpected_exception(self):
        """Test get_order handles a generic Exception."""
        self.mock_rest_client_instance.get_order.side_effect = Exception('Generic error')
        client = self.CoinbaseClient()
        result = client.get_order(order_id='test_order_1')

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An unexpected error occurred while retrieving order test_order_1: Generic error",
            exc_info=True
        )

    def test_get_order_invalid_id(self):
        """Test get_order with an invalid order_id (empty string)."""
        client = self.CoinbaseClient()
        with self.assertRaises(AssertionError) as cm:
            client.get_order(order_id='')
        self.assertEqual(str(cm.exception), 'order_id must be a non-empty string.')

    def test_get_product_candles_http_error(self):
        """Test get_product_candles handles HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        http_error = HTTPError(response=mock_response)
        self.mock_rest_client_instance.get_public_candles.side_effect = http_error
        client = self.CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "15_MINUTE")
        self.assertIsNone(candles)
        self.mock_logger_instance.error.assert_called_with(
            f"HTTP error retrieving candles for BTC-USD: {mock_response.status_code} {mock_response.text}",
            exc_info=True,
        )

    def test_get_product_candles_request_exception(self):
        """Test get_product_candles handles RequestException."""
        request_exception = RequestException("Connection timeout")
        self.mock_rest_client_instance.get_public_candles.side_effect = request_exception
        client = self.CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "15_MINUTE")
        self.assertIsNone(candles)
        self.mock_logger_instance.error.assert_called_with(
            f"Request exception retrieving candles for BTC-USD: {request_exception}",
            exc_info=True,
        )

    def test_get_product_candles_no_candles_key(self):
        """Test get_product_candles handles a response missing the 'candles' key."""
        self.mock_rest_client_instance.get_public_candles.return_value = {"data": "no candles here"}
        client = self.CoinbaseClient()
        candles = client.get_product_candles("BTC-USD", "15_MINUTE")
        self.assertIsNone(candles)
        self.mock_logger_instance.warning.assert_called_with(
            "get_product_candles for BTC-USD response format not recognized or key data missing: {'data': 'no candles here'}"
        )

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
        ]
        self.mock_logger_instance.info.assert_has_calls(calls, any_order=False)
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
        client = self.CoinbaseClient()
        with self.assertRaises(AssertionError):
            client.cancel_orders([])
        self.mock_rest_client_instance.cancel_orders.assert_not_called()


if __name__ == "__main__":
    unittest.main()
