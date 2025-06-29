from __future__ import annotations

import logging
import time
import unittest
from decimal import Decimal
from unittest.mock import ANY, MagicMock

import pandas as pd

from trading.coinbase_client import CoinbaseClient
from trading.persistence import PersistenceManager
from trading.trade_manager import TradeManager


class TestTradeManager(unittest.TestCase):
    def setUp(self):
        """Set up a TradeManager instance with mocked dependencies."""
        self.mock_client = MagicMock(spec=CoinbaseClient)
        self.mock_persistence = MagicMock(spec=PersistenceManager)
        self.mock_ta = MagicMock()
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock(spec=logging.Logger)

        # Configure default mock behaviors
        self.mock_config.TRADING_PAIRS = {
            "BTC-USD": {
                "buy_amount_usd": 10,
                "rsi_period": 14,
                "rsi_oversold_threshold": 30,
                "sell_profit_tiers": [],
                "candle_granularity_api_name": "ONE_HOUR",
            }
        }
        self.mock_client.get_product.return_value = {
            "product_id": "BTC-USD",
            "quote_increment": "0.01",
            "base_increment": "0.0001",
            "base_min_size": "0.001",
        }
        # Configure private methods called by TradeManager
        self.mock_client._generate_client_order_id.return_value = "test-order-id"

        self.mock_signal_analyzer = MagicMock()
        self.mock_order_calculator = MagicMock()

        self.trade_manager = TradeManager(
            client=self.mock_client,
            persistence_manager=self.mock_persistence,
            ta_module=self.mock_ta,
            config_module=self.mock_config,
            logger=self.mock_logger,
            signal_analyzer=self.mock_signal_analyzer,
            order_calculator=self.mock_order_calculator,
        )

    def test_process_cycle_handles_no_config(self):
        """Test that the trade cycle exits gracefully if asset config is missing."""
        self.mock_config.TRADING_PAIRS = {}
        self.trade_manager.process_asset_trade_cycle("BTC-USD")
        self.mock_logger.error.assert_called_with("[BTC-USD] Configuration not found.")

    def test_get_asset_config_handles_missing_trading_pairs_attribute(self):
        """Test _get_asset_config returns None if TRADING_PAIRS attribute is missing."""
        # Arrange
        asset_id = "BTC-USD"
        # Ensure the TRADING_PAIRS attribute does not exist on the mock
        if hasattr(self.mock_config, "TRADING_PAIRS"):
            delattr(self.mock_config, "TRADING_PAIRS")

        # Act
        result = self.trade_manager._get_asset_config(asset_id)

        # Assert
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_with(f"[{asset_id}] Configuration not found.")

    def test_process_cycle_handles_no_product_details(self):
        """Test trade cycle exits gracefully if product details fail to load."""
        self.mock_client.get_product.return_value = None
        self.trade_manager.process_asset_trade_cycle("BTC-USD")
        self.mock_logger.error.assert_called_with(
            "[BTC-USD] Failed to fetch valid product details."
        )

    def test_get_product_details_caching(self):
        """Test that product details are fetched and cached correctly."""
        # Arrange
        asset_id = "BTC-USD"
        product_details = {
            "product_id": asset_id,
            "quote_increment": "0.01",
            "base_increment": "0.0001",
            "base_min_size": "0.001",
        }
        self.mock_client.get_product.return_value = product_details

        # Act: First call - should fetch from API
        result1 = self.trade_manager._get_product_details(asset_id)

        # Assert: First call
        self.mock_client.get_product.assert_called_once_with(asset_id)
        self.assertEqual(result1, product_details)
        self.assertIn(asset_id, self.trade_manager.product_details_cache)
        self.assertEqual(self.trade_manager.product_details_cache[asset_id], product_details)

        # Act: Second call - should use cache
        result2 = self.trade_manager._get_product_details(asset_id)

        # Assert: Second call
        # The mock should still have been called only once from the first call
        self.mock_client.get_product.assert_called_once_with(asset_id)
        self.assertEqual(result2, product_details)

    def test_get_product_details_api_failure(self):
        """Test that None is returned and not cached on API failure."""
        # Arrange
        asset_id = "ETH-USD"
        self.mock_client.get_product.return_value = None
        # Ensure cache is empty for this asset
        self.trade_manager.product_details_cache.pop(asset_id, None)

        # Act
        result = self.trade_manager._get_product_details(asset_id)

        # Assert
        self.assertIsNone(result)
        self.assertNotIn(asset_id, self.trade_manager.product_details_cache)
        self.mock_logger.error.assert_called_with(
            f"[{asset_id}] Failed to fetch valid product details."
        )

    def test_get_product_details_exception_logging(self):
        """Test that exceptions during product detail fetching are logged with traceback."""
        # Arrange
        asset_id = "XRP-USD"
        error_message = "API is down"
        self.mock_client.get_product.side_effect = Exception(error_message)
        # Ensure cache is empty for this asset
        self.trade_manager.product_details_cache.pop(asset_id, None)

        # Act
        result = self.trade_manager._get_product_details(asset_id)

        # Assert
        self.assertIsNone(result)
        self.assertNotIn(asset_id, self.trade_manager.product_details_cache)
        self.mock_logger.error.assert_called_once_with(
            f"[{asset_id}] Exception fetching product details: {error_message}",
            exc_info=True,
        )

    def test_handle_new_buy_order_places_order_on_signal(self):
        """Test that a new buy order is placed when conditions are met."""

        # Arrange: No existing orders
        self.mock_persistence.load_trade_state.return_value = {}
        self.mock_client.get_product.return_value = {
            "product_id": "BTC-USD",
            "base_increment": "0.00000001",
            "quote_increment": "0.01",
            "base_min_size": "0.001",
        }
        self.mock_client.get_public_candles.return_value = [
            {
                "timestamp": time.time(),
                "low": 99.0,
                "high": 101.0,
                "open": 100.0,
                "close": 100.0,
                "volume": 10.0,
            }
        ] * 20
        self.mock_ta.calculate_rsi.return_value = pd.Series([25, 35])
        self.mock_signal_analyzer.should_buy_asset.return_value = True
        self.mock_order_calculator.calculate_buy_order_details.return_value = (
            Decimal("0.001"),
            Decimal("100.00"),
        )
        self.mock_client.limit_order_buy.return_value = {
            "success": True,
            "order_id": "order-123",
        }

        # Act
        self.trade_manager.process_asset_trade_cycle("BTC-USD")

        # Assert
        self.mock_client.limit_order_buy.assert_called_once_with(
            client_order_id=unittest.mock.ANY,
            product_id="BTC-USD",
            base_size="0.001",
            limit_price="100.00",
        )
        self.mock_persistence.save_open_buy_order.assert_called_once_with(
            asset_id="BTC-USD",
            order_id="order-123",
            order_details={"timestamp": ANY, "size": "0.001", "price": "100.00"},
        )

    def test_handle_new_buy_order_does_not_place_order_on_no_signal(self):
        """Test that no order is placed if the buy signal is false."""
        # Arrange: No existing orders
        self.mock_persistence.load_trade_state.return_value = {}
        self.mock_client.get_public_candles.return_value = [(0, 0, 0, 0, 100)] * 20
        self.mock_ta.calculate_rsi.return_value = pd.Series([40, 45])
        self.mock_signal_analyzer.should_buy_asset.return_value = False

        # Act
        self.trade_manager.process_asset_trade_cycle("BTC-USD")

        # Assert

        self.mock_client.limit_order_buy.assert_not_called()
        self.mock_persistence.save_open_buy_order.assert_not_called()

    def test_handle_open_buy_order_is_filled(self):
        """Test handling a buy order that has been filled."""
        # Arrange: An open buy order exists
        open_order = {"order_id": "order-123", "size": "0.1", "price": "100.00"}
        self.mock_persistence.load_trade_state.return_value = {
            "open_buy_order": open_order
        }
        mock_order = MagicMock()
        order_data = {
            "order_id": "order-123",
            "status": "FILLED",
            "filled_size": "0.1",
            "average_filled_price": "99.98",
            "created_time": time.time(),
        }
        mock_order.get.side_effect = lambda key, default=None: order_data.get(
            key, default
        )
        mock_order.__getitem__.side_effect = lambda key: order_data[key]
        mock_order.__contains__.side_effect = lambda key: key in order_data
        self.mock_client.get_order.return_value = mock_order
        self.mock_order_calculator.determine_sell_orders_params.return_value = []

        # Act
        self.trade_manager.process_asset_trade_cycle("BTC-USD")

        # Assert
        self.mock_client.get_order.assert_called_once_with("order-123")
        self.mock_persistence.save_filled_buy_trade.assert_called_once_with(
            asset_id="BTC-USD",
            buy_order_id="order-123",
            filled_order=mock_order,
            sell_orders_params=[],
        )
        self.mock_persistence.clear_open_buy_order.assert_called_once_with(
            asset_id="BTC-USD"
        )

    def test_handle_open_buy_order_is_still_open(self):
        """Test handling a buy order that is still open."""
        open_order = {"order_id": "order-123"}
        self.mock_persistence.load_trade_state.return_value = {
            "open_buy_order": open_order
        }
        self.mock_client.get_order.return_value = {"status": "OPEN"}

        # Act
        self.trade_manager.process_asset_trade_cycle("BTC-USD")

        # Assert
        self.mock_client.get_order.assert_called_once_with("order-123")
        self.mock_persistence.clear_open_buy_order.assert_not_called()
        self.mock_persistence.save_filled_buy_trade.assert_not_called()

    def test_handle_filled_buy_order_places_new_sell_orders(self):
        """Test placing sell orders after a buy order is filled."""
        # Arrange: A filled buy trade exists with no associated sell orders
        filled_buy = {
            "buy_order_id": "buy-123",
            "buy_price": "100.00",
            "buy_quantity": "1.0",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy
        }
        self.mock_config.TRADING_PAIRS["BTC-USD"]["sell_profit_tiers"] = [
            {"profit_target": 0.02, "quantity_percentage": 1.0}
        ]
        self.mock_client.limit_order_sell.return_value = {
            "success": True,
            "order_id": "sell-456",
        }
        self.mock_order_calculator.determine_sell_orders_params.return_value = [
            {"limit_price": "102.00", "base_size": "1.0"}
        ]

        # Act
        self.trade_manager.process_asset_trade_cycle("BTC-USD")

        # Assert
        self.mock_client.limit_order_sell.assert_called_once_with(
            product_id="BTC-USD",
            base_size="1.0",
            limit_price="102.00",
            client_order_id=ANY,
        )
        self.mock_persistence.add_sell_order_to_filled_trade.assert_called_once_with(
            asset_id="BTC-USD",
            buy_order_id="buy-123",
            sell_order_details={
                "order_id": "sell-456",
                "size": "1.0",
                "price": "102.00",
                "status": "OPEN",
                "timestamp": ANY,
            },
        )

    def test_handle_filled_buy_order_checks_existing_sell_orders(self):
        """Test checking the status of existing sell orders."""
        # Arrange: A filled buy trade with an open sell order
        sell_order = {"order_id": "sell-456", "status": "OPEN"}
        filled_buy = {
            "buy_order_id": "buy-123",
            "associated_sell_orders": [sell_order],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy
        }
        # Simulate the sell order is now filled
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager.process_asset_trade_cycle("BTC-USD")

        # Assert
        self.mock_client.get_order.assert_called_once_with("sell-456")
        self.mock_persistence.update_sell_order_status_in_filled_trade.assert_called_once_with(
            asset_id="BTC-USD",
            buy_order_id="buy-123",
            sell_order_id="sell-456",
            new_status="FILLED",
        )
        # Since the only sell order is now filled, the trade should be cleared
        self.mock_persistence.clear_filled_buy_trade.assert_called_once_with(
            asset_id="BTC-USD"
        )

    def test_process_asset_trade_cycle_unhandled_exception_logging(self):
        """Test that unhandled exceptions in the trade cycle are logged with traceback."""
        # Arrange
        asset_id = "BTC-USD"
        error_message = "Something went wrong"
        self.mock_persistence.load_trade_state.side_effect = Exception(error_message)

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        self.mock_logger.error.assert_called_once_with(
            f"[{asset_id}] Unhandled error in process_asset_trade_cycle: {error_message}",
            exc_info=True,
        )
        # Also verify that the 'finally' block runs
        self.mock_logger.info.assert_any_call(f"[{asset_id}] Trade cycle processing finished.")

    def test_check_and_update_sell_orders_continues_after_invalid_order(self):
        """Test that the loop checking sell orders continues after an invalid one."""
        # Arrange: A filled buy trade with one invalid and one valid sell order
        asset_id = "BTC-USD"
        buy_order_id = "buy-123"
        invalid_sell_order = {"status": "OPEN"}  # Missing 'order_id'
        valid_sell_order = {"order_id": "sell-789", "status": "OPEN"}

        filled_buy = {
            "buy_order_id": buy_order_id,
            "associated_sell_orders": [invalid_sell_order, valid_sell_order],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy
        }
        # Simulate the valid sell order is now filled
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        # Check that the invalid order was logged
        self.mock_logger.warning.assert_called_with(f"[{asset_id}] Skipping sell order with no ID.")
        # Crucially, check that the valid order was still processed
        self.mock_client.get_order.assert_called_once_with("sell-789")
        self.mock_persistence.update_sell_order_status_in_filled_trade.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_id="sell-789",
            new_status="FILLED",
        )

    def test_check_and_update_sell_orders_skips_already_filled_orders(self):
        """Test that sell orders already marked as FILLED are skipped."""
        # Arrange: A filled buy trade with one open and one already-filled sell order
        asset_id = "BTC-USD"
        buy_order_id = "buy-123"
        already_filled_order = {"order_id": "sell-456", "status": "FILLED"}
        open_order = {"order_id": "sell-789", "status": "OPEN"}

        filled_buy = {
            "buy_order_id": buy_order_id,
            "associated_sell_orders": [already_filled_order, open_order],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy
        }
        # The client should only be called for the open order
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        # Crucially, assert that get_order was only called for the open order
        self.mock_client.get_order.assert_called_once_with("sell-789")
        # And that the persistence layer was updated for it
        self.mock_persistence.update_sell_order_status_in_filled_trade.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_id="sell-789",
            new_status="FILLED",
        )
        # Since both are now filled, the trade should be cleared
        self.mock_persistence.clear_filled_buy_trade.assert_called_once_with(asset_id=asset_id)
