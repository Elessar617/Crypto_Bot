"""
Unit tests for the persistence.py module.
"""

import unittest
import os
import shutil
import pytest
from unittest.mock import mock_open, patch, MagicMock
from trading.persistence import PersistenceManager

# Define a consistent DATA_DIR for tests. Since all file operations are mocked,
# this is primarily for ensuring the mock paths are consistent.
TEST_PERSISTENCE_DIR = "tests/mock_data"


class TestPersistenceManager(unittest.TestCase):
    """Test suite for persistence functions."""

    def setUp(self):
        """Set up test environment."""
        # Ensure the test directory is clean before each test
        if os.path.exists(TEST_PERSISTENCE_DIR):
            shutil.rmtree(TEST_PERSISTENCE_DIR)
        self.persistence_manager = PersistenceManager(
            persistence_dir=TEST_PERSISTENCE_DIR
        )

    @patch("trading.persistence.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_trade_state_success(
        self, mock_json_dump, mock_file_open, mock_os_makedirs
    ):
        """Test save_trade_state successfully saves data."""
        asset_id = "BTC-USD"
        state_data = {"key": "value", "number": 123}
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        self.persistence_manager.save_trade_state(asset_id, state_data)

        mock_os_makedirs.assert_called_once_with(TEST_PERSISTENCE_DIR, exist_ok=True)
        mock_file_open.assert_called_once_with(
            expected_file_path, "w", encoding="utf-8"
        )
        mock_json_dump.assert_called_once_with(state_data, mock_file_open(), indent=4)

    @patch("trading.persistence.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_trade_state_creates_dir(
        self, mock_json_dump, mock_file_open, mock_os_makedirs
    ):
        """Test save_trade_state creates PERSISTENCE_DIR if it doesn't exist."""
        asset_id = "ETH-USD"
        state_data = {"another_key": "another_value"}
        expected_file_path = os.path.join(
            TEST_PERSISTENCE_DIR, f"{asset_id}_trade_state.json"
        )

        self.persistence_manager.save_trade_state(asset_id, state_data)

        mock_os_makedirs.assert_called_once_with(TEST_PERSISTENCE_DIR, exist_ok=True)
        mock_file_open.assert_called_once_with(
            expected_file_path, "w", encoding="utf-8"
        )
        mock_json_dump.assert_called_once_with(state_data, mock_file_open(), indent=4)

    @patch("trading.persistence.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    @patch("json.load")
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

        loaded_data = self.persistence_manager.load_trade_state(asset_id)

        mock_os_exists.assert_called_once_with(expected_file_path)
        mock_file_open.assert_called_once_with(
            expected_file_path, "r", encoding="utf-8"
        )
        mock_json_load.assert_called_once_with(mock_file_open())
        self.assertEqual(loaded_data, expected_data)

    @patch("os.path.exists", return_value=False)
    def test_load_trade_state_file_not_found(self, mock_exists):
        """Test load_trade_state returns empty dict if file doesn't exist."""
        self.assertEqual(self.persistence_manager.load_trade_state("NO-ASSET"), {})
        mock_exists.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    def test_load_trade_state_json_decode_error(self, mock_file, mock_exists):
        """Test load_trade_state returns empty dict on JSON decode error."""
        self.assertEqual(self.persistence_manager.load_trade_state("BAD-JSON"), {})
        mock_exists.assert_called_once()

    @patch("builtins.open", new_callable=mock_open, read_data='"not a dict"')
    @patch("os.path.exists", return_value=True)
    def test_load_trade_state_corrupted_data_not_dict(self, mock_exists, mock_file):
        """Test load_trade_state returns empty dict if data is not a dictionary."""
        self.assertEqual(self.persistence_manager.load_trade_state("CORRUPTED"), {})

    # --- Tests for open_buy_order helper functions ---

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_save_open_buy_order(self, mock_load_trade_state, mock_save_trade_state):
        """Test save_open_buy_order correctly structures and saves data."""
        asset_id = "BTC-USD"
        order_id = "order123"
        buy_params = {"price": "30000", "size": "0.01"}

        # Simulate load_trade_state returning an empty state or some existing state
        mock_load_trade_state.return_value = {"some_other_key": "some_value"}

        self.persistence_manager.save_open_buy_order(asset_id, order_id, buy_params)

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_saved_state = {
            "some_other_key": "some_value",
            "open_buy_order": {"order_id": order_id, "params": buy_params},
        }
        mock_save_trade_state.assert_called_once_with(asset_id, expected_saved_state)

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_open_buy_order_success(self, mock_load_trade_state):
        """Test load_open_buy_order successfully retrieves order details."""
        asset_id = "ETH-USD"
        order_details = {"order_id": "order456", "params": {"price": "2000"}}
        mock_load_trade_state.return_value = {"open_buy_order": order_details}

        result = self.persistence_manager.load_open_buy_order(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        self.assertEqual(result, order_details)

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_open_buy_order_not_found(self, mock_load_trade_state):
        """Test load_open_buy_order returns None if no open order exists."""
        asset_id = "LTC-USD"
        mock_load_trade_state.return_value = {
            "some_other_key": "data"
        }  # No 'open_buy_order' key

        result = self.persistence_manager.load_open_buy_order(asset_id)
        self.assertIsNone(result)

        mock_load_trade_state.return_value = {}  # Empty state
        result = self.persistence_manager.load_open_buy_order(asset_id)
        self.assertIsNone(result)

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_open_buy_order_corrupted_data(self, mock_load_trade_state):
        """Test load_open_buy_order returns None if data is malformed."""
        asset_id = "ADA-USD"
        mock_load_trade_state.return_value = {"open_buy_order": "not_a_dict"}
        self.assertIsNone(self.persistence_manager.load_open_buy_order(asset_id))

        # Case 3: open_buy_order is a dict but missing 'params'
        mock_load_trade_state.return_value = {"open_buy_order": {"order_id": "123"}}
        self.assertIsNone(self.persistence_manager.load_open_buy_order(asset_id))

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
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

        self.persistence_manager.clear_open_buy_order(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_saved_state = {"other_data": "remains"}
        mock_save_trade_state.assert_called_once_with(asset_id, expected_saved_state)

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_clear_open_buy_order_not_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test clear_open_buy_order does nothing if order doesn't exist."""
        asset_id = "SOL-USD"
        initial_state = {"other_data": "remains"}  # No open_buy_order
        mock_load_trade_state.return_value = initial_state

        self.persistence_manager.clear_open_buy_order(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_not_called()

    # --- Tests for filled_buy_trade helper functions ---

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_save_filled_buy_trade(self, mock_load_trade_state, mock_save_trade_state):
        """Test save_filled_buy_trade correctly structures and saves data."""
        asset_id = "DOT-USD"
        buy_order_id = "buy-dot-123"
        filled_order = {
            "average_filled_price": "7.5",
            "filled_size": "10",
            "created_time": "2023-01-01T00:00:00Z",
        }
        sell_params = [{"price": "8.0"}]
        mock_load_trade_state.return_value = {"some_other_data": "value"}

        self.persistence_manager.save_filled_buy_trade(
            asset_id, buy_order_id, filled_order, sell_params
        )

        mock_load_trade_state.assert_called_once_with(asset_id)
        # Correctly check the structure saved by the method
        saved_state = mock_save_trade_state.call_args[0][1]
        self.assertIn("filled_buy_trade", saved_state)
        self.assertEqual(saved_state["filled_buy_trade"]["buy_order_id"], buy_order_id)

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_filled_buy_trade_success(self, mock_load_trade_state):
        """Test load_filled_buy_trade successfully retrieves trade details."""
        asset_id = "AVAX-USD"
        trade_details = {"price": "15", "quantity": "5", "id": "trade001"}
        mock_load_trade_state.return_value = {"filled_buy_trade": trade_details}

        result = self.persistence_manager.load_filled_buy_trade(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        self.assertEqual(result, trade_details)

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_filled_buy_trade_not_found(self, mock_load_trade_state):
        """Test load_filled_buy_trade returns None if no filled trade exists."""
        asset_id = "MATIC-USD"
        mock_load_trade_state.return_value = {
            "open_buy_order": {}
        }  # No 'filled_buy_trade'
        self.assertIsNone(self.persistence_manager.load_filled_buy_trade(asset_id))

        mock_load_trade_state.reset_mock()
        mock_load_trade_state.return_value = {}  # Empty state
        self.assertIsNone(self.persistence_manager.load_filled_buy_trade(asset_id))

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_filled_buy_trade_corrupted_data(self, mock_load_trade_state):
        """Test load_filled_buy_trade returns None if data is malformed."""
        asset_id = "LINK-USD"
        mock_load_trade_state.return_value = {"filled_buy_trade": "not_a_dict"}
        self.assertIsNone(self.persistence_manager.load_filled_buy_trade(asset_id))

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
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

        self.persistence_manager.clear_filled_buy_trade(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        expected_saved_state = {"other_info": "test"}
        mock_save_trade_state.assert_called_once_with(asset_id, expected_saved_state)

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_clear_filled_buy_trade_not_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test clear_filled_buy_trade does nothing if trade doesn't exist."""
        asset_id = "ICP-USD"
        initial_state = {"some_data": "info"}  # No filled_buy_trade
        mock_load_trade_state.return_value = initial_state

        self.persistence_manager.clear_filled_buy_trade(asset_id)

        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_not_called()

    # --- Tests for associated_sell_orders helper functions ---

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_to_filled_trade_success(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test adding a sell order to an existing filled trade."""
        asset_id = "ATOM-USD"
        buy_order_id = "buy-atom-456"
        sell_order_id = "sell789"
        sell_order_details = {
            "order_id": sell_order_id,
            "price": "12",
            "status": "OPEN",
        }
        initial_filled_trade = {
            "buy_order_id": buy_order_id,
            "price": "10",
            "quantity": "5",
            "associated_sell_orders": [],
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        self.persistence_manager.add_sell_order_to_filled_trade(
            asset_id, buy_order_id, sell_order_details
        )

        mock_load_trade_state.assert_called_once_with(asset_id)
        saved_state = mock_save_trade_state.call_args[0][1]
        self.assertEqual(
            saved_state["filled_buy_trade"]["associated_sell_orders"],
            [sell_order_details],
        )

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_creates_list_if_not_exists(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test add_sell_order creates associated_sell_orders list if it's missing."""
        asset_id = "XTZ-USD"
        buy_order_id = "buy-xtz-789"
        sell_order_id = "sell101"
        sell_order_details = {
            "order_id": sell_order_id,
            "price": "1.5",
            "status": "NEW",
        }
        initial_filled_trade = {
            "buy_order_id": buy_order_id,
            "price": "1.2",
            "quantity": "100",
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        self.persistence_manager.add_sell_order_to_filled_trade(
            asset_id, buy_order_id, sell_order_details
        )

        saved_state = mock_save_trade_state.call_args[0][1]
        self.assertEqual(
            saved_state["filled_buy_trade"]["associated_sell_orders"],
            [sell_order_details],
        )

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_no_filled_trade(self, mock_load_trade_state):
        """Test add_sell_order raises ValueError if no filled trade exists."""
        asset_id = "FIL-USD"
        mock_load_trade_state.return_value = {}  # No filled_buy_trade
        with self.assertRaisesRegex(
            ValueError, f"No matching filled buy trade found for {asset_id}."
        ):
            self.persistence_manager.add_sell_order_to_filled_trade(
                asset_id, "any-buy-id", {"order_id": "sell112"}
            )

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_duplicate_not_added(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test add_sell_order does not add a duplicate sell order ID."""
        asset_id = "GRT-USD"
        buy_order_id = "buy-grt-333"
        sell_order_id = "sellDuplicate"
        existing_sell_order = {
            "order_id": sell_order_id,
            "price": "0.3",
            "status": "OPEN",
        }
        initial_filled_trade = {
            "buy_order_id": buy_order_id,
            "price": "0.25",
            "quantity": "1000",
            "associated_sell_orders": [existing_sell_order],
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        self.persistence_manager.add_sell_order_to_filled_trade(
            asset_id, buy_order_id, existing_sell_order
        )

        mock_save_trade_state.assert_not_called()  # Not saved if duplicate

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_update_sell_order_status_success(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test updating status of an existing sell order."""
        asset_id = "AAVE-USD"
        buy_order_id = "buy-aave-111"
        sell_order_id = "sellOrderToUpdate"
        new_status = "FILLED"
        initial_sell_orders = [
            {"order_id": "sellOrderOther", "status": "OPEN"},
            {"order_id": sell_order_id, "status": "OPEN"},
        ]
        initial_filled_trade = {
            "buy_order_id": buy_order_id,
            "price": "100",
            "quantity": "1",
            "associated_sell_orders": initial_sell_orders,
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        result = self.persistence_manager.update_sell_order_status_in_filled_trade(
            asset_id, buy_order_id, sell_order_id, new_status
        )
        self.assertTrue(result)

        saved_state = mock_save_trade_state.call_args[0][1]
        updated_order = next(
            order
            for order in saved_state["filled_buy_trade"]["associated_sell_orders"]
            if order["order_id"] == sell_order_id
        )
        self.assertEqual(updated_order["status"], new_status)

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_update_sell_order_status_no_filled_trade(self, mock_load_trade_state):
        """Test update_sell_order_status raises ValueError if no filled trade."""
        asset_id = "COMP-USD"
        mock_load_trade_state.return_value = {}
        with self.assertRaisesRegex(
            ValueError, f"No matching filled buy trade found for {asset_id}."
        ):
            self.persistence_manager.update_sell_order_status_in_filled_trade(
                asset_id, "any-buy-id", "anyID", "FILLED"
            )

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_update_sell_order_status_no_sell_orders_list(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test update returns False if associated_sell_orders list is missing."""
        asset_id = "SNX-USD"
        buy_order_id = "buy-snx-222"
        initial_filled_trade = {
            "buy_order_id": buy_order_id,
            "price": "3",
            "quantity": "50",
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        result = self.persistence_manager.update_sell_order_status_in_filled_trade(
            asset_id, buy_order_id, "anyID", "FILLED"
        )
        self.assertFalse(result)
        mock_save_trade_state.assert_not_called()

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_update_sell_order_status_order_not_found(
        self, mock_load_trade_state, mock_save_trade_state
    ):
        """Test update returns False if specific sell order ID is not found."""
        asset_id = "MKR-USD"
        buy_order_id = "buy-mkr-444"
        initial_sell_orders = [{"order_id": "actualSellID", "status": "OPEN"}]
        initial_filled_trade = {
            "buy_order_id": buy_order_id,
            "price": "1000",
            "quantity": "0.1",
            "associated_sell_orders": initial_sell_orders,
        }
        mock_load_trade_state.return_value = {"filled_buy_trade": initial_filled_trade}

        result = self.persistence_manager.update_sell_order_status_in_filled_trade(
            asset_id, buy_order_id, "nonExistentID", "FILLED"
        )
        self.assertFalse(result)
        mock_save_trade_state.assert_not_called()


@pytest.fixture
def persistence_manager(tmp_path):
    """Provides a PersistenceManager instance with a temporary directory."""
    logger_mock = MagicMock()
    return PersistenceManager(persistence_dir=str(tmp_path), logger=logger_mock)


def test_save_trade_state_empty_asset_id_raises_error(persistence_manager):
    """Kill mutant #3 & #4: Test that an empty asset_id raises an AssertionError."""
    with pytest.raises(
        AssertionError, match=r"^asset_id must be a non-empty string\.$"
    ):
        persistence_manager.save_trade_state("", {"key": "value"})


def test_save_trade_state_invalid_state_data_raises_error(persistence_manager):
    """Kill mutant #5: Test that non-dict state_data raises an AssertionError."""
    with pytest.raises(AssertionError, match=r"^state_data must be a dictionary\.$"):
        persistence_manager.save_trade_state("test-asset", "not-a-dict")


def test_save_trade_state_bad_path_raises_error(persistence_manager):
    """Kill mutant #8: Test that a bad file path raises an AssertionError."""
    with patch.object(
        persistence_manager, "_get_file_path", return_value="some/relative/path"
    ):
        with pytest.raises(
            AssertionError, match=r"^File path construction seems incorrect\.$"
        ):
            persistence_manager.save_trade_state("test-asset", {"key": "value"})


def test_save_trade_state_io_error_logs_traceback(persistence_manager):
    """Kill mutant #13: Test that IOError on save logs with exc_info=True."""
    asset_id = "test-asset"
    state_data = {"key": "value"}

    with patch("builtins.open", side_effect=IOError("Disk full")):
        with pytest.raises(IOError):
            persistence_manager.save_trade_state(asset_id, state_data)

    persistence_manager.logger.error.assert_called()
    args, kwargs = persistence_manager.logger.error.call_args
    assert "exc_info" in kwargs
    assert kwargs["exc_info"] is True


def test_save_trade_state_type_error_logs_traceback(persistence_manager):
    """Kill mutants #14 & #15: Test TypeError on save logs with exc_info=True."""
    asset_id = "test-asset"
    # A set is not JSON-serializable
    state_data = {"key": {1, 2, 3}}

    with pytest.raises(
        TypeError, match=r"^state_data contains non-serializable content\.$"
    ):
        persistence_manager.save_trade_state(asset_id, state_data)

    persistence_manager.logger.error.assert_called()
    args, kwargs = persistence_manager.logger.error.call_args
    assert "exc_info" in kwargs
    assert kwargs["exc_info"] is True


def test_load_trade_state_empty_asset_id_raises_error(persistence_manager):
    """Kill mutants #16 & #17: Test that an empty asset_id raises an AssertionError."""
    with pytest.raises(
        AssertionError, match=r"^asset_id must be a non-empty string\.$"
    ):
        persistence_manager.load_trade_state("")


def test_load_trade_state_json_decode_error_logs_traceback(persistence_manager):
    """Kill mutant #24: Test that JSONDecodeError on load logs with exc_info=True."""
    asset_id = "test-asset"
    mock_file_content = "this is not valid json"

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            result = persistence_manager.load_trade_state(asset_id)

    assert result == {}
    persistence_manager.logger.error.assert_called()
    args, kwargs = persistence_manager.logger.error.call_args
    assert "exc_info" in kwargs
    assert kwargs["exc_info"] is True


def test_load_trade_state_io_error_logs_traceback(persistence_manager):
    """Kill mutant #25: Test that IOError on load logs with exc_info=True."""
    asset_id = "test-asset"

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            result = persistence_manager.load_trade_state(asset_id)

    assert result == {}
    persistence_manager.logger.error.assert_called()
    args, kwargs = persistence_manager.logger.error.call_args
    assert "exc_info" in kwargs
    assert kwargs["exc_info"] is True


def test_save_filled_buy_trade_verifies_data_structure(persistence_manager):
    """Test that save_filled_buy_trade saves the correct data structure."""
    asset_id = "BTC-USD"
    buy_order_id = "buy123"
    filled_order = {
        "created_time": "2023-01-01T12:00:00Z",
        "average_filled_price": "50000.00",
        "filled_size": "0.1",
    }
    sell_orders_params = [{"price": "51000.00", "size": "0.1"}]

    with patch.object(persistence_manager, "save_trade_state") as mock_save:
        persistence_manager.save_filled_buy_trade(
            asset_id, buy_order_id, filled_order, sell_orders_params
        )

    mock_save.assert_called_once()
    saved_data = mock_save.call_args[0][1]
    filled_trade = saved_data["filled_buy_trade"]

    assert filled_trade["buy_order_id"] == buy_order_id
    assert filled_trade["timestamp"] == "2023-01-01T12:00:00Z"
    assert filled_trade["buy_price"] == "50000.00"
    assert filled_trade["buy_quantity"] == "0.1"
    assert filled_trade["associated_sell_orders"] == []
    assert filled_trade["sell_orders_params"] == sell_orders_params


def test_add_sell_order_to_mismatched_buy_trade_logs_error(persistence_manager):
    """Kill mutant #72: Test error logging for mismatched buy trade."""
    asset_id = "BTC-USD"
    correct_buy_id = "buy123"
    incorrect_buy_id = "buy456"
    sell_order_details = {"order_id": "sell789"}

    initial_state = {
        "filled_buy_trade": {
            "buy_order_id": correct_buy_id,
            "associated_sell_orders": [],
        }
    }

    with patch.object(
        persistence_manager, "load_trade_state", return_value=initial_state
    ):
        with patch.object(persistence_manager, "save_trade_state") as mock_save:
            with pytest.raises(ValueError):
                persistence_manager.add_sell_order_to_filled_trade(
                    asset_id, incorrect_buy_id, sell_order_details
                )

            persistence_manager.logger.error.assert_called_once()
            log_args, _ = persistence_manager.logger.error.call_args
            expected_log_msg = (
                "Attempted to add sell order to non-matching or "
                f"non-existent buy trade for {asset_id} "
                f"(expected {incorrect_buy_id}, found {correct_buy_id})."
            )
            assert log_args[0] == expected_log_msg
            mock_save.assert_not_called()


def test_add_sell_order_to_non_existent_buy_trade_logs_error(persistence_manager):
    """Kill mutant #73: Test error logging for non-existent buy trade."""
    asset_id = "BTC-USD"
    buy_order_id = "buy123"
    sell_order_details = {"order_id": "sell789"}

    # Simulate load_trade_state returning an empty state
    with patch.object(persistence_manager, "load_trade_state", return_value={}):
        with patch.object(persistence_manager, "save_trade_state") as mock_save:
            with pytest.raises(ValueError):
                persistence_manager.add_sell_order_to_filled_trade(
                    asset_id, buy_order_id, sell_order_details
                )

            persistence_manager.logger.error.assert_called_once()
            log_args, _ = persistence_manager.logger.error.call_args
            expected_log_msg = (
                "Attempted to add sell order to non-matching or "
                f"non-existent buy trade for {asset_id} "
                f"(expected {buy_order_id}, found None)."
            )
            assert log_args[0] == expected_log_msg
            mock_save.assert_not_called()


def test_update_sell_order_status_not_found_returns_false(persistence_manager):
    """Kill mutant #97: Test that update returns False if sell order is not found."""
    asset_id = "BTC-USD"
    buy_order_id = "buy123"
    existing_sell_id = "sell789"
    non_existent_sell_id = "sell000"

    initial_state = {
        "filled_buy_trade": {
            "buy_order_id": buy_order_id,
            "associated_sell_orders": [
                {"order_id": existing_sell_id, "status": "open"}
            ],
        }
    }

    with patch.object(
        persistence_manager, "load_trade_state", return_value=initial_state
    ):
        with patch.object(persistence_manager, "save_trade_state") as mock_save:
            result = persistence_manager.update_sell_order_status_in_filled_trade(
                asset_id, buy_order_id, non_existent_sell_id, "filled"
            )

            assert result is False
            mock_save.assert_not_called()
            expected_warning = (
                f"Sell order {non_existent_sell_id} not found for {asset_id} "
                "to update status."
            )
            persistence_manager.logger.warning.assert_called_with(expected_warning)


def test_update_sell_order_stops_after_found(persistence_manager):
    """Kill mutant #105: Test that the update loop breaks after finding the order."""
    asset_id = "BTC-USD"
    buy_order_id = "buy123"
    sell_order_id_to_update = "sell789"

    initial_state = {
        "filled_buy_trade": {
            "buy_order_id": buy_order_id,
            "associated_sell_orders": [
                {"order_id": sell_order_id_to_update, "status": "open"},
                "malformed_entry",  # This would cause an error if the loop continues
            ],
        }
    }

    with patch.object(
        persistence_manager, "load_trade_state", return_value=initial_state
    ):
        with patch.object(persistence_manager, "save_trade_state") as mock_save:
            try:
                result = persistence_manager.update_sell_order_status_in_filled_trade(
                    asset_id, buy_order_id, sell_order_id_to_update, "filled"
                )
            except AttributeError:
                pytest.fail(
                    "AttributeError was raised, indicating the loop did not break."
                )

            assert result is True
            mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
