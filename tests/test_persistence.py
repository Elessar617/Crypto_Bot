"""
Unit tests for the persistence.py module.
"""

import unittest
import os
import json
from unittest.mock import patch, mock_open

from trading import persistence

# Define a consistent DATA_DIR for tests. Since all file operations are mocked,
# this is primarily for ensuring the mock paths are consistent.
TEST_PERSISTENCE_DIR = "tests/mock_data"


class TestPersistence(unittest.TestCase):
    """Test suite for persistence functions."""

    def setUp(self):
        """Set up for test methods."""
        # Ensure persistence module is loaded
        self.assertIsNotNone(persistence, "Persistence module failed to load.")
        # This path is used by the persistence module internally. We mock its behavior.
        self.persistence_dir_patch = patch(
            "trading.persistence.PERSISTENCE_DIR", TEST_PERSISTENCE_DIR
        )
        self.mock_persistence_dir = self.persistence_dir_patch.start()
        self.addCleanup(self.persistence_dir_patch.stop)

    @patch("trading.persistence.os.makedirs")
    @patch("trading.persistence.open", new_callable=mock_open)
    @patch("trading.persistence.json.dump")
    def test_save_trade_state_success(
        self, mock_json_dump, mock_file_open, mock_os_makedirs
    ):
        """Test save_trade_state successfully saves data."""
        asset_id = "BTC-USD"
        state_data = {"key": "value", "number": 123}
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        persistence.save_trade_state(asset_id, state_data)

        mock_os_makedirs.assert_called_once_with(TEST_PERSISTENCE_DIR, exist_ok=True)
        mock_file_open.assert_called_once_with(
            expected_file_path, "w", encoding="utf-8"
        )
        mock_json_dump.assert_called_once_with(state_data, mock_file_open(), indent=4)

    @patch("trading.persistence.os.makedirs")
    @patch("trading.persistence.open", new_callable=mock_open)
    @patch("trading.persistence.json.dump")
    def test_save_trade_state_creates_dir(
        self, mock_json_dump, mock_file_open, mock_os_makedirs
    ):
        """Test save_trade_state creates PERSISTENCE_DIR if it doesn't exist."""
        asset_id = "ETH-USD"
        state_data = {"another_key": "another_value"}
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        persistence.save_trade_state(asset_id, state_data)

        mock_os_makedirs.assert_called_once_with(TEST_PERSISTENCE_DIR, exist_ok=True)
        mock_file_open.assert_called_once_with(
            expected_file_path, "w", encoding="utf-8"
        )
        mock_json_dump.assert_called_once_with(state_data, mock_file_open(), indent=4)

    @patch("trading.persistence.os.path.exists")
    @patch("trading.persistence.open", new_callable=mock_open, read_data='{"key": "value"}')
    @patch("trading.persistence.json.load")
    def test_load_trade_state_success(
        self, mock_json_load, mock_file_open, mock_os_exists
    ):
        """Test load_trade_state successfully loads data."""
        mock_os_exists.return_value = True
        asset_id = "BTC-USD"
        expected_data = {"key": "value"}
        mock_json_load.return_value = expected_data
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        loaded_data = persistence.load_trade_state(asset_id)

        mock_os_exists.assert_called_once_with(expected_file_path)
        mock_file_open.assert_called_once_with(
            expected_file_path, "r", encoding="utf-8"
        )
        mock_json_load.assert_called_once_with(mock_file_open())
        self.assertEqual(loaded_data, expected_data)

    @patch("persistence.os.path.exists")
    def test_load_trade_state_file_not_found(self, mock_os_exists):
        """Test load_trade_state returns empty dict if file not found."""
        mock_os_exists.return_value = False
        asset_id = "LTC-USD"
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        loaded_data = persistence.load_trade_state(asset_id)

        mock_os_exists.assert_called_once_with(expected_file_path)
        self.assertEqual(loaded_data, {})

    @patch("trading.persistence.os.path.exists")
    @patch("trading.persistence.open", new_callable=mock_open, read_data="invalid json")
    @patch("trading.persistence.json.load", side_effect=json.JSONDecodeError("Error", "doc", 0))
    def test_load_trade_state_json_decode_error(
        self, mock_json_load, mock_file_open, mock_os_exists
    ):
        """Test load_trade_state returns empty dict on JSONDecodeError."""
        mock_os_exists.return_value = True
        asset_id = "XRP-USD"
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        loaded_data = persistence.load_trade_state(asset_id)

        mock_os_exists.assert_called_once_with(expected_file_path)
        mock_file_open.assert_called_once_with(
            expected_file_path, "r", encoding="utf-8"
        )
        mock_json_load.assert_called_once_with(mock_file_open())
        self.assertEqual(loaded_data, {})

    @patch("persistence.os.path.exists")
    @patch("persistence.open", new_callable=mock_open)
    @patch("persistence.json.load")
    def test_load_trade_state_corrupted_data_not_dict(
        self, mock_json_load, mock_file_open, mock_os_exists
    ):
        """Test load_trade_state returns empty dict for a non-dict file."""
        mock_os_exists.return_value = True
        asset_id = "ADA-USD"
        mock_json_load.return_value = "this is a string, not a dict"
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        loaded_data = persistence.load_trade_state(asset_id)

        mock_os_exists.assert_called_once_with(expected_file_path)
        mock_file_open.assert_called_once_with(
            expected_file_path, "r", encoding="utf-8"
        )
        mock_json_load.assert_called_once_with(mock_file_open())
        self.assertEqual(loaded_data, {})

    # --- Tests for open_buy_order helper functions ---

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_save_open_buy_order(self, mock_load_trade_state, mock_save_trade_state):
        """Test save_open_buy_order correctly structures and saves data."""
        asset_id = "BTC-USD"
        order_id = "order123"
        buy_params = {"price": "30000", "size": "0.01"}

        # Simulate load_trade_state returning an empty state or some existing state
        mock_load_trade_state.return_value = {"some_other_key": "some_value"}

        persistence.save_open_buy_order(asset_id, order_id, buy_params)

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_saved_state = {
            "some_other_key": "some_value",
            "open_buy_order": {"order_id": order_id, "params": buy_params},
        }
        mock_save_trade_state.assert_called_once_with(asset_id, expected_saved_state)

    @patch("persistence.load_trade_state")
    def test_load_open_buy_order_success(self, mock_load_trade_state):
        """Test load_open_buy_order successfully retrieves order details."""
        asset_id = "ETH-USD"
        order_details = {"order_id": "order456", "params": {"price": "2000"}}
        mock_load_trade_state.return_value = {"open_buy_order": order_details}

        result = persistence.load_open_buy_order(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        self.assertEqual(result, order_details)

    @patch("persistence.load_trade_state")
    def test_load_open_buy_order_not_found(self, mock_load_trade_state):
        """Test load_open_buy_order returns None if no open order exists."""
        asset_id = "LTC-USD"
        mock_load_trade_state.return_value = {
            "some_other_key": "data"
        }  # No 'open_buy_order' key

        result = persistence.load_open_buy_order(asset_id)
        self.assertIsNone(result)

        mock_load_trade_state.return_value = {}  # Empty state
        result = persistence.load_open_buy_order(asset_id)
        self.assertIsNone(result)

    @patch("persistence.load_trade_state")
    def test_load_open_buy_order_corrupted_data(self, mock_load_trade_state):
        """Test load_open_buy_order returns None if data is malformed."""
        asset_id = "XRP-USD"
        # Case 1: open_buy_order is not a dict
        mock_load_trade_state.return_value = {"open_buy_order": "not_a_dict"}
        self.assertIsNone(persistence.load_open_buy_order(asset_id))

        # Case 2: open_buy_order is a dict but missing 'order_id'
        mock_load_trade_state.return_value = {"open_buy_order": {"params": {}}}
        self.assertIsNone(persistence.load_open_buy_order(asset_id))

        # Case 3: open_buy_order is a dict but missing 'params'
        mock_load_trade_state.return_value = {"open_buy_order": {"order_id": "123"}}
        self.assertIsNone(persistence.load_open_buy_order(asset_id))

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_clear_open_buy_order_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test clear_open_buy_order removes the order if it exists."""
        asset_id = "ADA-USD"
        initial_state = {
            "open_buy_order": {"order_id": "order789", "params": {}},
            "other_data": "remains",
        }
        mock_load_trade_state.return_value = initial_state

        persistence.clear_open_buy_order(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_saved_state = {"other_data": "remains"}
        mock_save_trade_state.assert_called_once_with(asset_id, expected_saved_state)

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_clear_open_buy_order_not_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test clear_open_buy_order does nothing if order doesn't exist."""
        asset_id = "SOL-USD"
        initial_state = {"other_data": "remains"}  # No open_buy_order
        mock_load_trade_state.return_value = initial_state

        persistence.clear_open_buy_order(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_not_called()

    # --- Tests for filled_buy_trade helper functions ---

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_save_filled_buy_trade(self, mock_load_trade_state, mock_save_trade_state):
        """Test save_filled_buy_trade correctly structures and saves data."""
        asset_id = "DOT-USD"
        trade_details = {
            "price": "7.5",
            "quantity": "10",
            "timestamp": "2023-01-01T00:00:00Z",
        }
        mock_load_trade_state.return_value = {"some_other_data": "value"}

        persistence.save_filled_buy_trade(asset_id, trade_details)

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_saved_state = {
            "some_other_data": "value",
            "filled_buy_trade": trade_details,
        }
        mock_save_trade_state.assert_called_once_with(asset_id, expected_saved_state)

    @patch("persistence.load_trade_state")
    def test_load_filled_buy_trade_success(self, mock_load_trade_state):
        """Test load_filled_buy_trade successfully retrieves trade details."""
        asset_id = "AVAX-USD"
        trade_details = {"price": "15", "quantity": "5", "id": "trade001"}
        mock_load_trade_state.return_value = {"filled_buy_trade": trade_details}

        result = persistence.load_filled_buy_trade(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        self.assertEqual(result, trade_details)

    @patch("persistence.load_trade_state")
    def test_load_filled_buy_trade_not_found(self, mock_load_trade_state):
        """Test load_filled_buy_trade returns None if no filled trade exists."""
        asset_id = "MATIC-USD"
        mock_load_trade_state.return_value = {
            "open_buy_order": {}
        }  # No 'filled_buy_trade'
        self.assertIsNone(persistence.load_filled_buy_trade(asset_id))

        mock_load_trade_state.reset_mock()
        mock_load_trade_state.return_value = {}  # Empty state
        self.assertIsNone(persistence.load_filled_buy_trade(asset_id))

    @patch("persistence.load_trade_state")
    def test_load_filled_buy_trade_corrupted_data(self, mock_load_trade_state):
        """Test load_filled_buy_trade returns None if data is malformed."""
        asset_id = "LINK-USD"
        # Case 1: filled_buy_trade is not a dict
        mock_load_trade_state.return_value = {"filled_buy_trade": "not_a_dict"}
        self.assertIsNone(persistence.load_filled_buy_trade(asset_id))

        # Case 2: filled_buy_trade is a dict but missing 'price'
        mock_load_trade_state.reset_mock()
        mock_load_trade_state.return_value = {"filled_buy_trade": {"quantity": "10"}}
        self.assertIsNone(persistence.load_filled_buy_trade(asset_id))

        # Case 3: filled_buy_trade is a dict but missing 'quantity'
        mock_load_trade_state.reset_mock()
        mock_load_trade_state.return_value = {"filled_buy_trade": {"price": "100"}}
        self.assertIsNone(persistence.load_filled_buy_trade(asset_id))

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_clear_filled_buy_trade_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test clear_filled_buy_trade removes the trade if it exists."""
        asset_id = "UNI-USD"
        initial_state = {
            "filled_buy_trade": {"price": "5", "quantity": "20"},
            "other_info": "test",
        }
        mock_load_trade_state.return_value = initial_state

        persistence.clear_filled_buy_trade(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_saved_state = {"other_info": "test"}
        mock_save_trade_state.assert_called_once_with(asset_id, expected_saved_state)

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_clear_filled_buy_trade_not_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test clear_filled_buy_trade does nothing if trade doesn't exist."""
        asset_id = "ICP-USD"
        initial_state = {"some_data": "info"}  # No filled_buy_trade
        mock_load_trade_state.return_value = initial_state

        persistence.clear_filled_buy_trade(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_not_called()

    # --- Tests for associated_sell_orders helper functions ---

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_add_sell_order_to_filled_trade_success(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test adding a sell order to an existing filled trade."""
        asset_id = "ATOM-USD"
        sell_order_id = "sell789"
        sell_order_details = {
            "order_id": sell_order_id,
            "price": "12",
            "status": "OPEN",
        }
        initial_filled_trade = {
            "price": "10",
            "quantity": "5",
            "associated_sell_orders": [],
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        persistence.add_sell_order_to_filled_trade(
            asset_id, sell_order_id, sell_order_details
        )

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_filled_trade = {
            "price": "10",
            "quantity": "5",
            "associated_sell_orders": [sell_order_details],
        }
        mock_save_trade_state.assert_called_once_with(
            asset_id, {"filled_buy_trade": expected_filled_trade}
        )

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_add_sell_order_creates_list_if_not_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test add_sell_order creates associated_sell_orders list if it's missing."""
        asset_id = "XTZ-USD"
        sell_order_id = "sell101"
        sell_order_details = {
            "order_id": sell_order_id,
            "price": "1.5",
            "status": "NEW",
        }
        # No 'associated_sell_orders' key initially
        initial_filled_trade = {"price": "1.2", "quantity": "100"}
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        persistence.add_sell_order_to_filled_trade(
            asset_id, sell_order_id, sell_order_details
        )

        expected_filled_trade = {
            "price": "1.2",
            "quantity": "100",
            "associated_sell_orders": [sell_order_details],
        }
        mock_save_trade_state.assert_called_once_with(
            asset_id, {"filled_buy_trade": expected_filled_trade}
        )

    @patch("persistence.load_trade_state")
    def test_add_sell_order_no_filled_trade(self, mock_load_trade_state):
        """Test add_sell_order raises ValueError if no filled trade exists."""
        asset_id = "FIL-USD"
        mock_load_trade_state.return_value = {}  # No filled_buy_trade
        with self.assertRaisesRegex(
            ValueError, f"No filled buy trade found for {asset_id}"
        ):
            persistence.add_sell_order_to_filled_trade(
                asset_id, "sell112", {"order_id": "sell112"}
            )

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_add_sell_order_duplicate_not_added(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test add_sell_order does not add a duplicate sell order ID."""
        asset_id = "GRT-USD"
        sell_order_id = "sellDuplicate"
        existing_sell_order = {
            "order_id": sell_order_id,
            "price": "0.3",
            "status": "OPEN",
        }
        sell_order_details_new = {
            "order_id": sell_order_id,
            "price": "0.31",
            "status": "PENDING",
        }  # Same ID

        initial_filled_trade = {
            "price": "0.25",
            "quantity": "1000",
            "associated_sell_orders": [existing_sell_order],
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        persistence.add_sell_order_to_filled_trade(
            asset_id, sell_order_id, sell_order_details_new
        )

        mock_save_trade_state.assert_not_called()  # Not saved if duplicate

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_update_sell_order_status_success(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test updating status of an existing sell order."""
        asset_id = "AAVE-USD"
        sell_order_id = "sellOrderToUpdate"
        new_status = "FILLED"
        initial_sell_orders = [
            {"order_id": "sellOrderOther", "status": "OPEN"},
            {"order_id": sell_order_id, "status": "OPEN"},
        ]
        initial_filled_trade = {
            "price": "100",
            "quantity": "1",
            "associated_sell_orders": initial_sell_orders,
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        result = persistence.update_sell_order_status_in_filled_trade(
            asset_id, sell_order_id, new_status
        )
        self.assertTrue(result)

        expected_sell_orders = [
            {"order_id": "sellOrderOther", "status": "OPEN"},
            {"order_id": sell_order_id, "status": new_status},
        ]
        expected_filled_trade = {
            "price": "100",
            "quantity": "1",
            "associated_sell_orders": expected_sell_orders,
        }
        mock_save_trade_state.assert_called_once_with(
            asset_id, {"filled_buy_trade": expected_filled_trade}
        )

    @patch("persistence.load_trade_state")
    def test_update_sell_order_status_no_filled_trade(self, mock_load_trade_state):
        """Test update_sell_order_status raises ValueError if no filled trade."""
        asset_id = "COMP-USD"
        mock_load_trade_state.return_value = {}
        with self.assertRaisesRegex(
            ValueError, f"No filled buy trade found for {asset_id}"
        ):
            persistence.update_sell_order_status_in_filled_trade(
                asset_id, "anyID", "FILLED"
            )

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_update_sell_order_status_no_sell_orders_list(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test update returns False if associated_sell_orders list is missing."""
        asset_id = "SNX-USD"
        # 'associated_sell_orders' key is missing
        initial_filled_trade = {"price": "3", "quantity": "50"}
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        result = persistence.update_sell_order_status_in_filled_trade(
            asset_id, "anyID", "FILLED"
        )
        self.assertFalse(result)
        mock_save_trade_state.assert_not_called()

    @patch("trading.persistence.save_trade_state")
    @patch("trading.persistence.load_trade_state")
    def test_update_sell_order_status_order_not_found(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test update returns False if specific sell order ID is not found."""
        asset_id = "MKR-USD"
        initial_sell_orders = [{"order_id": "actualSellID", "status": "OPEN"}]
        initial_filled_trade = {
            "price": "1000",
            "quantity": "0.1",
            "associated_sell_orders": initial_sell_orders,
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        result = persistence.update_sell_order_status_in_filled_trade(
            asset_id, "nonExistentID", "FILLED"
        )
        self.assertFalse(result)
        mock_save_trade_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
