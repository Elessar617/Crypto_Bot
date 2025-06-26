"""Unit tests for main.py module."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

# Ensure the project root is in the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to be tested
import main


class TestMainModule(unittest.TestCase):
    """Tests for the main.py run_bot function."""

    def test_run_bot_success(self):
        """Test successful execution of run_bot with multiple assets."""
        # Create mocks for all modules imported within run_bot
        mock_cc_module = MagicMock()
        mock_p_module = MagicMock()
        mock_ta_module = MagicMock()
        mock_sa_module = MagicMock()
        mock_oc_module = MagicMock()

        # Mock the TradeManager class separately
        mock_tm_class = MagicMock()

        # Set up the mocks for the 'trading' package structure
        mock_trading_pkg = MagicMock()
        mock_trading_pkg.signal_analyzer = mock_sa_module
        mock_trading_pkg.order_calculator = mock_oc_module
        mock_trading_pkg.TradeManager = mock_tm_class

        mock_modules = {
            'coinbase_client': mock_cc_module,
            'persistence': mock_p_module,
            'technical_analysis': mock_ta_module,
            'trading': mock_trading_pkg,
            'trading.signal_analyzer': mock_sa_module,
            'trading.order_calculator': mock_oc_module,
            'trading.trade_manager': MagicMock(TradeManager=mock_tm_class)
        }

        with patch.dict('sys.modules', mock_modules), \
             patch("main.config") as mock_config, \
             patch("main.get_logger") as mock_get_logger, \
             patch("main.sys.exit") as mock_sys_exit:

            # --- Setup Mocks ---
            mock_config.LOG_LEVEL = "DEBUG"
            mock_config.TRADING_PAIRS = ["BTC-USD", "ETH-USD"]
            mock_logger = mock_get_logger.return_value
            mock_client_instance = mock_cc_module.CoinbaseClient.return_value
            mock_trade_manager_instance = mock_tm_class.return_value

            # --- Run the function ---
            main.run_bot()

            # --- Assertions ---
            mock_get_logger.assert_called_once_with()
            mock_logger.info.assert_any_call("--- Starting v6 crypto trading bot run ---")
            mock_cc_module.CoinbaseClient.assert_called_once_with()
            mock_logger.info.assert_any_call("Coinbase client initialized successfully.")

            # Verify TradeManager was initialized correctly
            mock_tm_class.assert_called_once_with(
                client=mock_client_instance,
                persistence_manager=mock_p_module,
                ta_module=mock_ta_module,
                config_module=mock_config,
                logger=mock_logger,
                signal_analyzer=mock_sa_module,
                order_calculator=mock_oc_module,
            )

            # Verify the processing loop
            mock_logger.info.assert_any_call("Processing 2 configured trading pairs.")
            self.assertEqual(mock_trade_manager_instance.process_asset_trade_cycle.call_count, 2)
            expected_calls = [call(asset_id="BTC-USD"), call(asset_id="ETH-USD")]
            mock_trade_manager_instance.process_asset_trade_cycle.assert_has_calls(
                expected_calls, any_order=True
            )

            # Verify logging for each asset cycle
            mock_logger.info.assert_any_call("--- Starting trade cycle for BTC-USD ---")
            mock_logger.info.assert_any_call("--- Completed trade cycle for BTC-USD ---")
            mock_logger.info.assert_any_call("--- Starting trade cycle for ETH-USD ---")
            mock_logger.info.assert_any_call("--- Completed trade cycle for ETH-USD ---")
            mock_logger.info.assert_any_call(unittest.mock.ANY)
            mock_sys_exit.assert_not_called()


    def test_run_bot_client_initialization_failure(self):
        """Test run_bot exits when CoinbaseClient initialization fails."""
        mock_cc_module = MagicMock()
        error_message = "Invalid API keys"
        mock_cc_module.CoinbaseClient.side_effect = RuntimeError(error_message)

        mock_modules = {'coinbase_client': mock_cc_module}

        with patch.dict('sys.modules', mock_modules), \
             patch("main.get_logger") as mock_get_logger, \
             patch("main.sys.exit") as mock_sys_exit, \
             patch("main.config") as mock_config:

            mock_config.LOG_LEVEL = "DEBUG"

            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            main.run_bot()

            mock_logger.critical.assert_called_once_with(
                f"A critical error occurred during bot initialization: {error_message}",
                exc_info=True,
            )
            mock_sys_exit.assert_called_once_with(1)

    def test_run_bot_asset_processing_error_continues(self):
        """Test that an error in one asset doesn't stop the next one."""
        mock_cc_module = MagicMock()
        mock_tm_module = MagicMock()
        mock_p_module = MagicMock()
        mock_sa_module = MagicMock()
        mock_oc_module = MagicMock()
        mock_ta_module = MagicMock()

        mock_modules = {
            'coinbase_client': mock_cc_module,
            'trading.trade_manager': mock_tm_module,
            'persistence': mock_p_module,
            'trading.signal_analyzer': mock_sa_module,
            'trading.order_calculator': mock_oc_module,
            'technical_analysis': mock_ta_module,
        }

        with patch.dict('sys.modules', mock_modules), \
             patch("main.config") as mock_config, \
             patch("main.get_logger") as mock_get_logger, \
             patch("main.sys.exit") as mock_sys_exit:

            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_trade_manager_instance = mock_tm_module.TradeManager.return_value
            mock_config.TRADING_PAIRS = ["BTC-USD", "ETH-USD"]
            mock_config.LOG_LEVEL = "DEBUG"

            error_message = "Test processing error"
            mock_trade_manager_instance.process_asset_trade_cycle.side_effect = [
                Exception(error_message),
                None,  # Success for the second asset
            ]

            main.run_bot()

            self.assertEqual(mock_trade_manager_instance.process_asset_trade_cycle.call_count, 2)
            mock_logger.error.assert_called_once_with(
                f"An unexpected error occurred while processing asset BTC-USD: {error_message}",
                exc_info=True,
            )
            # Check that the second asset was still processed
            mock_trade_manager_instance.process_asset_trade_cycle.assert_any_call(asset_id="ETH-USD")
            mock_logger.info.assert_any_call("--- Completed trade cycle for BTC-USD ---")
            mock_logger.info.assert_any_call("--- Completed trade cycle for ETH-USD ---")
            mock_sys_exit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
