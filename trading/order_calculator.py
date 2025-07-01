from __future__ import annotations

"""Module for performing financial calculations for trading."""

import logging
from decimal import Decimal, InvalidOperation, ROUND_DOWN
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
        buy_amount_usd (Decimal): The amount in USD to buy.
        last_close_price (Decimal): The last closing price of the asset.
        product_details (Dict[str, Any]): A dictionary containing product details
            such as 'base_increment', 'quote_increment', and 'base_min_size'.
        logger (logging.Logger): The logger instance.

    Returns:
        Optional[Tuple[Decimal, Decimal]]: A tuple containing the calculated
        order size and limit price, or None if the calculation fails.
    """
    asset_id = product_details.get("product_id", "UNKNOWN_ASSET")
    try:
        try:
            # Attempt to convert product details to Decimal
            base_increment = Decimal(str(product_details["base_increment"]))
            quote_increment = Decimal(str(product_details["quote_increment"]))
            base_min_size = Decimal(str(product_details["base_min_size"]))
        except (TypeError, InvalidOperation) as e:
            logger.error(
                f"[{asset_id}] Invalid numeric value in product_details: {e}",
                exc_info=True,
            )
            return None

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
        logger.error(f"[{asset_id}] Missing required key in product_details: {e}")
        return None

    except Exception as e:
        logger.error(
            f"Exception calculating buy order details for {asset_id}: {e}",
            exc_info=True,
        )
        return None


def _round_decimal(d: Decimal, increment: Decimal) -> Decimal:
    """Rounds a Decimal to the nearest specified increment."""
    assert isinstance(d, Decimal), "Value to round must be a Decimal."
    assert (
        isinstance(increment, Decimal) and increment > 0
    ), "Increment must be a positive Decimal."
    return (d / increment).quantize(Decimal("1"), rounding=ROUND_DOWN) * increment


def _calculate_tier_price_and_size(
    buy_price: Decimal,
    quantity: Decimal,
    profit_target: Decimal,
    quote_increment: Decimal,
    base_increment: Decimal,
) -> Tuple[Decimal, Decimal]:
    """Calculates the rounded price and size for a single sell tier."""
    sell_price_unrounded = buy_price * (Decimal("1") + profit_target)
    sell_price_rounded = _round_decimal(sell_price_unrounded, quote_increment)
    quantity_to_sell_rounded = _round_decimal(quantity, base_increment)
    return quantity_to_sell_rounded, sell_price_rounded


def determine_sell_orders_params(
    buy_price: Decimal,
    buy_quantity: Decimal,
    product_details: Dict[str, Any],
    config_asset_params: Dict[str, Any],
    logger: logging.Logger,
) -> List[Dict[str, str]]:
    """
    Calculates parameters for tiered sell orders based on profit targets and product
    constraints.
    """
    asset_id = product_details.get("product_id", "UNKNOWN_ASSET")
    try:
        # --- Input & Config Validation ---
        assert buy_price > 0, "Buy price must be positive."
        assert buy_quantity > 0, "Buy quantity must be positive."

        sell_profit_tiers = config_asset_params["sell_profit_tiers"]

        # --- Tier Config Validation ---
        for i, tier in enumerate(sell_profit_tiers):
            profit_target = Decimal(str(tier["profit_target"]))
            quantity_percentage = Decimal(str(tier["quantity_percentage"]))
            assert 0 < profit_target, f"Tier {i+1} profit target must be positive."
            assert (
                0 < quantity_percentage <= 1
            ), f"Tier {i+1} quantity percentage must be between 0 and 1."

        # --- Main Calculation ---
        quote_increment = Decimal(str(product_details["quote_increment"]))
        base_increment = Decimal(str(product_details["base_increment"]))
        base_min_size = Decimal(str(product_details["base_min_size"]))

        total_quantity_to_sell = buy_quantity
        remaining_quantity = total_quantity_to_sell
        sell_order_params = []

        for i, tier in enumerate(sell_profit_tiers):
            is_last_tier = i == len(sell_profit_tiers) - 1

            profit_target = Decimal(str(tier["profit_target"]))
            quantity_percentage = Decimal(str(tier["quantity_percentage"]))

            if is_last_tier:
                quantity_to_sell_unrounded = remaining_quantity
            else:
                quantity_to_sell_unrounded = (
                    total_quantity_to_sell * quantity_percentage
                )

            (
                quantity_to_sell_rounded,
                sell_price_rounded,
            ) = _calculate_tier_price_and_size(
                buy_price,
                quantity_to_sell_unrounded,
                profit_target,
                quote_increment,
                base_increment,
            )

            if quantity_to_sell_rounded <= 0:
                logger.warning(
                    f"[{asset_id}] Tier {i+1} sell quantity is zero. Skipping."
                )
                continue

            if quantity_to_sell_rounded < base_min_size:
                logger.info(
                    f"[{asset_id}] Skipping tier {i+1} because its size is below min",
                    extra={
                        "tier": i + 1,
                        "calculated_size": str(quantity_to_sell_rounded),
                        "min_size": str(base_min_size),
                    },
                )
                continue

            remaining_quantity -= quantity_to_sell_rounded
            sell_order_params.append(
                {
                    "price": f"{sell_price_rounded}",
                    "size": f"{quantity_to_sell_rounded}",
                }
            )

        return sell_order_params

    except KeyError as e:
        # Distinguish between an expected missing config and an unexpected one.
        if "sell_profit_tiers" in str(e):
            logger.error(
                f"[{asset_id}] 'sell_profit_tiers' not found in config_asset_params."
            )
        else:
            logger.error(
                f"[{asset_id}] Missing key in config or product details: {e}",
                exc_info=True,
            )
        return []
    except (TypeError, InvalidOperation, AssertionError) as e:
        logger.error(f"[{asset_id}] Invalid value for sell calc: {e}", exc_info=True)
        return []
    except AttributeError as e:
        logger.error(f"[{asset_id}] Attribute error in sell calc: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(
            f"[{asset_id}] Unexpected exception in sell calc: {e}", exc_info=True
        )
        return []
