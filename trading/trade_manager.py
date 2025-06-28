from __future__ import annotations

"""Module containing the TradeManager class, which orchestrates the trade cycle."""

import logging
import time
from typing import Any, Dict, Optional

import pandas as pd
from decimal import Decimal

from trading.coinbase_client import CoinbaseClient
from trading.persistence import PersistenceManager


class TradeManager:
    """Manages the trading cycle for assets."""

    def __init__(
        self,
        client: CoinbaseClient,
        persistence_manager: PersistenceManager,
        ta_module: Any,
        config_module: Any,
        logger: logging.Logger,
        signal_analyzer: Any,
        order_calculator: Any,
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
                f"[{asset_id}] Exception fetching product details: {e}",
                exc_info=True,
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
            self._handle_open_buy_order(
                asset_id, open_buy_order, product_details, config_asset_params
            )
        else:
            self._handle_new_buy_order(
                asset_id,
                product_details,
                config_asset_params,
            )

    def process_asset_trade_cycle(self, asset_id: str) -> None:
        """
        Processes one full trading cycle for a given asset.
        This includes loading state, checking existing orders, and potentially placing
        new orders.
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
        buy_order_id = filled_buy_trade.get("buy_order_id")
        if not buy_order_id:
            self.logger.error(
                f"[{asset_id}] Corrupted trade state: buy_order_id missing."
            )
            return

        sell_orders = filled_buy_trade.get("associated_sell_orders", [])
        if sell_orders:
            self._check_and_update_sell_orders(
                asset_id=asset_id,
                buy_order_id=buy_order_id,
                sell_orders=sell_orders,
            )
        else:
            self._place_new_sell_orders(
                asset_id=asset_id,
                filled_buy_trade=filled_buy_trade,
                product_details=product_details,
                config_asset_params=config_asset_params,
            )

    def _check_and_update_sell_orders(
        self, asset_id: str, buy_order_id: str, sell_orders: list
    ) -> None:
        """Checks status of open sell orders and updates persistence."""
        if not sell_orders:
            return

        all_orders_filled = True
        for order in sell_orders:
            order_id = order.get("order_id")
            if not order_id:
                self.logger.warning(f"[{asset_id}] Skipping sell order with no ID.")
                continue

            current_status = order.get("status", "OPEN")
            if current_status == "FILLED":
                continue

            try:
                updated_order = self.client.get_order(order_id)
                if not updated_order:
                    self.logger.warning(
                        f"[{asset_id}] Failed to get status for sell order {order_id}."
                    )
                    all_orders_filled = False
                    continue

                new_status = updated_order.get("status")
                if new_status and current_status != new_status:
                    self.logger.info(
                        f"[{asset_id}] Sell order {order_id} status updated to {new_status}."
                    )
                    self.persistence_manager.update_sell_order_status_in_filled_trade(
                        asset_id=asset_id,
                        buy_order_id=buy_order_id,
                        sell_order_id=order_id,
                        new_status=new_status,
                    )
                    order["status"] = new_status

                if new_status != "FILLED":
                    all_orders_filled = False

            except Exception as e:
                self.logger.error(
                    f"[{asset_id}] Error checking sell order {order_id}: {e}",
                    exc_info=True,
                )
                all_orders_filled = False

        if all_orders_filled:
            self.logger.info(
                f"[{asset_id}] All sell orders are filled. Clearing trade state."
            )
            self.persistence_manager.clear_filled_buy_trade(asset_id=asset_id)

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
            buy_price = Decimal(str(filled_buy_trade["buy_price"]))
            buy_quantity = Decimal(str(filled_buy_trade["buy_quantity"]))

            sell_order_params = self.order_calculator.determine_sell_orders_params(
                buy_price=buy_price,
                buy_quantity=buy_quantity,
                sell_profit_tiers=config_asset_params["sell_profit_tiers"],
                product_details=product_details,
                logger=self.logger,
            )

            if not sell_order_params:
                self.logger.error(
                    f"[{asset_id}] No sell orders were generated. Check config and logs."
                )
                return

            placed_orders = 0
            for i, params in enumerate(sell_order_params):
                size = params["base_size"]
                price = params["limit_price"]
                self.logger.info(
                    f"[{asset_id}] Placing sell order "
                    f"{i + 1}/{len(sell_order_params)}: size={size}, price={price}"
                )
                client_order_id = self.client._generate_client_order_id()
                order_result = self.client.limit_order_sell(
                    product_id=asset_id,
                    base_size=str(size),
                    limit_price=str(price),
                    client_order_id=client_order_id,
                )

                if order_result and order_result.get("success"):
                    order_id = order_result.get("order_id")
                    if order_id:
                        self.logger.info(
                            f"[{asset_id}] Successfully placed sell order {order_id}."
                        )
                        sell_order_details = {
                            "order_id": order_id,
                            "size": str(size),
                            "price": str(price),
                            "timestamp": time.time(),
                            "status": "OPEN",
                        }
                        self.persistence_manager.add_sell_order_to_filled_trade(
                            asset_id=asset_id,
                            buy_order_id=filled_buy_trade["buy_order_id"],
                            sell_order_details=sell_order_details,
                        )
                        placed_orders += 1
                elif order_result:
                    error_response = order_result.get("error_response", {})
                    error_message = error_response.get("message", "No message")
                    self.logger.error(
                        f"[{asset_id}] Failed to place sell order. Reason: {error_message}"
                    )

            if placed_orders == 0:
                self.logger.warning(
                    f"[{asset_id}] No sell orders were successfully placed. The filled buy trade will be re-processed."
                )
            else:
                self.logger.info(
                    f"[{asset_id}] Successfully placed and saved {placed_orders} sell orders."
                )

        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception in _place_new_sell_orders: {e}", exc_info=True
            )

    def _handle_open_buy_order(
        self,
        asset_id: str,
        open_buy_order: Dict[str, Any],
        product_details: Dict[str, Any],
        config_asset_params: Dict[str, Any],
    ) -> None:
        """Checks the status of an open buy order and handles it accordingly."""
        order_id = open_buy_order["order_id"]
        self.logger.info(f"[{asset_id}] Checking status of open buy order {order_id}.")

        try:
            order_status = self.client.get_order(order_id)

            if not order_status:
                self.logger.error(
                    f"[{asset_id}] Could not get status for order {order_id}."
                )
                return

            status = order_status.get("status")
            if status == "FILLED":
                self.logger.info(f"[{asset_id}] Buy order {order_id} is filled.")

                filled_size = Decimal(order_status.get("filled_size", "0"))
                avg_price = Decimal(order_status.get("average_filled_price", "0"))

                if filled_size > 0 and avg_price > 0:
                    sell_orders_params = (
                        self.order_calculator.determine_sell_orders_params(
                            buy_price=avg_price,
                            buy_quantity=filled_size,
                            sell_profit_tiers=config_asset_params["sell_profit_tiers"],
                            product_details=product_details,
                            logger=self.logger,
                        )
                    )

                    self.persistence_manager.save_filled_buy_trade(
                        asset_id=asset_id,
                        buy_order_id=order_id,
                        filled_order=order_status,
                        sell_orders_params=sell_orders_params,
                    )
                    self.persistence_manager.clear_open_buy_order(asset_id=asset_id)
                    self.logger.info(
                        f"[{asset_id}] Saved filled trade data and cleared open buy order."
                    )
                else:
                    self.logger.error(
                        f"[{asset_id}] Order {order_id} filled but size/price is zero."
                    )
                    self.persistence_manager.clear_open_buy_order(asset_id)

            elif status == "CANCELLED":
                self.logger.info(f"[{asset_id}] Buy order {order_id} was cancelled.")
                self.persistence_manager.clear_open_buy_order(asset_id)

            elif status == "OPEN":
                self.logger.info(f"[{asset_id}] Buy order {order_id} is still open.")
                # Optional: Add logic for order timeout and cancellation here
                # For now, we just leave it open.

            else:
                self.logger.warning(
                    f"[{asset_id}] Unhandled order status '{status}' for order {order_id}."
                )

        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception checking open buy order {order_id}: {e}",
                exc_info=True,
            )

    def _analyze_market_for_buy_signal(
        self, asset_id: str, config_asset_params: Dict[str, Any]
    ) -> Optional[list]:
        """
        Fetches market data, calculates indicators, and checks for a buy signal.
        Returns candle data if a buy signal is present, otherwise None.
        """
        try:
            candles = self.client.get_public_candles(
                asset_id, granularity=config_asset_params["candle_granularity_api_name"]
            )
            if not candles:
                self.logger.warning(f"[{asset_id}] No candle data returned.")
                return None

            candles_df = pd.DataFrame(candles)
            for col in ["open", "high", "low", "close", "volume"]:
                if col in candles_df.columns:
                    candles_df[col] = pd.to_numeric(candles_df[col])

            rsi_series = self.ta_module.calculate_rsi(
                candles_df, period=config_asset_params["rsi_period"]
            )
            if rsi_series is None or rsi_series.empty:
                self.logger.warning(f"[{asset_id}] RSI calculation failed.")
                return None

            if self.signal_analyzer.should_buy_asset(
                rsi_series, config_asset_params, self.logger
            ):
                self.logger.info(f"[{asset_id}] Buy signal detected.")
                return candles

            self.logger.info(f"[{asset_id}] Buy conditions not met.")
            return None
        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception in _analyze_market_for_buy_signal: {e}",
                exc_info=True,
            )
            return None

    def _execute_buy_order(
        self,
        asset_id: str,
        product_details: Dict[str, Any],
        config_asset_params: Dict[str, Any],
        candles: list,
    ) -> None:
        """Calculates order details and places a new buy order."""
        try:
            buy_details = self.order_calculator.calculate_buy_order_details(
                buy_amount_usd=Decimal(str(config_asset_params["buy_amount_usd"])),
                last_close_price=Decimal(str(candles[-1]["close"])),
                product_details=product_details,
                logger=self.logger,
            )

            if not buy_details:
                self.logger.warning(
                    f"[{asset_id}] Could not calculate buy order details. Skipping."
                )
                return

            size, limit_price = buy_details
            client_order_id = self.client._generate_client_order_id()
            order_result = self.client.limit_order_buy(
                product_id=asset_id,
                base_size=str(size),
                limit_price=str(limit_price),
                client_order_id=client_order_id,
            )

            if order_result and order_result.get("success"):
                order_id = order_result.get("order_id")
                if order_id:
                    self.logger.info(
                        f"[{asset_id}] Successfully placed buy order {order_id}."
                    )
                    buy_params = {
                        "timestamp": time.time(),
                        "size": str(size),
                        "price": str(limit_price),
                    }
                    self.persistence_manager.save_open_buy_order(
                        asset_id=asset_id, order_id=order_id, order_details=buy_params
                    )
            elif order_result:
                error_response = order_result.get("error_response", {})
                error_message = error_response.get("message", "No message")
                self.logger.error(
                    f"[{asset_id}] Failed to place buy order. Reason: {error_message}"
                )
        except Exception as e:
            self.logger.error(
                f"[{asset_id}] Exception in _execute_buy_order: {e}", exc_info=True
            )

    def _handle_new_buy_order(
        self,
        asset_id: str,
        product_details: Dict[str, Any],
        config_asset_params: Dict[str, Any],
    ) -> None:
        """Handles the logic for creating a new buy order."""
        self.logger.info(f"[{asset_id}] Checking for new buy opportunities.")

        candles = self._analyze_market_for_buy_signal(asset_id, config_asset_params)

        if candles:
            self._execute_buy_order(
                asset_id, product_details, config_asset_params, candles
            )
