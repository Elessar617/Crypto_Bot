"""
Handles technical analysis calculations, primarily RSI.
"""

from typing import Optional

import pandas as pd  # type: ignore[import]
import ta  # type: ignore[import] # ta library might not have type stubs

from trading.logger import (
    get_logger,
)  # Assuming logger.py is in the same directory or PYTHONPATH


def _validate_candles_df(candles_df: pd.DataFrame, indicator_name: str) -> bool:
    """
    Validates the input DataFrame for technical analysis calculations.

    Args:
        candles_df: The DataFrame to validate.
        indicator_name: The name of the indicator being calculated (for logging).

    Returns:
        True if the DataFrame is valid, False otherwise.
    """
    logger = get_logger()
    if not isinstance(candles_df, pd.DataFrame):
        logger.warning(f"Input for {indicator_name} is not a DataFrame.")
        return False

    if candles_df.empty:
        logger.warning(f"Cannot calculate {indicator_name}: candles_df is empty.")
        return False

    if "close" not in candles_df.columns:
        logger.warning(f"Cannot calculate {indicator_name}: 'close' column missing.")
        return False

    if not pd.api.types.is_numeric_dtype(candles_df["close"]):
        logger.warning(
            f"Cannot calculate {indicator_name}: 'close' column is not numeric."
        )
        return False

    return True


def calculate_rsi(candles_df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]:
    """
    Calculates the Relative Strength Index (RSI) for a given DataFrame of candles.

    Args:
        candles_df: Pandas DataFrame containing candle data.
                    Must include a 'close' column with numeric closing prices.
                    The DataFrame should be sorted by time, oldest to newest.
        period: The period to use for RSI calculation (default is 14).

    Returns:
        A pandas Series containing the RSI values, or None if calculation fails
        (e.g., insufficient data, missing 'close' column).
    """
    logger = get_logger()
    # Rule: Use a minimum of two runtime assertions per function.
    assert isinstance(
        candles_df, pd.DataFrame
    ), "candles_df must be a pandas DataFrame."
    assert isinstance(period, int) and period > 0, "period must be a positive integer."

    logger.debug(
        f"Attempting to calculate RSI with period {period} on DataFrame with {len(candles_df)} rows."
    )

    if not _validate_candles_df(candles_df, "RSI"):
        return None

    # Ensure there are enough data points for the RSI calculation
    # The ta library needs at least 'period' data points to start calculating RSI.
    # To get a non-NaN value, it typically needs more, often period + lookback for smoothing.
    # A common rule of thumb is at least 2 * period for a stable first RSI value.
    if len(candles_df["close"].dropna()) < period:
        logger.warning(
            f"Cannot calculate RSI: Insufficient data. Need at least {period} non-NaN close prices, found {len(candles_df['close'].dropna())}."
        )
        return None

    try:
        # Initialize RSIIndicator
        rsi_indicator = ta.momentum.RSIIndicator(
            close=candles_df["close"], window=period
        )

        # Calculate RSI
        rsi_series = rsi_indicator.rsi()

        if (
            rsi_series is None
        ):  # Should not happen if previous checks are fine, but good to be safe
            logger.error("RSI calculation returned None unexpectedly.")
            return None

        # Rule: Check the return value of all non-void functions. (Handled by caller)
        # Rule: Restrict functions to a single printed page. (This function is concise)
        # Rule: Restrict the scope of data to the smallest possible. (Scope is local)

        logger.info(
            f"Successfully calculated RSI series with {len(rsi_series.dropna())} non-NaN values."
        )
        return rsi_series

    except Exception as e:
        logger.error(f"Error calculating RSI: {e}", exc_info=True)
        return None


def calculate_sma(candles_df: pd.DataFrame, period: int = 20) -> Optional[pd.Series]:
    """
    Calculates the Simple Moving Average (SMA) for a given DataFrame of candles.

    Args:
        candles_df: Pandas DataFrame containing candle data.
                    Must include a 'close' column with numeric closing prices.
                    The DataFrame should be sorted by time, oldest to newest.
        period: The period to use for SMA calculation (default is 20).

    Returns:
        A pandas Series containing the SMA values, or None if calculation fails
        (e.g., insufficient data, missing 'close' column).
    """
    logger = get_logger()
    # Rule: Use a minimum of two runtime assertions per function.
    assert isinstance(
        candles_df, pd.DataFrame
    ), "candles_df must be a pandas DataFrame."
    assert isinstance(period, int) and period > 0, "period must be a positive integer."

    logger.debug(
        f"Attempting to calculate SMA with period {period} on DataFrame with {len(candles_df)} rows."
    )

    if not _validate_candles_df(candles_df, "SMA"):
        return None

    # Ensure there are enough data points for the SMA calculation
    # The ta library needs at least 'period' data points to calculate the first SMA value.
    if len(candles_df["close"].dropna()) < period:
        logger.warning(
            f"Cannot calculate SMA: Insufficient data. Need at least {period} non-NaN close prices, found {len(candles_df['close'].dropna())}."
        )
        return None

    try:
        # Initialize SMAIndicator
        sma_indicator = ta.trend.SMAIndicator(close=candles_df["close"], window=period)

        # Calculate SMA
        sma_series = sma_indicator.sma_indicator()

        if sma_series is None:  # Should not happen if previous checks are fine
            logger.error("SMA calculation returned None unexpectedly.")
            return None

        logger.info(
            f"Successfully calculated SMA series with {len(sma_series.dropna())} non-NaN values."
        )
        return sma_series

    except Exception as e:
        logger.error(f"Error calculating SMA: {e}", exc_info=True)
        return None
