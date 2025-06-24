from __future__ import annotations

"""Core trading decision logic for the bot."""

import logging
import math
import types
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from coinbase_client import CoinbaseClient


def should_buy_asset(
    rsi_series: Optional[pd.Series], config_asset_params: Dict[str, Any]
) -> bool:
    """
    Determines if an asset should be bought based on RSI conditions.

    Args:
        rsi_series: A pandas Series representing the RSI values for the asset.
                    The series should be ordered from oldest to newest.
        config_asset_params: A dictionary containing configuration parameters for the asset,
                             expected to include 'rsi_oversold_threshold'.

    Returns:
        True if the buying conditions are met, False otherwise.

    Buy Conditions:
    1. Current 14-period RSI (e.g., 15-min candles) > buy_rsi_threshold.
    2. Previous RSI <= buy_rsi_threshold.
    3. One of the 3 prior RSIs (before the 'previous' one) < buy_rsi_threshold.
    """
    # Assertion 1: Validate rsi_series input
    assert rsi_series is not None, "RSI series cannot be None."
    assert not rsi_series.empty, "RSI series cannot be empty."
    # The logic requires the current RSI, the previous, and 3 prior values.
    required_len = 5
    assert (
        len(rsi_series) >= required_len
    ), f"RSI series must have at least {required_len} data points for the logic."

    # Assertion 3: Validate config_asset_params for required keys
    assert isinstance(
        config_asset_params, dict
    ), "config_asset_params must be a dictionary."
    assert (
        "rsi_oversold_threshold" in config_asset_params
    ), "'rsi_oversold_threshold' missing from config_asset_params."

    buy_rsi_threshold = config_asset_params["rsi_oversold_threshold"]
    # Assertion 4: Validate buy_rsi_threshold type and value (optional, but good practice)
    assert isinstance(
        buy_rsi_threshold, (int, float)
    ), "'buy_rsi_threshold' must be a number."
    assert 0 < buy_rsi_threshold < 100, "'buy_rsi_threshold' must be between 0 and 100."

    # Extract relevant RSI values
    # Pandas series are 0-indexed. iloc[-1] is the last, iloc[-2] is second to last, etc.
    current_rsi = rsi_series.iloc[-1]
    previous_rsi = rsi_series.iloc[-2]
    # The three RSI values prior to the 'previous_rsi'
    # If series is [rsi_n-4, rsi_n-3, rsi_n-2, rsi_n-1, rsi_n], these are indices -5, -4, -3
    prior_rsis = rsi_series.iloc[-5:-2]  # This will slice elements at index -5, -4, -3

    # Combine all conditions into a single boolean expression for clarity and conciseness.
    buy_signal = (
        current_rsi > buy_rsi_threshold
        and previous_rsi <= buy_rsi_threshold
        and any(rsi < buy_rsi_threshold for rsi in prior_rsis)
    )

    return buy_signal


def _get_product_details(
    asset_id: str, client: CoinbaseClient, logger: logging.Logger
) -> Optional[Dict[str, Any]]:
    """
    Fetches and returns product details for a given asset.

    Args:
        asset_id: The ID of the asset.
        client: The Coinbase client instance.
        logger: The logger instance.

    Returns:
        A dictionary containing product details, or None if fetching fails.
    """
    try:
        product_details = client.get_product(product_id=asset_id)
        if not product_details:
            logger.error(f"[{asset_id}] Could not retrieve product details.")
            return None
        return product_details
    except Exception as e:
        logger.error(
            f"[{asset_id}] Exception while fetching product details: {e}", exc_info=True
        )
        return None


def determine_sell_orders_params(
    buy_price: float,
    buy_quantity: float,
    product_details: Dict[str, Any],
    config_asset_params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Calculates parameters for tiered sell orders based on profit targets and product constraints.

    Args:
        buy_price: The price at which the asset was bought.
        buy_quantity: The total quantity of the asset bought.
        product_details: Dictionary with product-specific constraints:
                         'quote_increment': Smallest price change unit (str).
                         'base_increment': Smallest quantity change unit (str).
                         'base_min_size': Minimum order quantity (str).
        config_asset_params: Asset-specific configuration, expecting:
                             'sell_profit_tiers': List of tiers, each a dict with:
                                 'percentage': Profit percentage for the tier (float).
                                 'quantity_percentage': Percentage of total buy quantity for this tier (float).

    Returns:
        A list of dictionaries, each with 'price' (float) and 'quantity' (float)
        for a sell order. Orders for tiers resulting in a quantity less than
        'base_min_size' after adjustment are omitted.
    """
    # --- Input Assertions ---
    assert (
        isinstance(buy_price, (int, float)) and buy_price > 0
    ), "buy_price must be a positive number."
    assert (
        isinstance(buy_quantity, (int, float)) and buy_quantity > 0
    ), "buy_quantity must be a positive number."
    assert isinstance(product_details, dict), "product_details must be a dictionary."
    for key in ["quote_increment", "base_increment", "base_min_size"]:
        assert key in product_details, f"'{key}' missing from product_details."
        assert isinstance(
            product_details[key], str
        ), f"product_details['{key}'] must be a string."
    assert isinstance(
        config_asset_params, dict
    ), "config_asset_params must be a dictionary."
    assert (
        "sell_profit_tiers" in config_asset_params
    ), "'sell_profit_tiers' missing from config_asset_params."
    assert isinstance(
        config_asset_params["sell_profit_tiers"], list
    ), "'sell_profit_tiers' must be a list."

    # Convert product detail strings to Decimal for precision
    try:
        quote_increment = Decimal(product_details["quote_increment"])
        base_increment = Decimal(product_details["base_increment"])
        base_min_size = Decimal(product_details["base_min_size"])
    except Exception as e:
        raise ValueError(
            f"Invalid number format in product_details increments/min_size: {e}"
        )

    assert quote_increment > Decimal(0), "quote_increment must be positive."
    assert base_increment > Decimal(0), "base_increment must be positive."
    assert base_min_size > Decimal(0), "base_min_size must be positive."

    sell_profit_tiers = config_asset_params["sell_profit_tiers"]
    calculated_sell_orders = []
    total_quantity_percentage_configured = Decimal(0)

    for tier in sell_profit_tiers:
        assert isinstance(
            tier, dict
        ), "Each tier in 'sell_profit_tiers' must be a dictionary."
        assert "percentage" in tier, "'percentage' missing from a tier."
        assert (
            "quantity_percentage" in tier
        ), "'quantity_percentage' missing from a tier."
        assert (
            isinstance(tier["percentage"], (int, float)) and tier["percentage"] > 0
        ), "Tier 'percentage' must be a positive number."
        assert (
            isinstance(tier["quantity_percentage"], (int, float))
            and tier["quantity_percentage"] > 0
        ), "Tier 'quantity_percentage' must be a positive number."

        total_quantity_percentage_configured += Decimal(
            str(tier["quantity_percentage"])
        )

        target_sell_price_raw = Decimal(str(buy_price)) * (
            Decimal(1) + Decimal(str(tier["percentage"])) / Decimal(100)
        )
        tier_quantity_raw = Decimal(str(buy_quantity)) * (
            Decimal(str(tier["quantity_percentage"])) / Decimal(100)
        )

        # Adjust price: Round down to the nearest quote_increment
        adjusted_price = target_sell_price_raw.quantize(
            quote_increment, rounding=ROUND_DOWN
        )

        # Adjust quantity: Round down to the nearest base_increment
        adjusted_quantity = tier_quantity_raw.quantize(
            base_increment, rounding=ROUND_DOWN
        )

        # Ensure adjusted price and quantity are not zero or negative if they were positive before adjustment
        if adjusted_price <= Decimal(0) or adjusted_quantity <= Decimal(0):
            # This might happen if increments are very large relative to calculated values
            # print(f"Warning: Tier resulted in non-positive price/quantity after adjustment. Skipping tier: {tier}") # noqa: T201
            continue

        if adjusted_quantity >= base_min_size:
            calculated_sell_orders.append(
                {"price": float(adjusted_price), "quantity": float(adjusted_quantity)}
            )
        # else:
        # print(f"Info: Tier quantity {float(adjusted_quantity)} for tier {tier} is below base_min_size {float(base_min_size)}. Skipping.") # noqa: T201

    # Assertion for total quantity percentage (optional, but good for config validation)
    # Using isclose due to potential floating point inaccuracies when summing percentages
    if not math.isclose(
        float(total_quantity_percentage_configured), 100.0, rel_tol=1e-5
    ):
        # print(f"Warning: Sum of 'quantity_percentage' in sell_profit_tiers is {float(total_quantity_percentage_configured)}, not 100%.") # noqa: T201
        pass  # Decide on strictness: raise error or just warn

    return calculated_sell_orders


def _handle_new_buy_order(
    asset_id: str,
    client: CoinbaseClient,
    persistence_manager: types.ModuleType,
    ta_module: types.ModuleType,
    product_details: Dict[str, Any],
    config_asset_params: Dict[str, Any],
    logger: logging.Logger,
) -> None:
    """
    Checks for a buy signal and places a new buy order if conditions are met.

    Args:
        asset_id: The ID of the asset.
        client: The Coinbase client instance.
        persistence_manager: The persistence manager instance.
        ta_module: The technical analysis module.
        product_details: The product details from the exchange.
        config_asset_params: The asset-specific configuration parameters.
        logger: The logger instance.
    """
    logger.info(
        f"[{asset_id}] No active trade or open buy order. Checking for buy signal."
    )
    try:
        candle_granularity_str = str(
            config_asset_params.get("candle_granularity_name", "FIFTEEN_MINUTE")
        )
        candles_list = client.get_product_candles(
            product_id=asset_id, granularity=candle_granularity_str
        )

        if not candles_list:
            logger.warning(
                f"[{asset_id}] Could not fetch candles or no candle data returned."
            )
            return

        candles_df = pd.DataFrame(candles_list)
        # Ensure required columns are numeric and sorted by time
        for col in ["high", "low", "close"]:
            candles_df[col] = pd.to_numeric(candles_df[col])
        candles_df = candles_df.sort_values("start").reset_index(drop=True)

        if "close" not in candles_df.columns:
            logger.error(f"[{asset_id}] 'close' column missing in candle data.")
            return
        candles_df["close"] = pd.to_numeric(candles_df["close"])

        rsi_period = config_asset_params.get("rsi_period", 14)
        rsi_series = ta_module.calculate_rsi(candles_df, period=rsi_period)
        if rsi_series is None or rsi_series.empty:
            logger.info(
                f"[{asset_id}] RSI could not be calculated (insufficient data?)."
            )
            return

        if should_buy_asset(rsi_series, config_asset_params):
            logger.info(f"[{asset_id}] Buy signal detected.")
            buy_amount_usd = Decimal(str(config_asset_params["buy_amount_usd"]))
            last_close_price = Decimal(str(candles_df["close"].iloc[-1]))
            if last_close_price <= Decimal(0):
                logger.error(
                    f"[{asset_id}] Last close price is zero or negative, cannot calculate buy quantity."
                )
                return

            raw_buy_quantity = buy_amount_usd / last_close_price
            base_increment = Decimal(str(product_details["base_increment"]))
            adjusted_buy_quantity = raw_buy_quantity.quantize(
                base_increment, rounding=ROUND_DOWN
            )

            base_min_size = Decimal(str(product_details["base_min_size"]))
            if adjusted_buy_quantity < base_min_size:
                logger.warning(
                    f"[{asset_id}] Calculated buy quantity {adjusted_buy_quantity} is less than min_order_size {base_min_size}."
                )
                return

            limit_buy_price = last_close_price

            logger.info(
                f"[{asset_id}] Attempting to place buy order. Size: {adjusted_buy_quantity}, Price: {limit_buy_price}"
            )
            buy_order_result = client.limit_order_buy(
                product_id=asset_id,
                size=str(adjusted_buy_quantity),
                price=str(limit_buy_price),
            )

            if buy_order_result and buy_order_result.get("success"):
                order_id = buy_order_result["order_id"]
                logger.info(f"[{asset_id}] Successfully placed buy order {order_id}.")
                persistence_manager.save_open_buy_order(
                    asset_id,
                    order_id,
                    {
                        "price": str(limit_buy_price),
                        "size": str(adjusted_buy_quantity),
                    },
                )
            else:
                logger.error(
                    f"[{asset_id}] Failed to place buy order. Result: {buy_order_result}"
                )
        else:
            logger.info(f"[{asset_id}] No buy signal detected.")

    except Exception as e:
        logger.error(
            f"[{asset_id}] Error during buy signal check or order placement: {e}",
            exc_info=True,
        )


def _handle_filled_buy_order(
    asset_id: str,
    filled_buy_trade: Dict[str, Any],
    client: CoinbaseClient,
    persistence_manager: types.ModuleType,
    product_details: Dict[str, Any],
    config_asset_params: Dict[str, Any],
    logger: logging.Logger,
) -> None:
    """
    Manages the sell side of a filled buy trade, including checking and placing sell orders.

    Args:
        asset_id: The ID of the asset.
        filled_buy_trade: The filled buy trade details from persistence.
        client: The Coinbase client instance.
        persistence_manager: The persistence manager instance.
        product_details: The product details from the exchange.
        config_asset_params: The asset-specific configuration parameters.
        logger: The logger instance.
    """
    logger.info(f"[{asset_id}] Found filled buy trade: {filled_buy_trade}")
    sell_orders_in_state = filled_buy_trade.get("sell_orders", [])
    all_sell_orders_filled = True if sell_orders_in_state else False
    needs_new_sell_orders = not sell_orders_in_state

    if sell_orders_in_state:
        all_sell_orders_filled = True
        active_sell_order_ids = []
        for so_state in sell_orders_in_state:
            if so_state["status"] not in ["FILLED", "CANCELLED", "EXPIRED", "FAILED"]:
                all_sell_orders_filled = False
                try:
                    order_detail = client.get_order(so_state["id"])
                    if order_detail and order_detail.get("order"):
                        current_status = order_detail.get("order", {}).get(
                            "status", "UNKNOWN"
                        )
                        persistence_manager.update_sell_order_status_in_filled_trade(
                            asset_id, so_state["id"], current_status
                        )
                        logger.info(
                            f"[{asset_id}] Updated sell order {so_state['id']} status to {current_status}"
                        )
                        if current_status not in [
                            "FILLED",
                            "CANCELLED",
                            "EXPIRED",
                            "FAILED",
                        ]:
                            active_sell_order_ids.append(so_state["id"])
                        elif current_status != "FILLED":
                            needs_new_sell_orders = True
                    else:
                        logger.warning(
                            f"[{asset_id}] Could not get details for sell order {so_state['id']}"
                        )
                        active_sell_order_ids.append(so_state["id"])
                except Exception as e:
                    logger.error(
                        f"[{asset_id}] Error checking sell order {so_state['id']}: {e}"
                    )
                    active_sell_order_ids.append(so_state["id"])
            elif so_state["status"] != "FILLED":
                all_sell_orders_filled = False
                needs_new_sell_orders = True

        if not active_sell_order_ids and not all_sell_orders_filled:
            needs_new_sell_orders = True

    if needs_new_sell_orders and not all_sell_orders_filled:
        logger.info(f"[{asset_id}] Determining and placing new sell orders.")
        sell_order_params_list = determine_sell_orders_params(
            buy_price=float(filled_buy_trade["buy_price"]),
            buy_quantity=float(filled_buy_trade["buy_quantity"]),
            product_details=product_details,
            config_asset_params=config_asset_params,
        )

        for params in sell_order_params_list:
            try:
                sell_order_result = client.limit_order_sell(
                    product_id=asset_id,
                    size=str(params["quantity"]),
                    price=str(params["price"]),
                )
                if sell_order_result and sell_order_result.get("success"):
                    order_id = sell_order_result["order_id"]
                    logger.info(
                        f"[{asset_id}] Successfully placed sell order {order_id}: {params}"
                    )
                    persistence_manager.add_sell_order_to_filled_trade(
                        asset_id, order_id, "OPEN"
                    )
                else:
                    logger.error(
                        f"[{asset_id}] Failed to place sell order: {params}, Result: {sell_order_result}"
                    )
            except Exception as e:
                logger.error(f"[{asset_id}] Exception placing sell order {params}: {e}")

    elif all_sell_orders_filled:
        logger.info(
            f"[{asset_id}] All sell orders for buy trade {filled_buy_trade['buy_order_id']} are filled. Clearing trade."
        )
        persistence_manager.clear_filled_buy_trade(asset_id)
    else:
        logger.info(f"[{asset_id}] Sell orders are active. Waiting for completion.")


def _handle_open_buy_order(
    asset_id: str,
    open_buy_order: Dict[str, Any],
    client: CoinbaseClient,
    persistence_manager: types.ModuleType,
    logger: logging.Logger,
) -> None:
    """
    Checks the status of an open buy order and handles it accordingly.

    Args:
        asset_id: The ID of the asset.
        open_buy_order: The open buy order details from persistence.
        client: The Coinbase client instance.
        persistence_manager: The persistence manager instance.
        logger: The logger instance.
    """
    logger.info(f"[{asset_id}] Found open buy order: {open_buy_order}")
    try:
        order_detail = client.get_order(open_buy_order["order_id"])
        if not (order_detail and order_detail.get("order")):
            logger.warning(
                f"[{asset_id}] Could not get details for open buy order {open_buy_order['order_id']}"
            )
            return

        order_data = order_detail["order"]
        status = order_data.get("status", "UNKNOWN")
        logger.info(
            f"[{asset_id}] Open buy order {open_buy_order['order_id']} status: {status}"
        )

        if status == "FILLED":
            filled_price = Decimal(
                order_data.get("average_filled_price", open_buy_order.get("price"))
            )
            filled_quantity = Decimal(
                order_data.get("filled_size", open_buy_order.get("size"))
            )

            if (
                not filled_price
                or not filled_quantity
                or filled_price <= Decimal(0)
                or filled_quantity <= Decimal(0)
            ):
                logger.error(
                    f"[{asset_id}] Buy order {open_buy_order['order_id']} FILLED but has invalid filled price/quantity. Price: {filled_price}, Qty: {filled_quantity}. Not processing further."
                )
                persistence_manager.clear_open_buy_order(asset_id)
                return

            logger.info(
                f"[{asset_id}] Buy order {open_buy_order['order_id']} filled. Price: {filled_price}, Quantity: {filled_quantity}"
            )
            persistence_manager.clear_open_buy_order(asset_id)
            trade_details = {
                "buy_order_id": open_buy_order["order_id"],
                "buy_price": str(filled_price),
                "buy_quantity": str(filled_quantity),
                "timestamp": order_data.get("created_at"),
                "sell_orders": [],
            }
            persistence_manager.save_filled_buy_trade(asset_id, trade_details)
            logger.info(f"[{asset_id}] Saved filled buy trade.")

        elif status in ["CANCELLED", "EXPIRED", "FAILED"]:
            logger.warning(
                f"[{asset_id}] Buy order {open_buy_order['order_id']} is {status}. Clearing order."
            )
            persistence_manager.clear_open_buy_order(asset_id)
        else:  # OPEN, PENDING, UNKNOWN etc.
            logger.info(
                f"[{asset_id}] Buy order {open_buy_order['order_id']} is still {status}. Waiting."
            )

    except Exception as e:
        logger.error(
            f"[{asset_id}] Error checking open buy order {open_buy_order['order_id']}: {e}",
            exc_info=True,
        )


def process_asset_trade_cycle(
    asset_id: str,
    client: CoinbaseClient,
    persistence_manager: types.ModuleType,
    ta_module: types.ModuleType,
    config_module: types.ModuleType,
    logger: logging.Logger,
) -> None:
    """
    Processes one full trading cycle for a given asset.
    This includes loading state, checking existing orders, and potentially placing new orders.

    Args:
        asset_id: The ID of the asset (e.g., "BTC-USD").
        client: Instance of CoinbaseClient for API interactions.
        persistence_manager: Instance of PersistenceManager for state handling.
        ta_module: Technical analysis module (e.g., technical_analysis.py).
        config_module: Configuration module (e.g., config.py).
        logger: Logger instance for logging.
    """
    logger.info(f"[{asset_id}] Starting trade cycle processing.")

    try:
        # Fetch asset-specific configuration
        if (
            not hasattr(config_module, "TRADING_PAIRS")
            or asset_id not in config_module.TRADING_PAIRS
        ):
            logger.error(f"[{asset_id}] Configuration not found for {asset_id}.")
            return
        config_asset_params = config_module.TRADING_PAIRS[asset_id]

        product_details = _get_product_details(asset_id, client, logger)
        if not product_details:
            logger.error(f"[{asset_id}] Aborting cycle due to missing product details.")
            return

        # Load current state for the asset
        trade_state = persistence_manager.load_trade_state(asset_id)
        open_buy_order = trade_state.get("open_buy_order")
        filled_buy_trade = trade_state.get("filled_buy_trade")

        # --- Handle Filled Buy Trade (Sell Logic) ---
        if filled_buy_trade:
            _handle_filled_buy_order(
                asset_id,
                filled_buy_trade,
                client,
                persistence_manager,
                product_details,
                config_asset_params,
                logger,
            )

        # --- Handle Open Buy Order (Buy Order Management) ---
        elif open_buy_order:
            _handle_open_buy_order(
                asset_id, open_buy_order, client, persistence_manager, logger
            )

        # --- Handle No Active Trade/Order (Buy Signal Check) ---
        else:
            _handle_new_buy_order(
                asset_id,
                client,
                persistence_manager,
                ta_module,
                product_details,
                config_asset_params,
                logger,
            )

    except Exception as e:
        logger.error(
            f"[{asset_id}] Unhandled error in process_asset_trade_cycle: {e}",
            exc_info=True,
        )
    finally:
        logger.info(f"[{asset_id}] Trade cycle processing finished.")
