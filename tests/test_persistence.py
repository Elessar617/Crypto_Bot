"""
Unit tests for the persistence.py module.
"""

import unittest
import pytest
from unittest.mock import mock_open, patch
from trading.persistence import PersistenceManager

# Define a consistent DATA_DIR for tests. Since all file operations are mocked,
# this is primarily for ensuring the mock paths are consistent.
TEST_PERSISTENCE_DIR = "tests/mock_data"


@pytest.fixture
def persistence_manager(mock_logger, tmp_path):
    """Provides a PersistenceManager instance with a mock logger and temp directory."""
    # tmp_path is a pytest fixture providing a temporary directory unique to the test.
    manager = PersistenceManager(persistence_dir=str(tmp_path), logger=mock_logger)
    return manager


class TestPersistenceManager:
    """Test suite for persistence functions, pytest-style."""

    @patch("trading.persistence.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_trade_state_success(
        self, mock_json_dump, mock_file_open, mock_os_makedirs, persistence_manager
    ):
        """Test save_trade_state successfully saves data."""
        asset_id = "BTC-USD"
        state_data = {"key": "value", "number": 123}
        expected_file_path = persistence_manager._get_file_path(asset_id)

        persistence_manager.save_trade_state(asset_id, state_data)

        mock_os_makedirs.assert_called_once_with(
            persistence_manager.persistence_dir, exist_ok=True
        )
        mock_file_open.assert_called_once_with(
            expected_file_path, "w", encoding="utf-8"
        )
        mock_json_dump.assert_called_once_with(state_data, mock_file_open(), indent=4)

    @patch("trading.persistence.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    @patch("json.load")
    def test_load_trade_state_success(
        self, mock_json_load, mock_file_open, mock_os_exists, persistence_manager
    ):
        """Test load_trade_state successfully loads data."""
        asset_id = "BTC-USD"
        expected_data = {"key": "value"}
        mock_json_load.return_value = expected_data
        expected_file_path = persistence_manager._get_file_path(asset_id)

        loaded_data = persistence_manager.load_trade_state(asset_id)

        mock_os_exists.assert_called_once_with(expected_file_path)
        mock_file_open.assert_called_once_with(
            expected_file_path, "r", encoding="utf-8"
        )
        mock_json_load.assert_called_once_with(mock_file_open())
        assert loaded_data == expected_data

    @patch("os.path.exists", return_value=False)
    def test_load_trade_state_file_not_found(self, mock_exists, persistence_manager):
        """Test load_trade_state returns empty dict if file doesn't exist."""
        assert persistence_manager.load_trade_state("NO-ASSET") == {}
        mock_exists.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    def test_load_trade_state_json_decode_error(
        self, mock_file, mock_exists, persistence_manager
    ):
        """Test load_trade_state returns empty dict on JSON decode error."""
        assert persistence_manager.load_trade_state("BAD-JSON") == {}

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='["not a dict"]')
    def test_load_trade_state_corrupted_data_not_dict(
        self, mock_exists, mock_file, persistence_manager
    ):
        """Test load_trade_state returns empty dict if data is not a dictionary."""
        assert persistence_manager.load_trade_state("CORRUPTED") == {}

    # --- Tests for open_buy_order helper functions ---

    @patch.object(PersistenceManager, "save_trade_state")
    @patch.object(PersistenceManager, "load_trade_state", return_value={})
    def test_save_open_buy_order(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test save_open_buy_order correctly structures and saves data."""
        asset_id = "BTC-USD"
        order_id = "12345"
        order_details = {"size": "1", "price": "50000"}

        persistence_manager.save_open_buy_order(asset_id, order_id, order_details)

        expected_state = {
            "open_buy_order": {"order_id": order_id, "params": order_details}
        }
        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_called_once_with(asset_id, expected_state)

    @patch.object(
        PersistenceManager,
        "load_trade_state",
        return_value={"open_buy_order": {"order_id": "123", "params": {"a": 1}}},
    )
    def test_load_open_buy_order_success(
        self, mock_load_trade_state, persistence_manager
    ):
        """Test load_open_buy_order successfully retrieves order details."""
        result = persistence_manager.load_open_buy_order("BTC-USD")
        assert result == {"order_id": "123", "params": {"a": 1}}

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_open_buy_order_not_found(
        self, mock_load_trade_state, persistence_manager
    ):
        """Test load_open_buy_order returns None if no open order exists."""
        mock_load_trade_state.return_value = {"no_order": True}
        assert persistence_manager.load_open_buy_order("BTC-USD") is None

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_open_buy_order_corrupted_data(
        self, mock_load_trade_state, persistence_manager
    ):
        """Test load_open_buy_order returns None if data is malformed."""
        mock_load_trade_state.return_value = {"open_buy_order": "string"}
        assert persistence_manager.load_open_buy_order("BTC-USD") is None

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_clear_open_buy_order_exists(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test clear_open_buy_order removes the order if it exists."""
        asset_id = "BTC-USD"
        mock_load_trade_state.return_value = {"open_buy_order": {"order_id": "123"}}
        persistence_manager.clear_open_buy_order(asset_id)
        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_called_once_with(asset_id, {})

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_clear_open_buy_order_not_exists(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test clear_open_buy_order does nothing if order doesn't exist."""
        asset_id = "BTC-USD"
        mock_load_trade_state.return_value = {}
        persistence_manager.clear_open_buy_order(asset_id)
        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_not_called()

    # --- Tests for filled_buy_trade helper functions ---

    @patch.object(PersistenceManager, "save_trade_state")
    @patch.object(PersistenceManager, "load_trade_state")
    def test_save_filled_buy_trade(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test save_filled_buy_trade correctly structures and saves data."""
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy123"
        filled_order = {
            "average_filled_price": "50000",
            "filled_size": "1",
            "created_time": "2023-01-01T12:00:00Z",
        }
        sell_params = [{"price": "51000", "size": "0.5"}]

        # This is what load_trade_state will return
        initial_state = {
            "some_other_data": "value",
            "open_buy_order": {"order_id": "old_order"},
        }
        mock_load_trade_state.return_value = initial_state

        # This is what the state should look like when save_trade_state is called
        expected_state_after_modification = {
            "some_other_data": "value",
            "filled_buy_trade": {
                "buy_order_id": buy_order_id,
                "timestamp": "2023-01-01T12:00:00Z",
                "buy_price": "50000",
                "buy_quantity": "1",
                "associated_sell_orders": [],
                "sell_orders_params": sell_params,
            },
        }

        # Act
        persistence_manager.save_filled_buy_trade(
            asset_id, buy_order_id, filled_order, sell_params
        )

        # Assert
        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_called_once_with(
            asset_id, expected_state_after_modification
        )

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_filled_buy_trade_success(
        self, mock_load_trade_state, persistence_manager
    ):
        """Test load_filled_buy_trade successfully retrieves trade details."""
        mock_load_trade_state.return_value = {
            "filled_buy_trade": {"buy_order_id": "123"}
        }
        result = persistence_manager.load_filled_buy_trade("BTC-USD")
        assert result == {"buy_order_id": "123"}

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_filled_buy_trade_not_found(
        self, mock_load_trade_state, persistence_manager
    ):
        """Test load_filled_buy_trade returns None if no filled trade exists."""
        mock_load_trade_state.return_value = {"no_trade": True}
        assert persistence_manager.load_filled_buy_trade("BTC-USD") is None

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_load_filled_buy_trade_corrupted_data(
        self, mock_load_trade_state, persistence_manager
    ):
        """Test load_filled_buy_trade returns None if data is malformed."""
        mock_load_trade_state.return_value = {"filled_buy_trade": "string"}
        assert persistence_manager.load_filled_buy_trade("BTC-USD") is None

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_clear_filled_buy_trade_exists(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test clear_filled_buy_trade removes the trade if it exists."""
        asset_id = "BTC-USD"
        mock_load_trade_state.return_value = {
            "filled_buy_trade": {"buy_order_id": "123"}
        }
        persistence_manager.clear_filled_buy_trade(asset_id)
        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_called_once_with(asset_id, {})

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_clear_filled_buy_trade_not_exists(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test clear_filled_buy_trade does nothing if trade doesn't exist."""
        asset_id = "BTC-USD"
        mock_load_trade_state.return_value = {}
        persistence_manager.clear_filled_buy_trade(asset_id)
        mock_load_trade_state.assert_called_once_with(asset_id)
        mock_save_trade_state.assert_not_called()

    # --- Tests for associated_sell_orders helper functions ---

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_to_filled_trade_success(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test adding a sell order to an existing filled trade."""
        asset_id = "BTC-USD"
        buy_order_id = "buy123"
        sell_order_details = {"order_id": "sell456", "price": "52000"}

        mock_load_trade_state.return_value = {
            "filled_buy_trade": {
                "buy_order_id": buy_order_id,
                "associated_sell_orders": [],
            }
        }

        persistence_manager.add_sell_order_to_filled_trade(
            asset_id, buy_order_id, sell_order_details
        )

        expected_state = {
            "filled_buy_trade": {
                "buy_order_id": "buy123",
                "associated_sell_orders": [sell_order_details],
            }
        }
        mock_save_trade_state.assert_called_once_with(asset_id, expected_state)

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_creates_list_if_not_exists(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test add_sell_order creates associated_sell_orders list if it's missing."""
        asset_id = "BTC-USD"
        buy_order_id = "buy123"
        sell_order_details = {"order_id": "sell456"}

        mock_load_trade_state.return_value = {
            "filled_buy_trade": {"buy_order_id": "buy123"}
        }

        persistence_manager.add_sell_order_to_filled_trade(
            asset_id, buy_order_id, sell_order_details
        )

        expected_state = {
            "filled_buy_trade": {
                "buy_order_id": "buy123",
                "associated_sell_orders": [sell_order_details],
            }
        }
        mock_save_trade_state.assert_called_once_with(asset_id, expected_state)

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_duplicate_not_added(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test that a duplicate sell order is not added."""
        asset_id = "BTC-USD"
        buy_order_id = "buy123"
        sell_order_details = {"order_id": "sell456"}  # Duplicate ID

        mock_load_trade_state.return_value = {
            "filled_buy_trade": {
                "buy_order_id": buy_order_id,
                "associated_sell_orders": [{"order_id": "sell456", "status": "open"}],
            }
        }

        persistence_manager.add_sell_order_to_filled_trade(
            asset_id, buy_order_id, sell_order_details
        )

        mock_save_trade_state.assert_not_called()

    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_add_sell_order_no_filled_trade(
        self, mock_load_trade_state, persistence_manager
    ):
        """Test ValueError is raised if no filled trade exists."""
        mock_load_trade_state.return_value = {}
        with pytest.raises(ValueError):
            persistence_manager.add_sell_order_to_filled_trade(
                "BTC-USD", "buy123", {"order_id": "sell456"}
            )

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_update_sell_order_status_success(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test sell order status is updated successfully."""
        asset_id = "BTC-USD"
        buy_order_id = "buy123"
        sell_order_id = "sell456"
        new_status = "filled"

        mock_load_trade_state.return_value = {
            "filled_buy_trade": {
                "buy_order_id": buy_order_id,
                "associated_sell_orders": [{"order_id": "sell456", "status": "open"}],
            }
        }

        result = persistence_manager.update_sell_order_status_in_filled_trade(
            asset_id, buy_order_id, sell_order_id, new_status
        )

        assert result is True
        expected_state = mock_load_trade_state.return_value
        expected_state["filled_buy_trade"]["associated_sell_orders"][0][
            "status"
        ] = new_status
        mock_save_trade_state.assert_called_once_with(asset_id, expected_state)

    def test_update_sell_order_status_no_filled_trade(self, persistence_manager):
        """Test update raises ValueError if no filled trade exists."""
        with patch.object(persistence_manager, "load_trade_state", return_value={}):
            with pytest.raises(ValueError):
                persistence_manager.update_sell_order_status_in_filled_trade(
                    "BTC-USD", "buy123", "sell456", "filled"
                )

    def test_update_sell_order_status_no_sell_orders_list(self, persistence_manager):
        """Test update returns False if associated_sell_orders list is missing."""
        with patch.object(
            persistence_manager,
            "load_trade_state",
            return_value={"filled_buy_trade": {"buy_order_id": "buy123"}},
        ):
            result = persistence_manager.update_sell_order_status_in_filled_trade(
                "BTC-USD", "buy123", "sell456", "filled"
            )
            assert result is False

    @patch("trading.persistence.PersistenceManager.save_trade_state")
    @patch("trading.persistence.PersistenceManager.load_trade_state")
    def test_update_sell_order_status_order_not_found(
        self, mock_load_trade_state, mock_save_trade_state, persistence_manager
    ):
        """Test update returns False if specific sell order ID is not found."""
        asset_id = "BTC-USD"
        buy_order_id = "buy123"
        sell_order_id = "sell456-not-found"
        new_status = "filled"

        mock_load_trade_state.return_value = {
            "filled_buy_trade": {
                "buy_order_id": buy_order_id,
                "associated_sell_orders": [{"order_id": "sellXYZ", "status": "open"}],
            }
        }

        result = persistence_manager.update_sell_order_status_in_filled_trade(
            asset_id, buy_order_id, sell_order_id, new_status
        )
        assert result is False
        mock_save_trade_state.assert_not_called()


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
