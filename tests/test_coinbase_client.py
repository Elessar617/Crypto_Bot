"""Unit tests for the CoinbaseClient class."""


import unittest
from unittest.mock import patch, MagicMock
import uuid
from requests.exceptions import HTTPError, RequestException
from datetime import datetime, timezone, timedelta

# Now that the path is set, we can import the class to be tested
from trading.coinbase_client import CoinbaseClient  # noqa: E402


class MockResponse:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


class TestCoinbaseClient(unittest.TestCase):
    """Test suite for the CoinbaseClient."""

    def setUp(self):
        """Set up test environment for each test."""
        patcher_rest_client = patch("trading.coinbase_client.RESTClient")
        patcher_config = patch("trading.coinbase_client.config")
        patcher_logger = patch("trading.coinbase_client.logger")

        self.mock_rest_client_class = patcher_rest_client.start()
        self.mock_config_module = patcher_config.start()
        self.mock_logger_module = patcher_logger.start()

        self.addCleanup(patcher_rest_client.stop)
        self.addCleanup(patcher_config.stop)
        self.addCleanup(patcher_logger.stop)

        self.mock_logger_instance = self.mock_logger_module.get_logger.return_value
        self.mock_rest_client_instance = self.mock_rest_client_class.return_value

        self.mock_config_module.COINBASE_API_KEY = "test_api_key"
        self.mock_config_module.COINBASE_API_SECRET = "test_api_secret"  # nosec

        # Common HTTP/Request exception mocks
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        self.mock_http_error = HTTPError("Test HTTP Error", response=mock_response)
        self.mock_request_exception = RequestException("Test Request Exception")

        # Instantiate the client here, so it uses all the mocks set up above
        self.client = CoinbaseClient()

    def _test_api_call_http_error(
        self, method_name, rest_method_name, api_args, log_message
    ):
        """Helper to test HTTPError handling for a given client method."""
        getattr(self.mock_rest_client_instance, rest_method_name).side_effect = (
            self.mock_http_error
        )
        result = getattr(self.client, method_name)(**api_args)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(log_message, exc_info=True)

    def _test_api_call_request_exception(
        self, method_name, rest_method_name, api_args, log_message
    ):
        """Helper to test RequestException handling for a given client method."""
        getattr(self.mock_rest_client_instance, rest_method_name).side_effect = (
            self.mock_request_exception
        )
        result = getattr(self.client, method_name)(**api_args)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(log_message, exc_info=True)

    # --- Test Initialization ---

    def test_initialization_success(self):
        """Test successful initialization of CoinbaseClient uses config values."""
        # The client is already initialized in setUp.
        self.mock_rest_client_class.assert_called_once_with(
            api_key="test_api_key",
            api_secret="test_api_secret",  # nosec
            rate_limit_headers=True,
        )
        self.mock_logger_instance.info.assert_called_with(
            "Coinbase RESTClient initialized successfully for the live API."
        )

    def test_initialization_with_arguments(self):
        """Test successful initialization with direct arguments."""
        self.mock_rest_client_class.reset_mock()
        self.mock_logger_instance.reset_mock()

        CoinbaseClient(api_key="direct_key", api_secret="direct_secret")  # nosec
        self.mock_rest_client_class.assert_called_once_with(
            api_key="direct_key",
            api_secret="direct_secret",  # nosec
            rate_limit_headers=True,
        )
        self.mock_logger_instance.info.assert_called_with(
            "Coinbase RESTClient initialized successfully for the live API."
        )

    def test_initialization_failure(self):
        """Test initialization failure if RESTClient instantiation fails."""
        self.mock_rest_client_class.side_effect = Exception("Connection Failed")
        with self.assertRaisesRegex(
            RuntimeError, "Coinbase RESTClient initialization failed: Connection Failed"
        ):
            CoinbaseClient()
        self.mock_logger_instance.error.assert_called_with(
            "Failed to initialize Coinbase RESTClient: Connection Failed", exc_info=True
        )

    def test_initialization_no_api_key(self):
        """Test initialization fails if API key is missing."""
        self.mock_config_module.COINBASE_API_KEY = None
        with self.assertRaises(AssertionError) as cm:
            CoinbaseClient()
        self.assertEqual(str(cm.exception), "API key must be a non-empty string.")

    def test_initialization_empty_api_key(self):
        """Test initialization fails if API key is an empty string."""
        with self.assertRaises(AssertionError) as cm:
            CoinbaseClient(api_key="", api_secret="a-secret")  # nosec
        self.assertEqual(str(cm.exception), "API key must be a non-empty string.")

    def test_initialization_no_api_secret(self):
        """Test initialization fails if API secret is missing."""
        self.mock_config_module.COINBASE_API_SECRET = None
        with self.assertRaises(AssertionError) as cm:
            CoinbaseClient()
        self.assertEqual(str(cm.exception), "API secret must be a non-empty string.")

    def test_initialization_empty_api_secret(self):
        """Test initialization fails if API secret is an empty string."""
        with self.assertRaises(AssertionError) as cm:
            CoinbaseClient(api_key="an-api-key", api_secret="")  # nosec
        self.assertEqual(str(cm.exception), "API secret must be a non-empty string.")

    def test_generate_client_order_id(self):
        """Test the generation of a unique client order ID."""
        order_id = self.client._generate_client_order_id()
        self.assertIsInstance(order_id, str)
        self.assertTrue(len(order_id) > 0)

    def test_generate_client_order_id_single_char_id(self):
        """Test that a single-character ID is handled correctly."""
        test_uuid = uuid.uuid4()
        with patch("trading.coinbase_client.uuid.uuid4", return_value=test_uuid):
            client_order_id = self.client._generate_client_order_id()
            self.assertEqual(client_order_id, str(test_uuid))

    def test_generate_client_order_id_uuid_error(self):
        """Test that an error is raised when uuid.uuid4 returns a non-UUID type."""
        with patch("trading.coinbase_client.uuid.uuid4", return_value="not-a-uuid"):
            try:
                self.client._generate_client_order_id()
                self.fail("AssertionError was not raised by _generate_client_order_id")
            except AssertionError as e:
                expected_msg = "uuid.uuid4() did not return a UUID object."
                self.assertEqual(str(e), expected_msg)

    def test_generate_client_order_id_empty_string(self):
        """Test that an error is raised when the generated order_id is an empty string."""
        mock_uuid = MagicMock(spec=uuid.UUID)
        mock_uuid.__str__.return_value = ""

        with patch("trading.coinbase_client.uuid.uuid4", return_value=mock_uuid):
            try:
                self.client._generate_client_order_id()
                self.fail("AssertionError was not raised for empty client_order_id")
            except AssertionError as e:
                self.assertEqual(str(e), "Generated client_order_id is empty.")

    def test_generate_client_order_id_length_one(self):
        """Test that _generate_client_order_id handles a one-character string."""
        mock_uuid = MagicMock(spec=uuid.UUID)
        mock_uuid.__str__.return_value = "a"

        with patch("trading.coinbase_client.uuid.uuid4", return_value=mock_uuid):
            order_id = self.client._generate_client_order_id()
            self.assertEqual(order_id, "a")

    # --- Test _handle_api_response ---

    def test_handle_api_response_with_to_dict_object(self):
        """Test _handle_api_response with an object that has a to_dict method."""

        # Create a spec class to constrain the mock's attributes
        class ToDictSpec:
            def to_dict(self):
                pass  # pragma: no cover

        # Create a mock object with a to_dict method using the spec
        mock_response = MagicMock(spec=ToDictSpec)
        mock_response.to_dict.return_value = {"key": "value"}

        # The mock object should not be an instance of dict or str
        self.assertNotIsInstance(mock_response, dict)
        self.assertNotIsInstance(mock_response, str)

        result = self.client._handle_api_response(mock_response)

        # Assert that to_dict was called and the correct dict is returned
        mock_response.to_dict.assert_called_once()
        self.assertEqual(result, {"key": "value"})

    # --- Test get_accounts ---

    def test_get_accounts_no_client(self):
        """Test get_accounts returns None if the RESTClient is not initialized."""
        self.client.client = None  # Manually set client to None after initialization

        result = self.client.get_accounts()

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_accounts: RESTClient not initialized.", exc_info=True
        )

    def test_get_accounts_success(self):
        """Test successful retrieval of accounts."""
        mock_accounts = [{"id": "1", "name": "BTC Wallet", "balance": "1.0"}]
        self.mock_rest_client_instance.get_accounts.return_value = {
            "accounts": mock_accounts
        }
        result = self.client.get_accounts()
        self.assertEqual(result, mock_accounts)
        self.mock_logger_instance.debug.assert_called_with(
            "Attempting to retrieve accounts."
        )
        self.mock_logger_instance.info.assert_called_with(
            f"Successfully retrieved {len(mock_accounts)} accounts."
        )
        self.mock_rest_client_instance.get_accounts.assert_called_once()

    def test_get_accounts_error_handling(self):
        """Test all error handling for get_accounts."""
        self.mock_logger_instance.reset_mock()
        log_message = f"An error occurred in get_accounts: {self.mock_http_error}"
        self._test_api_call_http_error("get_accounts", "get_accounts", {}, log_message)

        self.mock_logger_instance.reset_mock()
        log_message = (
            f"An error occurred in get_accounts: {self.mock_request_exception}"
        )
        self._test_api_call_request_exception(
            "get_accounts", "get_accounts", {}, log_message
        )

    def test_get_accounts_malformed_response_not_dict(self):
        """Test get_accounts handles a response that is not a dictionary."""
        self.mock_rest_client_instance.get_accounts.return_value = "not_a_dict"
        result = self.client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_accounts: get_accounts response should be a dictionary.",
            exc_info=True,
        )

    def test_get_accounts_malformed_response_no_accounts_key(self):
        """Test get_accounts handles a response missing the 'accounts' key."""
        self.mock_rest_client_instance.get_accounts.return_value = {"data": []}
        result = self.client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_accounts: 'accounts' key is missing in the response.",
            exc_info=True,
        )

    def test_get_accounts_malformed_response_accounts_not_list(self):
        """Test get_accounts handles a response where 'accounts' is not a list."""
        self.mock_rest_client_instance.get_accounts.return_value = {
            "accounts": "not_a_list"
        }
        result = self.client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_accounts: 'accounts' key should be a list.",
            exc_info=True,
        )

    def test_get_accounts_invalid_json_response(self):
        """Test get_accounts handles a response that is an invalid JSON string."""
        invalid_json_string = "{'bad': 'json'"
        self.mock_rest_client_instance.get_accounts.return_value = invalid_json_string
        result = self.client.get_accounts()
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_any_call(
            "Failed to decode JSON from response: %s", invalid_json_string
        )
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_accounts: get_accounts response should be a dictionary.",
            exc_info=True,
        )

    # --- Test get_public_candles ---

    def test_get_public_candles_no_client(self):
        """Test get_public_candles returns None if the RESTClient is not initialized."""
        self.client.client = None  # Manually set client to None

        result = self.client.get_public_candles(
            "BTC-USD", "start", "end", "granularity"
        )

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_public_candles for BTC-USD: RESTClient not initialized.",
            exc_info=True,
        )

    def test_get_public_candles_empty_product_id(self):
        """Test get_public_candles returns None if product_id is empty."""
        result = self.client.get_public_candles("", "start", "end", "granularity")

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_public_candles for : Product ID must be a non-empty string.",
            exc_info=True,
        )

    def test_get_public_candles_success(self):
        """Test successful retrieval of product candles."""
        self.mock_logger_instance.reset_mock()
        mock_response_dict = {"candles": [{"open": "100"}]}
        self.mock_rest_client_instance.get_product_candles.return_value = mock_response_dict
        result = self.client.get_public_candles(
            product_id="BTC-USD", start="2023-01-01", end="2023-01-02", granularity="ONE_HOUR"
        )
        self.assertEqual(result, [{"open": "100"}])
        self.mock_rest_client_instance.get_product_candles.assert_called_once_with(
            product_id="BTC-USD",
            start="2023-01-01",
            end="2023-01-02",
            granularity="ONE_HOUR",
        )
        self.mock_logger_instance.info.assert_called_once_with(
            "Successfully retrieved 1 candles for BTC-USD."
        )

    def test_get_public_candles_error_handling(self):
        """Test all error handling for get_public_candles."""
        self.mock_logger_instance.reset_mock()
        log_message = f"An error occurred in get_public_candles for BTC-USD: {self.mock_http_error}"
        self._test_api_call_http_error(
            "get_public_candles", "get_product_candles", {"product_id": "BTC-USD", "granularity": "ONE_MINUTE"}, log_message
        )

        self.mock_logger_instance.reset_mock()
        log_message = f"An error occurred in get_public_candles for BTC-USD: {self.mock_request_exception}"
        self._test_api_call_request_exception(
            "get_public_candles", "get_product_candles", {"product_id": "BTC-USD", "granularity": "ONE_MINUTE"}, log_message
        )

    def test_get_public_candles_malformed_response_candles_not_list(self):
        """Test get_public_candles handles a response where 'candles' is not a list."""
        self.mock_logger_instance.reset_mock()
        mock_response_dict = {"candles": "not-a-list"}
        self.mock_rest_client_instance.get_product_candles.return_value = mock_response_dict
        result = self.client.get_public_candles(
            product_id="BTC-USD", granularity="ONE_MINUTE"
        )
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in get_public_candles for BTC-USD: 'candles' key must be a list.",
            exc_info=True,
        )

    # --- Test get_product ---

    def test_get_product_no_client(self):
        """Test get_product returns None if the RESTClient is not initialized."""
        self.mock_logger_instance.reset_mock()
        self.client.client = None
        result = self.client.get_product("BTC-USD")

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_product for BTC-USD: RESTClient not initialized.",
            exc_info=True,
        )

    def test_get_product_success(self):
        """Test successful retrieval of a single product."""
        mock_response = {"id": "BTC-USD"}
        self.mock_rest_client_instance.get_product.return_value = mock_response
        result = self.client.get_product("BTC-USD")
        self.assertEqual(result, {"id": "BTC-USD"})
        self.mock_rest_client_instance.get_product.assert_called_once_with(
            product_id="BTC-USD"
        )

    def test_get_product_error_handling(self):
        """Test the generic exception handling for get_product."""
        self.mock_logger_instance.reset_mock()
        product_id = "BTC-USD"
        # Simulate a non-HTTP, non-RequestException error
        error_message = "A wild error appears!"
        self.mock_rest_client_instance.get_product.side_effect = Exception(error_message)

        result = self.client.get_product(product_id=product_id)

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            f"An error occurred in get_product for {product_id}: {error_message}",
            exc_info=True,
        )
        # Ensure no retries were attempted for an unexpected error
        self.assertEqual(self.mock_rest_client_instance.get_product.call_count, 1)

    @patch("trading.coinbase_client.time.sleep", return_value=None)
    def test_get_product_error_handling_retry(self, mock_sleep):
        """Test error handling and retry logic in get_product."""
        self.mock_rest_client_instance.get_product.side_effect = HTTPError("API Error")

        result = self.client.get_product(product_id="BTC-USD")

        self.assertIsNone(result)
        self.assertEqual(self.mock_rest_client_instance.get_product.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        self.mock_logger_instance.warning.assert_called()
        self.mock_logger_instance.error.assert_called_once()

    def test_limit_order_no_client(self):
        """Test limit_order returns None if the RESTClient is not initialized."""
        self.client.client = None

        result = self.client.limit_order(
            side="BUY", product_id="BTC-USD", base_size="1", limit_price="10000"
        )

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in limit_order for BTC-USD: RESTClient not initialized.",
            exc_info=True,
        )

    def test_limit_order_invalid_side(self):
        """Test that limit_order logs an error for an invalid side."""
        result = self.client.limit_order(
            side="INVALID", product_id="BTC-USD", base_size="1", limit_price="10000"
        )
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in limit_order for BTC-USD: Side must be 'BUY' or 'SELL'.",
            exc_info=True,
        )

    def test_limit_order_empty_product_id(self):
        """Test that limit_order logs an error for an empty product_id."""
        result = self.client.limit_order(
            side="BUY", product_id="", base_size="1", limit_price="10000"
        )
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in limit_order for : Product ID must be a non-empty string.",
            exc_info=True,
        )

    def test_limit_order_success(self):
        """Test successful placement of a limit order."""
        self.mock_rest_client_instance.limit_order.return_value = {
            "success": True,
            "order_id": "order-123",
        }
        response = self.client.limit_order(
            side="BUY", product_id="BTC-USD", base_size="1", limit_price="10000"
        )
        self.assertIsNotNone(response)
        self.assertTrue(response["success"])
        self.assertEqual(response["order_id"], "order-123")
        self.mock_logger_instance.info.assert_called_with(
            "Successfully placed buy order for BTC-USD. Order ID: order-123"
        )
        # Check that limit_order was called on the RESTClient with correct args
        self.mock_rest_client_instance.limit_order.assert_called_once()
        call_args, call_kwargs = self.mock_rest_client_instance.limit_order.call_args
        self.assertEqual(call_kwargs.get("side"), "BUY")
        self.assertEqual(call_kwargs.get("product_id"), "BTC-USD")

    def test_limit_order_failure(self):
        """Test failed placement of a limit order with failure_reason."""
        self.mock_rest_client_instance.limit_order.return_value = {
            "success": False,
            "failure_reason": "INSUFFICIENT_FUNDS",
        }
        response = self.client.limit_order(
            side="BUY", product_id="BTC-USD", base_size="1", limit_price="10000"
        )
        self.assertIsNotNone(response)
        self.assertFalse(response["success"])
        self.assertEqual(response["failure_reason"], "INSUFFICIENT_FUNDS")
        self.mock_logger_instance.error.assert_called_with(
            "Failed to place buy order for BTC-USD. Reason: INSUFFICIENT_FUNDS"
        )

    def test_limit_order_failure_with_error_response(self):
        """Test order failure with a detailed error_response."""
        self.mock_rest_client_instance.limit_order.return_value = {
            "success": False,
            "error_response": {"message": "Insufficient funds"},
        }
        response = self.client.limit_order(
            side="BUY", product_id="BTC-USD", base_size="1", limit_price="10000"
        )
        self.assertIsNotNone(response)
        self.assertFalse(response["success"])
        self.mock_logger_instance.error.assert_called_with(
            "Failed to place buy order for BTC-USD. Reason: Insufficient funds"
        )

    def test_limit_order_failure_unknown_error(self):
        """Test order failure with no specific reason given."""
        self.mock_rest_client_instance.limit_order.return_value = {"success": False}
        response = self.client.limit_order(
            side="BUY", product_id="BTC-USD", base_size="1", limit_price="10000"
        )
        self.assertIsNotNone(response)
        self.assertFalse(response["success"])
        self.mock_logger_instance.error.assert_called_with(
            "Failed to place buy order for BTC-USD. Reason: Unknown reason"
        )

    # ... rest of the code remains the same ...
        """Test get_order handles a response that is not a dictionary."""
        self.mock_rest_client_instance.get_order.return_value = "not_a_dict"
        order_id = "some-order-id"
        result = self.client.get_order(order_id)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in get_order for {order_id}: get_order response should be a dictionary.",
            exc_info=True,
        )

    def test_get_order_malformed_response_no_order_key(self):
        """Test get_order handles a response missing the 'order' key."""
        self.mock_rest_client_instance.get_order.return_value = {"data": {}}
        order_id = "some-order-id"
        result = self.client.get_order(order_id)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in get_order for {order_id}: 'order' key missing in response.",
            exc_info=True,
        )

    def test_get_order_malformed_response_order_not_dict(self):
        """Test get_order handles a response where 'order' is not a dict."""
        self.mock_rest_client_instance.get_order.return_value = {"order": "not_a_dict"}
        order_id = "some-order-id"
        result = self.client.get_order(order_id)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in get_order for {order_id}: 'order' must be a dictionary.",
            exc_info=True,
        )

    # --- Test cancel_orders ---

    def test_cancel_orders_no_client(self):
        """Test cancel_orders returns None if the RESTClient is not initialized."""
        self.client.client = None
        order_ids = ["some-order-id"]
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: RESTClient not initialized.",
            exc_info=True,
        )

    def test_cancel_orders_empty_order_ids(self):
        """Test cancel_orders with an empty order_ids list."""
        order_ids = []
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in cancel_orders for []: order_ids must be a non-empty list.",
            exc_info=True,
        )

    def test_cancel_orders_success(self):
        """Test successful cancellation of orders."""
        order_ids = ["order-123"]
        response_data = {
            "results": [
                {
                    "success": True,
                    "order_id": "order-123",
                    "failure_reason": None,
                }
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = response_data
        result = self.client.cancel_orders(order_ids=order_ids)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["success"])

        # Check for both the overall success message and the individual success message
        self.mock_logger_instance.info.assert_any_call(
            f"Successfully processed cancel orders request for {order_ids}."
        )
        self.mock_logger_instance.info.assert_any_call(
            "Successfully cancelled order order-123."
        )

    def test_cancel_orders_error_handling(self):
        """Test all error handling for cancel_orders."""
        order_ids = ["some-order-id"]
        # Test HTTPError
        self.mock_rest_client_instance.cancel_orders.side_effect = self.mock_http_error
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: {self.mock_http_error}",
            exc_info=True,
        )

        # Test RequestException
        self.mock_rest_client_instance.cancel_orders.side_effect = (
            self.mock_request_exception
        )
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: {self.mock_request_exception}",
            exc_info=True,
        )

        # Test Unexpected Error
        self.mock_rest_client_instance.cancel_orders.side_effect = Exception("Chaos")
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: Chaos",
            exc_info=True,
        )

    def test_cancel_orders_malformed_response_not_dict(self):
        """Test cancel_orders handles a response that is not a dictionary."""
        self.mock_rest_client_instance.cancel_orders.return_value = "not_a_dict"
        order_ids = ["some-order-id"]
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: cancel_orders response should be a dictionary.",
            exc_info=True,
        )

    def test_cancel_orders_malformed_response_no_results_key(self):
        """Test cancel_orders handles a response missing the 'results' key."""
        self.mock_rest_client_instance.cancel_orders.return_value = {"data": {}}
        order_ids = ["some-order-id"]
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: 'results' key missing in response.",
            exc_info=True,
        )

    def test_cancel_orders_malformed_response_results_not_list(self):
        """Test cancel_orders handles a response where 'results' is not a list."""
        self.mock_rest_client_instance.cancel_orders.return_value = {
            "results": "not_a_list"
        }
        order_ids = ["some-order-id"]
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: 'results' key should be a list.",
            exc_info=True,
        )

    def test_limit_order_malformed_response_not_dict(self):
        """Test limit_order handles a response that is not a dictionary."""
        self.mock_rest_client_instance.limit_order.return_value = "not_a_dict"
        result = self.client.limit_order(
            side="BUY", product_id="BTC-USD", base_size="1", limit_price="10000"
        )
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            "An error occurred in limit_order for BTC-USD: limit_order response should be a dictionary.",
            exc_info=True,
        )

    def test_cancel_orders_failure_with_error_response(self):
        """Test failure with error_response and message."""
        response_data = {
            "results": [
                {
                    "success": False,
                    "order_id": "order-456",
                    "error_response": {"message": "Insufficient funds"},
                }
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = response_data
        self.client.cancel_orders(order_ids=["order-456"])
        self.mock_logger_instance.error.assert_called_with(
            "Failed to cancel order order-456. Reason: Insufficient funds"
        )

    def test_cancel_orders_failure_with_failure_reason(self):
        """Test failure with failure_reason."""
        response_data = {
            "results": [
                {
                    "success": False,
                    "order_id": "order-456",
                    "failure_reason": "Order not found",
                }
            ]
        }
        self.mock_rest_client_instance.cancel_orders.return_value = response_data
        self.client.cancel_orders(order_ids=["order-456"])
        self.mock_logger_instance.error.assert_called_with(
            "Failed to cancel order order-456. Reason: Order not found"
        )

    def test_cancel_orders_failure_unknown_reason(self):
        """Test failure with unknown reason."""
        response_data = {"results": [{"success": False, "order_id": "order-456"}]}
        self.mock_rest_client_instance.cancel_orders.return_value = response_data
        self.client.cancel_orders(order_ids=["order-456"])
        self.mock_logger_instance.error.assert_called_with(
            "Failed to cancel order order-456. Reason: Unknown reason"
        )

    def test_cancel_orders_malformed_response_results_item_not_dict(self):
        """Test cancel_orders handles a response where an item in 'results' is not a dict."""
        self.mock_rest_client_instance.cancel_orders.return_value = {
            "results": ["not_a_dict"]
        }
        order_ids = ["order-123"]
        result = self.client.cancel_orders(order_ids)
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_with(
            f"An error occurred in cancel_orders for {order_ids}: Each item in 'results' should be a dictionary.",
            exc_info=True,
        )

    def test_get_public_candles_start_only(self):
        """Test get_public_candles with only start time provided."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start_time = mock_now - timedelta(hours=1)
            self.client.get_public_candles(
                product_id="BTC-USD", start=start_time, granularity="ONE_MINUTE"
            )

            delta = timedelta(minutes=1) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="ONE_MINUTE",
            )

    def test_get_public_candles_end_only(self):
        """Test get_public_candles with only end time provided."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            end_time = mock_now
            self.client.get_public_candles(
                product_id="BTC-USD", end=end_time, granularity="ONE_MINUTE"
            )

            delta = timedelta(minutes=1) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="ONE_MINUTE",
            )


    def test_get_public_candles_five_minute_granularity(self):
        """Test get_public_candles with FIVE_MINUTE granularity and no start/end."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            self.client.get_public_candles(
                product_id="BTC-USD", granularity="FIVE_MINUTE"
            )

            delta = timedelta(minutes=5) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="FIVE_MINUTE",
            )

    def test_get_public_candles_fifteen_minute_granularity(self):
        """Test get_public_candles with FIFTEEN_MINUTE granularity and no start/end."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            self.client.get_public_candles(
                product_id="BTC-USD", granularity="FIFTEEN_MINUTE"
            )

            delta = timedelta(minutes=15) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="FIFTEEN_MINUTE",
            )

    def test_get_public_candles_thirty_minute_granularity(self):
        """Test get_public_candles with THIRTY_MINUTE granularity and no start/end."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            self.client.get_public_candles(
                product_id="BTC-USD", granularity="THIRTY_MINUTE"
            )

            delta = timedelta(minutes=30) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="THIRTY_MINUTE",
            )

    def test_get_public_candles_one_hour_granularity(self):
        """Test get_public_candles with ONE_HOUR granularity and no start/end."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            self.client.get_public_candles(
                product_id="BTC-USD", granularity="ONE_HOUR"
            )

            delta = timedelta(hours=1) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="ONE_HOUR",
            )

    def test_get_public_candles_two_hour_granularity(self):
        """Test get_public_candles with TWO_HOUR granularity and no start/end."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            self.client.get_public_candles(
                product_id="BTC-USD", granularity="TWO_HOUR"
            )

            delta = timedelta(hours=2) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="TWO_HOUR",
            )

    def test_get_public_candles_six_hour_granularity(self):
        """Test get_public_candles with SIX_HOUR granularity and no start/end."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            self.client.get_public_candles(
                product_id="BTC-USD", granularity="SIX_HOUR"
            )

            delta = timedelta(hours=6) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="SIX_HOUR",
            )

    def test_get_public_candles_one_day_granularity(self):
        """Test get_public_candles with ONE_DAY granularity and no start/end."""
        with patch("trading.coinbase_client.datetime") as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            self.client.get_public_candles(
                product_id="BTC-USD", granularity="ONE_DAY"
            )

            delta = timedelta(days=1) * 300
            expected_start = int((mock_now - delta).timestamp())
            expected_end = int(mock_now.timestamp())

            self.mock_rest_client_instance.get_product_candles.assert_called_with(
                product_id="BTC-USD",
                start=str(expected_start),
                end=str(expected_end),
                granularity="ONE_DAY",
            )

    def test_get_public_candles_response_not_a_dict(self):
        """Test get_public_candles when the API response is not a dictionary."""
        self.mock_rest_client_instance.get_product_candles.return_value = "not a dict"

        result = self.client.get_public_candles(
            product_id="BTC-USD",
            granularity="ONE_MINUTE",
            start="1672531200",
            end="1672531260",
        )

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_public_candles for BTC-USD: Response was not a dictionary.",
            exc_info=True,
        )

    def test_get_product_book_no_client(self):
        """Test get_product_book returns None if the RESTClient is not initialized."""
        # This is a bit artificial, as __init__ would raise an error,
        # but it's necessary to test the assertion directly.
        self.client.client = None
        result = self.client.get_product_book(product_id="BTC-USD")
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_product_book for BTC-USD: RESTClient not initialized.",
            exc_info=True,
        )

    def test_get_product_book_empty_product_id(self):
        """Test get_product_book with an empty product_id."""
        result = self.client.get_product_book(product_id="")
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_product_book for : Product ID must be a non-empty string.",
            exc_info=True,
        )

    def test_get_product_book_api_returns_none(self):
        """Test get_product_book when the API call returns None."""
        self.mock_rest_client_instance.get_product_book.return_value = None
        result = self.client.get_product_book(product_id="BTC-USD")
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_product_book for BTC-USD: get_product_book response should be a dictionary.",
            exc_info=True,
        )

    def test_get_product_book_success(self):
        """Test successful retrieval of the product book."""
        expected_pricebook = {"bids": [["100", "10"]], "asks": [["101", "10"]]}
        mock_response = {"pricebook": expected_pricebook}
        self.mock_rest_client_instance.get_product_book.return_value = mock_response

        result = self.client.get_product_book(product_id="BTC-USD")

        self.assertEqual(result, expected_pricebook)
        self.mock_rest_client_instance.get_product_book.assert_called_once_with(
            product_id="BTC-USD", limit=None
        )
        self.mock_logger_instance.info.assert_called_with(
            "Successfully retrieved order book for BTC-USD."
        )

    def test_get_product_book_missing_pricebook_key(self):
        """Test get_product_book when 'pricebook' key is missing in the response."""
        mock_response = {"not_pricebook": {}}
        self.mock_rest_client_instance.get_product_book.return_value = mock_response

        result = self.client.get_product_book(product_id="BTC-USD")

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_product_book for BTC-USD: 'pricebook' key missing in response.",
            exc_info=True,
        )

    def test_get_product_book_pricebook_not_a_dict(self):
        """Test get_product_book when 'pricebook' value is not a dictionary."""
        mock_response = {"pricebook": ["not a dict"]}
        self.mock_rest_client_instance.get_product_book.return_value = mock_response

        result = self.client.get_product_book(product_id="BTC-USD")

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_product_book for BTC-USD: 'pricebook' must be a dictionary.",
            exc_info=True,
        )

    @patch("trading.coinbase_client.time.sleep")
    def test_get_product_retry_logic(self, mock_sleep):
        """Test the retry logic in get_product, including the sleep delay."""
        mock_success_response = {"product_id": "BTC-USD", "price": "50000"}
        self.mock_rest_client_instance.get_product.side_effect = [
            self.mock_http_error,
            mock_success_response,
        ]

        result = self.client.get_product(product_id="BTC-USD")

        self.assertEqual(result, mock_success_response)
        self.assertEqual(self.mock_rest_client_instance.get_product.call_count, 2)
        mock_sleep.assert_called_once_with(5)
        self.mock_logger_instance.warning.assert_called_with(
            f"HTTP error on attempt 1/3 for BTC-USD: {self.mock_http_error}. Retrying in 5s..."
        )

    def test_get_product_empty_product_id(self):
        """Test get_product with an empty product_id."""
        result = self.client.get_product(product_id="")

        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_product for : Product ID must be a non-empty string.",
            exc_info=True,
        )

    def test_get_product_response_not_a_dict(self):
        """Test get_product when the API response is not a dictionary."""
        self.mock_rest_client_instance.get_product.return_value = "not a dict"

        result = self.client.get_product(product_id="BTC-USD")

        self.assertIsNone(result)
        # This assertion is key to killing mutant #96
        self.mock_logger_instance.error.assert_any_call(
            "An error occurred in get_product for BTC-USD: get_product response should be a dictionary.",
            exc_info=True,
        )

    @patch("trading.coinbase_client.time.sleep")
    def test_get_product_all_retries_fail(self, mock_sleep):
        """Test get_product when all retry attempts fail."""
        self.mock_rest_client_instance.get_product.side_effect = self.mock_http_error

        result = self.client.get_product(product_id="BTC-USD")

        self.assertIsNone(result)
        self.assertEqual(self.mock_rest_client_instance.get_product.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        self.mock_logger_instance.error.assert_called_once_with(
            "Failed to fetch product details for BTC-USD after 3 attempts.",
            exc_info=True,
        )

    def test_limit_order_buy_with_client_order_id(self):
        """Test limit_order_buy with a provided client_order_id."""
        custom_order_id = "my-custom-buy-order-id-123"
        mock_response = {"success": True, "order_id": "12345"}
        self.mock_rest_client_instance.limit_order.return_value = mock_response

        result = self.client.limit_order_buy(
            product_id="BTC-USD",
            base_size="0.01",
            limit_price="50000",
            client_order_id=custom_order_id,
        )

        self.assertEqual(result, mock_response)
        self.mock_rest_client_instance.limit_order.assert_called_once_with(
            side="BUY",
            client_order_id=custom_order_id,
            product_id="BTC-USD",
            order_configuration={
                "limit_limit_gtc": {
                    "base_size": "0.01",
                    "limit_price": "50000",
                    "post_only": False,
                }
            },
        )

    def test_limit_order_sell_with_client_order_id(self):
        """Test limit_order_sell with a provided client_order_id."""
        custom_order_id = "my-custom-sell-order-id-456"
        mock_response = {"success": True, "order_id": "67890"}
        self.mock_rest_client_instance.limit_order.return_value = mock_response

        result = self.client.limit_order_sell(
            product_id="BTC-USD",
            base_size="0.01",
            limit_price="51000",
            client_order_id=custom_order_id,
        )

        self.assertEqual(result, mock_response)
        self.mock_rest_client_instance.limit_order.assert_called_once_with(
            side="SELL",
            client_order_id=custom_order_id,
            product_id="BTC-USD",
            order_configuration={
                "limit_limit_gtc": {
                    "base_size": "0.01",
                    "limit_price": "51000",
                    "post_only": False,
                }
            },
        )

    def test_limit_order_buy_generates_client_order_id(self):
        """Test limit_order_buy generates a client_order_id if not provided."""
        mock_response = {"success": True, "order_id": "12345"}
        self.mock_rest_client_instance.limit_order.return_value = mock_response

        # Call without client_order_id
        self.client.limit_order_buy(
            product_id="BTC-USD",
            base_size="0.01",
            limit_price="50000",
        )

        # Inspect the arguments it was called with
        _args, call_kwargs = self.mock_rest_client_instance.limit_order.call_args

        # Assert that a client_order_id was generated and is a valid UUID string
        generated_id = call_kwargs.get("client_order_id")
        self.assertIsInstance(generated_id, str)
        self.assertTrue(len(generated_id) > 0)

        # Verify it's a valid UUID
        try:
            uuid.UUID(generated_id)
        except ValueError:
            self.fail("Generated client_order_id is not a valid UUID")

    def test_get_order_rest_client_not_initialized(self):
        """Test get_order logs an error if RESTClient is not initialized."""
        self.client.client = None
        result = self.client.get_order("some-order-id")
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_order for some-order-id: RESTClient not initialized.",
            exc_info=True,
        )

    def test_get_order_with_empty_order_id(self):
        """Test get_order logs an error if order_id is empty."""
        result = self.client.get_order("")
        self.assertIsNone(result)
        self.mock_logger_instance.error.assert_called_once_with(
            "An error occurred in get_order for : Order ID must be a non-empty string.",
            exc_info=True,
        )


if __name__ == "__main__":
    unittest.main()
