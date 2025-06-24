"""
Unit tests for the process_asset_trade_cycle function in trading_logic.py module.
"""

import unittest
from unittest.mock import Mock, patch
import types
import logging

# Import the function to test
from trading_logic import process_asset_trade_cycle


class TestProcessAssetTradeCycle(unittest.TestCase):
    """Test suite for process_asset_trade_cycle function."""

    def setUp(self):
        """Set up common test objects."""
        self.asset_id = "BTC-USD"
        self.client = Mock()
        self.persistence_manager = Mock()
        self.ta_module = Mock()
        self.config_module = types.SimpleNamespace()
        self.logger = Mock(spec=logging.Logger)

        self.config_module.TRADING_PAIRS = {
            "BTC-USD": {"some_key": "some_value"}  # Simplified config
        }
        # Mock product details to prevent early exit
        self.client.get_product.return_value = {"id": self.asset_id}

    def test_no_config_for_asset(self):
        """Test handling when config for asset is not found."""
        self.config_module.TRADING_PAIRS = {}
        process_asset_trade_cycle(
            self.asset_id,
            self.client,
            self.persistence_manager,
            self.ta_module,
            self.config_module,
            self.logger,
        )
        self.logger.error.assert_called_once_with(
            f"[{self.asset_id}] Configuration not found for {self.asset_id}."
        )

    @patch("trading_logic._handle_new_buy_order")
    def test_dispatches_to_new_buy_order_handler(self, mock_handle_new):
        """Test that it dispatches to the new buy order handler when no trades are active."""
        self.persistence_manager.load_trade_state.return_value = {
            "open_buy_order": None,
            "filled_buy_trade": None,
        }
        process_asset_trade_cycle(
            self.asset_id,
            self.client,
            self.persistence_manager,
            self.ta_module,
            self.config_module,
            self.logger,
        )
        mock_handle_new.assert_called_once()

    @patch("trading_logic._handle_open_buy_order")
    def test_dispatches_to_open_buy_order_handler(self, mock_handle_open):
        """Test that it dispatches to the open buy order handler when a buy order is open."""
        self.persistence_manager.load_trade_state.return_value = {
            "open_buy_order": {"order_id": "buy123"},
            "filled_buy_trade": None,
        }
        process_asset_trade_cycle(
            self.asset_id,
            self.client,
            self.persistence_manager,
            self.ta_module,
            self.config_module,
            self.logger,
        )
        mock_handle_open.assert_called_once()

    @patch("trading_logic._handle_filled_buy_order")
    def test_dispatches_to_filled_buy_order_handler(self, mock_handle_filled):
        """Test that it dispatches to the filled buy order handler when a trade is active."""
        self.persistence_manager.load_trade_state.return_value = {
            "open_buy_order": None,
            "filled_buy_trade": {"buy_order_id": "buy123"},
        }
        process_asset_trade_cycle(
            self.asset_id,
            self.client,
            self.persistence_manager,
            self.ta_module,
            self.config_module,
            self.logger,
        )
        mock_handle_filled.assert_called_once()

    def test_exception_handling_in_trade_cycle(self):
        """Test exception handling within the trade cycle."""
        self.persistence_manager.load_trade_state.side_effect = Exception(
            "Test exception"
        )
        process_asset_trade_cycle(
            self.asset_id,
            self.client,
            self.persistence_manager,
            self.ta_module,
            self.config_module,
            self.logger,
        )
        self.logger.error.assert_any_call(
            f"[{self.asset_id}] Unhandled error in process_asset_trade_cycle: Test exception",
            exc_info=True,
        )


if __name__ == "__main__":
    unittest.main()
