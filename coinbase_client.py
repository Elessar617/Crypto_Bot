"""Handles all interactions with the Coinbase Advanced Trade API."""

import json
import uuid
from typing import Optional, Dict, Any, List


from requests.exceptions import HTTPError, RequestException

from coinbase.rest import RESTClient

import config
import logger


class CoinbaseClient:
    """A client to interact with the Coinbase Advanced Trade API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        """
        Initializes the CoinbaseClient.

        Args:
            api_key (str, optional): The API key. Defaults to value in config.
            api_secret (str, optional): The API secret. Defaults to value in config.
            api_url (str, optional): The API URL to use. Defaults to the production URL.
        """
        self.logger = logger.get_logger()

        self.api_url = api_url or config.COINBASE_SANDBOX_API_URL
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
                base_url=self.api_url,
                rate_limit_headers=True,
            )
            self.logger.info(
                f"Coinbase RESTClient initialized successfully for {self.api_url} URL."
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
                self.logger.error("Failed to decode JSON from response: %s", response)
                # Return original string to trigger caller's error handling
                return response
        return response

    def get_accounts(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves a list of all trading accounts."""
        self.logger.debug("Attempting to retrieve accounts.")
        try:
            assert self.client is not None, "RESTClient not initialized."
            response = self.client.get_accounts()
            response_dict = self._handle_api_response(response)

            assert isinstance(
                response_dict, dict
            ), "get_accounts response should be a dictionary."
            accounts = response_dict.get("accounts")

            assert accounts is not None, "'accounts' key is missing in the response."
            assert isinstance(accounts, list), "'accounts' key should be a list."

            self.logger.info(f"Successfully retrieved {len(accounts)} accounts.")
            return accounts
        except (HTTPError, RequestException) as e:
            self.logger.error(f"Network error retrieving accounts: {e}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving accounts: {e}",
                exc_info=True,
            )
            return None

    def get_product_candles(
        self,
        product_id: str,
        granularity: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Retrieves historical candles for a product."""
        self.logger.debug(f"Attempting to retrieve candles for {product_id}.")
        try:
            assert self.client is not None, "RESTClient not initialized."
            assert product_id, "Product ID must be a non-empty string."

            response = self.client.get_product_candles(
                product_id=product_id, start=start, end=end, granularity=granularity
            )
            response_dict = self._handle_api_response(response)

            assert isinstance(
                response_dict, dict
            ), "get_product_candles response should be a dictionary."
            candles = response_dict.get("candles")

            assert candles is not None, "'candles' key missing in response."
            assert isinstance(candles, list), "'candles' key must be a list."

            self.logger.info(
                f"Successfully retrieved {len(candles)} candles for {product_id}."
            )
            return candles
        except (HTTPError, RequestException) as e:
            self.logger.error(
                f"Network error retrieving candles for {product_id}: {e}", exc_info=True
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
        """Retrieves the order book for a specific product."""
        self.logger.debug(f"Attempting to retrieve order book for {product_id}.")
        try:
            assert self.client is not None, "RESTClient not initialized."
            assert product_id, "Product ID must be a non-empty string."

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
        except (HTTPError, RequestException) as e:
            self.logger.error(
                f"Network error retrieving order book for {product_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving order book for {product_id}: {e}",
                exc_info=True,
            )
            return None

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details for a single product."""
        self.logger.debug(f"Attempting to retrieve product {product_id}.")
        try:
            assert self.client is not None, "RESTClient not initialized."
            assert product_id, "Product ID must be a non-empty string."

            response = self.client.get_product(product_id=product_id)
            product_details = self._handle_api_response(response)

            assert isinstance(
                product_details, dict
            ), "get_product response should be a dictionary."
            assert (
                "product_id" in product_details
            ), "'product_id' missing from product data."

            self.logger.info(
                f"Successfully retrieved product details for {product_id}."
            )
            return product_details
        except (HTTPError, RequestException) as e:
            self.logger.error(
                f"Network error retrieving product {product_id}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving product {product_id}: {e}",
                exc_info=True,
            )
            return None

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
            assert self.client is not None, "RESTClient not initialized."

            response = self.client.limit_order(
                client_order_id=client_order_id,
                product_id=product_id,
                side=side.upper(),
                base_size=base_size,
                limit_price=limit_price,
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
                error_details = response_dict.get("error_response", {})
                reason = error_details.get("message", "Unknown reason")
                self.logger.error(
                    f"Failed to place {side.lower()} order for {product_id}. Reason: {reason}"
                )

            return response_dict
        except (HTTPError, RequestException) as e:
            self.logger.error(
                f"Network error on limit {side.lower()} for {product_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred on limit {side.lower()} for {product_id}: {e}",
                exc_info=True,
            )
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
        except (HTTPError, RequestException) as e:
            self.logger.error(
                f"Network error retrieving order {order_id}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while retrieving order {order_id}: {e}",
                exc_info=True,
            )
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
        except (HTTPError, RequestException) as e:
            self.logger.error(
                f"Network error cancelling orders {order_ids}: {e}", exc_info=True
            )
            return None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while cancelling orders {order_ids}: {e}",
                exc_info=True,
            )
            return None
