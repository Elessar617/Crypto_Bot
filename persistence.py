"""Handles saving and loading of persistent bot state, like buy prices."""

import json
import os
from typing import Dict, Any, Optional

# Use centralized config and logger
from config import PERSISTENCE_DIR
from logger import get_logger

# Initialize logger for this module
logger = get_logger()


def save_trade_state(asset_id: str, state_data: Dict[str, Any]) -> None:
    """
    Saves the provided state_data dictionary to a JSON file named
    [asset_id]_trade_state.json in the DATA_DIR.

    Args:
        asset_id: The identifier for the asset (e.g., 'BTC-USD').
        state_data: A dictionary containing the trade state to save.

    Raises:
        IOError: If there is an error writing to the file.
        TypeError: If asset_id is not a string or state_data is not a dict.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."
    assert isinstance(state_data, dict), "state_data must be a dictionary."

    file_path = os.path.join(PERSISTENCE_DIR, f"{asset_id}_trade_state.json")

    # Two runtime assertions per function (Power of 10 Rule 5)
    # 1. asset_id is a non-empty string (checked by initial assertions)
    # 2. state_data is a dictionary (checked by initial assertions)
    # Additional check for file path construction:
    assert os.path.isabs(file_path) or file_path.startswith(
        PERSISTENCE_DIR
    ), "File path construction seems incorrect."

    try:
        os.makedirs(PERSISTENCE_DIR, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)
        logger.debug(f"Successfully saved trade state for {asset_id} to {file_path}")

    except (IOError, OSError) as e:
        logger.error(
            f"Error writing trade state for {asset_id} to {file_path}: {e}",
            exc_info=True,
        )
        raise IOError(f"Failed to write to {file_path}.") from e
    except TypeError as e:
        logger.error(
            f"TypeError during JSON serialization for {asset_id}: {e}", exc_info=True
        )
        raise TypeError("state_data contains non-serializable content.") from e


def load_trade_state(asset_id: str) -> Dict[str, Any]:
    """
    Loads trade state from [asset_id]_trade_state.json located in DATA_DIR.

    Args:
        asset_id: The identifier for the asset (e.g., 'BTC-USD').

    Returns:
        A dictionary containing the trade state if the file exists and is valid,
        otherwise an empty dictionary.

    Raises:
        TypeError: If asset_id is not a string.
    """
    assert isinstance(asset_id, str), "asset_id must be a string."
    assert len(asset_id) > 0, "asset_id cannot be empty."

    file_path = os.path.join(PERSISTENCE_DIR, f"{asset_id}_trade_state.json")

    # Two runtime assertions per function (Power of 10 Rule 5)
    # 1. asset_id is a non-empty string (checked by initial assertions)
    # 2. File path is correctly constructed (implicit in logic, but good to be mindful)
    # For load, the primary concern is handling file absence or corruption gracefully.

    if not os.path.exists(file_path):
        # In a real application, this might be a debug log, not an error
        # print(f"Trade state file not found for {asset_id}: {file_path}") # noqa: T201
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            state_data: Dict[str, Any] = json.load(f)
            if not isinstance(state_data, dict):
                # File content is not a dictionary
                logger.error(
                    f"Corrupted trade state file for {asset_id}: content is not a dict. File: {file_path}"
                )
                return {}
            # In a real application, log successful load
            logger.debug(
                f"Successfully loaded trade state for {asset_id} from {file_path}"
            )
            return state_data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}", exc_info=True)
        return {}
    except IOError as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
        return {}


# --- Helper functions for specific trade state components ---


def save_open_buy_order(
    asset_id: str, order_id: str, buy_params: Dict[str, Any]
) -> None:
    """
    Saves details of an open buy order for a given asset.

    Args:
        asset_id: The identifier for the asset.
        order_id: The ID of the open buy order.
        buy_params: A dictionary containing parameters of the buy order.

    Raises:
        TypeError: If arguments are of incorrect types.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."
    assert (
        isinstance(order_id, str) and len(order_id) > 0
    ), "order_id must be a non-empty string."
    assert isinstance(buy_params, dict), "buy_params must be a dictionary."

    trade_state = load_trade_state(asset_id)
    trade_state["open_buy_order"] = {"order_id": order_id, "params": buy_params}
    save_trade_state(asset_id, trade_state)
    # print(f"Saved open buy order {order_id} for {asset_id}") # noqa: T201


def load_open_buy_order(asset_id: str) -> Optional[Dict[str, Any]]:
    """
    Loads the details of an open buy order for a given asset.

    Args:
        asset_id: The identifier for the asset.

    Returns:
        A dictionary containing the open buy order details ('order_id', 'params')
        if one exists, otherwise None.

    Raises:
        TypeError: If asset_id is not a string.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."

    trade_state = load_trade_state(asset_id)
    open_order_data = trade_state.get("open_buy_order")

    if (
        open_order_data
        and isinstance(open_order_data, dict)
        and "order_id" in open_order_data
        and "params" in open_order_data
    ):
        # print(f"Loaded open buy order for {asset_id}: {open_order_data['order_id']}") # noqa: T201
        return open_order_data

    # print(f"No open buy order found for {asset_id}") # noqa: T201
    return None


def clear_open_buy_order(asset_id: str) -> None:
    """
    Clears any open buy order details for a given asset.

    Args:
        asset_id: The identifier for the asset.

    Raises:
        TypeError: If asset_id is not a string.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."

    trade_state = load_trade_state(asset_id)
    if "open_buy_order" in trade_state:
        del trade_state["open_buy_order"]
        save_trade_state(asset_id, trade_state)
        # print(f"Cleared open buy order for {asset_id}") # noqa: T201
    # else: # noqa: E701
    # print(f"No open buy order to clear for {asset_id}") # noqa: T201


def save_filled_buy_trade(asset_id: str, trade_details: Dict[str, Any]) -> None:
    """
    Saves details of a filled buy trade for a given asset.

    Args:
        asset_id: The identifier for the asset.
        trade_details: A dictionary containing details of the filled buy trade
                       (e.g., price, quantity, timestamp, associated_sell_order_ids).

    Raises:
        TypeError: If arguments are of incorrect types.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."
    assert isinstance(trade_details, dict), "trade_details must be a dictionary."
    # Ensure essential keys are present, e.g., price, quantity
    assert "price" in trade_details, "trade_details must contain 'price'."
    assert "quantity" in trade_details, "trade_details must contain 'quantity'."

    trade_state = load_trade_state(asset_id)
    trade_state["filled_buy_trade"] = trade_details
    save_trade_state(asset_id, trade_state)
    # print(f"Saved filled buy trade for {asset_id}") # noqa: T201


def load_filled_buy_trade(asset_id: str) -> Optional[Dict[str, Any]]:
    """
    Loads the details of a filled buy trade for a given asset.

    Args:
        asset_id: The identifier for the asset.

    Returns:
        A dictionary containing the filled buy trade details if one exists,
        otherwise None.

    Raises:
        TypeError: If asset_id is not a string.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."

    trade_state = load_trade_state(asset_id)
    filled_trade_data = trade_state.get("filled_buy_trade")

    if (
        filled_trade_data
        and isinstance(filled_trade_data, dict)
        and "price" in filled_trade_data
        and "quantity" in filled_trade_data
    ):  # Basic validation
        # print(f"Loaded filled buy trade for {asset_id}") # noqa: T201
        return filled_trade_data

    # print(f"No filled buy trade found for {asset_id}") # noqa: T201
    return None


def clear_filled_buy_trade(asset_id: str) -> None:
    """
    Clears any filled buy trade details for a given asset.

    Args:
        asset_id: The identifier for the asset.

    Raises:
        TypeError: If asset_id is not a string.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."

    trade_state = load_trade_state(asset_id)
    if "filled_buy_trade" in trade_state:
        del trade_state["filled_buy_trade"]
        save_trade_state(asset_id, trade_state)
        # print(f"Cleared filled buy trade for {asset_id}") # noqa: T201
    # else: # noqa: E701
    # print(f"No filled buy trade to clear for {asset_id}") # noqa: T201


def add_sell_order_to_filled_trade(
    asset_id: str, sell_order_id: str, sell_order_details: Dict[str, Any]
) -> None:
    """
    Adds a sell order's ID and details to the list of associated sell orders
    for a filled buy trade.

    Args:
        asset_id: The identifier for the asset.
        sell_order_id: The ID of the sell order to add.
        sell_order_details: A dictionary containing details of the sell order
                              (e.g., price, size, initial status).
                              It must include 'order_id'.

    Raises:
        TypeError: If arguments are of incorrect types.
        ValueError: If filled_buy_trade does not exist or sell_order_id is missing.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."
    assert (
        isinstance(sell_order_id, str) and len(sell_order_id) > 0
    ), "sell_order_id must be a non-empty string."
    assert isinstance(
        sell_order_details, dict
    ), "sell_order_details must be a dictionary."
    # Ensure sell_order_id is part of the details for consistency, though passed separately
    if (
        "order_id" not in sell_order_details
        or sell_order_details["order_id"] != sell_order_id
    ):
        sell_order_details["order_id"] = sell_order_id

    trade_state = load_trade_state(asset_id)
    filled_trade = trade_state.get("filled_buy_trade")

    if not filled_trade or not isinstance(filled_trade, dict):
        logger.error(
            f"Cannot add sell order: No filled buy trade found for {asset_id}."
        )
        raise ValueError(
            f"No filled buy trade found for {asset_id} to add sell order to."
        )

    if "associated_sell_orders" not in filled_trade:
        filled_trade["associated_sell_orders"] = []

    # Check if sell order already exists to prevent duplicates
    for so in filled_trade["associated_sell_orders"]:
        if so.get("order_id") == sell_order_id:
            logger.warning(
                f"Sell order {sell_order_id} already exists for {asset_id}. Not adding again."
            )
            return

    filled_trade["associated_sell_orders"].append(sell_order_details)
    save_trade_state(asset_id, trade_state)
    logger.info(f"Added sell order {sell_order_id} to filled trade for {asset_id}")


def update_sell_order_status_in_filled_trade(
    asset_id: str, sell_order_id: str, status: str
) -> bool:
    """
    Updates the status of a specific sell order associated with a filled buy trade.

    Args:
        asset_id: The identifier for the asset.
        sell_order_id: The ID of the sell order to update.
        status: The new status for the sell order.

    Returns:
        True if the status was updated, False otherwise (e.g., order not found).

    Raises:
        TypeError: If arguments are of incorrect types.
        ValueError: If filled_buy_trade does not exist.
    """
    assert (
        isinstance(asset_id, str) and len(asset_id) > 0
    ), "asset_id must be a non-empty string."
    assert (
        isinstance(sell_order_id, str) and len(sell_order_id) > 0
    ), "sell_order_id must be a non-empty string."
    assert (
        isinstance(status, str) and len(status) > 0
    ), "status must be a non-empty string."

    trade_state = load_trade_state(asset_id)
    filled_trade = trade_state.get("filled_buy_trade")

    if not filled_trade or not isinstance(filled_trade, dict):
        logger.error(
            f"Cannot update sell order: No filled buy trade found for {asset_id}."
        )
        raise ValueError(
            f"No filled buy trade found for {asset_id} to update sell order status."
        )

    if "associated_sell_orders" not in filled_trade or not isinstance(
        filled_trade["associated_sell_orders"], list
    ):
        logger.warning(f"No sell orders list found for {asset_id} to update status.")
        return False

    updated = False
    for sell_order in filled_trade["associated_sell_orders"]:
        if isinstance(sell_order, dict) and sell_order.get("order_id") == sell_order_id:
            sell_order["status"] = status
            updated = True
            break

    if updated:
        save_trade_state(asset_id, trade_state)
        logger.info(
            f"Updated status of sell order {sell_order_id} to '{status}' for {asset_id}"
        )
    else:
        logger.warning(
            f"Sell order {sell_order_id} not found for {asset_id} to update status."
        )

    return updated
