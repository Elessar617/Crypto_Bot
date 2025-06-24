"""
Unit tests for the trading_logic.py module using pytest.
"""

import pandas as pd
import pytest
from typing import List, Dict, Any, Optional
from decimal import Decimal

# Imports from the application source
from trading_logic import (
    should_buy_asset,
    determine_sell_orders_params,
)

# --- Helper Functions ---

def _create_rsi_series(rsi_values: Optional[List[float]]) -> Optional[pd.Series]:
    """Helper to create a pandas Series from a list of RSI values."""
    if rsi_values is None:
        return None
    return pd.Series(rsi_values, dtype=float)


# --- Tests for should_buy_asset ---

@pytest.mark.parametrize("rsi_values, config, expected", [
    # Condition Met
    ([20.0, 25.0, 28.0, 29.0, 35.0], {"rsi_oversold_threshold": 30}, True),
    # Current RSI not above threshold
    ([20.0, 25.0, 28.0, 29.0, 25.0], {"rsi_oversold_threshold": 30}, False),
    # Previous RSI not below or equal to threshold
    ([20.0, 25.0, 28.0, 31.0, 35.0], {"rsi_oversold_threshold": 30}, False),
    # No prior RSI below threshold
    ([32.0, 33.0, 34.0, 29.0, 35.0], {"rsi_oversold_threshold": 30}, False),
    # Exact threshold crossing
    ([20.0, 25.0, 28.0, 30.0, 35.0], {"rsi_oversold_threshold": 30}, True),
    # One of three priors just below threshold (pass case)
    ([31.0, 32.0, 29.0, 28.0, 35.0], {"rsi_oversold_threshold": 30}, True),
    # All three priors below threshold (pass case)
    ([28.0, 27.0, 29.0, 25.0, 35.0], {"rsi_oversold_threshold": 30}, True),
])
def test_should_buy_asset(rsi_values, config, expected):
    """Tests various scenarios for should_buy_asset logic."""
    rsi_series = _create_rsi_series(rsi_values)
    assert should_buy_asset(rsi_series, config) == expected


@pytest.mark.parametrize("rsi_series, config, error_msg", [
    (None, {"rsi_oversold_threshold": 30}, "RSI series cannot be None."),
    (_create_rsi_series([1, 2, 3, 4]), {"rsi_oversold_threshold": 30}, "RSI series must have at least 5 data points"),
    (_create_rsi_series([1, 2, 3, 4, 5]), {}, "'rsi_oversold_threshold' missing from config_asset_params."),
    (_create_rsi_series([1, 2, 3, 4, 5]), {"rsi_oversold_threshold": "30"}, "'rsi_oversold_threshold' must be a number."),
    (_create_rsi_series([1, 2, 3, 4, 5]), {"rsi_oversold_threshold": 101}, "'rsi_oversold_threshold' must be between 0 and 100."),
    (_create_rsi_series([1, 2, 3, 4, 5]), {"rsi_oversold_threshold": 0}, "'rsi_oversold_threshold' must be between 0 and 100."),
])
def test_should_buy_asset_assertions(rsi_series, config, error_msg):
    """Tests assertion errors for should_buy_asset."""
    with pytest.raises(AssertionError, match=error_msg):
        should_buy_asset(rsi_series, config)


# --- Tests for determine_sell_orders_params ---

def test_determine_sell_orders_params_valid_tiers(valid_product_details):
    """Test with valid inputs and multiple profit tiers."""
    buy_price = 100.0
    buy_quantity = 10.0
    config = {
        "sell_profit_tiers": [
            {"percentage": 10.0, "quantity_percentage": 30.0},
            {"percentage": 20.0, "quantity_percentage": 50.0},
            {"percentage": 30.0, "quantity_percentage": 20.0},
        ]
    }

    result = determine_sell_orders_params(buy_price, buy_quantity, valid_product_details, config)

    assert len(result) == 3
    assert result[0] == {"price": 110.00, "quantity": 3.0}
    assert result[1] == {"price": 120.00, "quantity": 5.0}
    assert result[2] == {"price": 130.00, "quantity": 2.0}

def test_determine_sell_orders_params_quantity_adjustment(valid_product_details, sample_trading_pair_config):
    """Test correct quantity adjustment based on base_increment."""
    result = determine_sell_orders_params(2000.0, 0.12345678, valid_product_details, sample_trading_pair_config)
    # Expected: 0.12345678 * 50% = 0.06172839 -> rounded down to 0.00001 increment -> 0.06172
    assert result[0]["quantity"] == 0.06172

def test_determine_sell_orders_params_price_adjustment(valid_product_details, sample_trading_pair_config):
    """Test correct price adjustment based on quote_increment."""
    result = determine_sell_orders_params(123.456, 10.0, valid_product_details, sample_trading_pair_config)
    # Expected price: 123.456 * 1.02 = 125.92512 -> rounded down to 0.01 increment -> 125.92
    assert result[0]["price"] == 125.92

def test_determine_sell_orders_params_tier_below_min_size(valid_product_details):
    """Test that a tier resulting in quantity below base_min_size is omitted."""
    config = {
        "sell_profit_tiers": [
            {"percentage": 10.0, "quantity_percentage": 40.0},  # 0.0008 -> too small
            {"percentage": 20.0, "quantity_percentage": 60.0}, # 0.0012 -> ok
        ]
    }
    product_details = valid_product_details.copy()
    product_details["base_min_size"] = "0.001"

    result = determine_sell_orders_params(100.0, 0.002, product_details, config)

    assert len(result) == 1
    assert result[0]["price"] == 120.00
    assert result[0]["quantity"] == 0.0012

@pytest.mark.parametrize("details_key, error_msg", [
    ("base_increment", "'base_increment' missing from product_details."),
    ("quote_increment", "'quote_increment' missing from product_details."),
    ("base_min_size", "'base_min_size' missing from product_details."),
])
def test_determine_sell_orders_params_missing_product_details(
    details_key, error_msg, valid_product_details, sample_trading_pair_config
):
    """Test assertion errors for missing keys in product_details."""
    del valid_product_details[details_key]
    with pytest.raises(AssertionError, match=error_msg):
        determine_sell_orders_params(100.0, 10.0, valid_product_details, sample_trading_pair_config)

@pytest.mark.parametrize("buy_price, buy_quantity, config, error_msg", [
    (0, 10, {}, "buy_price must be a positive number."),
    (100, 0, {}, "buy_quantity must be a positive number."),
    (100, 10, {"sell_profit_tiers": "not_a_list"}, "'sell_profit_tiers' must be a list."),
    (100, 10, {"sell_profit_tiers": [123]}, "Each tier in 'sell_profit_tiers' must be a dictionary."),
])
def test_determine_sell_orders_params_assertions(
    buy_price, buy_quantity, config, error_msg, valid_product_details
):
    """Test various input assertion errors."""
    with pytest.raises(AssertionError, match=error_msg):
        determine_sell_orders_params(buy_price, buy_quantity, valid_product_details, config)
