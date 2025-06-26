from __future__ import annotations

"""Module for performing financial calculations for trading."""

import logging
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple


def calculate_buy_order_details(
    buy_amount_usd: Decimal,
    last_close_price: Decimal,
    product_details: Dict[str, Any],
    logger: logging.Logger,
) -> Optional[Tuple[Decimal, Decimal]]:
    """
    Calculates the size and price for a new buy order based on constraints.

    Args:
        buy_amount_usd: The amount in USD to spend.
        last_close_price: The last closing price of the asset.
        product_details: Dict with product constraints (increments, min size).
        logger: Logger instance.

    Returns:
        A tuple of (size, price) as Decimals, or None if calculation fails.
    """
    try:
        base_increment = Decimal(str(product_details["base_increment"]))
        quote_increment = Decimal(str(product_details["quote_increment"]))
        base_min_size = Decimal(str(product_details["base_min_size"]))
        asset_id = product_details.get("product_id", "UNKNOWN_ASSET")

        # Round the price for the order to the nearest quote increment
        limit_price = _round_decimal(last_close_price, quote_increment)
        if limit_price <= 0:
            logger.error(f"[{asset_id}] Calculated limit price is zero or negative.")
            return None

        # Calculate the size of the buy order in the base currency
        size = _round_decimal(buy_amount_usd / limit_price, base_increment)

        if size < base_min_size:
            logger.warning(
                f"[{asset_id}] Calculated buy size {size} is below min size "
                f"{base_min_size}. Not placing order."
            )
            return None

        return size, limit_price

    except KeyError as e:
        logger.error(f"[{asset_id}] Missing key in product_details: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(
            f"[{asset_id}] Exception calculating buy order details: {e}", exc_info=True
        )
        return None


def _round_decimal(d: Decimal, increment: Decimal) -> Decimal:
    """Rounds a Decimal to the nearest specified increment."""
    assert isinstance(d, Decimal), "Value to round must be a Decimal."
    assert (
        isinstance(increment, Decimal) and increment > 0
    ), "Increment must be a positive Decimal."
    return (d / increment).quantize(Decimal("1"), rounding=ROUND_DOWN) * increment


def determine_sell_orders_params(
    buy_price: float,
    buy_quantity: float,
    product_details: Dict[str, Any],
    config_asset_params: Dict[str, Any],
    logger: logging.Logger,
) -> List[Dict[str, str]]:
    """
    Calculates parameters for tiered sell orders based on profit targets and product
    constraints.

    Args:
        buy_price: The price at which the asset was bought.
        buy_quantity: The total quantity of the asset bought.
        product_details: A dictionary containing details about the trading product,
                         including 'quote_increment', 'base_increment', and
                         'base_min_size'.
        config_asset_params: A dictionary of configuration parameters for the asset,
                             including 'sell_profit_tiers'.
        logger: Logger instance for logging messages.

    Returns:
        A list of dictionaries, where each dictionary represents a sell order and
        contains 'price' and 'size' as strings. Orders that do not meet the
        'base_min_size' after adjustment are omitted.
    """
    # --- Input Assertions ---
    assert buy_price > 0, "Buy price must be positive."
    assert buy_quantity > 0, "Buy quantity must be positive."
    assert (
        "quote_increment" in product_details
    ), "'quote_increment' missing from product_details."
    assert (
        "base_increment" in product_details
    ), "'base_increment' missing from product_details."
    assert (
        "base_min_size" in product_details
    ), "'base_min_size' missing from product_details."
    assert (
        "sell_profit_tiers" in config_asset_params
    ), "'sell_profit_tiers' missing from config_asset_params."

    # --- Initialization ---
    asset_id = product_details.get("product_id", "UNKNOWN_ASSET")
    sell_profit_tiers = config_asset_params["sell_profit_tiers"]
    quote_increment = Decimal(str(product_details["quote_increment"]))
    base_increment = Decimal(str(product_details["base_increment"]))
    base_min_size = Decimal(str(product_details["base_min_size"]))
    total_quantity_to_sell = Decimal(str(buy_quantity))
    remaining_quantity = total_quantity_to_sell
    sell_order_params = []

    # --- Tiered Order Calculation ---
    for i, tier in enumerate(sell_profit_tiers):
        is_last_tier = i == len(sell_profit_tiers) - 1
        profit_target = tier["profit_target"]
        quantity_percentage = tier["quantity_percentage"]

        assert 0 < profit_target, f"Tier {i+1} profit target must be positive."
        assert (
            0 < quantity_percentage <= 1
        ), f"Tier {i+1} quantity percentage must be between 0 and 1."

        # Calculate sell price
        sell_price_unrounded = Decimal(str(buy_price)) * (
            Decimal("1") + Decimal(str(profit_target))
        )
        sell_price_rounded = _round_decimal(sell_price_unrounded, quote_increment)

        # Calculate sell quantity
        if is_last_tier:
            # Assign all remaining quantity to the last tier to avoid rounding leftovers
            quantity_to_sell_unrounded = remaining_quantity
        else:
            quantity_to_sell_unrounded = total_quantity_to_sell * Decimal(
                str(quantity_percentage)
            )

        quantity_to_sell_rounded = _round_decimal(
            quantity_to_sell_unrounded, base_increment
        )

        # --- Validation and Adjustment ---
        if quantity_to_sell_rounded <= 0:
            logger.warning(
                f"[{asset_id}] Tier {i+1} sell quantity is zero after rounding. "
                f"Skipping."
            )
            continue

        if quantity_to_sell_rounded < base_min_size:
            logger.warning(
                f"[{asset_id}] Tier {i+1} quantity {quantity_to_sell_rounded} is below "
                f"min size {base_min_size}. Skipping."
            )
            continue

        # Update remaining quantity
        remaining_quantity -= quantity_to_sell_rounded
        if (
            remaining_quantity < -base_increment
        ):  # Allow for small floating point inaccuracies
            log_message = (
                f"[{asset_id}] Negative remaining quantity ({remaining_quantity}) "
                f"after tier {i+1}. This should not happen."
            )
            logger.error(log_message)
            # This indicates a logic error, stop processing to be safe
            return []

        sell_order_params.append(
            {
                "price": f"{sell_price_rounded}",
                "size": f"{quantity_to_sell_rounded}",
            }
        )

    # --- Final Check ---
    if remaining_quantity > base_min_size:
        logger.warning(
            f"[{asset_id}] {remaining_quantity} of asset remains unsold after "
            f"tiering logic due to rounding."
        )

    return sell_order_params
