from __future__ import annotations

"""Module containing the TradeManager class, which orchestrates the trade cycle."""

import logging
import time
import types
from typing import Any, Dict, List, Optional
from decimal import Decimal

from coinbase_client import CoinbaseClient
from trading import order_calculator, signal_analyzer


class TradeManager:
    """Manages the trading cycle for assets."""

    def __init__(
        self,
        client: CoinbaseClient,
        persistence_manager: types.ModuleType,
        ta_module: types.ModuleType,
        config_module: types.ModuleType,
        logger: logging.Logger,
        signal_analyzer: types.ModuleType,
        order_calculator: types.ModuleType,
    ):
        """Initializes the TradeManager."""
        self.client = client
        self.persistence_manager = persistence_manager
        self.ta_module = ta_module
        self.config_module = config_module
        self.logger = logger
        self.signal_analyzer = signal_analyzer
        self.order_calculator = order_calculator
        self.product_details_cache: Dict[str, Dict[str, Any]] = {}

    def _get_product_details(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Fetches product details from cache or API."""
        if asset_id in self.product_details_cache:
            return self.product_details_cache[asset_id]
        try:
            product = self.client.get_product(asset_id)
            if product and product.get("product_id") == asset_id:
                self.product_details_cache[asset_id] = product
                self.logger.info(f"[{asset_id}] Cached product details.")
                return product
            self.logger.error(f"[{asset_id}] Failed to fetch valid product details.")
            return None
        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception fetching product details: {e}", exc_info=True
            )
            return None

    def _get_asset_config(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Fetches asset-specific configuration."""
        if (
            not hasattr(self.config_module, "TRADING_PAIRS")
            or asset_id not in self.config_module.TRADING_PAIRS
        ):
            self.logger.error(f"[{asset_id}] Configuration not found.")
            return None
        return self.config_module.TRADING_PAIRS[asset_id]

    def _main_trade_logic(
        self,
        asset_id: str,
        config_asset_params: Dict[str, Any],
        product_details: Dict[str, Any],
    ) -> None:
        """Main logic flow for an asset trade cycle."""
        trade_state = self.persistence_manager.load_trade_state(asset_id)
        open_buy_order = trade_state.get("open_buy_order")
        filled_buy_trade = trade_state.get("filled_buy_trade")

        if filled_buy_trade:
            self._handle_filled_buy_order(
                asset_id,
                filled_buy_trade,
                product_details,
                config_asset_params,
            )
        elif open_buy_order:
            self._handle_open_buy_order(asset_id, open_buy_order, product_details)
        else:
            self._handle_new_buy_order(
                asset_id,
                product_details,
                config_asset_params,
            )

    def process_asset_trade_cycle(self, asset_id: str) -> None:
        """
        Processes one full trading cycle for a given asset.
        This includes loading state, checking existing orders, and potentially placing new orders.
        """
        self.logger.info(f"[{asset_id}] Starting trade cycle processing.")
        try:
            config_asset_params = self._get_asset_config(asset_id)
            if not config_asset_params:
                return

            product_details = self._get_product_details(asset_id)
            if not product_details:
                return

            self._main_trade_logic(
                asset_id,
                config_asset_params,
                product_details,
            )

        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Unhandled error in process_asset_trade_cycle: {e}",
                exc_info=True,
            )
        finally:
            self.logger.info(f"[{asset_id}] Trade cycle processing finished.")

    # --- Placeholder Methods ---
    def _handle_filled_buy_order(
        self,
        asset_id: str,
        filled_buy_trade: Dict[str, Any],
        product_details: Dict[str, Any],
        config_asset_params: Dict[str, Any],
    ) -> None:
        """Manages sell-side logic for a filled buy trade."""
        sell_orders = filled_buy_trade.get("associated_sell_orders", [])
        if sell_orders:
            self._check_and_update_sell_orders(asset_id, sell_orders)
        else:
            self._place_new_sell_orders(
                asset_id, filled_buy_trade, product_details, config_asset_params
            )

    def _check_and_update_sell_orders(
        self, asset_id: str, sell_orders: List[Dict[str, Any]]
    ) -> None:
        """Checks status of open sell orders and updates persistence."""
        self.logger.info(f"[{asset_id}] Checking status of {len(sell_orders)} sell orders.")
        try:
            all_filled = True
            updated_orders_details = []

            for order in sell_orders:
                order_id = order["order_id"]
                order_details = self.client.get_order(order_id)

                if not order_details or "status" not in order_details:
                    self.logger.error(
                        f"[{asset_id}] Could not retrieve status for order {order_id}. Keeping old status."
                    )
                    updated_orders_details.append(order)  # Keep original if fetch fails
                    all_filled = False
                    continue

                status = order_details["status"]
                self.logger.info(f"[{asset_id}] Sell order {order_id} status: {status}")

                if status != "FILLED":
                    all_filled = False

                updated_orders_details.append({"order_id": order_id, "status": status})

            if all_filled:
                self.logger.info(
                    f"[{asset_id}] All sell orders are filled. Trade cycle complete."
                )
                self.persistence_manager.clear_filled_buy_trade(asset_id)
            else:
                self.logger.info(f"[{asset_id}] Not all sell orders are filled. Updating status.")
                trade_state = self.persistence_manager.load_trade_state(asset_id)
                if trade_state.get("filled_buy_trade"):
                    trade_state["filled_buy_trade"][
                        "associated_sell_orders"
                    ] = updated_orders_details
                    self.persistence_manager.save_filled_buy_trade(
                        asset_id, trade_state["filled_buy_trade"]
                    )
        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception checking sell orders: {e}", exc_info=True
            )

    def _place_new_sell_orders(
        self,
        asset_id: str,
        filled_buy_trade: Dict[str, Any],
        product_details: Dict[str, Any],
        config_asset_params: Dict[str, Any],
    ) -> None:
        """Calculates and places new tiered sell orders."""
        self.logger.info(f"[{asset_id}] Placing new sell orders.")
        try:
            buy_price = float(filled_buy_trade["buy_price"])
            buy_quantity = float(filled_buy_trade["buy_quantity"])

            sell_order_params = order_calculator.determine_sell_orders_params(
                buy_price,
                buy_quantity,
                product_details,
                config_asset_params,
                self.logger,
            )

            if not sell_order_params:
                self.logger.error(
                    f"[{asset_id}] No sell orders were generated. Check config and logs."
                )
                return

            placed_orders = []
            for params in sell_order_params:
                client_order_id = self.client._generate_client_order_id(asset_id)
                order_result = self.client.limit_order_sell(
                    client_order_id=client_order_id,
                    product_id=asset_id,
                    base_size=params["size"],
                    limit_price=params["price"],
                )

                if order_result and order_result.get("success"):
                    order_id = order_result["order_id"]
                    self.logger.info(
                        f"[{asset_id}] Successfully placed sell order {order_id} "
                        f"for {params['size']} @ {params['price']}."
                    )
                    placed_orders.append({"order_id": order_id, "status": "OPEN"})
                else:
                    error_response = order_result.get("error_response", {})
                    error_message = error_response.get("message", "No message")
                    self.logger.error(
                        f"[{asset_id}] Failed to place sell order. Reason: {error_message}"
                    )

            if placed_orders:
                self.logger.info(
                    f"[{asset_id}] Saving {len(placed_orders)} new sell orders to state."
                )
                filled_buy_trade["associated_sell_orders"] = placed_orders
                self.persistence_manager.save_filled_buy_trade(
                    asset_id, filled_buy_trade
                )

        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception placing new sell orders: {e}", exc_info=True
            )

    def _handle_open_buy_order(
        self, asset_id: str, open_buy_order: Dict[str, Any], product_details: Dict[str, Any]
    ) -> None:
        """Checks the status of an open buy order and handles it accordingly."""
        order_id = open_buy_order.get("order_id")
        if not order_id:
            self.logger.error(
                f"[{asset_id}] 'order_id' missing from open_buy_order state. Clearing."
            )
            self.persistence_manager.clear_open_buy_order(asset_id)
            return

        self.logger.info(f"[{asset_id}] Checking status of open buy order {order_id}.")
        try:
            order_details = self.client.get_order(order_id)

            if not order_details:
                self.logger.error(f"[{asset_id}] Failed to fetch details for order {order_id}.")
                return

            order_status = order_details.get("status")

            if order_status == "FILLED":
                filled_size_str = order_details.get("filled_size")
                avg_price_str = order_details.get("average_fill_price")
                created_at = order_details.get("created_time")

                if not all([filled_size_str, avg_price_str, created_at]):
                    self.logger.error(
                        f"[{asset_id}] Filled order {order_id} is missing critical data."
                    )
                    return

                self.logger.info(
                    f"[{asset_id}] Buy order {order_id} is FILLED. Saving trade details."
                )
                self.persistence_manager.clear_open_buy_order(asset_id)
                trade_details = {
                    "buy_order_id": order_id,
                    "buy_price": str(avg_price_str),
                    "buy_quantity": str(filled_size_str),
                    "timestamp": created_at,
                    "associated_sell_orders": [],
                }
                self.persistence_manager.save_filled_buy_trade(asset_id, trade_details)

            elif order_status in ["CANCELLED", "EXPIRED", "FAILED"]:
                self.logger.warning(
                    f"[{asset_id}] Buy order {order_id} has status {order_status}. Clearing state."
                )
                self.persistence_manager.clear_open_buy_order(asset_id)

            else:  # OPEN, PENDING, etc.
                self.logger.info(
                    f"[{asset_id}] Buy order {order_id} is still {order_status}. Waiting."
                )

        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception checking open buy order {order_id}: {e}",
                exc_info=True,
            )

    def _handle_new_buy_order(
        self,
        asset_id: str,
        product_details: Dict[str, Any],
        config_asset_params: Dict[str, Any],
    ) -> None:
        """Handles the logic for creating a new buy order."""
        self.logger.info(f"[{asset_id}] Checking for new buy opportunities.")

        try:
            # 1. Get candle data
            candles = self.client.get_product_candles(asset_id)
            if not candles:
                self.logger.warning(f"[{asset_id}] No candle data returned.")
                return

            # 2. Calculate indicator (RSI)
            rsi_series = self.ta_module.calculate_rsi(
                candles, period=config_asset_params["rsi_period"]
            )
            if rsi_series is None or rsi_series.empty:
                self.logger.warning(f"[{asset_id}] RSI calculation failed.")
                return

            # 3. Check buy condition
            if not self.signal_analyzer.should_buy_asset(
                rsi_series, config_asset_params, self.logger
            ):
                self.logger.info(f"[{asset_id}] Buy conditions not met.")
                return

            self.logger.info(f"[{asset_id}] Buy signal detected. Placing order.")

            # 4. Calculate order price and size
            buy_details = self.order_calculator.calculate_buy_order_details(
                buy_amount_usd=Decimal(str(config_asset_params["buy_amount_usd"])),
                last_close_price=Decimal(str(candles[-1][4])),
                product_details=product_details,
                logger=self.logger,
            )

            if not buy_details:
                self.logger.warning(
                    f"[{asset_id}] Could not calculate buy order details. Skipping."
                )
                return

            size, limit_price = buy_details

            # 5. Place the buy order
            client_order_id = self.client._generate_client_order_id(asset_id)
            order_result = self.client.limit_order_buy(
                client_order_id=client_order_id,
                product_id=asset_id,
                base_size=str(size),
                limit_price=str(limit_price),
            )

            if order_result and order_result.get("success"):
                order_id = order_result["order_id"]
                self.logger.info(
                    f"[{asset_id}] Successfully placed buy order {order_id}."
                )
                # Save the open order state
                open_order_data = {
                    "order_id": order_id,
                    "timestamp": time.time(),
                    "size": str(size),
                    "price": str(limit_price),
                }
                self.persistence_manager.save_open_buy_order(asset_id, open_order_data)
            else:
                error_response = order_result.get("error_response", {})
                error_message = error_response.get("message", "No message")
                self.logger.error(
                    f"[{asset_id}] Failed to place buy order. Reason: {error_message}"
                )

        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception in _handle_new_buy_order: {e}", exc_info=True
            )
