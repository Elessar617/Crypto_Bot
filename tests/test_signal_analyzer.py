"""Unit tests for the trading.signal_analyzer module."""

import logging
import os
import sys
import unittest
from unittest.mock import MagicMock

import pandas as pd

# Ensure the project root is in the system path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.signal_analyzer import should_buy_asset  # noqa: E402


class TestSignalAnalyzer(unittest.TestCase):
    """Tests for the signal_analyzer module."""

    def setUp(self):
        """Set up a mock logger for each test."""
        self.mock_logger = MagicMock(spec=logging.Logger)
        self.config_params = {"rsi_oversold_threshold": 30}

    def test_should_buy_asset_true_when_rsi_crosses_up(self):
        """Test returns True when RSI crosses above the threshold."""
        rsi_series = pd.Series([25, 35])  # Previous below, current above
        self.assertTrue(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
        )
        self.mock_logger.info.assert_called_once()

    def test_should_buy_asset_false_when_rsi_below_threshold(self):
        """Test returns False when RSI stays below the threshold."""
        rsi_series = pd.Series([15, 25])
        self.assertFalse(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
        )

    def test_should_buy_asset_false_when_rsi_above_threshold(self):
        """Test returns False when RSI stays above the threshold."""
        rsi_series = pd.Series([35, 45])
        self.assertFalse(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
        )

    def test_should_buy_asset_false_when_rsi_crosses_down(self):
        """Test returns False when RSI crosses below the threshold."""
        rsi_series = pd.Series([35, 25])
        self.assertFalse(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
        )

    def test_should_buy_asset_false_on_rsi_equals_threshold(self):
        """Test returns False on edge cases where RSI equals the threshold."""
        rsi_series_1 = pd.Series([25, 30])  # Current equals threshold
        self.assertFalse(
            should_buy_asset(rsi_series_1, self.config_params, self.mock_logger)
        )
        rsi_series_2 = pd.Series([30, 35])  # Previous equals threshold
        self.assertFalse(
            should_buy_asset(rsi_series_2, self.config_params, self.mock_logger)
        )

    def test_input_validation_raises_assertion_error(self):
        """Test that invalid inputs raise AssertionErrors."""
        with self.assertRaises(AssertionError):
            should_buy_asset(None, self.config_params, self.mock_logger)

        with self.assertRaises(AssertionError):
            should_buy_asset(pd.Series([]), self.config_params, self.mock_logger)

        with self.assertRaises(AssertionError):
            should_buy_asset(pd.Series([10]), self.config_params, self.mock_logger)

        with self.assertRaises(AssertionError):
            should_buy_asset(pd.Series([10, 20]), {}, self.mock_logger)

        with self.assertRaises(AssertionError):
            should_buy_asset(
                pd.Series([10, 20]), {"rsi_oversold_threshold": 101}, self.mock_logger
            )

    def test_handles_non_numeric_rsi_values(self):
        """Test returns False for non-numeric RSI values."""
        rsi_series = pd.Series([25, "invalid"])
        self.assertFalse(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
        )
        self.mock_logger.error.assert_called_once_with(
            "RSI values are not valid numbers."
        )


if __name__ == "__main__":
    unittest.main()
