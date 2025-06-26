from __future__ import annotations

"""Module for analyzing market data to generate trading signals."""

from typing import Any, Dict, Optional
import logging
import pandas as pd
from pandas.api.types import is_numeric_dtype


def should_buy_asset(
    rsi_series: Optional[pd.Series],
    config_asset_params: Dict[str, Any],
    logger: logging.Logger,
) -> bool:
    """
    Determines if an asset should be bought based on its RSI crossing an
    oversold threshold.

    This function implements the primary buy signal logic: it checks if the most
    recent RSI value has crossed up and over a defined oversold threshold from
    the previous RSI value.

    Args:
        rsi_series: A pandas Series containing the two most recent RSI values.
        config_asset_params: A dictionary containing asset-specific configuration,
                             including the 'rsi_oversold_threshold'.
        logger: A configured logger instance for logging events.

    Returns:
        True if the buy condition is met, False otherwise.

    Assertions:
        - rsi_series is not None and contains at least two numeric values.
        - config_asset_params contains a valid 'rsi_oversold_threshold'.
    """
    # Dual validation: Assertions for developers, explicit checks for runtime
    # robustness.
    assert rsi_series is not None, "RSI series cannot be None."
    assert len(rsi_series) >= 2, "RSI series must have at least 2 data points."
    assert "rsi_oversold_threshold" in config_asset_params, "RSI threshold missing."
    assert (
        0 < config_asset_params["rsi_oversold_threshold"] < 100
    ), "RSI threshold must be between 0 and 100."
    assert logger is not None, "Logger cannot be None."

    # Explicit runtime checks
    if rsi_series is None or len(rsi_series) < 2:
        logger.warning("RSI series is None or too short to analyze.")
        return False

    if not is_numeric_dtype(rsi_series):
        logger.error("RSI values are not valid numbers.")
        return False

    current_rsi = rsi_series.iloc[-1]
    previous_rsi = rsi_series.iloc[-2]
    rsi_threshold = config_asset_params["rsi_oversold_threshold"]

    # The core buy condition: RSI must cross UP through the oversold threshold.
    if previous_rsi < rsi_threshold < current_rsi:
        logger.info(
            f"Buy signal detected: RSI crossed up from {previous_rsi:.2f} "
            f"to {current_rsi:.2f} (Threshold: {rsi_threshold})."
        )
        return True

    return False
