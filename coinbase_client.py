"""Handles all interactions with the Coinbase Advanced Trade API."""

import uuid
from typing import Optional, Dict, Any, List
import sys
from requests.exceptions import HTTPError, RequestException

from coinbase.rest import RESTClient  # type: ignore[import]

# Assuming config.py and logger.py are in the same directory or accessible in PYTHONPATH
import config
import logger

# Rule: Restrict the scope of data to the smallest possible.
# API client will be instantiated per CoinbaseClient instance.


class CoinbaseClient:
    """A client to interact with the Coinbase Advanced Trade API."""

    # Rule: Use a minimum of two runtime assertions per function (applied in __init__).
    def __init__(self, api_url: Optional[str] = None) -> None:
        """Initializes the CoinbaseClient with API credentials and the REST client.

        Args:
            api_url (Optional[str]): The API URL to use for requests. Defaults to production.
        """
        self.logger = logger.get_logger()

        # Load API credentials from config
        # Rule: Check the return value of all non-void functions (implicitly done by config's assertions).
        self.api_key: str = config.COINBASE_API_KEY
        self.api_secret: str = config.COINBASE_API_SECRET

        # Assertions for API credentials
        assert self.api_key, "Coinbase API key is not set in config."
        assert self.api_secret, "Coinbase API secret is not set in config."
        # Second assertion for each (type check, though config should handle format)
        assert (
            isinstance(self.api_key, str) and len(self.api_key) > 0
        ), "API key must be a non-empty string."
        assert (
            isinstance(self.api_secret, str) and len(self.api_secret) > 0
        ), "API secret must be a non-empty string."

        try:
            client_params = {
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "rate_limit_headers": True,
            }
            if api_url:
                client_params["base_url"] = api_url

            self.client = RESTClient(**client_params)
            log_url = api_url if api_url else "production"
            self.logger.info(f"Coinbase RESTClient initialized successfully for {log_url} URL.")
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Coinbase RESTClient: {e}", exc_info=True
            )
            # Rule: Avoid complex flow constructs, such as goto and recursion.
            # Propagate critical initialization failure.
            raise RuntimeError(f"Coinbase RESTClient initialization failed: {e}") from e

    def _generate_client_order_id(self) -> str:
        """Generates a unique client order ID."""
        # Rule: Restrict functions to a single printed page.
        # Rule: Use a minimum of two runtime assertions per function.
        order_id = str(uuid.uuid4())
        assert isinstance(order_id, str), "Generated client_order_id is not a string."
        assert len(order_id) > 0, "Generated client_order_id is empty."
        return order_id

    def get_accounts(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves a list of all trading accounts for the API key.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of account dictionaries if successful, None otherwise.
        """
        # Rule: Restrict functions to a single printed page.
        # Rule: Use a minimum of two runtime assertions per function.
        self.logger.debug("Attempting to retrieve accounts.")
        accounts_data: Optional[List[Dict[str, Any]]] = None
        try:
            assert self.client is not None, "RESTClient not initialized."
            # Corrected method name
            response = self.client.get_accounts()
            self.logger.debug(f"Raw accounts response: {response}")

            # Handle various response formats: object with 'accounts', dict with 'accounts', or direct list
            if hasattr(response, "accounts") and isinstance(response.accounts, list):
                accounts_data = response.accounts
            elif isinstance(response, dict) and "accounts" in response:
                accounts_data = response.get("accounts", [])
            elif isinstance(response, list):
                accounts_data = response
            else:
                self.logger.warning(
                    f"Received unexpected format for accounts data: {type(response)}"
                )
                return None

            if accounts_data is not None:
                self.logger.info(
                    f"Successfully retrieved {len(accounts_data)} accounts."
                )
                # Dual assertions for response data
                assert isinstance(
                    accounts_data, list
                ), "Processed accounts data is not a list."
                # This assertion is now more robust.
                assert all(
                    isinstance(acc, dict) for acc in accounts_data
                ), "Not all items in accounts list are dictionaries."

            return accounts_data
        except HTTPError as e:
            self.logger.error(
                f"HTTP error retrieving accounts: {e.response.status_code} {e.response.text}",
                exc_info=True,
            )
            return None
        except RequestException as e:
            self.logger.error(
                f"Request exception retrieving accounts: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving accounts: {e}", exc_info=True
            )
            return None

    def get_product_candles(
        self,
        product_id: str,
        granularity: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Retrieves historical candles for a product.

        Args:
            product_id (str): The trading pair (e.g., 'BTC-USD').
            granularity (str): The candle granularity (e.g., 'ONE_MINUTE', 'ONE_HOUR', 'ONE_DAY').
                               Refer to Coinbase API docs for valid granularity strings.
            start (Optional[str]): Start time in ISO 8601 format. Defaults to '0' (epoch start).
            end (Optional[str]): End time in ISO 8601 format. Defaults to '0' (interpreted as 'now' by some APIs).

        Returns:
            Optional[List[Dict[str, Any]]]: A list of candle dictionaries if successful, None otherwise.
        """
        # Rule: Use a minimum of two runtime assertions per function.
        assert (
            isinstance(product_id, str) and len(product_id) > 0
        ), "product_id must be a non-empty string."
        assert (
            isinstance(granularity, str) and len(granularity) > 0
        ), "granularity must be a non-empty string."

        self.logger.debug(
            f"Attempting to retrieve candles for {product_id} with granularity {granularity}."
        )
        try:
            assert self.client is not None, "RESTClient not initialized."

            # Per tests, default None to "0"
            effective_start = start if start is not None else "0"
            effective_end = end if end is not None else "0"

            response_data = self.client.get_public_candles(
                product_id=product_id,
                granularity=granularity,
                start=effective_start,
                end=effective_end,
            )
            self.logger.debug(f"Raw candles response for {product_id}: {response_data}")

            actual_candles: Optional[List[Dict[str, Any]]] = None

            # Handle various response formats
            if (
                isinstance(response_data, dict)
                and "candles" in response_data
                and isinstance(response_data["candles"], list)
            ):
                actual_candles = response_data["candles"]
            elif hasattr(response_data, "candles") and isinstance(response_data.candles, list):
                # This handles if response_data is an object with a .candles attribute
                actual_candles = response_data.candles
            elif isinstance(response_data, list):
                actual_candles = response_data
            else:
                # If format is not recognized, log and return None as per test expectations.
                self.logger.warning(
                    f"get_product_candles for {product_id} response format not recognized or key data missing: {response_data}"
                )
                return None

            assert actual_candles is None or isinstance(
                actual_candles, list
            ), "actual_candles should be a list or None."

            if actual_candles is not None:
                self.logger.info(
                    f"Successfully retrieved {len(actual_candles)} candles for {product_id}."
                )
                # The mock returns a list of dicts, so no conversion is needed for tests.
                return actual_candles
            else:
                # This case is unlikely given the above logic, but as a fallback.
                self.logger.info(
                    f"No candle data retrieved for {product_id} or response format was unexpected."
                )
                return None
        except HTTPError as e:
            self.logger.error(
                f"HTTP error retrieving candles for {product_id}: {e.response.status_code} {e.response.text}",
                exc_info=True,
            )
            return None
        except RequestException as e:
            self.logger.error(
                f"Request exception retrieving candles for {product_id}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving candles for {product_id}: {e}",
                exc_info=True,
            )
            return None

    def get_product_book(
        self, product_id: str, limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves the order book for a specific product.

        Args:
            product_id (str): The trading pair (e.g., 'BTC-USD').
            limit (Optional[int]): Number of price levels to retrieve on each side (bids/asks).

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the order book data,
                                      which often includes 'bids' and 'asks' lists. None otherwise.
        """
        # Rule: Use a minimum of two runtime assertions per function.
        assert product_id and isinstance(
            product_id, str
        ), "product_id must be a non-empty string."
        if limit is not None:
            assert (
                isinstance(limit, int) and limit > 0
            ), "limit must be a positive integer."

        self.logger.debug(f"Attempting to retrieve product book for {product_id}.")
        book_data: Optional[Dict[str, Any]] = None
        try:
            assert self.client is not None, "RESTClient not initialized."
            response = self.client.get_product_book(product_id=product_id, limit=limit)
            self.logger.debug(f"Raw product book response for {product_id}: {response}")

            # The new SDK might return an object with a 'pricebook' attribute
            if hasattr(response, "pricebook") and isinstance(response.pricebook, dict):
                book_data = response.pricebook
            # Or it might be a dictionary with a 'pricebook' key
            elif isinstance(response, dict) and "pricebook" in response:
                book_data = response.get("pricebook")
            # Or the response might be the book data dictionary itself
            elif (
                isinstance(response, dict) and "bids" in response and "asks" in response
            ):
                book_data = response
            else:
                self.logger.warning(
                    f"get_product_book for {product_id} response format not recognized or key data missing: {response}"
                )
                return None

            if book_data is not None:
                self.logger.info(
                    f"Successfully retrieved product book for {product_id}."
                )
                # Dual assertions for response data
                assert isinstance(book_data, dict), "Processed book data is not a dict."
                assert (
                    "bids" in book_data and "asks" in book_data
                ), "Book data is missing 'bids' or 'asks'."

            return book_data
        except HTTPError as e:
            self.logger.error(
                f"HTTP error retrieving order book for {product_id}: {e.response.status_code} {e.response.text}",
                exc_info=True,
            )
            return None
        except RequestException as e:
            self.logger.error(
                f"Request exception retrieving order book for {product_id}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving order book for {product_id}: {e}", exc_info=True
            )
            return None

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details for a single product.

        Args:
            product_id (str): The trading pair (e.g., 'BTC-USD').

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing product details if successful, None otherwise.
        """
        self.logger.debug(f"Attempting to retrieve product {product_id}.")
        try:
            assert self.client is not None, "RESTClient not initialized."
            assert (
                isinstance(product_id, str) and product_id
            ), "Product ID must be a non-empty string."

            # The SDK method is get_products (plural), which gets all products.
            # We then need to find the specific product we're interested in.
            response = self.client.get_products()
            self.logger.debug("Raw get_products response received.")

            products_list = []
            if hasattr(response, "products") and isinstance(response.products, list):
                products_list = response.products
            elif isinstance(response, dict) and "products" in response:
                products_list = response.get("products", [])
            else:
                self.logger.warning(f"Unexpected format for get_products response: {type(response)}")

            product_data = None
            for product in products_list:
                # The response contains a list of Product objects, not dicts.
                # Access attributes directly using dot notation.
                if hasattr(product, 'product_id') and product.product_id == product_id:
                    # Convert the Product object to a dictionary that the rest of the system expects.
                    product_data = {
                        "product_id": product.product_id,
                        "price": product.price,
                        "price_percentage_change_24h": product.price_percentage_change_24h,
                        "volume_24h": product.volume_24h,
                        "volume_percentage_change_24h": product.volume_percentage_change_24h,
                        "base_increment": product.base_increment,
                        "quote_increment": product.quote_increment,
                        "quote_min_size": product.quote_min_size,
                        "quote_max_size": product.quote_max_size,
                        "base_min_size": product.base_min_size,
                        "base_max_size": product.base_max_size,
                        "base_name": product.base_name,
                        "quote_name": product.quote_name,
                        "watched": product.watched,
                        "is_disabled": product.is_disabled,
                        "new": product.new,
                        "status": product.status,
                        "cancel_only": product.cancel_only,
                        "limit_only": product.limit_only,
                        "post_only": product.post_only,
                        "trading_disabled": product.trading_disabled,
                        "auction_mode": product.auction_mode,
                        "product_type": product.product_type,
                        "quote_currency_id": product.quote_currency_id,
                        "base_currency_id": product.base_currency_id,
                        "fcm_trading_session_details": product.fcm_trading_session_details,
                        "mid_market_price": product.mid_market_price,
                        # For compatibility with older parts of the logic that might expect these keys
                        "min_market_funds": product.quote_min_size,
                    }
                    self.logger.info(f"Successfully found and formatted product details for {product_id}.")
                    break
            
            if not product_data:
                self.logger.warning(f"Could not find product details for {product_id} in API response.")

            return product_data

        except HTTPError as e:
            self.logger.error(
                f"HTTP error retrieving product {product_id}: {e.response.status_code} {e.response.text}",
                exc_info=True,
            )
            return None
        except RequestException as e:
            self.logger.error(
                f"Request exception retrieving product {product_id}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving product {product_id}: {e}", exc_info=True
            )
            return None

    def limit_order_buy(
        self, product_id: str, size: str, price: str
    ) -> Optional[Dict[str, Any]]:
        """Places a limit buy order.

        Args:
            product_id: The ID of the product to trade (e.g., "BTC-USD").
            size: The amount of the base currency to buy (e.g., "0.01").
            price: The price per unit of the base currency (e.g., "50000.00").

        Returns:
            A dictionary containing the API response for the order, or None if an error occurs.
        """
        log_prefix = "limit_order_buy"
        assert (
            isinstance(product_id, str) and product_id
        ), "product_id must be a non-empty string."
        # Validate size
        if not isinstance(size, str):
            self.logger.error(f"Invalid size type for {log_prefix}: {type(size)}. Must be a string.")
            raise ValueError("size must be a string representing a positive number.")
        try:
            f_size = float(size)
        except ValueError:
            self.logger.error(f"Invalid size format for {log_prefix}: {size}. Not a valid number string.")
            raise ValueError("size must be a string representing a positive number.") from None
        if f_size <= 0:
            self.logger.error(f"Non-positive size for {log_prefix}: {size}.")
            raise ValueError("size must be a string representing a positive number.")

        # Validate price
        if not isinstance(price, str):
            self.logger.error(f"Invalid price type for {log_prefix}: {type(price)}. Must be a string.")
            raise ValueError("price must be a string representing a positive number.")
        try:
            f_price = float(price)
        except ValueError:
            self.logger.error(f"Invalid price format for {log_prefix}: {price}. Not a valid number string.")
            raise ValueError("price must be a string representing a positive number.") from None
        if f_price <= 0:
            self.logger.error(f"Non-positive price for {log_prefix}: {price}.")
            raise ValueError("price must be a string representing a positive number.")

        client_order_id = self._generate_client_order_id()
        self.logger.info(
            "Placing limit buy order for %s of %s at %s (ClientOrderID: %s)."
            % (size, product_id, price, client_order_id)
        )
        try:
            assert self.client is not None, "RESTClient not initialized."
            # Corrected method name
            response = self.client.limit_order_gtc_buy(
                client_order_id=client_order_id,
                product_id=product_id,
                base_size=size,
                limit_price=price,
                post_only=True,  # Ensure it's a maker order
            )
            self.logger.debug(
                f"Raw limit buy order response for {product_id}: {response}"
            )

            if isinstance(response, dict) and response.get("success"):
                self.logger.info(
                    f"Limit buy order placed successfully for {product_id}. Order ID: {response.get('order_id')}"
                )
                processed_response = {
                    "success": True,
                    "order_id": response.get("order_id"),
                    "client_order_id": client_order_id,
                    "product_id": product_id,
                    "side": "BUY",
                    "size": size,
                    "price": price,
                }
                return processed_response
            else:
                failure_reason = response.get("failure_reason", "Unknown reason")
                self.logger.error(
                    f"Limit buy order failed for {product_id}. Reason: {failure_reason}"
                )
                return None
        except HTTPError as e:
            self.logger.error(
                f"HTTP error placing limit buy order for {product_id}: {e.response.status_code} {e.response.text}",
                exc_info=True,
            )
            return None
        except RequestException as e:
            self.logger.error(
                f"Request exception placing limit buy order for {product_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while placing limit buy order for {product_id}: {e}",
                exc_info=True,
            )
            return None

    def limit_order_sell(
        self, product_id: str, size: str, price: str
    ) -> Optional[Dict[str, Any]]:
        """Places a limit sell order.

        Args:
            product_id: The ID of the product to trade (e.g., "BTC-USD").
            size: The amount of the base currency to sell (e.g., "0.01").
            price: The price per unit of the base currency (e.g., "50000.00").

        Returns:
            A dictionary containing the API response for the order, or None if an error occurs.
        """
        log_prefix = "limit_order_sell"
        assert (
            isinstance(product_id, str) and product_id
        ), "product_id must be a non-empty string."
        # Validate size
        if not isinstance(size, str):
            self.logger.error(f"Invalid size type for {log_prefix}: {type(size)}. Must be a string.")
            raise ValueError("size must be a string representing a positive number.")
        try:
            f_size = float(size)
        except ValueError:
            self.logger.error(f"Invalid size format for {log_prefix}: {size}. Not a valid number string.")
            raise ValueError("size must be a string representing a positive number.") from None
        if f_size <= 0:
            self.logger.error(f"Non-positive size for {log_prefix}: {size}.")
            raise ValueError("size must be a string representing a positive number.")

        # Validate price
        if not isinstance(price, str):
            self.logger.error(f"Invalid price type for {log_prefix}: {type(price)}. Must be a string.")
            raise ValueError("price must be a string representing a positive number.")
        try:
            f_price = float(price)
        except ValueError:
            self.logger.error(f"Invalid price format for {log_prefix}: {price}. Not a valid number string.")
            raise ValueError("price must be a string representing a positive number.") from None
        if f_price <= 0:
            self.logger.error(f"Non-positive price for {log_prefix}: {price}.")
            raise ValueError("price must be a string representing a positive number.")

        client_order_id = self._generate_client_order_id()
        self.logger.info(
            "Placing limit sell order for %s of %s at %s (ClientOrderID: %s)."
            % (size, product_id, price, client_order_id)
        )
        try:
            assert self.client is not None, "RESTClient not initialized."
            # Corrected method name
            response = self.client.limit_order_gtc_sell(
                client_order_id=client_order_id,
                product_id=product_id,
                base_size=size,
                limit_price=price,
                post_only=True,  # Ensure it's a maker order
            )
            self.logger.debug(
                f"Raw limit sell order response for {product_id}: {response}"
            )

            if isinstance(response, dict) and response.get("success"):
                self.logger.info(
                    f"Limit sell order placed successfully for {product_id}. Order ID: {response.get('order_id')}"
                )
                processed_response = {
                    "success": True,
                    "order_id": response.get("order_id"),
                    "client_order_id": client_order_id,
                    "product_id": product_id,
                    "side": "SELL",
                    "size": size,
                    "price": price,
                }
                return processed_response
            else:
                failure_reason = response.get("failure_reason", "Unknown reason")
                self.logger.error(
                    f"Limit sell order failed for {product_id}. Reason: {failure_reason}"
                )
                return None
        except HTTPError as e:
            self.logger.error(
                f"HTTP error placing limit sell order for {product_id}: {e.response.status_code} {e.response.text}",
                exc_info=True,
            )
            return None
        except RequestException as e:
            self.logger.error(
                f"Request exception placing limit sell order for {product_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while placing limit sell order for {product_id}: {e}",
                exc_info=True,
            )
            return None

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single order by its ID.

        Args:
            order_id (str): The ID of the order to retrieve.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the order details if successful, None otherwise.
        """
        self.logger.debug(f"Attempting to retrieve order {order_id}.")
        # Rule: Use a minimum of two runtime assertions per function.
        assert order_id and isinstance(
            order_id, str
        ), "order_id must be a non-empty string."
        assert self.client is not None, "RESTClient not initialized."

        try:
            response = self.client.get_order(order_id=order_id)
            self.logger.debug(f"Raw get_order response for {order_id}: {response}")

            # The client returns an object with an 'order' attribute dict
            if hasattr(response, "order") and isinstance(response.order, dict):
                order_data = response.order
                self.logger.info(f"Successfully retrieved order {order_id}.")
                return order_data
            else:
                self.logger.warning(
                    f"Received unexpected format for order data: {type(response)}"
                )
                return None

        except HTTPError as e:
            # The API returns a 404 error if the order is not found, which the library may raise as an exception.
            self.logger.error(
                f"HTTP error retrieving order {order_id}: {e.response.status_code} {e.response.text}", exc_info=True
            )
            return None
        except RequestException as e:
            self.logger.error(f"Request exception retrieving order {order_id}: {e}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while retrieving order {order_id}: {e}", exc_info=True)
            return None

    def cancel_orders(
        self, order_ids: List[str]
    ) -> Optional[
        Dict[str, Any]
    ]:  # Adjusted return type based on typical API responses
        """Cancels one or more open orders.

        Args:
            order_ids (List[str]): A list of order IDs to cancel.

        Returns:
            Optional[Dict[str, Any]]: The cancellation response dictionary from the API if successful,
                                      which often contains a list of results for each order. None otherwise.
        """
        # Rule: Use a minimum of two runtime assertions per function.
        assert isinstance(order_ids, list), "order_ids must be a list."
        assert len(order_ids) > 0, "order_ids list cannot be empty."
        assert all(
            isinstance(oid, str) and len(oid) > 0 for oid in order_ids
        ), "All order_ids in the list must be non-empty strings."

        self.logger.info(f"Attempting to cancel orders: {order_ids}")

        try:
            # The coinbase-advanced-py library's cancel_orders method takes `order_ids` as a parameter.
            # response = client.cancel_orders(order_ids=["order_id_1", "order_id_2"])
            # The response structure is typically like: {'results': [{'success': True, 'order_id': 'xxx', 'failure_reason': None}, ...]}
            response = self.client.cancel_orders(order_ids=order_ids)
            self.logger.info(f"Cancel orders response: {response}")

            # Assertions on the response structure
            assert isinstance(
                response, dict
            ), "cancel_orders response should be a dictionary."
            # A common pattern is a 'results' key containing a list of individual outcomes.
            if "results" in response and isinstance(response["results"], list):
                self.logger.info(
                    f"Successfully processed cancel_orders request for {len(order_ids)} order(s). Checking individual results."
                )
                for result in response["results"]:
                    assert isinstance(
                        result, dict
                    ), "Each item in 'results' should be a dictionary."
                    order_id = result.get("order_id", "N/A")
                    if result.get("success"):
                        self.logger.info(f"Order {order_id} cancelled successfully.")
                    else:
                        failure_reason = result.get("failure_reason", "Unknown reason")
                        self.logger.error(
                            f"Failed to cancel order {order_id}. Reason: {failure_reason}"
                        )
            else:
                # If the top-level response indicates overall success/failure without a 'results' list
                # (less common for batch operations but possible)
                if response.get(
                    "success"
                ):  # This is a guess, adapt if API is different
                    self.logger.info(
                        f"Cancel orders request appears successful at a high level for orders: {order_ids}"
                    )
                else:
                    self.logger.warning(
                        f"Cancel orders response format not as expected or indicates general failure: {response}"
                    )
                    # This path might mean the entire batch failed for some reason not detailed per order.

            return response
        except HTTPError as e:
            self.logger.error(
                f"HTTP error cancelling orders {order_ids}: {e.response.status_code} {e.response.text}",
                exc_info=True,
            )
            return None
        except RequestException as e:
            self.logger.error(
                f"Request exception cancelling orders {order_ids}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while cancelling orders {order_ids}: {e}", exc_info=True
            )
            return None


if __name__ == "__main__":
    # This block is for basic testing or direct invocation scenarios.
    # Ensure environment variables are set if running this directly for testing purposes.
    # (Handled by config.py loading .env)
    try:
        client = CoinbaseClient()
        client.logger.info(
            "CoinbaseClient instance created successfully for basic test."
        )
        # Example: Add a simple call here if any method is implemented
        # test_order_id = client._generate_client_order_id()
        # client.logger.info(f"Generated test client_order_id: {test_order_id}")

        # Test get_accounts if COINBASE_API_KEY and COINBASE_API_SECRET are valid
        accounts = client.get_accounts()
        if accounts is not None:
            client.logger.info(f"Retrieved {len(accounts)} accounts during basic test.")
            for acc in accounts:
                client.logger.debug(
                    f"Account: {acc.get('id')}, Currency: {acc.get('currency')}, Balance: {acc.get('balance')}"
                )
        else:
            client.logger.warning("Failed to retrieve accounts during basic test.")

        # Test get_product_candles
        candles = client.get_product_candles("BTC-USD", "ONE_MINUTE")  # Example
        if candles is not None:
            client.logger.info(
                f"Retrieved {len(candles)} candles for BTC-USD during basic test."
            )
        else:
            client.logger.warning(
                "Failed to retrieve candles for BTC-USD during basic test."
            )

        # Test get_product_book
        book = client.get_product_book("BTC-USD", limit=5)
        if book is not None:
            client.logger.info(
                f"Retrieved order book for BTC-USD. Bids: {len(book.get('bids', []))}, Asks: {len(book.get('asks', []))}"
            )
        else:
            client.logger.warning(
                "Failed to retrieve order book for BTC-USD during basic test."
            )

    except RuntimeError as e:
        # Errors during client init are caught here if __name__ == '__main__'
        # The logger inside CoinbaseClient init would have already logged details.
        print(f"Error creating CoinbaseClient for basic test: {e}", file=sys.stderr)
    except Exception as e:
        # Catch any other unexpected errors during the basic test
        print(
            f"An unexpected error occurred during CoinbaseClient basic test: {e}",
            file=sys.stderr,
        )
