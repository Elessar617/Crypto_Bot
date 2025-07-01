"""
Unit tests for the technical_analysis.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import ta  # type: ignore

from trading.technical_analysis import (
    calculate_rsi,
    calculate_sma,
)


class TestTechnicalAnalysis(unittest.TestCase):
    """
    Test suite for technical analysis functions.
    """

    get_logger_patcher: unittest.mock._patch

    @classmethod
    def setUpClass(cls) -> None:
        """Set up class-level resources, primarily mocks."""
        cls.get_logger_patcher = patch("trading.technical_analysis.get_logger")

    def setUp(self) -> None:
        """Reset mocks before each test and start the logger patcher."""
        mock_get_logger = self.get_logger_patcher.start()
        self.mock_logger_instance = MagicMock()
        mock_get_logger.return_value = self.mock_logger_instance
        self.addCleanup(self.get_logger_patcher.stop)

    # --- Test cases for calculate_rsi ---

    def test_calculate_rsi_valid_data(self) -> None:
        """Test RSI calculation with a typical valid dataset."""
        close_prices = [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
            46.00,
            46.03,
            46.41,
            46.22,
            45.64,
            46.21,
            46.25,
            45.71,
            46.34,
            46.00,
            46.00,
            45.69,
            45.28,
            45.09,
            45.38,
        ]
        period = 14
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        expected_rsi_series = ta.momentum.RSIIndicator(
            close=candles_df["close"], window=period
        ).rsi()
        result_rsi_series = calculate_rsi(candles_df, period=period)
        self.assertIsNotNone(
            result_rsi_series, "RSI series should not be None for valid data."
        )
        if result_rsi_series is not None:
            self.assertIsInstance(
                result_rsi_series, pd.Series, "Result should be a pandas Series."
            )
            pd.testing.assert_series_equal(
                result_rsi_series, expected_rsi_series, check_dtype=False, rtol=1e-4
            )
            self.mock_logger_instance.debug.assert_called()
            self.mock_logger_instance.info.assert_called_with(
                f"Successfully calculated RSI series with {len(result_rsi_series.dropna())} non-NaN values."
            )
        else:
            self.fail("result_rsi_series should not be None for valid data.")

    def test_calculate_rsi_uses_default_period(self) -> None:
        """Test RSI calculation uses the default period of 14."""
        close_prices = [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
            46.00,
            46.03,
            46.41,
            46.22,
            45.64,
            46.21,
            46.25,
            45.71,
            46.34,
            46.00,
            46.00,
            45.69,
            45.28,
            45.09,
            45.38,
        ]
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        # Calculate expected RSI with the default period of 14
        expected_rsi_series = ta.momentum.RSIIndicator(
            close=candles_df["close"], window=14
        ).rsi()
        # Call calculate_rsi without the period argument
        result_rsi_series = calculate_rsi(candles_df)
        self.assertIsNotNone(result_rsi_series)
        if result_rsi_series is not None:
            pd.testing.assert_series_equal(
                result_rsi_series, expected_rsi_series, check_dtype=False, rtol=1e-4
            )

    def test_calculate_rsi_empty_dataframe(self) -> None:
        """Test RSI calculation with an empty DataFrame."""
        candles_df = pd.DataFrame(columns=["close"])
        result = calculate_rsi(candles_df, period=14)
        self.assertIsNone(result, "RSI should be None for an empty DataFrame.")
        self.mock_logger_instance.warning.assert_called_with(
            "Cannot calculate RSI: candles_df is empty."
        )

    def test_calculate_rsi_insufficient_data(self) -> None:
        """Test RSI calculation when there's not enough data for the period."""
        close_prices = [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
        ]
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        period = 14
        result = calculate_rsi(candles_df, period=period)
        self.assertIsNone(result, "RSI should be None for insufficient data.")
        self.mock_logger_instance.warning.assert_called_with(
            f"Cannot calculate RSI: Insufficient data. Need at least {period} non-NaN close prices, found {len(close_prices)}."
        )

    def test_calculate_rsi_missing_close_column(self) -> None:
        """Test RSI calculation when the 'close' column is missing."""
        candles_df = pd.DataFrame({"open": [10, 11], "high": [12, 13]})
        result = calculate_rsi(candles_df, period=14)
        self.assertIsNone(result, "RSI should be None if 'close' column is missing.")
        self.mock_logger_instance.warning.assert_called_with(
            "Cannot calculate RSI: 'close' column missing."
        )

    def test_calculate_rsi_non_numeric_close_column(self) -> None:
        """Test RSI calculation when the 'close' column is not numeric."""
        candles_df = pd.DataFrame({"close": ["a", "b", "c"] * 5})
        result = calculate_rsi(candles_df, period=14)
        self.assertIsNone(
            result, "RSI should be None if 'close' column is not numeric."
        )
        self.mock_logger_instance.warning.assert_called_with(
            "Cannot calculate RSI: 'close' column is not numeric."
        )
        self.mock_logger_instance.error.assert_not_called()

    def test_calculate_rsi_all_nan_close(self) -> None:
        """Test RSI with 'close' column containing all NaNs."""
        num_rows = 20
        period = 14
        candles_df = pd.DataFrame({"close": [np.nan] * num_rows})
        result = calculate_rsi(candles_df, period=period)
        self.assertIsNone(result, "RSI should be None if all 'close' values are NaN.")
        self.mock_logger_instance.warning.assert_called_with(
            f"Cannot calculate RSI: Insufficient data. Need at least {period} non-NaN close prices, found 0."
        )

    def test_calculate_rsi_contains_some_nan_close(self) -> None:
        """Test RSI with 'close' column containing some NaNs but enough valid data."""
        close_prices_with_nans = [
            44.34,
            np.nan,
            44.09,
            44.15,
            np.nan,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            np.nan,
            46.08,
            45.89,
            46.03,
            45.61,
            np.nan,
            46.28,
            46.28,
            46.00,
        ]
        period = 14
        candles_df = pd.DataFrame(
            {"close": pd.Series(close_prices_with_nans, dtype=float)}
        )
        expected_rsi_series = ta.momentum.RSIIndicator(
            close=candles_df["close"], window=period
        ).rsi()
        result_rsi_series = calculate_rsi(candles_df, period=period)
        self.assertIsNotNone(
            result_rsi_series,
            "RSI series should not be None when enough valid data despite NaNs.",
        )
        if result_rsi_series is not None:
            self.assertIsInstance(
                result_rsi_series, pd.Series, "Result should be a pandas Series."
            )
            pd.testing.assert_series_equal(
                result_rsi_series, expected_rsi_series, check_dtype=False, rtol=1e-4
            )
            self.mock_logger_instance.debug.assert_called()
            non_nan_rsi_count = len(result_rsi_series.dropna())
            self.mock_logger_instance.info.assert_called_with(
                f"Successfully calculated RSI series with {non_nan_rsi_count} non-NaN values."
            )
        else:
            self.fail(
                "result_rsi_series should not be None when enough valid data despite NaNs."
            )

    def test_calculate_rsi_exact_data_points_for_period(self) -> None:
        """Test RSI with exactly 'period' number of data points."""
        close_prices = [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
        ]
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        period = 14
        expected_rsi_series = ta.momentum.RSIIndicator(
            close=candles_df["close"], window=period
        ).rsi()
        result_rsi_series = calculate_rsi(candles_df, period=period)
        self.assertIsNotNone(result_rsi_series, "RSI series should not be None.")
        if result_rsi_series is not None:
            self.assertIsInstance(
                result_rsi_series, pd.Series, "Result should be a pandas Series."
            )
            pd.testing.assert_series_equal(
                result_rsi_series, expected_rsi_series, check_dtype=False, rtol=1e-4
            )
            self.mock_logger_instance.debug.assert_called()
            self.mock_logger_instance.info.assert_called_with(
                f"Successfully calculated RSI series with {len(result_rsi_series.dropna())} non-NaN values."
            )
        else:
            self.fail("result_rsi_series should not be None.")

    @patch("trading.technical_analysis.ta.momentum.RSIIndicator")
    def test_calculate_rsi_generic_exception(
        self, MockRSIIndicatorClass: MagicMock
    ) -> None:
        """Test RSI calculation handles generic exceptions from ta library."""
        mock_rsi_instance = MagicMock()
        mock_rsi_instance.rsi.side_effect = Exception("TA Library Method Error")
        MockRSIIndicatorClass.return_value = mock_rsi_instance
        close_prices_series = pd.Series([1.0] * 20, dtype=float)
        candles_df = pd.DataFrame({"close": close_prices_series})
        period = 14
        result = calculate_rsi(candles_df, period=period)
        self.assertIsNone(result, "RSI should be None on generic exception.")
        MockRSIIndicatorClass.assert_called_once()
        called_kwargs = MockRSIIndicatorClass.call_args.kwargs
        pd.testing.assert_series_equal(
            called_kwargs["close"], close_prices_series, check_names=False
        )
        self.assertEqual(called_kwargs["window"], period)
        mock_rsi_instance.rsi.assert_called_once()
        self.mock_logger_instance.error.assert_called_once()
        args, kwargs_log = self.mock_logger_instance.error.call_args
        self.assertEqual(args[0], "Error calculating RSI: TA Library Method Error")
        self.assertTrue(kwargs_log.get("exc_info"))

    # --- Test cases for calculate_sma ---

    def test_calculate_sma_valid_data(self) -> None:
        """Test SMA calculation with a typical valid dataset."""
        close_prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        period = 3
        expected_sma_series = ta.trend.SMAIndicator(
            close=candles_df["close"], window=period
        ).sma_indicator()

        result_sma_series = calculate_sma(candles_df, period=period)

        self.assertIsNotNone(result_sma_series, "SMA series should not be None.")
        self.assertIsInstance(
            result_sma_series, pd.Series, "Result should be a pandas Series."
        )

        if result_sma_series is not None:
            pd.testing.assert_series_equal(
                result_sma_series, expected_sma_series, check_dtype=False, rtol=1e-4
            )
            self.mock_logger_instance.debug.assert_called()
            self.mock_logger_instance.info.assert_called_with(
                f"Successfully calculated SMA series with {len(result_sma_series.dropna())} non-NaN values."
            )
        else:
            self.fail("result_sma_series became None after assertIsNotNone check.")

    def test_calculate_sma_empty_dataframe(self) -> None:
        """Test SMA calculation with an empty DataFrame."""
        candles_df = pd.DataFrame(columns=["close"], dtype=float)
        result_sma_series = calculate_sma(candles_df, period=5)
        self.assertIsNone(
            result_sma_series, "SMA should be None for an empty DataFrame."
        )
        self.mock_logger_instance.warning.assert_called_with(
            "Cannot calculate SMA: candles_df is empty."
        )

    def test_calculate_sma_insufficient_data(self) -> None:
        """Test SMA calculation when there's not enough data for the period."""
        close_prices = [10, 11, 12]  # 3 data points
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        period = 5  # Need 5 data points
        result_sma_series = calculate_sma(candles_df, period=period)
        self.assertIsNone(
            result_sma_series, "SMA should be None for insufficient data."
        )
        self.mock_logger_instance.warning.assert_called_with(
            f"Cannot calculate SMA: Insufficient data. Need at least {period} non-NaN close prices, found {len(close_prices)}."
        )

    def test_calculate_sma_missing_close_column(self) -> None:
        """Test SMA calculation when the 'close' column is missing."""
        candles_df = pd.DataFrame({"open": [10, 11], "high": [12, 13]})
        result_sma_series = calculate_sma(candles_df, period=2)
        self.assertIsNone(
            result_sma_series, "SMA should be None if 'close' column is missing."
        )
        self.mock_logger_instance.warning.assert_called_with(
            "Cannot calculate SMA: 'close' column missing."
        )

    def test_calculate_sma_non_numeric_close_column(self) -> None:
        """Test SMA calculation when the 'close' column is not numeric."""
        candles_df = pd.DataFrame({"close": ["a", "b", "c"]})
        result_sma_series = calculate_sma(candles_df, period=2)
        self.assertIsNone(
            result_sma_series, "SMA should be None if 'close' column is not numeric."
        )
        self.mock_logger_instance.warning.assert_called_with(
            "Cannot calculate SMA: 'close' column is not numeric."
        )
        self.mock_logger_instance.error.assert_not_called()

    def test_calculate_sma_all_nan_close(self) -> None:
        """Test SMA with 'close' column containing all NaNs."""
        close_prices = [np.nan, np.nan, np.nan, np.nan, np.nan]
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        period = 3
        result_sma_series = calculate_sma(candles_df, period=period)
        self.assertIsNone(
            result_sma_series,
            "SMA should be None if all close prices are NaN due to insufficient non-NaN data.",
        )
        self.mock_logger_instance.warning.assert_called_with(
            f"Cannot calculate SMA: Insufficient data. Need at least {period} non-NaN close prices, found 0."
        )

    def test_calculate_sma_contains_some_nan_close(self) -> None:
        """Test SMA with 'close' column containing some NaNs but enough valid data."""
        close_prices = [10, 11, np.nan, 13, 14, 15, np.nan, 17, 18]
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        period = 3
        expected_sma_series = ta.trend.SMAIndicator(
            close=candles_df["close"], window=period
        ).sma_indicator()
        result_sma_series = calculate_sma(candles_df, period=period)
        self.assertIsNotNone(result_sma_series, "SMA series should not be None.")
        self.assertIsInstance(
            result_sma_series, pd.Series, "Result should be a pandas Series."
        )
        if result_sma_series is not None:
            pd.testing.assert_series_equal(
                result_sma_series, expected_sma_series, check_dtype=False, rtol=1e-4
            )
            self.mock_logger_instance.debug.assert_called()
            self.mock_logger_instance.info.assert_called_with(
                f"Successfully calculated SMA series with {len(result_sma_series.dropna())} non-NaN values."
            )
        else:
            self.fail("result_sma_series became None after assertIsNotNone check.")

    def test_calculate_sma_exact_data_points_for_period(self) -> None:
        """Test SMA with exactly 'period' number of data points."""
        close_prices = [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
            46.00,
            46.03,
            46.41,
            46.22,
            45.64,
        ]
        period = 20
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        expected_sma_series = ta.trend.SMAIndicator(
            close=candles_df["close"], window=period
        ).sma_indicator()
        result_sma_series = calculate_sma(candles_df, period=period)
        self.assertIsNotNone(result_sma_series, "SMA series should not be None.")
        if result_sma_series is not None:
            self.assertIsInstance(
                result_sma_series, pd.Series, "Result should be a pandas Series."
            )
            pd.testing.assert_series_equal(
                result_sma_series, expected_sma_series, check_dtype=False, rtol=1e-4
            )
            self.mock_logger_instance.info.assert_called_with(
                f"Successfully calculated SMA series with {len(result_sma_series.dropna())} non-NaN values."
            )
        else:
            self.fail("result_sma_series became None after assertIsNotNone check.")

    def test_calculate_sma_uses_default_period(self) -> None:
        """Test SMA calculation uses the default period of 20."""
        close_prices = [
            44.34,
            44.09,
            44.15,
            43.61,
            44.33,
            44.83,
            45.10,
            45.42,
            45.84,
            46.08,
            45.89,
            46.03,
            45.61,
            46.28,
            46.28,
            46.00,
            46.03,
            46.41,
            46.22,
            45.64,
            46.21,
            46.25,
            45.71,
            46.34,
            46.00,
            46.00,
            45.69,
            45.28,
            45.09,
            45.38,
        ]
        candles_df = pd.DataFrame({"close": pd.Series(close_prices, dtype=float)})
        # Calculate expected SMA with the default period of 20
        expected_sma_series = ta.trend.SMAIndicator(
            close=candles_df["close"], window=20
        ).sma_indicator()
        # Call calculate_sma without the period argument
        result_sma_series = calculate_sma(candles_df)
        self.assertIsNotNone(result_sma_series)
        if result_sma_series is not None:
            pd.testing.assert_series_equal(
                result_sma_series, expected_sma_series, check_dtype=False, rtol=1e-4
            )

    @patch("trading.technical_analysis.ta.trend.SMAIndicator")
    def test_calculate_sma_generic_exception(
        self, MockSMAIndicatorClass: MagicMock
    ) -> None:
        """Test SMA calculation handles generic exceptions from ta library."""
        mock_sma_instance = MagicMock()
        mock_sma_instance.sma_indicator.side_effect = Exception(
            "TA Library Method Error"
        )
        MockSMAIndicatorClass.return_value = mock_sma_instance
        close_prices_series = pd.Series([1.0] * 20, dtype=float)
        candles_df = pd.DataFrame({"close": close_prices_series})
        period = 14
        result = calculate_sma(candles_df, period=period)
        self.assertIsNone(result, "SMA should be None on generic exception.")
        MockSMAIndicatorClass.assert_called_once()
        called_kwargs = MockSMAIndicatorClass.call_args.kwargs
        pd.testing.assert_series_equal(
            called_kwargs["close"], close_prices_series, check_names=False
        )
        self.assertEqual(called_kwargs["window"], period)
        mock_sma_instance.sma_indicator.assert_called_once()
        self.mock_logger_instance.error.assert_called_once()
        args, kwargs_log = self.mock_logger_instance.error.call_args
        self.assertEqual(args[0], "Error calculating SMA: TA Library Method Error")
        self.assertTrue(kwargs_log.get("exc_info"))

    def test_calculate_rsi_with_zero_period(self) -> None:
        """Test RSI calculation raises AssertionError for a period of 0."""
        candles_df = pd.DataFrame({"close": [1, 2, 3, 4, 5]})
        with self.assertRaises(AssertionError) as cm:
            calculate_rsi(candles_df, period=0)
        self.assertEqual(str(cm.exception), "period must be a positive integer.")

    def test_calculate_sma_with_zero_period(self) -> None:
        """Test SMA calculation raises AssertionError for a period of 0."""
        candles_df = pd.DataFrame({"close": [1, 2, 3, 4, 5]})
        with self.assertRaises(AssertionError) as cm:
            calculate_sma(candles_df, period=0)
        self.assertEqual(str(cm.exception), "period must be a positive integer.")

    def test_calculate_rsi_with_period_of_one(self) -> None:
        """Test RSI calculation with a period of 1."""
        candles_df = pd.DataFrame({"close": [10, 11, 12, 13, 14]})
        result = calculate_rsi(candles_df, period=1)
        self.assertIsNotNone(result, "RSI should not be None for period=1.")
        if result is not None:
            # For period=1, RSI is 100 for price increases, 0 for decreases.
            # The 'ta' library implementation returns 100.0 for the first element.
            expected = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0], name="close")
            pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_calculate_sma_with_period_of_one(self) -> None:
        """Test SMA calculation with a period of 1."""
        candles_df = pd.DataFrame({"close": [10, 11, 12, 13, 14]})
        result = calculate_sma(candles_df, period=1)
        self.assertIsNotNone(result, "SMA should not be None for period=1.")
        if result is not None:
            # For period=1, SMA is the series itself.
            expected = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0], name="close")
            pd.testing.assert_series_equal(result, expected, check_names=False)


if __name__ == "__main__":
    unittest.main()
