"""Handles all interactions with the Coinbase Advanced Trade API."""

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union


from requests.exceptions import HTTPError, RequestException

from coinbase.rest import RESTClient

from trading import config
from trading import logger


class CoinbaseClient:
    """A client to interact with the Coinbase Advanced Trade API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ) -> None:
        """
        Initializes the CoinbaseClient.

        Args:
            api_key (str, optional): The API key. Defaults to value in config.
            api_secret (str, optional): The API secret. Defaults to value in config.
        """
        self.logger = logger.get_logger()

        self.api_key = api_key if api_key is not None else config.COINBASE_API_KEY
        self.api_secret = (
            api_secret if api_secret is not None else config.COINBASE_API_SECRET
        )

        assert (
            isinstance(self.api_key, str) and self.api_key
        ), "API key must be a non-empty string."
        assert (
            isinstance(self.api_secret, str) and self.api_secret
        ), "API secret must be a non-empty string."

        try:
            self.client: Optional[RESTClient] = RESTClient(
                api_key=self.api_key,
                api_secret=self.api_secret,
                rate_limit_headers=True,
            )
            self.logger.info(
                "Coinbase RESTClient initialized successfully for the live API."
            )
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Coinbase RESTClient: {e}", exc_info=True
            )
            raise RuntimeError(f"Coinbase RESTClient initialization failed: {e}") from e

    def _generate_client_order_id(self) -> str:
        """Generates a unique client order ID."""
        raw_id = uuid.uuid4()
        assert isinstance(
            raw_id, uuid.UUID
        ), "uuid.uuid4() did not return a UUID object."
        order_id = str(raw_id)
        assert len(order_id) > 0, "Generated client_order_id is empty."
        return order_id

    def _handle_api_response(self, response: Any) -> Any:
        """Converts API response to a dictionary, handling various formats."""
        if isinstance(response, dict):
            return response
        if hasattr(response, "to_dict"):
            return response.to_dict()
        if isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Let the caller handle the error by returning the original string
                return response
        return response

    def _log_api_error(self, method_name: str, error: Exception) -> None:
        """Logs a standardized error message for API call failures."""
        self.logger.error(
            f"An error occurred in {method_name}: {error}", exc_info=True
        )

    def get_accounts(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves a list of all trading accounts."""
        self.logger.debug("Attempting to retrieve accounts.")
        try:
            assert self.client is not None, "RESTClient not initialized."
            response = self.client.get_accounts()
            response_dict = self._handle_api_response(response)

            if not isinstance(response_dict, dict):
                self.logger.error(
                    f"An error occurred in get_accounts: Response was not a dictionary. Response: {response_dict}"
                )
                return None

            accounts = response_dict.get("accounts")

            if not isinstance(accounts, list):
                self.logger.error(
                    f"An error occurred in get_accounts: 'accounts' key must be a list. Response: {response_dict}"
                )
                return None

            self.logger.info(f"Successfully retrieved {len(accounts)} accounts.")
            return accounts
        except (HTTPError, RequestException, Exception) as e:
            self._log_api_error("get_accounts", e)
            return None

    def get_public_candles(
        self,
        product_id: str,
        granularity: str,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetches historical candle data for a product."""
        try:
            assert self.client is not None, "RESTClient not initialized."
            assert product_id, "Product ID must be a non-empty string."

            # 1. Determine end datetime object (end_dt)
            if end is None:
                end_dt = datetime.now(timezone.utc)
            elif isinstance(end, datetime):
                end_dt = end
            else:
                try:
                    end_dt = datetime.fromtimestamp(int(end), tz=timezone.utc)
                except (ValueError, TypeError):
                    self.logger.error(f"Invalid format for end time: {end}")
                    return None

            # 2. Determine start datetime object (start_dt)
            if start is None:
                granularity_map = {
                    "ONE_MINUTE": timedelta(minutes=1),
                    "FIVE_MINUTE": timedelta(minutes=5),
                    "FIFTEEN_MINUTE": timedelta(minutes=15),
                    "THIRTY_MINUTE": timedelta(minutes=30),
                    "ONE_HOUR": timedelta(hours=1),
                    "TWO_HOUR": timedelta(hours=2),
                    "SIX_HOUR": timedelta(hours=6),
                    "ONE_DAY": timedelta(days=1),
                }
                candle_duration = granularity_map.get(granularity)
                if not candle_duration:
                    self.logger.error(f"Unsupported granularity: {granularity}")
                    return None
                start_dt = end_dt - (candle_duration * 300)
            elif isinstance(start, datetime):
                start_dt = start
            else:
                try:
                    start_dt = datetime.fromtimestamp(int(start), tz=timezone.utc)
                except (ValueError, TypeError):
                    self.logger.error(f"Invalid format for start time: {start}")
                    return None

            # 3. Convert to string timestamps for the API call
            start_ts = str(int(start_dt.timestamp()))
            end_ts = str(int(end_dt.timestamp()))

            # 4. Make the API call
            response = self.client.get_public_candles(
                product_id=product_id,
                start=start_ts,
                end=end_ts,
                granularity=granularity,
            )
            self.logger.info(f"Raw response from get_product_candles: {response}")
            response_dict = self._handle_api_response(response)

            if not isinstance(response_dict, dict):
                self.logger.error(
                    f"An error occurred in get_public_candles for {product_id}: Response was not a dictionary.",
                    exc_info=True,
                )
                return None

            candles = response_dict.get("candles")

            if not isinstance(candles, list):
                self.logger.error(
                    f"An error occurred in get_public_candles for {product_id}: 'candles' key must be a list.",
                    exc_info=True,
                )
                return None

            self.logger.info(
                f"Successfully retrieved {len(candles)} candles for {product_id}."
            )
            return candles
        except (HTTPError, RequestException, ValueError) as e:
            self._log_api_error(f"get_public_candles for {product_id}", e)
            return None

    def get_product_book(
        self, product_id: str, limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves the order book for a specific product."""
        self.logger.debug(f"Attempting to retrieve order book for {product_id}.")
        assert product_id, "Product ID must be a non-empty string."
        try:
            assert self.client is not None, "RESTClient not initialized."

            response = self.client.get_product_book(product_id=product_id, limit=limit)
            response_dict = self._handle_api_response(response)

            assert isinstance(
                response_dict, dict
            ), "get_product_book response should be a dictionary."
            pricebook = response_dict.get("pricebook")

            assert pricebook is not None, "'pricebook' key missing in response."
            assert isinstance(pricebook, dict), "'pricebook' must be a dictionary."

            self.logger.info(f"Successfully retrieved order book for {product_id}.")
            return pricebook
        except (HTTPError, RequestException, Exception) as e:
            self._log_api_error(f"get_product_book for {product_id}", e)
            return None

    def get_product(
        self, product_id: str, max_retries: int = 3, base_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Retrieves details for a single product with retry logic."""
        self.logger.debug(f"Attempting to retrieve product details for {product_id}.")
        assert product_id, "Product ID must be a non-empty string."
        assert max_retries > 0, "max_retries must be positive."
        assert base_delay > 0, "base_delay must be positive."

        for attempt in range(max_retries):
            try:
                assert self.client is not None, "RESTClient not initialized."
                response = self.client.get_product(product_id=product_id)
                response_dict = self._handle_api_response(response)

                assert isinstance(
                    response_dict, dict
                ), "get_product response should be a dictionary."

                self.logger.info(f"Successfully retrieved product {product_id}.")
                return response_dict

            except (HTTPError, RequestException) as e:
                self.logger.warning(
                    f"Attempt {attempt + 1} of {max_retries} failed for get_product({product_id}). Error: {e}"
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    self.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self._log_api_error(f"get_product for {product_id}", e)
                    return None
            except Exception as e:
                self._log_api_error(f"get_product for {product_id}", e)
                return None

        return None  # Should not be reached if logic is correct

    def limit_order(
        self,
        side: str,
        product_id: str,
        base_size: str,
        limit_price: str,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Places a limit order (buy or sell)."""
        if client_order_id is None:
            client_order_id = self._generate_client_order_id()

        self.logger.debug(
            f"Attempting to place {side.lower()} limit order for {base_size} of {product_id} at {limit_price}."
        )
        try:
            assert side.upper() in ["BUY", "SELL"], "Side must be 'BUY' or 'SELL'."
            assert product_id, "Product ID must be a non-empty string."
            assert self.client is not None, "RESTClient not initialized."

            order_configuration = {
                "limit_limit_gtc": {
                    "base_size": base_size,
                    "limit_price": limit_price,
                    "post_only": False,
                }
            }

            response = self.client.limit_order(
                side=side.upper(),
                client_order_id=client_order_id,
                product_id=product_id,
                order_configuration=order_configuration,
            )
            response_dict = self._handle_api_response(response)

            assert isinstance(
                response_dict, dict
            ), "limit_order response should be a dictionary."

            if response_dict.get("success"):
                self.logger.info(
                    f"Successfully placed {side.lower()} order for {product_id}. Order ID: {response_dict.get('order_id')}"
                )
            else:
                reason = response_dict.get("failure_reason")
                if not reason:
                    error_details = response_dict.get("error_response", {})
                    reason = error_details.get("message", "Unknown reason")
                self.logger.error(
                    f"Failed to place {side.lower()} order for {product_id}. Reason: {reason}"
                )

            return response_dict
        except (HTTPError, RequestException, Exception) as e:
            self._log_api_error(f"limit_order for {product_id}", e)
            return None

    def limit_order_buy(
        self,
        product_id: str,
        base_size: str,
        limit_price: str,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """A wrapper for limit_order specific to BUY orders."""
        return self.limit_order(
            side="BUY",
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price,
            client_order_id=client_order_id,
        )

    def limit_order_sell(
        self,
        product_id: str,
        base_size: str,
        limit_price: str,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """A wrapper for limit_order specific to SELL orders."""
        return self.limit_order(
            side="SELL",
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price,
            client_order_id=client_order_id,
        )

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single order by its ID."""
        self.logger.debug(f"Attempting to retrieve order {order_id}.")
        try:
            assert self.client is not None, "RESTClient not initialized."
            assert order_id, "Order ID must be a non-empty string."

            response = self.client.get_order(order_id=order_id)
            response_dict = self._handle_api_response(response)

            assert isinstance(
                response_dict, dict
            ), "get_order response should be a dictionary."
            order_details = response_dict.get("order")

            assert order_details is not None, "'order' key missing in response."
            assert isinstance(order_details, dict), "'order' must be a dictionary."

            self.logger.info(f"Successfully retrieved order {order_id}.")
            return order_details
        except (HTTPError, RequestException, Exception) as e:
            self._log_api_error(f"get_order for {order_id}", e)
            return None

    def cancel_orders(self, order_ids: List[str]) -> Optional[List[Dict[str, Any]]]:
        """Cancels one or more open orders."""
        self.logger.debug(f"Attempting to cancel orders: {order_ids}")
        try:
            assert self.client is not None, "RESTClient not initialized."
            assert (
                isinstance(order_ids, list) and order_ids
            ), "order_ids must be a non-empty list."

            response = self.client.cancel_orders(order_ids=order_ids)
            response_dict = self._handle_api_response(response)

            assert isinstance(
                response_dict, dict
            ), "cancel_orders response should be a dictionary."

            results = response_dict.get("results")
            assert results is not None, "'results' key missing in response."
            assert isinstance(results, list), "'results' key should be a list."

            self.logger.info(
                f"Successfully processed cancel orders request for {order_ids}."
            )
            for item in results:
                assert isinstance(
                    item, dict
                ), "Each item in 'results' should be a dictionary."
                if item.get("success"):
                    self.logger.info(
                        f"Successfully cancelled order {item.get('order_id')}."
                    )
                else:
                    error_details = item.get("error_response", {})
                    reason = error_details.get(
                        "message", item.get("failure_reason", "Unknown reason")
                    )
                    self.logger.error(
                        f"Failed to cancel order {item.get('order_id')}. Reason: {reason}"
                    )

            return results
        except (HTTPError, RequestException, Exception) as e:
            self._log_api_error(f"cancel_orders for {order_ids}", e)
            return None
