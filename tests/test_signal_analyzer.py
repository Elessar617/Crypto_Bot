"""Unit tests for the trading.signal_analyzer module."""

import logging

import unittest
from unittest.mock import MagicMock

import pandas as pd

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

    def test_should_buy_asset_false_when_current_rsi_equals_threshold(self):
        """Test returns False when the current RSI equals the threshold."""
        rsi_series = pd.Series([25, 30])  # Current RSI equals threshold
        self.assertFalse(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
        )

    def test_should_buy_asset_false_when_previous_rsi_equals_threshold(self):
        """Test returns False when the previous RSI equals the threshold."""
        rsi_series = pd.Series([30, 35])  # Previous RSI equals threshold
        self.assertFalse(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
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

        with self.assertRaises(AssertionError):
            should_buy_asset(
                pd.Series([10, 20]), {"rsi_oversold_threshold": 0}, self.mock_logger
            )

        with self.assertRaises(AssertionError):
            should_buy_asset(
                pd.Series([10, 20]), {"rsi_oversold_threshold": 100}, self.mock_logger
            )

    def test_threshold_at_lower_boundary_is_valid(self):
        """Test does not raise an error for a valid threshold at the lower boundary."""
        # This test kills a mutant changing `0 < threshold` to `1 < threshold`.
        # The original code accepts threshold=1, but the mutant would reject it.
        rsi_series = pd.Series([10, 20])  # Does not trigger a buy signal
        config_params = {"rsi_oversold_threshold": 1}
        try:
            should_buy_asset(rsi_series, config_params, self.mock_logger)
        except AssertionError:
            self.fail(
                "should_buy_asset() raised AssertionError for a valid threshold of 1."
            )

    def test_should_buy_asset_true_with_longer_rsi_series(self):
        """Test returns True for a buy signal with more than two RSI values."""
        # This test ensures that the logic correctly uses the last two points
        # of a longer series, killing a mutant that changes iloc[-1] to iloc[1].
        rsi_series = pd.Series([20, 25, 35])  # Previous below, current above
        self.assertTrue(
            should_buy_asset(rsi_series, self.config_params, self.mock_logger)
        )
        self.mock_logger.info.assert_called_once()

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
