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
    @patch("main.trading_logic.process_asset_trade_cycle")
    @patch("main.persistence")
    def test_run_bot_success(
        self,
        mock_persistence,
        mock_process_cycle,
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

        # Configure mock_config with test data
        mock_config.TRADING_PAIRS = {
            "BTC-USD": {},
            "ETH-USD": {},
        }

        # --- Run the function ---
        main.run_bot()

        # --- Assertions ---
        # Logger initialization
        mock_get_logger.assert_called_once_with("v6_bot_main")
        mock_logger.info.assert_any_call("--- Starting v6 crypto trading bot run ---")

        # Coinbase client initialization
        mock_client_class.assert_called_once_with()
        mock_logger.info.assert_any_call("Coinbase client initialized successfully.")

        # Asset processing loop
        mock_logger.info.assert_any_call("Processing 2 configured trading pairs.")
        self.assertEqual(mock_process_cycle.call_count, 2)

        # Verify the calls to the core trading logic function
        expected_calls = [
            call(
                asset_id="BTC-USD",
                client=mock_client_instance,
                persistence_manager=mock_persistence,  # The module itself
                ta_module=main.technical_analysis,
                config_module=mock_config,
                logger=mock_logger,
            ),
            call(
                asset_id="ETH-USD",
                client=mock_client_instance,
                persistence_manager=mock_persistence,  # The module itself
                ta_module=main.technical_analysis,
                config_module=mock_config,
                logger=mock_logger,
            ),
        ]
        mock_process_cycle.assert_has_calls(expected_calls, any_order=True)

        # Verify logging for each asset cycle
        mock_logger.info.assert_any_call("--- Starting trade cycle for BTC-USD ---")
        mock_logger.info.assert_any_call("--- Completed trade cycle for BTC-USD ---")
        mock_logger.info.assert_any_call("--- Starting trade cycle for ETH-USD ---")
        mock_logger.info.assert_any_call("--- Completed trade cycle for ETH-USD ---")

        # Final log message
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
        # --- Setup Mocks ---
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure the mock to raise a critical error
        error_message = "Invalid API keys"
        mock_client_class.side_effect = RuntimeError(error_message)

        # --- Run the function ---
        main.run_bot()

        # --- Assertions ---
        # Verify critical error logging and system exit
        mock_logger.critical.assert_called_once_with(
            f"A critical error occurred during bot initialization: {error_message}",
            exc_info=True,
        )
        mock_exit.assert_called_once_with(1)

    @patch("main.config")
    @patch("main.get_logger")
    @patch("main.coinbase_client.CoinbaseClient")
    @patch("main.trading_logic.process_asset_trade_cycle")
    def test_run_bot_asset_processing_error_continues(
        self, mock_process_cycle, mock_client_class, mock_get_logger, mock_config
    ):
        """Test that an error in one asset doesn't stop the next one."""
        # --- Setup Mocks ---
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        mock_config.TRADING_PAIRS = {"BTC-USD": {}, "ETH-USD": {}}

        # Configure process_asset_trade_cycle to fail for the first asset
        error_message = "Test processing error"
        mock_process_cycle.side_effect = [Exception(error_message), None]

        # --- Run the function ---
        main.run_bot()

        # --- Assertions ---
        # Verify that both assets were attempted
        self.assertEqual(mock_process_cycle.call_count, 2)

        # Verify the error was logged correctly for the failing asset
        mock_logger.error.assert_called_once_with(
            f"An unexpected error occurred while processing asset BTC-USD: {error_message}",
            exc_info=True,
        )

        # Verify the second asset was still processed
        mock_process_cycle.assert_any_call(
            asset_id="ETH-USD",
            client=mock_client_instance,
            persistence_manager=main.persistence,
            ta_module=main.technical_analysis,
            config_module=mock_config,
            logger=mock_logger,
        )

        # Verify the completion log was still called for both
        mock_logger.info.assert_any_call("--- Completed trade cycle for BTC-USD ---")
        mock_logger.info.assert_any_call("--- Completed trade cycle for ETH-USD ---")


if __name__ == "__main__":
    unittest.main()
