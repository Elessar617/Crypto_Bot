"""Handles saving and loading of persistent bot state, like buy prices."""

import json
import os
import time
from typing import Any, Dict, List, Optional, cast

from .config import PERSISTENCE_DIR
from .logger import get_logger


class PersistenceManager:
    """Manages reading and writing the bot's trade state to the filesystem."""

    def __init__(
        self, persistence_dir: Optional[str] = None, logger: Optional[Any] = None
    ) -> None:
        """
        Initializes the PersistenceManager.

        Args:
            persistence_dir: The directory for storing persistence files.
                             Defaults to PERSISTENCE_DIR from config.
            logger: An optional logger instance.
        """
        self.persistence_dir = persistence_dir if persistence_dir else PERSISTENCE_DIR
        self.logger = logger if logger else get_logger()

    def _get_file_path(self, asset_id: str) -> str:
        """Constructs the file path for the asset's state file."""
        return os.path.join(self.persistence_dir, f"{asset_id}_trade_state.json")

    def save_trade_state(self, asset_id: str, state_data: Dict[str, Any]) -> None:
        """
        Saves the provided state_data dictionary to a JSON file.

        Args:
            asset_id: The identifier for the asset (e.g., 'BTC-USD').
            state_data: A dictionary containing the trade state to save.

        Raises:
            IOError: If there is an error writing to the file.
            TypeError: If arguments have incorrect types or content is not serializable.
        """
        assert (
            isinstance(asset_id, str) and asset_id
        ), "asset_id must be a non-empty string."
        assert isinstance(state_data, dict), "state_data must be a dictionary."

        file_path = self._get_file_path(asset_id)
        assert os.path.isabs(file_path) or file_path.startswith(
            self.persistence_dir
        ), "File path construction seems incorrect."

        try:
            os.makedirs(self.persistence_dir, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
            self.logger.debug(
                f"Successfully saved trade state for {asset_id} to {file_path}"
            )
        except (IOError, OSError) as e:
            self.logger.error(f"Error writing to {file_path}: {e}", exc_info=True)
            raise IOError(f"Failed to write to {file_path}.") from e
        except TypeError as e:
            self.logger.error(
                f"TypeError during JSON serialization for {asset_id}: {e}",
                exc_info=True,
            )
            raise TypeError("state_data contains non-serializable content.") from e

    def load_trade_state(self, asset_id: str) -> Dict[str, Any]:
        """
        Loads trade state from a JSON file.

        Args:
            asset_id: The identifier for the asset (e.g., 'BTC-USD').

        Returns:
            A dictionary with the trade state, or an empty dict if not found/invalid.
        """
        assert (
            isinstance(asset_id, str) and asset_id
        ), "asset_id must be a non-empty string."
        file_path = self._get_file_path(asset_id)

        if not os.path.exists(file_path):
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                if not isinstance(state_data, dict):
                    self.logger.error(
                        f"Corrupted state file for {asset_id}: content is not a dict."
                    )
                    return {}
                self.logger.debug(f"Successfully loaded trade state for {asset_id}")
                return state_data
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Error decoding JSON from {file_path}: {e}", exc_info=True
            )
            return {}
        except IOError as e:
            self.logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            return {}

    def save_open_buy_order(
        self, asset_id: str, order_id: str, order_details: Dict[str, Any]
    ) -> None:
        """Saves details of an open buy order."""
        trade_state = self.load_trade_state(asset_id)
        trade_state["open_buy_order"] = {"order_id": order_id, "params": order_details}
        self.save_trade_state(asset_id, trade_state)

    def load_open_buy_order(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Loads the details of an open buy order."""
        trade_state = self.load_trade_state(asset_id)
        open_order = trade_state.get("open_buy_order")
        if (
            not isinstance(open_order, dict)
            or "order_id" not in open_order
            or "params" not in open_order
        ):
            return None
        return cast(Optional[Dict[str, Any]], open_order)

    def clear_open_buy_order(self, asset_id: str) -> None:
        """Clears any open buy order details."""
        trade_state = self.load_trade_state(asset_id)
        if "open_buy_order" in trade_state:
            del trade_state["open_buy_order"]
            self.save_trade_state(asset_id, trade_state)

    def save_filled_buy_trade(
        self,
        asset_id: str,
        buy_order_id: str,
        filled_order: Dict[str, Any],
        sell_orders_params: List[Dict[str, Any]],
    ) -> None:
        """Saves details of a filled buy trade."""
        trade_state = self.load_trade_state(asset_id)
        trade_details = {
            "buy_order_id": buy_order_id,
            "timestamp": filled_order.get("created_time", time.time()),
            "buy_price": str(filled_order.get("average_filled_price")),
            "buy_quantity": str(filled_order.get("filled_size")),
            "associated_sell_orders": [],
            "sell_orders_params": sell_orders_params,
        }
        trade_state.pop("open_buy_order", None)  # Clear the now-filled open buy order
        trade_state["filled_buy_trade"] = trade_details
        self.save_trade_state(asset_id, trade_state)

    def load_filled_buy_trade(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Loads the details of a filled buy trade."""
        trade_state = self.load_trade_state(asset_id)
        filled_trade = trade_state.get("filled_buy_trade")
        if not isinstance(filled_trade, dict):
            return None
        return cast(Optional[Dict[str, Any]], filled_trade)

    def clear_filled_buy_trade(self, asset_id: str) -> None:
        """Clears any filled buy trade details."""
        trade_state = self.load_trade_state(asset_id)
        if "filled_buy_trade" in trade_state:
            del trade_state["filled_buy_trade"]
            self.save_trade_state(asset_id, trade_state)

    def add_sell_order_to_filled_trade(
        self, asset_id: str, buy_order_id: str, sell_order_details: Dict[str, Any]
    ) -> None:
        """Adds a sell order to a filled buy trade's sell order list."""
        trade_state = self.load_trade_state(asset_id)
        filled_trade = trade_state.get("filled_buy_trade")

        if not filled_trade or filled_trade.get("buy_order_id") != buy_order_id:
            found_id = filled_trade.get("buy_order_id") if filled_trade else "None"
            self.logger.error(
                "Attempted to add sell order to non-matching or "
                f"non-existent buy trade for {asset_id} "
                f"(expected {buy_order_id}, found {found_id})."
            )
            raise ValueError(f"No matching filled buy trade found for {asset_id}.")

        if "associated_sell_orders" not in filled_trade:
            filled_trade["associated_sell_orders"] = []

        sell_order_id = sell_order_details.get("order_id")
        if any(
            so.get("order_id") == sell_order_id
            for so in filled_trade["associated_sell_orders"]
        ):
            self.logger.warning(
                f"Sell order {sell_order_id} already exists for {asset_id}."
            )
            return

        filled_trade["associated_sell_orders"].append(sell_order_details)
        self.save_trade_state(asset_id, trade_state)
        self.logger.info(
            f"Added sell order {sell_order_id} to filled trade for {asset_id}"
        )

    def update_sell_order_status_in_filled_trade(
        self, asset_id: str, buy_order_id: str, sell_order_id: str, new_status: str
    ) -> bool:
        """Updates the status of a specific sell order."""
        trade_state = self.load_trade_state(asset_id)
        filled_trade = trade_state.get("filled_buy_trade")

        if not filled_trade or filled_trade.get("buy_order_id") != buy_order_id:
            raise ValueError(f"No matching filled buy trade found for {asset_id}.")

        if "associated_sell_orders" not in filled_trade:
            self.logger.warning(f"No sell orders found for {asset_id} to update.")
            return False

        updated = False
        for sell_order in filled_trade["associated_sell_orders"]:
            if sell_order.get("order_id") == sell_order_id:
                sell_order["status"] = new_status
                updated = True
                break

        if updated:
            self.save_trade_state(asset_id, trade_state)
            self.logger.info(
                f"Updated status of sell order {sell_order_id} "
                f"to '{new_status}' for {asset_id}"
            )
        else:
            self.logger.warning(
                f"Sell order {sell_order_id} not found for {asset_id} to update status."
            )

        return updated
