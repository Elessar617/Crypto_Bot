from __future__ import annotations

import logging
import time
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch, call

import pandas as pd
import pytest

from trading.coinbase_client import CoinbaseClient
from trading.persistence import PersistenceManager
from trading import technical_analysis
from trading.trade_manager import TradeManager


class TestTradeManager(unittest.TestCase):
    def setUp(self):
        """Set up a TradeManager instance with mocked dependencies."""
        # Mock modules that are passed as dependencies
        self.mock_config_module = MagicMock()
        self.mock_order_calculator_module = MagicMock()
        self.mock_signal_analyzer_module = MagicMock()
        self.mock_ta_module = MagicMock()

        # Mock object instances that are passed as dependencies
        self.mock_client = MagicMock(spec=CoinbaseClient)
        self.mock_persistence = MagicMock(spec=PersistenceManager)
        self.mock_logger = MagicMock(spec=logging.Logger)

        # Configure default mock behaviors *before* each test.
        self._configure_mocks()

        # Set up default attributes for the mock config module
        self.mock_config_module.TRADING_PAIRS = {
            "BTC-USD": {
                "rsi_period": 14,
                "candle_granularity_api_name": "ONE_HOUR",
                "sell_profit_tiers": [
                    {
                        "profit_percentage": 1.5,
                        "quantity_percentage": 0.25,
                        "order_type": "limit",
                    }
                ],
                "fixed_buy_usd_amount": 10,
            }
        }

        # Instantiate the TradeManager with all mocked dependencies
        self.trade_manager = TradeManager(
            client=self.mock_client,
            persistence_manager=self.mock_persistence,
            ta_module=self.mock_ta_module,
            config_module=self.mock_config_module,
            logger=self.mock_logger,
            signal_analyzer=self.mock_signal_analyzer_module,
            order_calculator=self.mock_order_calculator_module,
        )

    def tearDown(self):
        """Reset all mocks after each test."""
        self.mock_client.reset_mock(return_value=True, side_effect=True)
        self.mock_logger.reset_mock(return_value=True, side_effect=True)
        self.mock_persistence.reset_mock(return_value=True, side_effect=True)
        self.mock_ta_module.reset_mock(return_value=True, side_effect=True)
        self.mock_config_module.reset_mock(return_value=True, side_effect=True)
        self.mock_signal_analyzer_module.reset_mock(return_value=True, side_effect=True)
        self.mock_order_calculator_module.reset_mock(
            return_value=True, side_effect=True
        )

    def _configure_mocks(self):
        """Configure default mock behaviors."""
        # Note: load_trade_state is NOT configured by default, as its return value
        # is highly test-dependent. Tests should configure it as needed.
        self.mock_config_module.TRADING_PAIRS = {
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
        self.mock_client.get_order.return_value = {}  # Default to an empty order
        self.mock_client._generate_client_order_id.return_value = "test-order-id"

    def test_initialization_with_none_persistence_manager(self):
        """Test that TradeManager raises an error if the persistence_manager is None."""
        with self.assertRaisesRegex(
            AssertionError, "^PersistenceManager dependency cannot be None$"
        ):
            TradeManager(
                client=self.mock_client,
                persistence_manager=None,
                ta_module=self.mock_ta_module,
                config_module=self.mock_config_module,
                logger=self.mock_logger,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=self.mock_order_calculator_module,
            )

    def test_initialization_with_none_client(self):
        """Test that TradeManager raises an error if the client is None."""
        with self.assertRaisesRegex(
            AssertionError, "^CoinbaseClient dependency cannot be None$"
        ):
            TradeManager(
                client=None,
                persistence_manager=self.mock_persistence,
                ta_module=self.mock_ta_module,
                config_module=self.mock_config_module,
                logger=self.mock_logger,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=self.mock_order_calculator_module,
            )

    def test_process_asset_trade_cycle_handles_filled_buy_trade(self):
        """
        Test that process_asset_trade_cycle correctly calls _handle_filled_buy_order
        when a filled_buy_trade exists in the trade state.
        """
        # Arrange
        asset_id = "BTC-USD"
        mock_filled_trade = {"buy_order_id": "buy-123", "sell_orders": {}}
        self.mock_persistence.load_trade_state.return_value = {
            "open_buy_order": None,
            "filled_buy_trade": mock_filled_trade,
        }
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        # Patch the method that would be called
        with patch.object(
            self.trade_manager, "_handle_filled_buy_order"
        ) as mock_handle_filled:
            # Act
            self.trade_manager.process_asset_trade_cycle(asset_id)

            # Assert
            self.mock_persistence.load_trade_state.assert_called_once_with(asset_id)
            mock_handle_filled.assert_called_once_with(
                asset_id, mock_filled_trade, product_details, config_asset_params
            )

    def test_initialization_with_none_ta_module(self):
        """Test that TradeManager raises an error if the ta_module is None."""
        with self.assertRaisesRegex(
            AssertionError, "^TA module dependency cannot be None$"
        ):
            TradeManager(
                client=self.mock_client,
                persistence_manager=self.mock_persistence,
                ta_module=None,
                config_module=self.mock_config_module,
                logger=self.mock_logger,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=self.mock_order_calculator_module,
            )

    def test_initialization_with_none_config_module(self):
        """Test that TradeManager raises an error if the config_module is None."""
        with pytest.raises(
            AssertionError, match="^Config module dependency cannot be None$"
        ):
            TradeManager(
                client=self.mock_client,
                persistence_manager=self.mock_persistence,
                ta_module=self.mock_ta_module,
                config_module=None,
                logger=self.mock_logger,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=self.mock_order_calculator_module,
            )

    def test_initialization_with_none_logger(self):
        """Test that TradeManager raises an error if the logger is None."""
        try:
            TradeManager(
                client=self.mock_client,
                persistence_manager=self.mock_persistence,
                ta_module=self.mock_ta_module,
                config_module=self.mock_config_module,
                logger=None,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=self.mock_order_calculator_module,
            )
            self.fail("AssertionError was not raised for logger")
        except AssertionError as e:
            self.assertEqual(str(e), "Logger dependency cannot be None")

    def test_initialization_with_none_signal_analyzer(self):
        """Test that TradeManager raises an error if the signal_analyzer is None."""
        with self.assertRaisesRegex(
            AssertionError, "^SignalAnalyzer dependency cannot be None$"
        ):
            TradeManager(
                client=self.mock_client,
                persistence_manager=self.mock_persistence,
                ta_module=self.mock_ta_module,
                config_module=self.mock_config_module,
                logger=self.mock_logger,
                signal_analyzer=None,
                order_calculator=self.mock_order_calculator_module,
            )

    def test_initialization_with_none_order_calculator(self):
        """Test that TradeManager raises an error if the order_calculator is None."""
        with pytest.raises(
            AssertionError, match="^OrderCalculator dependency cannot be None$"
        ):
            TradeManager(
                client=self.mock_client,
                persistence_manager=self.mock_persistence,
                ta_module=self.mock_ta_module,
                config_module=self.mock_config_module,
                logger=self.mock_logger,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=None,
            )

    def test_process_cycle_handles_no_config(self):
        """Test that the trade cycle exits gracefully if asset config is missing."""
        self.mock_config_module.TRADING_PAIRS = {}
        self.trade_manager.process_asset_trade_cycle("BTC-USD")
        self.mock_logger.error.assert_called_with("[BTC-USD] Configuration not found.")

    def test_get_asset_config_handles_missing_trading_pairs_attribute(self):
        """Test _get_asset_config returns None if TRADING_PAIRS attribute is missing."""
        # Arrange
        asset_id = "BTC-USD"
        # Temporarily remove the attribute and ensure it's restored after the test
        if hasattr(self.mock_config_module, "TRADING_PAIRS"):
            original_trading_pairs = self.mock_config_module.TRADING_PAIRS
            delattr(self.mock_config_module, "TRADING_PAIRS")
            self.addCleanup(
                setattr,
                self.mock_config_module,
                "TRADING_PAIRS",
                original_trading_pairs,
            )

        # Act
        result = self.trade_manager._get_asset_config(asset_id)

        # Assert
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_with(
            f"[{asset_id}] Configuration not found."
        )

    def test_get_asset_config_handles_asset_id_not_in_trading_pairs(self):
        """Test _get_asset_config returns None if asset_id is not in TRADING_PAIRS."""
        # Arrange
        asset_id = "ETH-USD"
        # Use patch.object to temporarily set the attribute, ensuring test isolation
        with patch.object(self.mock_config_module, "TRADING_PAIRS", {"BTC-USD": {}}):
            # Act
            result = self.trade_manager._get_asset_config(asset_id)

            # Assert
            self.assertIsNone(result)
            self.mock_logger.error.assert_called_with(
                f"[{asset_id}] Configuration not found."
            )

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
        self.assertEqual(
            self.trade_manager.product_details_cache[asset_id], product_details
        )

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
        """Test exceptions during product detail fetching are logged."""
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
        self.mock_ta_module.calculate_rsi.return_value = pd.Series([25, 35])
        self.mock_signal_analyzer_module.should_buy_asset.return_value = True
        self.mock_order_calculator_module.calculate_buy_order_details.return_value = (
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
            product_id="BTC-USD",
            base_size="0.001",
            limit_price="100.00",
        )
        self.mock_persistence.save_trade_state.assert_called_once_with(
            "BTC-USD", {"open_buy_order": {"order_id": "order-123"}}
        )

    def test_handle_new_buy_order_does_not_place_order_on_no_signal(self):
        """Test that no order is placed if the buy signal is false."""
        # Arrange: No existing orders
        self.mock_persistence.load_trade_state.return_value = {}
        self.mock_client.get_public_candles.return_value = [(0, 0, 0, 0, 100)] * 20
        self.mock_ta_module.calculate_rsi.return_value = pd.Series([40, 45])
        self.mock_signal_analyzer_module.should_buy_asset.return_value = False

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
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = []

        # Act
        with patch.object(
            self.mock_client, "get_order", return_value=mock_order
        ) as mock_get_order:
            self.trade_manager.process_asset_trade_cycle("BTC-USD")

            # Assert
            mock_get_order.assert_called_once_with("order-123")
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
        self.mock_logger.warning.assert_not_called()

    def test_handle_open_buy_order_directly_when_filled(self):
        """Test _handle_open_buy_order directly for a FILLED order."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {"order_id": order_id}
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        mock_order_status = {
            "status": "FILLED",
            "filled_size": "1.0",
            "average_filled_price": "50000",
        }
        self.mock_client.get_order.return_value = mock_order_status

        # Mock the load_trade_state call that happens inside _handle_open_buy_order
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": {"some_key": "some_value"}
        }

        # Patch the nested call to _handle_filled_buy_order to isolate the test
        with patch.object(
            self.trade_manager, "_handle_filled_buy_order"
        ) as mock_handle_filled:
            # Act
            self.trade_manager._handle_open_buy_order(
                asset_id, open_buy_order, product_details, config_asset_params
            )

            # Assert
            self.mock_client.get_order.assert_called_once_with(order_id)
            self.mock_persistence.save_filled_buy_trade.assert_called_once()
            self.mock_persistence.clear_open_buy_order.assert_called_once_with(
                asset_id=asset_id
            )
            mock_handle_filled.assert_called_once()
            self.mock_logger.warning.assert_not_called()

    def test_handle_filled_buy_order_places_new_sell_orders(self):
        """Test placing sell orders after a buy order is filled."""
        # Arrange: A filled buy trade exists with no associated sell orders
        self.mock_persistence.load_open_buy_order.return_value = None
        filled_buy = {
            "buy_order_id": "buy-123",
            "buy_price": "100.00",
            "buy_quantity": "1.0",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy
        }
        self.mock_config_module.TRADING_PAIRS["BTC-USD"]["sell_profit_tiers"] = [
            {"profit_target": 0.02, "quantity_percentage": 1.0}
        ]
        self.mock_client.limit_order_sell.return_value = {
            "success": True,
            "order_id": "sell-456",
        }
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = [
            {"limit_price": "102.00", "base_size": "1.0"}
        ]

        # Act
        self.trade_manager.process_asset_trade_cycle("BTC-USD")

        # Assert
        determine_sell_params_mock = (
            self.mock_order_calculator_module.determine_sell_orders_params
        )
        determine_sell_params_mock.assert_called_once()
        kwargs = determine_sell_params_mock.call_args.kwargs
        self.assertEqual(
            kwargs["sell_profit_tiers"],
            self.mock_config_module.TRADING_PAIRS["BTC-USD"]["sell_profit_tiers"],
        )

        self.mock_client.limit_order_sell.assert_called_once_with(
            client_order_id=unittest.mock.ANY,
            product_id="BTC-USD",
            base_size="1.0",
            limit_price="102.00",
        )
        self.mock_persistence.add_sell_order_to_filled_trade.assert_called_once()
        call_args = self.mock_persistence.add_sell_order_to_filled_trade.call_args
        self.assertEqual(call_args.kwargs["asset_id"], "BTC-USD")
        self.assertEqual(call_args.kwargs["buy_order_id"], "buy-123")
        sell_details = call_args.kwargs["sell_order_details"]
        self.assertEqual(sell_details["order_id"], "sell-456")
        self.assertEqual(sell_details["size"], "1.0")
        self.assertEqual(sell_details["price"], "102.00")
        self.assertEqual(sell_details["status"], "OPEN")
        self.assertIn("timestamp", sell_details)

    def test_check_and_update_sell_orders_does_not_clear_trade_if_not_all_filled(self):
        """
        Test that the filled buy trade is not cleared if not all sell orders are filled.
        """
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        # An invalid order (empty order_id key) and a valid one
        sell_orders = {
            "sell-1": {"status": "OPEN"},
            "sell-2": {"status": "OPEN"},  # Valid
        }

        # Mock get_order to return FILLED for one order and OPEN for the other
        def get_order_side_effect(order_id):
            if order_id == "sell-1":
                return {"status": "FILLED"}
            if order_id == "sell-2":
                return {"status": "OPEN"}
            return {}

        self.mock_client.get_order.side_effect = get_order_side_effect

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        self.mock_persistence.clear_filled_buy_trade.assert_not_called()
        self.assertEqual(self.mock_client.get_order.call_count, 2)

    def test_check_and_update_sell_orders_handles_filled_order(self):
        """Test checking the status of existing sell orders."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-123"
        sell_orders = {"sell-456": {"status": "OPEN"}}

        # Simulate the sell order is now filled
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        self.mock_client.get_order.assert_called_once_with("sell-456")
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_id="sell-456",
            new_status="FILLED",
        )
        # Since the only sell order is now filled, the trade should be cleared
        self.mock_persistence.clear_filled_buy_trade.assert_called_once_with(
            asset_id="BTC-USD"
        )

    def test_process_asset_cycle_exception_logging(self):
        """Test unhandled exceptions in the trade cycle are logged."""
        # Arrange
        asset_id = "BTC-USD"
        error_message = "Something went wrong"
        self.mock_persistence.load_trade_state.side_effect = Exception(error_message)

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        self.assertEqual(self.mock_logger.error.call_count, 1)
        call_args, call_kwargs = self.mock_logger.error.call_args
        expected_msg = (
            f"[{asset_id}] Unhandled error in process_asset_trade_cycle: "
            f"{error_message}"
        )
        self.assertIn(expected_msg, call_args[0])
        self.assertTrue(call_kwargs.get("exc_info"))
        # Also verify that the 'finally' block runs
        self.mock_logger.info.assert_any_call(
            f"[{asset_id}] Trade cycle processing finished."
        )

    def test_check_sell_orders_continues_on_invalid(self):
        """Test sell order check loop continues after an invalid order."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        # An invalid order (empty order_id key) and a valid one
        sell_orders = {
            "": {"status": "OPEN"},  # Invalid
            "sell-456": {"status": "OPEN"},  # Valid
        }
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # Check that the invalid order was logged
        self.mock_logger.warning.assert_called_with(
            f"[{asset_id}] Skipping sell order with no ID."
        )
        # Should be called only for the valid order
        self.mock_client.get_order.assert_called_once_with("sell-456")
        # Status should be updated for the valid order
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_id="sell-456",
            new_status="FILLED",
        )

    def test_check_and_update_sell_orders_updates_local_status_explicitly(self):
        """
        Test that _check_and_update_sell_orders correctly updates the status
        of an order in the local dictionary passed to it. This is a more
        explicit test to kill mutant #69.
        """
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-123"
        sell_order_id = "sell-456"
        # This dictionary will be modified in place by the method under test.
        local_sell_orders = {sell_order_id: {"status": "OPEN", "price": "100"}}

        # Mock the API to return a new status
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, local_sell_orders
        )

        # Assert
        # The primary assertion is that the dictionary passed to the function
        # has been modified as expected.
        self.assertEqual(local_sell_orders[sell_order_id]["status"], "FILLED")
        # Also check that other keys are untouched
        self.assertEqual(local_sell_orders[sell_order_id]["price"], "100")

    def test_check_and_update_sell_orders_skips_already_filled_orders(self):
        """Test that sell orders already marked as FILLED are skipped."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        sell_orders = {
            "sell-123": {"status": "FILLED"},
            "sell-456": {"status": "OPEN"},
        }
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # Should only be called for the OPEN order
        self.assertEqual(
            self.mock_client.get_order.call_count,
            1,
            "get_order should only be called for non-FILLED orders.",
        )
        self.mock_client.get_order.assert_called_with("sell-456")
        # Status should only be updated for the OPEN order
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_id="sell-456",
            new_status="FILLED",
        )
        # Since both are now filled, the trade should be cleared
        self.mock_persistence.clear_filled_buy_trade.assert_called_once_with(
            asset_id=asset_id
        )

    def test_check_and_update_sell_orders_updates_local_status(self):
        """Test _check_and_update_sell_orders updates local order status."""
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        # The method expects a dictionary of orders, keyed by order_id.
        sell_orders = {"sell-123": {"status": "OPEN"}}
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # The primary assertion: the local dictionary's value should be updated.
        self.assertEqual(sell_orders["sell-123"]["status"], "FILLED")
        # Also assert that the persistence layer was called
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_id="sell-123",
            new_status="FILLED",
        )

    def test_check_sell_order_with_missing_status_is_not_updated_if_still_open(self):
        """Test a sell order with no local status is not updated if API shows OPEN."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        sell_orders = {"sell-123": {}}  # Status is missing

        # Mock the client to return an OPEN status
        self.mock_client.get_order.return_value = {"status": "OPEN"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        self.mock_client.get_order.assert_called_once_with("sell-123")
        # Since status is unchanged (default OPEN to remote OPEN), no update call
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_not_called()

    def test_continues_checking_orders_after_one_fails(self):
        """Test it continues checking orders after one fails API check."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        # An invalid order (empty order_id key) and a valid one
        sell_orders = {
            "sell-1": {"status": "FILLED"},
            "sell-2": {"status": "OPEN"},  # This one will fail
            "sell-3": {"status": "OPEN"},
        }

        # Mock the client to fail only for the second order
        def get_order_side_effect(order_id):
            if order_id == "sell-2":
                return None
            return {"status": "FILLED"}  # Changed to FILLED to test update logic

        self.mock_client.get_order.side_effect = get_order_side_effect

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # Should be called for the two OPEN orders, not the FILLED one.
        self.assertEqual(self.mock_client.get_order.call_count, 2)
        # The logger should warn about the specific failure.
        self.mock_logger.warning.assert_any_call(
            f"[{asset_id}] Failed to get status for sell order sell-2."
        )
        # It should update the status for the one that succeeded.
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_id="sell-3",
            new_status="FILLED",
        )
        # The trade should not be cleared.
        self.mock_persistence.clear_filled_buy_trade.assert_not_called()

    def test_trade_not_cleared_if_one_sell_order_is_still_open(self):
        """Test that a trade is not cleared if one sell order is still open."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        sell_orders = {
            "sell-1": {"status": "FILLED"},
            "sell-2": {"status": "OPEN"},
        }

        # Mock the client to return an OPEN status for the open order
        self.mock_client.get_order.return_value = {"status": "OPEN"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # The client should have been called for the open order.
        self.mock_client.get_order.assert_called_once_with("sell-2")
        # No update should be called because the status hasn't changed.
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_not_called()
        # The trade should not be cleared because one order is still open.
        self.mock_persistence.clear_filled_buy_trade.assert_not_called()

    def test_exception_in_sell_order_check_logs_traceback(self):
        """Test exception during sell order check logs traceback."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        sell_orders = {
            "sell-1": {"status": "FILLED"},
            "sell-2": {"status": "OPEN"},
        }

        # Mock the client to raise an exception
        error_message = "API is down"
        self.mock_client.get_order.side_effect = Exception(error_message)

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # The logger should have been called with the exception and traceback.
        self.mock_logger.error.assert_called_once_with(
            f"[{asset_id}] Error checking sell order sell-2: {error_message}",
            exc_info=True,
        )
        # The trade should not be cleared.
        self.mock_persistence.clear_filled_buy_trade.assert_not_called()

    def test_trade_not_cleared_when_one_order_fails_and_others_are_filled(self):
        """Test trade not cleared if one order fails and others are filled."""
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        sell_orders = {
            "sell-1": {"status": "FILLED"},
            "sell-2": {"status": "OPEN"},  # This one will fail
        }

        # Mock the client to raise an exception for the open order
        self.mock_client.get_order.side_effect = Exception("API Error")

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # The client should only be called for the OPEN order.
        self.mock_client.get_order.assert_called_once_with("sell-2")
        # No update should happen because of the exception.
        update_status_mock = (
            self.mock_persistence.update_sell_order_status_in_filled_trade
        )
        update_status_mock.assert_not_called()
        # The trade should not be cleared.
        self.mock_persistence.clear_filled_buy_trade.assert_not_called()
        # An error should be logged.
        self.mock_logger.error.assert_called_with(
            f"[{asset_id}] Error checking sell order sell-2: API Error", exc_info=True
        )

    def test_place_new_sell_orders_uses_correct_buy_details(self):
        """Test that correct buy details are used for placing sell orders."""
        # Arrange
        asset_id = "BTC-USD"
        buy_price = Decimal("50000.00")
        buy_quantity = Decimal("0.0002")

        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": str(buy_price),
            "buy_quantity": str(buy_quantity),
            "associated_sell_orders": [],  # No existing sell orders
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        # Mock the order calculator to return some dummy sell parameters
        sell_order_params = [
            {"base_size": "0.0001", "limit_price": "51000.00"},
            {"base_size": "0.0001", "limit_price": "52000.00"},
        ]
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = (
            sell_order_params
        )

        # Mock the config to have sell tiers
        self.mock_config_module.TRADING_PAIRS["BTC-USD"]["sell_profit_tiers"] = [
            {"trigger_percentage": 2.0, "size_percentage": 50.0},
            {"trigger_percentage": 4.0, "size_percentage": 50.0},
        ]

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        # Verify that the order calculator was called with the correct Decimal buy_price
        determine_params_mock = (
            self.mock_order_calculator_module.determine_sell_orders_params
        )
        determine_params_mock.assert_called_once()
        _, call_kwargs = determine_params_mock.call_args
        self.assertEqual(call_kwargs["buy_price"], buy_price)
        self.assertEqual(call_kwargs["buy_quantity"], buy_quantity)

        # Verify that limit_order_sell was called with the correct parameters
        self.assertEqual(self.mock_client.limit_order_sell.call_count, 2)
        calls = self.mock_client.limit_order_sell.call_args_list
        self.assertEqual(
            calls[0].kwargs["base_size"], sell_order_params[0]["base_size"]
        )
        self.assertEqual(
            calls[0].kwargs["limit_price"], sell_order_params[0]["limit_price"]
        )
        self.assertEqual(
            calls[1].kwargs["base_size"], sell_order_params[1]["base_size"]
        )
        self.assertEqual(
            calls[1].kwargs["limit_price"], sell_order_params[1]["limit_price"]
        )

    def test_place_new_sell_orders_logs_individual_and_summary_messages(self):
        """Test that individual and summary sell order logs are correct."""
        # Arrange
        asset_id = "BTC-USD"
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "buy_quantity": "0.0002",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        sell_order_params = [
            {"base_size": "0.0001", "limit_price": "51000.00"},
            {"base_size": "0.0001", "limit_price": "52000.00"},
        ]
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = (
            sell_order_params
        )

        self.mock_client.limit_order_sell.return_value = {
            "success": True,
            "order_id": "test-sell-order-id",
        }

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        # Expected individual order logs
        first_order_params = sell_order_params[0]
        expected_first_log = (
            f"[{asset_id}] Placing sell order "
            f"1/{len(sell_order_params)}: size={first_order_params['base_size']}, "
            f"price={first_order_params['limit_price']}"
        )
        second_order_params = sell_order_params[1]
        expected_second_log = (
            f"[{asset_id}] Placing sell order "
            f"2/{len(sell_order_params)}: size={second_order_params['base_size']}, "
            f"price={second_order_params['limit_price']}"
        )

        # Expected summary log
        expected_summary_log = (
            f"[{asset_id}] Successfully placed and saved "
            f"{len(sell_order_params)} sell orders."
        )

        # Check that the logs were called in the correct order.
        successful_placement_log = (
            f"[{asset_id}] Successfully placed sell order test-sell-order-id."
        )
        calls_to_check = [
            call(expected_first_log),
            call(successful_placement_log),
            call(expected_second_log),
            call(successful_placement_log),
            call(expected_summary_log),
        ]

        actual_calls = self.mock_logger.info.call_args_list
        actual_log_messages = [c.args[0] for c in actual_calls]

        start_index = -1
        for i in range(len(actual_log_messages) - len(calls_to_check) + 1):
            if actual_log_messages[i] == calls_to_check[0].args[0]:
                start_index = i
                break

        self.assertNotEqual(
            start_index, -1, "The start of the expected log sequence was not found."
        )

        self.assertEqual(
            actual_calls[start_index : start_index + len(calls_to_check)],
            calls_to_check,
        )

    def test_place_sell_orders_uses_generated_id(self):
        """Test that generated client_order_id is used for sell orders."""
        # Arrange
        asset_id = "BTC-USD"
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "buy_quantity": "0.0002",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        sell_order_params = [{"base_size": "0.0002", "limit_price": "51000.00"}]
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = (
            sell_order_params
        )

        self.mock_client.limit_order_sell.return_value = {
            "success": True,
            "order_id": "test-sell-order-id",
        }

        # Mock the client_order_id generation
        expected_client_order_id = "custom-client-order-id-123"
        self.mock_client._generate_client_order_id.return_value = (
            expected_client_order_id
        )

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        self.mock_client.limit_order_sell.assert_called_once()
        call_kwargs = self.mock_client.limit_order_sell.call_args.kwargs
        self.assertEqual(call_kwargs["base_size"], sell_order_params[0]["base_size"])
        self.assertEqual(
            call_kwargs["limit_price"], sell_order_params[0]["limit_price"]
        )

    def test_place_new_sell_orders_handles_placement_failure(self):
        """Test that a failure to place a sell order is handled correctly."""
        # Arrange
        asset_id = "BTC-USD"
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "buy_quantity": "0.0002",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        sell_order_params = [{"base_size": "0.0002", "limit_price": "51000.00"}]
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = (
            sell_order_params
        )

        # Mock a failed order placement
        failure_reason = "INSUFFICIENT_FUNDS"
        self.mock_client.limit_order_sell.return_value = {
            "success": False,
            "error_response": {"message": failure_reason},
        }

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        # Check that the failure was logged as an error
        expected_error_log = (
            f"[{asset_id}] Failed to place sell order. Reason: {failure_reason}"
        )
        self.mock_logger.error.assert_any_call(expected_error_log)

        # Check that the warning about reprocessing was logged
        expected_warning_log = (
            f"[{asset_id}] No sell orders were successfully placed. "
            "The filled buy trade will be re-processed."
        )
        self.mock_logger.warning.assert_called_once_with(expected_warning_log)

        # Check that no sell order was persisted
        self.mock_persistence.add_sell_order_to_filled_trade.assert_not_called()

        # Check that the "Successfully placed" info log was NOT called.
        all_info_calls = [call[0][0] for call in self.mock_logger.info.call_args_list]
        # Check that the "Successfully placed" info log was NOT called.
        all_info_calls = [call[0][0] for call in self.mock_logger.info.call_args_list]
        self.assertFalse(
            any("Successfully placed" in call for call in all_info_calls),
            "The 'Successfully placed' log should not be present on failure.",
        )

    def test_init_raises_on_none_persistence(self):
        """Test TradeManager raises AssertionError if persistence is None."""
        with self.assertRaisesRegex(
            AssertionError, "PersistenceManager dependency cannot be None"
        ):
            TradeManager(
                client=self.mock_client,
                persistence_manager=None,
                ta_module=self.mock_ta_module,
                config_module=self.mock_config_module,
                logger=self.mock_logger,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=self.mock_order_calculator_module,
            )

    def test_main_logic_routes_to_filled_buy(self):
        """Test _main_trade_logic calls _handle_filled_buy_order for filled buys."""
        # Arrange
        from unittest.mock import patch

        asset_id = "BTC-USD"
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": {"buy_order_id": "buy-123"},
            "open_buy_order": None,
        }

        with patch(
            "trading.trade_manager.TradeManager._handle_filled_buy_order"
        ) as mock_handle_filled_buy:
            # Act
            self.trade_manager.process_asset_trade_cycle(asset_id)

            # Assert
            mock_handle_filled_buy.assert_called_once()

    def test_trade_not_cleared_if_one_sell_order_is_open(self):
        """Test that a trade is not cleared if at least one sell order is not filled."""
        # Arrange
        asset_id = "BTC-USD"
        sell_orders = [
            {"order_id": "sell-1", "status": "OPEN"},
            {"order_id": "sell-2", "status": "OPEN"},
        ]
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": {
                "buy_order_id": "buy-123",
                "associated_sell_orders": sell_orders,
            }
        }

        # One order is filled, the other is still open
        self.mock_client.get_order.side_effect = [
            {"status": "FILLED"},  # For sell-1
            {"status": "OPEN"},  # For sell-2
        ]

        with patch.object(
            self.trade_manager, "_check_and_update_sell_orders"
        ) as mock_check_and_update, patch.object(
            self.trade_manager, "_place_new_sell_orders"
        ) as mock_place_new:
            # Act
            self.trade_manager.process_asset_trade_cycle(asset_id)

            # Assert
            # The key assertion: _check_and_update_sell_orders should be called
            mock_check_and_update.assert_called_once()
            # And the alternative path should not be taken
            mock_place_new.assert_not_called()
            self.mock_persistence.clear_filled_buy_trade.assert_not_called()

    def test_add_sell_order_is_called_with_correct_details(self):
        """Test that add_sell_order_to_filled_trade is called with correct details."""
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-123"
        filled_buy_trade = {
            "buy_order_id": buy_order_id,
            "buy_price": "50000",
            "buy_quantity": "0.0002",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        sell_order_params = [{"base_size": "0.0002", "limit_price": "51000.00"}]
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = (
            sell_order_params
        )

        # Mock a successful order placement
        sell_order_id = "sell-456"
        self.mock_client.limit_order_sell.return_value = {
            "success": True,
            "order_id": sell_order_id,
        }

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        expected_sell_details = {
            "order_id": sell_order_id,
            "size": str(sell_order_params[0]["base_size"]),
            "price": str(sell_order_params[0]["limit_price"]),
            "timestamp": unittest.mock.ANY,
            "status": "OPEN",
        }
        self.mock_persistence.add_sell_order_to_filled_trade.assert_called_once_with(
            asset_id=asset_id,
            buy_order_id=buy_order_id,
            sell_order_details=expected_sell_details,
        )

    def test_sell_order_failure_logs_default_message(self):
        """Test default error message is logged if no failure reason is given."""
        # Arrange
        asset_id = "BTC-USD"
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "buy_quantity": "0.0002",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        sell_order_params = [{"base_size": "0.0002", "limit_price": "51000.00"}]
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = (
            sell_order_params
        )

        # Mock a failed order placement without a specific message
        self.mock_client.limit_order_sell.return_value = {
            "success": False,
            "error_response": {},  # No 'message' key
        }

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        expected_error_log = (
            f"[{asset_id}] Failed to place sell order. Reason: No message"
        )
        self.mock_logger.error.assert_any_call(expected_error_log)

    def test_place_new_sell_orders_exception_logs_traceback(self):
        """Test that an exception in _place_new_sell_orders logs a traceback."""
        # Arrange
        asset_id = "BTC-USD"
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "buy_quantity": "0.0002",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        # Mock an exception during sell order calculation
        error_message = "Calculation Error"
        self.mock_order_calculator_module.determine_sell_orders_params.side_effect = (
            ValueError(error_message)
        )

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        self.mock_logger.error.assert_called_once_with(
            f"[{asset_id}] Exception in _place_new_sell_orders: {error_message}",
            exc_info=True,
        )

    def test_place_new_sell_orders_handles_missing_key(self):
        """Test that a KeyError in _place_new_sell_orders is handled and logged."""
        # Arrange
        asset_id = "BTC-USD"
        # This dictionary is missing the 'buy_quantity' key
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "associated_sell_orders": [],
        }
        self.mock_persistence.load_trade_state.return_value = {
            "filled_buy_trade": filled_buy_trade
        }

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        # The code should catch the KeyError and log it
        self.mock_logger.error.assert_called_once()
        logged_message = self.mock_logger.error.call_args[0][0]
        self.assertIn(
            f"[{asset_id}] Exception in _place_new_sell_orders", logged_message
        )
        self.assertIn("'buy_quantity'", logged_message)
        # Ensure traceback is logged
        self.assertEqual(self.mock_logger.error.call_args[1], {"exc_info": True})
        # Ensure no sell orders were placed
        self.mock_client.limit_order_sell.assert_not_called()

    def test_place_new_sell_orders_handles_key_error_in_loop(self):
        """Test that a KeyError in the sell order loop is handled and logged."""
        # Arrange
        asset_id = "BTC-USD"
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "buy_quantity": "1",
            "associated_sell_orders": [],
        }
        # Mock the calculator to return params missing the 'base_size' key
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = [
            {"limit_price": "50500.00"}  # Missing 'base_size'
        ]
        product_details = {"quote_increment": "0.01"}
        config_asset_params = {
            "sell_portion_pct": "0.5",
            "sell_profit_tiers": [
                {"pct": "0.5", "price_multiple": "1.01"},
                {"pct": "0.5", "price_multiple": "1.02"},
            ],
        }

        # Act
        self.trade_manager._place_new_sell_orders(
            asset_id, filled_buy_trade, product_details, config_asset_params
        )

        # Assert
        self.mock_logger.error.assert_called_once()
        logged_message = self.mock_logger.error.call_args[0][0]
        self.assertIn(
            f"[{asset_id}] Exception in _place_new_sell_orders", logged_message
        )
        self.assertIn("'base_size'", logged_message)
        self.assertEqual(self.mock_logger.error.call_args[1], {"exc_info": True})
        self.mock_client.limit_order_sell.assert_not_called()

    def test_place_new_sell_orders_handles_key_error_on_price(self):
        """Test that a KeyError for 'limit_price' is handled and logged."""
        # Arrange
        asset_id = "BTC-USD"
        filled_buy_trade = {
            "buy_order_id": "buy-123",
            "buy_price": "50000",
            "buy_quantity": "1",
            "associated_sell_orders": [],
        }
        # Mock the calculator to return params missing the 'limit_price' key
        self.mock_order_calculator_module.determine_sell_orders_params.return_value = [
            {"base_size": "0.001"}  # Missing 'limit_price'
        ]
        product_details = {"quote_increment": "0.01"}
        config_asset_params = {
            "sell_portion_pct": "0.5",
            "sell_profit_tiers": [
                {"pct": "0.5", "price_multiple": "1.01"},
                {"pct": "0.5", "price_multiple": "1.02"},
            ],
        }

        # Act
        self.trade_manager._place_new_sell_orders(
            asset_id, filled_buy_trade, product_details, config_asset_params
        )

        # Assert
        self.mock_logger.error.assert_called_once()
        logged_message = self.mock_logger.error.call_args[0][0]
        self.assertIn(
            f"[{asset_id}] Exception in _place_new_sell_orders", logged_message
        )
        self.assertIn("'limit_price'", logged_message)
        self.assertEqual(self.mock_logger.error.call_args[1], {"exc_info": True})
        self.mock_client.limit_order_sell.assert_not_called()

    def test_handle_buy_filled_with_no_filled_size(self):
        """Test handling a filled buy order with no 'filled_size' in API response."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {
            "order_id": order_id,
            "timestamp": time.time(),
            "size": "0.1",
            "price": "50000",
        }
        self.mock_persistence.load_trade_state.return_value = {
            "open_buy_order": open_buy_order
        }

        # Act
        with patch.object(
            self.mock_client,
            "get_order",
            return_value={
                "status": "FILLED",
                "average_filled_price": "50001",
                # 'filled_size' is missing
            },
        ) as mock_get_order:
            self.trade_manager.process_asset_trade_cycle(asset_id)

            # Assert
            mock_get_order.assert_called_once_with(order_id)
            self.mock_persistence.save_filled_buy_trade.assert_not_called()
            self.mock_persistence.clear_open_buy_order.assert_not_called()
            self.mock_logger.error.assert_not_called()
            self.mock_logger.warning.assert_called_once_with(
                f"[{asset_id}] Buy order {order_id} filled but with 0 size or price."
            )

    def test_handle_new_buy_order_executes_buy_on_signal(self):
        """Test that a new buy order is executed when a buy signal is detected."""
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        product_details = self.mock_client.get_product.return_value
        mock_candles = MagicMock()

        with patch.object(
            self.trade_manager,
            "_analyze_market_for_buy_signal",
            return_value=mock_candles,
        ) as mock_analyze, patch.object(
            self.trade_manager, "_execute_buy_order"
        ) as mock_execute:
            # Act
            self.trade_manager._handle_new_buy_order(
                asset_id, product_details, config_asset_params
            )

            # Assert
            mock_analyze.assert_called_once_with(asset_id, config_asset_params)
            mock_execute.assert_called_once_with(
                asset_id, product_details, config_asset_params, mock_candles
            )

    def test_handle_filled_buy_order_checks_existing_sell_orders(self):
        """
        Test that _handle_filled_buy_order calls _check_and_update_sell_orders
        when associated_sell_orders exist.
        """
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-123"
        mock_sell_orders = {"sell-1": {"status": "OPEN"}}

        mock_filled_trade = {
            "buy_order_id": buy_order_id,
            "associated_sell_orders": mock_sell_orders,
        }

        product_details = {}
        config_asset_params = {}

        with patch.object(
            self.trade_manager, "_check_and_update_sell_orders"
        ) as mock_check_sells, patch.object(
            self.trade_manager, "_place_new_sell_orders"
        ) as mock_place_sells:
            # Act
            self.trade_manager._handle_filled_buy_order(
                asset_id, mock_filled_trade, product_details, config_asset_params
            )

            # Assert
            mock_check_sells.assert_called_once_with(
                asset_id=asset_id,
                buy_order_id=buy_order_id,
                sell_orders=mock_sell_orders,
            )
            mock_place_sells.assert_not_called()

    def test_handle_open_buy_order_handles_type_error_from_decimal(self):
        """Test that a TypeError from Decimal conversion is handled gracefully."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {
            "order_id": order_id,
            "timestamp": time.time(),
            "size": "0.1",
            "price": "50000",
        }
        self.mock_persistence.load_trade_state.return_value = {
            "open_buy_order": open_buy_order
        }

        # Act
        with patch.object(
            self.mock_client,
            "get_order",
            return_value={
                "status": "FILLED",
                "filled_size": None,  # Decimal(None) raises TypeError
                "average_filled_price": "50001",
            },
        ) as mock_get_order:
            self.trade_manager.process_asset_trade_cycle(asset_id)

            # Assert
            mock_get_order.assert_called_once_with(order_id)
            # Check that the error was logged with a traceback
            self.mock_logger.error.assert_called_once()
        args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            f"[{asset_id}] Exception checking open buy order {order_id}", args[0]
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_handle_buy_filled_with_no_avg_price(self):
        """Test handling a filled buy order with no 'average_filled_price'."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {"order_id": order_id}
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        # Mock API response: filled, has size, but no price.
        self.mock_client.get_order.return_value = {
            "status": "FILLED",
            "filled_size": "1.0",
            # 'average_filled_price' is missing
        }

        with patch.object(
            self.trade_manager, "_handle_filled_buy_order"
        ) as mock_handle_filled:
            # Act
            self.trade_manager._handle_open_buy_order(
                asset_id, open_buy_order, product_details, config_asset_params
            )

            # Assert
            self.mock_client.get_order.assert_called_once_with(order_id)
            mock_handle_filled.assert_not_called()
            self.mock_persistence.save_filled_buy_trade.assert_not_called()
            self.mock_logger.warning.assert_called_once_with(
                f"[{asset_id}] Buy order {order_id} filled but with 0 size or price."
            )
            self.mock_logger.error.assert_not_called()

    def test_handle_buy_filled_with_invalid_avg_price(self):
        """Test handling a filled buy with an invalid 'average_filled_price'."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {"order_id": order_id}
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        self.mock_client.get_order.return_value = {
            "status": "FILLED",
            "filled_size": "1.0",
            "average_filled_price": "not-a-decimal",
        }

        with patch.object(
            self.trade_manager, "_handle_filled_buy_order"
        ) as mock_handle_filled:
            # Act
            self.trade_manager._handle_open_buy_order(
                asset_id, open_buy_order, product_details, config_asset_params
            )

            # Assert
            mock_handle_filled.assert_not_called()
            # An error should be logged for the invalid price.
            expected_log = (
                f"[{asset_id}] Invalid 'average_filled_price' "
                f"received for order {order_id}."
            )
            self.mock_logger.error.assert_called_once_with(expected_log)
            # A warning should be logged because avg_price defaults to 0.
            self.mock_logger.warning.assert_called_once_with(
                f"[{asset_id}] Buy order {order_id} filled but with 0 size or price."
            )

    def test_handle_open_buy_order_filled_with_zero_avg_price(self):
        """Test handling a filled buy order with an average_filled_price of zero."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {"order_id": order_id}
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        # Mock API response: filled, has size, but zero price.
        self.mock_client.get_order.return_value = {
            "status": "FILLED",
            "filled_size": "1.0",
            "average_filled_price": "0",
        }

        with patch.object(
            self.trade_manager, "_handle_filled_buy_order"
        ) as mock_handle_filled:
            # Act
            self.trade_manager._handle_open_buy_order(
                asset_id, open_buy_order, product_details, config_asset_params
            )

            # Assert
            self.mock_client.get_order.assert_called_once_with(order_id)
            mock_handle_filled.assert_not_called()
            self.mock_persistence.save_filled_buy_trade.assert_not_called()
            self.mock_logger.warning.assert_called_once_with(
                f"[{asset_id}] Buy order {order_id} filled but with 0 size or price."
            )
            self.mock_logger.error.assert_not_called()

    def test_handle_buy_filled_with_low_avg_price(self):
        """Test handling a filled buy with a low but valid 'average_filled_price'."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {"order_id": order_id}
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        # Mock API response: filled, has size, and a low price.
        self.mock_client.get_order.return_value = {
            "status": "FILLED",
            "filled_size": "1.0",
            "average_filled_price": "1",
        }

        with patch.object(
            self.trade_manager, "_handle_filled_buy_order"
        ) as mock_handle_filled:
            # Act
            self.trade_manager._handle_open_buy_order(
                asset_id, open_buy_order, product_details, config_asset_params
            )

            # Assert
            self.mock_client.get_order.assert_called_once_with(order_id)
            # The success path should be taken
            mock_handle_filled.assert_called_once()
            self.mock_persistence.save_filled_buy_trade.assert_called_once()
            self.mock_logger.warning.assert_not_called()
            self.mock_logger.error.assert_not_called()

    def test_handle_open_buy_order_cancelled(self):
        """Test handling a cancelled open buy order."""
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-123"
        open_buy_order = {"order_id": order_id}
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        # Mock API response for a cancelled order
        self.mock_client.get_order.return_value = {"status": "CANCELLED"}

        # Act
        self.trade_manager._handle_open_buy_order(
            asset_id, open_buy_order, product_details, config_asset_params
        )

        # Assert
        self.mock_client.get_order.assert_called_once_with(order_id)
        self.mock_logger.info.assert_any_call(
            f"[{asset_id}] Buy order {order_id} was cancelled."
        )
        self.mock_persistence.clear_open_buy_order.assert_called_once_with(
            asset_id=asset_id
        )

    def test_analyze_market_converts_columns_to_numeric(self):
        """Test _analyze_market_for_buy_signal converts columns to numeric."""
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        mock_candles = [
            {
                "start": "1672531200",
                "open": "16500.0",
                "high": "16600.0",
                "low": "16400.0",
                "close": "16550.0",
                "volume": "100.0",
            }
        ]
        self.mock_client.get_public_candles.return_value = mock_candles
        # Mock downstream calls to isolate the numeric conversion logic
        self.trade_manager.ta_module.calculate_rsi.return_value = pd.Series([50])
        self.mock_signal_analyzer_module.should_buy_asset.return_value = True

        # Act
        self.trade_manager._analyze_market_for_buy_signal(asset_id, config_asset_params)

        # Assert
        # Verify that the DataFrame passed to calculate_rsi has numeric columns
        self.trade_manager.ta_module.calculate_rsi.assert_called_once()
        call_args, _ = self.trade_manager.ta_module.calculate_rsi.call_args
        candles_df = call_args[0]

        self.assertIsInstance(candles_df, pd.DataFrame)
        for col in ["open", "high", "low", "close", "volume"]:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(candles_df[col]),
                (
                    f"Column '{col}' should be numeric "
                    f"but has dtype {candles_df[col].dtype}"
                ),
            )

    def test_analyze_market_does_not_log_on_success(self):
        """Test _analyze_market_for_buy_signal does not log on success."""
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        mock_candles = [
            {
                "start": "1672531200",
                "open": "16500.0",
                "high": "16600.0",
                "low": "16400.0",
                "close": "16550.0",
                "volume": "100.0",
            }
        ]
        self.mock_client.get_public_candles.return_value = mock_candles
        self.trade_manager.ta_module.calculate_rsi.return_value = pd.Series([50])
        self.mock_signal_analyzer_module.should_buy_asset.return_value = True

        # Act
        self.trade_manager._analyze_market_for_buy_signal(asset_id, config_asset_params)

        # Assert
        self.mock_logger.error.assert_not_called()
        self.mock_logger.warning.assert_not_called()

    def test_process_asset_trade_cycle_handles_none_trade_state(self):
        """Test that process_asset_trade_cycle handles a None trade_state gracefully."""
        # Arrange
        asset_id = "BTC-USD"
        self.mock_persistence.load_trade_state.return_value = None

        # Act
        self.trade_manager.process_asset_trade_cycle(asset_id)

        # Assert
        self.mock_logger.error.assert_called_once()
        args, kwargs = self.mock_logger.error.call_args
        self.assertIn(
            f"[{asset_id}] Unhandled error in process_asset_trade_cycle", args[0]
        )
        self.assertTrue(kwargs.get("exc_info"))

    def test_check_and_update_sell_orders_handles_none_from_get_order(self):
        """Test _check_and_update_sell_orders handles None from get_order."""
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        sell_order_id = "sell-123"
        sell_orders = {
            sell_order_id: {"status": "OPEN", "size": "0.1", "price": "60000"}
        }
        self.mock_client.get_order.return_value = None

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        self.mock_logger.warning.assert_called_once_with(
            f"[{asset_id}] Failed to get status for sell order {sell_order_id}."
        )
        self.mock_persistence.clear_filled_buy_trade.assert_not_called()

    def test_check_and_update_sell_orders_skips_empty_order_id(self):
        """Test that _check_and_update_sell_orders skips orders with an empty ID."""
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-abc"
        sell_orders = {
            "": {"status": "OPEN"},  # Order with empty ID
            "sell-456": {"status": "OPEN"},
        }
        self.mock_client.get_order.return_value = {"status": "FILLED"}

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        # Logger should warn about the empty ID
        self.mock_logger.warning.assert_called_once_with(
            f"[{asset_id}] Skipping sell order with no ID."
        )
        # get_order should only be called for the valid order
        self.mock_client.get_order.assert_called_once_with("sell-456")

    def test_init_raises_assertion_error_if_ta_module_is_none(self):
        """Test __init__ raises AssertionError if ta_module is None."""
        with pytest.raises(
            AssertionError, match=r"TA module dependency cannot be None"
        ):
            TradeManager(
                client=self.mock_client,
                persistence_manager=self.mock_persistence,
                ta_module=None,
                config_module=self.mock_config_module,
                logger=self.mock_logger,
                signal_analyzer=self.mock_signal_analyzer_module,
                order_calculator=self.mock_order_calculator_module,
            )

    def test_analyze_market_for_buy_signal_handles_none_rsi_series(self):
        """
        Test that _analyze_market_for_buy_signal returns None when RSI calculation
        returns None.
        """
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        self.mock_client.get_public_candles.return_value = [
            (1622548800, 50000, 51000, 49000, 50500, 100)
        ] * 20

        # Mock RSI calculation to return None
        self.trade_manager.ta_module.calculate_rsi.return_value = None

        # Act
        result = self.trade_manager._analyze_market_for_buy_signal(
            asset_id, config_asset_params
        )

        # Assert
        self.assertIsNone(result)
        self.mock_logger.warning.assert_called_with(
            f"[{asset_id}] RSI calculation failed."
        )

    def test_analyze_market_for_buy_signal_logs_exception_with_traceback(self):
        """
        Test that _analyze_market_for_buy_signal logs exceptions with a full traceback.
        """
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        error_message = "API Error"
        self.mock_client.get_public_candles.side_effect = Exception(error_message)

        # Act
        result = self.trade_manager._analyze_market_for_buy_signal(
            asset_id, config_asset_params
        )

        # Assert
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()
        call_args, call_kwargs = self.mock_logger.error.call_args
        expected_log = (
            f"[{asset_id}] Exception in _analyze_market_for_buy_signal: "
            f"{error_message}"
        )
        self.assertIn(expected_log, call_args[0])
        self.assertTrue(call_kwargs.get("exc_info"))

    def test_execute_buy_order_uses_last_candle_close_price(self):
        """
        Test that _execute_buy_order uses the 'close' price of the last candle
        and calls the client with a valid client_order_id.
        """
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        product_details = self.mock_client.get_product.return_value
        candles = [
            {"close": 50000, "volume": 100},
            {"close": 51000, "volume": 110},
            {"close": 52000, "volume": 120},  # This is the last candle
        ]
        last_candle_close = Decimal(str(candles[-1]["close"]))

        buy_size = Decimal("0.001")
        buy_price = Decimal("51500")
        self.trade_manager.order_calculator.calculate_buy_order_details.return_value = (
            buy_size,
            buy_price,
        )

        # Act
        self.trade_manager._execute_buy_order(
            asset_id, product_details, config_asset_params, candles
        )

        # Assert
        calculate_details_mock = (
            self.trade_manager.order_calculator.calculate_buy_order_details
        )
        calculate_details_mock.assert_called_once()
        (
            _,
            kwargs,
        ) = calculate_details_mock.call_args
        self.assertEqual(kwargs["last_close_price"], last_candle_close)

        self.mock_client.limit_order_buy.assert_called_once_with(
            product_id=asset_id,
            base_size=str(buy_size),
            limit_price=str(buy_price),
        )

    def test_execute_buy_order_handles_failed_order_placement(self):
        """
        Test that _execute_buy_order correctly handles a failed API call
        when placing a buy order.
        """
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        product_details = self.mock_client.get_product.return_value
        candles = [{"close": 52000, "volume": 120}]

        buy_size = Decimal("0.001")
        buy_price = Decimal("51500")
        self.trade_manager.order_calculator.calculate_buy_order_details.return_value = (
            buy_size,
            buy_price,
        )

        # Mock a failed order placement
        error_message = "Insufficient funds"
        self.mock_client.limit_order_buy.return_value = {
            "success": False,
            "error_response": {"message": error_message},
        }

        # Act
        self.trade_manager._execute_buy_order(
            asset_id, product_details, config_asset_params, candles
        )

        # Assert
        expected_log_message = (
            f"[{asset_id}] Failed to place buy order. Reason: {error_message}"
        )
        self.mock_logger.error.assert_called_once_with(expected_log_message)
        self.mock_persistence.save_open_buy_order.assert_not_called()

    def test_execute_buy_order_handles_failed_order_with_no_message(self):
        """
        Test that _execute_buy_order handles a failed order placement
        where the error_response does not contain a 'message' key.
        """
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        product_details = self.mock_client.get_product.return_value
        candles = [{"close": 52000, "volume": 120}]

        buy_size = Decimal("0.001")
        buy_price = Decimal("51500")
        self.trade_manager.order_calculator.calculate_buy_order_details.return_value = (
            buy_size,
            buy_price,
        )

        # Mock a failed order placement with no specific message
        self.mock_client.limit_order_buy.return_value = {
            "success": False,
            "error_response": {},
        }

        # Act
        self.trade_manager._execute_buy_order(
            asset_id, product_details, config_asset_params, candles
        )

        # Assert
        expected_log_message = (
            f"[{asset_id}] Failed to place buy order. Reason: No message"
        )
        self.mock_logger.error.assert_called_once_with(expected_log_message)
        self.mock_persistence.save_open_buy_order.assert_not_called()

    def test_handle_open_buy_order_transitions_to_handle_filled_buy_order(self):
        """
        Test that a filled open buy order correctly transitions to handling the
        filled trade, passing a correctly structured dictionary.
        """
        # Arrange
        asset_id = "BTC-USD"
        order_id = "buy-order-123"
        open_buy_order = {"order_id": order_id}
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]

        order_status = {
            "status": "FILLED",
            "filled_size": "1.0",
            "average_filled_price": "50000.0",
        }
        self.mock_client.get_order.return_value = order_status

        sell_params = {"tier_1": "params"}
        mock_order_calculator = self.trade_manager.order_calculator
        mock_order_calculator.determine_sell_orders_params.return_value = sell_params

        # Patch the method that gets called after the transition
        with patch.object(
            self.trade_manager, "_handle_filled_buy_order"
        ) as mock_handle_filled:
            # Act
            self.trade_manager._handle_open_buy_order(
                asset_id, open_buy_order, product_details, config_asset_params
            )

            # Assert
            mock_handle_filled.assert_called_once()

            args, _ = mock_handle_filled.call_args
            passed_asset_id = args[0]
            filled_buy_trade_arg = args[1]

            self.assertEqual(passed_asset_id, asset_id)
            self.assertIn("buy_order_id", filled_buy_trade_arg)
            self.assertEqual(filled_buy_trade_arg["buy_order_id"], order_id)
            self.assertEqual(filled_buy_trade_arg["filled_order"], order_status)
            self.assertEqual(filled_buy_trade_arg["sell_orders_params"], sell_params)
            self.assertEqual(filled_buy_trade_arg["sell_orders"], {})

    def test_process_asset_trade_cycle_with_valid_config_proceeds(self):
        """
        Test that process_asset_trade_cycle proceeds past the config check
        when a valid asset config is found.
        """
        # Arrange
        asset_id = "BTC-USD"

        # Patch a method that is called immediately after the config check
        with patch.object(
            self.trade_manager, "_get_product_details"
        ) as mock_get_product_details:
            # Configure mocks to prevent downstream errors
            mock_get_product_details.return_value = (
                self.mock_client.get_product.return_value
            )
            self.mock_persistence.load_open_buy_order.return_value = None
            self.mock_persistence.load_filled_buy_trade.return_value = None
            self.trade_manager._handle_new_buy_order = Mock()

            # Act
            self.trade_manager.process_asset_trade_cycle(asset_id)

            # Assert
            # This assertion will fail if the mutant is active, as the function will
            # have returned before this method is called.
            mock_get_product_details.assert_called_once_with(asset_id)

    def test_execute_buy_order_logs_exception_with_traceback(self):
        """
        Test that _execute_buy_order logs an exception with a traceback
        if an unexpected error occurs.
        """
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        product_details = self.mock_client.get_product.return_value
        candles = [{"close": 52000, "volume": 120}]
        test_exception = Exception("Something went wrong")

        # Force an exception
        self.trade_manager.order_calculator.calculate_buy_order_details.side_effect = (
            test_exception
        )

        # Act
        self.trade_manager._execute_buy_order(
            asset_id, product_details, config_asset_params, candles
        )

        # Assert
        self.mock_logger.error.assert_called_once()
        call_args, call_kwargs = self.mock_logger.error.call_args
        self.assertIn(
            f"[{asset_id}] Exception in _execute_buy_order: {test_exception}",
            call_args[0],
        )
        self.assertTrue(call_kwargs.get("exc_info"))

    def test_check_and_update_sell_orders_clears_trade_state_when_all_filled(self):
        """
        Test that _check_and_update_sell_orders clears the trade state
        when all sell orders are filled.
        """
        # Arrange
        asset_id = "BTC-USD"
        buy_order_id = "buy-order-123"
        sell_orders = {
            "sell-order-1": {"status": "FILLED"},
            "sell-order-2": {"status": "FILLED"},
        }

        # Act
        self.trade_manager._check_and_update_sell_orders(
            asset_id, buy_order_id, sell_orders
        )

        # Assert
        self.mock_persistence.clear_filled_buy_trade.assert_called_once_with(
            asset_id=asset_id
        )

    def test_execute_buy_order_does_not_log_on_success(self):
        """Test that _execute_buy_order does not log any errors on a successful run."""
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        product_details = self.mock_client.get_product.return_value
        candles = [{"close": "52000", "volume": "120"}]

        # Mock the return value for the calculation
        self.trade_manager.order_calculator.calculate_buy_order_details.return_value = (
            Decimal("0.00019"),
            Decimal("51000.00"),
        )
        self.mock_client.limit_order_buy.return_value = {
            "success": True,
            "order_id": "new-buy-order",
        }

        # Act
        self.trade_manager._execute_buy_order(
            asset_id, product_details, config_asset_params, candles
        )

        # Assert
        self.mock_logger.error.assert_not_called()
        self.mock_logger.warning.assert_not_called()
        self.mock_client.limit_order_buy.assert_called_once()

    def test_execute_buy_order_logs_error_if_order_id_is_missing(self):
        """Test that an error is logged if a successful order is missing an order_id."""
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        product_details = self.mock_client.get_product.return_value
        candles = [{"close": "52000", "volume": "120"}]

        # Mock the return value for the calculation
        self.trade_manager.order_calculator.calculate_buy_order_details.return_value = (
            Decimal("0.00019"),
            Decimal("51000.00"),
        )
        # Simulate a successful order but with a missing order_id
        self.mock_client.limit_order_buy.return_value = {"success": True}

        # Act
        self.trade_manager._execute_buy_order(
            asset_id, product_details, config_asset_params, candles
        )

        # Assert
        expected_error_log = (
            f"[{asset_id}] Order placed successfully but no "
            "order_id returned from exchange."
        )
        self.mock_logger.error.assert_called_once_with(expected_error_log)
        self.mock_persistence.save_trade_state.assert_not_called()

    def test_handle_filled_buy_order_logs_error_if_buy_order_id_missing(self):
        """Test that an error is logged if buy_order_id is missing."""
        # Arrange
        asset_id = "BTC-USD"
        product_details = self.mock_client.get_product.return_value
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        filled_buy_trade = {
            "buy_price": "50000",
            "buy_quantity": "0.0002",
            "associated_sell_orders": [],
        }
        # Patch the method that would be called next to prevent side effects
        self.trade_manager._place_new_sell_orders = Mock()

        # Act
        self.trade_manager._handle_filled_buy_order(
            asset_id, filled_buy_trade, product_details, config_asset_params
        )

        # Assert
        self.mock_logger.error.assert_called_once_with(
            f"[{asset_id}] Corrupted trade state: buy_order_id missing."
        )
        self.trade_manager._place_new_sell_orders.assert_not_called()

    def test_place_new_sell_orders_logs_error_if_no_params_generated(self):
        """Test that an error is logged if no sell order parameters are generated."""
        # Arrange
        asset_id = "BTC-USD"
        product_details = {"quote_increment": "0.01", "base_increment": "0.00001"}
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        filled_buy_trade = {
            "buy_order_id": "buy-order-123",
            "buy_price": "50000",
            "buy_quantity": "0.0002",
        }

        self.mock_order_calculator_module.determine_sell_orders_params.return_value = []

        # Act
        self.trade_manager._place_new_sell_orders(
            asset_id, filled_buy_trade, product_details, config_asset_params
        )

        # Assert
        self.mock_logger.error.assert_called_once_with(
            f"[{asset_id}] No sell orders were generated. Check config and logs."
        )
        self.mock_client.limit_order_sell.assert_not_called()

    def test_analyze_market_integration_with_real_ta(self):
        """Test integration with real TA module for candle processing."""
        # Arrange
        asset_id = "BTC-USD"
        config_asset_params = self.mock_config_module.TRADING_PAIRS[asset_id]
        mock_candles = [
            {
                "start": "1672531200",
                "open": "16500.0",
                "high": "16600.0",
                "low": "16400.0",
                "close": "16550.0",
                "volume": "100.0",
            }
        ] * 20  # Ensure enough data for RSI calculation
        self.mock_client.get_public_candles.return_value = mock_candles

        # Use the real technical_analysis module instead of a mock
        self.trade_manager.ta_module = technical_analysis

        # Mock the signal analyzer to return True to complete the code path
        self.mock_signal_analyzer_module.should_buy_asset.return_value = True

        # Act & Assert
        # This should run without error as columns are converted to numeric
        try:
            self.trade_manager._analyze_market_for_buy_signal(
                asset_id, config_asset_params
            )
        except Exception as e:
            self.fail(
                f"_analyze_market_for_buy_signal raised an unexpected exception: {e}"
            )
