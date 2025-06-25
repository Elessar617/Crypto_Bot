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

    @patch("main.config")
    @patch("main.get_logger")
    @patch("main.coinbase_client.CoinbaseClient")
    @patch("main.TradeManager")
    @patch("main.persistence")
    @patch("main.sys.exit")
    @patch("main.signal_analyzer")
    @patch("main.order_calculator")
    def test_run_bot_success(
        self,
        mock_order_calculator,
        mock_signal_analyzer,
        mock_sys_exit,
        mock_persistence,
        mock_trade_manager_class,
        mock_client_class,
        mock_get_logger,
        mock_config,
    ):
        """Test successful execution of run_bot with multiple assets."""
        # --- Setup Mocks ---
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        mock_trade_manager_instance = MagicMock()
        mock_trade_manager_class.return_value = mock_trade_manager_instance

        # Configure mock_config with test data
        mock_config.TRADING_PAIRS = {
            "BTC-USD": {},
            "ETH-USD": {},
        }

        # --- Run the function ---
        main.run_bot()

        # --- Assertions ---
        mock_get_logger.assert_called_once_with("v6_bot_main")
        mock_logger.info.assert_any_call("--- Starting v6 crypto trading bot run ---")
        mock_client_class.assert_called_once_with()
        mock_logger.info.assert_any_call("Coinbase client initialized successfully.")

        # Verify TradeManager was initialized correctly
        mock_trade_manager_class.assert_called_once_with(
            client=mock_client_instance,
            persistence_manager=mock_persistence,
            ta_module=main.technical_analysis,
            config_module=mock_config,
            logger=mock_logger,
            signal_analyzer=mock_signal_analyzer,
            order_calculator=mock_order_calculator,
        )

        # Verify the processing loop
        mock_logger.info.assert_any_call("Processing 2 configured trading pairs.")
        self.assertEqual(
            mock_trade_manager_instance.process_asset_trade_cycle.call_count, 2
        )
        expected_calls = [call(asset_id="BTC-USD"), call(asset_id="ETH-USD")]
        mock_trade_manager_instance.process_asset_trade_cycle.assert_has_calls(
            expected_calls, any_order=True
        )

        # Verify logging for each asset cycle
        mock_logger.info.assert_any_call("--- Starting trade cycle for BTC-USD ---")
        mock_logger.info.assert_any_call("--- Completed trade cycle for BTC-USD ---")
        mock_logger.info.assert_any_call("--- Starting trade cycle for ETH-USD ---")
        mock_logger.info.assert_any_call("--- Completed trade cycle for ETH-USD ---")
        mock_logger.info.assert_any_call(
            unittest.mock.ANY  # Match any string for the final time log
        )

    @patch("main.sys.exit")
    @patch("main.get_logger")
    @patch("main.coinbase_client.CoinbaseClient")
    def test_run_bot_client_initialization_failure(
        self, mock_client_class, mock_get_logger, mock_exit
    ):
        """Test run_bot exits when CoinbaseClient initialization fails."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        error_message = "Invalid API keys"
        mock_client_class.side_effect = RuntimeError(error_message)

        main.run_bot()

        mock_logger.critical.assert_called_once_with(
            f"A critical error occurred during bot initialization: {error_message}",
            exc_info=True,
        )
        mock_exit.assert_called_once_with(1)

    @patch("main.config")
    @patch("main.get_logger")
    @patch("main.coinbase_client.CoinbaseClient")
    @patch("main.TradeManager")
    @patch("main.persistence")
    @patch("main.sys.exit")
    def test_run_bot_asset_processing_error_continues(
        self, mock_exit, mock_persistence, mock_trade_manager_class, mock_client_class, mock_get_logger, mock_config
    ):
        """Test that an error in one asset doesn't stop the next one."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_client_class.return_value = MagicMock()
        mock_trade_manager_instance = MagicMock()
        mock_trade_manager_class.return_value = mock_trade_manager_instance
        mock_config.TRADING_PAIRS = {"BTC-USD": {}, "ETH-USD": {}}

        error_message = "Test processing error"
        mock_trade_manager_instance.process_asset_trade_cycle.side_effect = [
            Exception(error_message),
            None,
        ]

        main.run_bot()

        self.assertEqual(
            mock_trade_manager_instance.process_asset_trade_cycle.call_count, 2
        )
        mock_logger.error.assert_called_once_with(
            f"An unexpected error occurred while processing asset BTC-USD: {error_message}",
            exc_info=True,
        )
        mock_trade_manager_instance.process_asset_trade_cycle.assert_any_call(
            asset_id="ETH-USD"
        )
        mock_logger.info.assert_any_call("--- Completed trade cycle for BTC-USD ---")
        mock_logger.info.assert_any_call("--- Completed trade cycle for ETH-USD ---")


if __name__ == "__main__":
    unittest.main()
