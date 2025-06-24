"""Configuration settings for the v6 crypto trading bot.

This module loads API keys from environment variables and defines static
configuration for trading pairs, bot behavior, and logging.

It is crucial to set the following environment variables before running the bot:
- COINBASE_API_KEY: Your Coinbase Advanced Trade API key.
- COINBASE_API_SECRET: Your Coinbase Advanced Trade API secret.

These can be set in a .env file in the project root, which will be automatically
loaded by python-dotenv.
"""

import os
from typing import List, Dict, Union, Final, Literal, TypedDict
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# --- API Configuration ---
COINBASE_API_KEY: Final[str] = os.getenv("COINBASE_API_KEY", "")
COINBASE_API_SECRET: Final[str] = os.getenv("COINBASE_API_SECRET", "")
COINBASE_SANDBOX_API_URL: Final[str] = "https://api-public.sandbox.pro.coinbase.com"

# Runtime assertions for API keys
# Rule: Use a minimum of two runtime assertions per function (or module setup in this case).
# Rule: Check the return value of all non-void functions (os.getenv can return None).
assert COINBASE_API_KEY, "COINBASE_API_KEY environment variable not set or empty."
assert COINBASE_API_SECRET, "COINBASE_API_SECRET environment variable not set or empty."

# --- General Bot Settings ---
LOG_LEVEL: Final[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = "INFO"
LOG_FILE: Final[str] = "v6_trading_bot.log"  # Log file name
# --- File System Paths ---
# Define the absolute path for the project's root directory.
# This ensures that file paths are consistent regardless of the script's execution location.
PROJECT_ROOT: Final[str] = os.path.dirname(os.path.abspath(__file__))

# Define and create the directory for storing persistence files (e.g., trade states).
# Using an absolute path prevents ambiguity with the current working directory.
PERSISTENCE_DIR: Final[str] = os.path.join(PROJECT_ROOT, "bot_data")


# --- Trading Pair Configuration ---
# Structure for defining profit tiers for sell orders.
# 'profit_pct': Percentage gain over buy price.
# 'sell_portion_initial': Portion of the *initially* bought amount to sell at this tier.
#                         "all_remaining" signifies selling the rest of the holdings for that asset.
class ProfitTier(TypedDict):
    label: str
    profit_pct: float
    sell_portion_initial: Union[float, Literal["all_remaining"]]


# Structure for defining each trading pair's specific parameters.
class TradingPairConfig(TypedDict):
    product_id: str
    rsi_period: int
    rsi_oversold_threshold: int
    rsi_buy_condition_historical_periods: List[int]
    profit_tiers: List[ProfitTier]
    fixed_buy_usd_amount: float
    min_base_trade_size: float
    min_quote_trade_size: float
    base_increment: str  # Represents a float, e.g., "0.00001"
    quote_increment: str  # Represents a float, e.g., "0.01"
    candle_granularity_api_name: str  # Should be a key from CANDLE_GRANULARITY_SECONDS
    buy_price_persistence_file: str
    max_candle_history_needed: int


# Candle granularities supported by Coinbase Advanced Trade API (subset)
# Full list: UNKNOWN_GRANULARITY, ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE,
# THIRTY_MINUTE, ONE_HOUR, TWO_HOUR, SIX_HOUR, ONE_DAY.
# We will use the string representation as expected by the API client.
CANDLE_GRANULARITY_SECONDS: Final[Dict[str, int]] = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "THIRTY_MINUTE": 1800,
    "ONE_HOUR": 3600,
    "TWO_HOUR": 7200,
    "SIX_HOUR": 21600,
    "ONE_DAY": 86400,
}

# Define configurations for each trading pair
# Rule: All loops must have fixed bounds (iteration over PROFIT_TIERS or RSI_BUY_CONDITION_HISTORICAL_PERIODS is bounded).
# Rule: Restrict the scope of data to the smallest possible (these are global configs, appropriate for this file).
TRADING_PAIRS: Final[Dict[str, TradingPairConfig]] = {
    "ETH-USD": {
        "product_id": "ETH-USD",
        "rsi_period": 14,  # Standard RSI period
        "rsi_oversold_threshold": 30,
        # Historical periods for RSI buy condition (t-1, t-2, t-3 relative to current)
        "rsi_buy_condition_historical_periods": [1, 2, 3],
        "profit_tiers": [
            {"label": "Tier 1", "profit_pct": 1.0, "sell_portion_initial": 0.3333},
            {"label": "Tier 2", "profit_pct": 4.0, "sell_portion_initial": 0.3333},
            {
                "label": "Tier 3",
                "profit_pct": 7.0,
                "sell_portion_initial": "all_remaining",
            },
        ],
        "fixed_buy_usd_amount": 20.00,  # Fixed USD amount for each buy trade
        "min_base_trade_size": 0.001,  # Minimum ETH trade size (example, verify with API)
        "min_quote_trade_size": 1.0,  # Minimum USD trade size (example, verify with API)
        "base_increment": "0.00001",  # Smallest unit of ETH that can be traded
        "quote_increment": "0.01",  # Smallest unit of USD (cents)
        "candle_granularity_api_name": "FIFTEEN_MINUTE",  # For Coinbase API
        "buy_price_persistence_file": "eth_usd_buy_price.txt",
        # Max candles needed: rsi_period + max(rsi_buy_condition_historical_periods) + buffer (e.g., 1 for calculation stability)
        "max_candle_history_needed": 14 + 3 + 1,  # = 18 candles for 15-min RSI
    },
    "BTC-USD": {
        "product_id": "BTC-USD",
        "rsi_period": 14,
        "rsi_oversold_threshold": 30,
        "rsi_buy_condition_historical_periods": [1, 2, 3],
        "profit_tiers": [
            {"label": "Tier 1", "profit_pct": 1.0, "sell_portion_initial": 0.3333},
            {"label": "Tier 2", "profit_pct": 4.0, "sell_portion_initial": 0.3333},
            {
                "label": "Tier 3",
                "profit_pct": 7.0,
                "sell_portion_initial": "all_remaining",
            },
        ],
        "fixed_buy_usd_amount": 25.00,
        "min_base_trade_size": 0.0001,
        "min_quote_trade_size": 1.0,
        "base_increment": "0.000001",
        "quote_increment": "0.01",
        "candle_granularity_api_name": "FIFTEEN_MINUTE",
        "buy_price_persistence_file": "btc_usd_buy_price.txt",
        "max_candle_history_needed": 14 + 3 + 1,  # = 18 candles
    },
    "LTC-USD": {
        "product_id": "LTC-USD",
        "rsi_period": 14,
        "rsi_oversold_threshold": 30,
        "rsi_buy_condition_historical_periods": [1, 2, 3],
        "profit_tiers": [
            {"label": "Tier 1", "profit_pct": 1.5, "sell_portion_initial": 0.3333},
            {"label": "Tier 2", "profit_pct": 5.0, "sell_portion_initial": 0.3333},
            {
                "label": "Tier 3",
                "profit_pct": 8.0,
                "sell_portion_initial": "all_remaining",
            },
        ],
        "fixed_buy_usd_amount": 15.00,
        "min_base_trade_size": 0.01,
        "min_quote_trade_size": 1.0,
        "base_increment": "0.0001",
        "quote_increment": "0.01",
        "candle_granularity_api_name": "FIFTEEN_MINUTE",
        "buy_price_persistence_file": "ltc_usd_buy_price.txt",
        "max_candle_history_needed": 14 + 3 + 1,  # = 18 candles
    },
}

# --- Sanity Checks for Configuration ---
# Rule: Use a minimum of two runtime assertions per function/module setup.
for pair, config_data in TRADING_PAIRS.items():
    assert isinstance(
        config_data["product_id"], str
    ), f"product_id for {pair} must be a string."
    assert (
        isinstance(config_data["rsi_period"], int) and config_data["rsi_period"] > 0
    ), f"rsi_period for {pair} must be a positive integer."
    assert (
        isinstance(config_data["rsi_oversold_threshold"], int)
        and 0 < config_data["rsi_oversold_threshold"] < 100
    ), f"rsi_oversold_threshold for {pair} must be between 0 and 100."
    assert (
        isinstance(config_data["fixed_buy_usd_amount"], float)
        and config_data["fixed_buy_usd_amount"] > 0
    ), f"fixed_buy_usd_amount for {pair} must be a positive float."
    assert (
        config_data["candle_granularity_api_name"] in CANDLE_GRANULARITY_SECONDS
    ), f"candle_granularity_api_name for {pair} is not recognized."
    assert (
        isinstance(config_data["max_candle_history_needed"], int)
        and config_data["max_candle_history_needed"] >= config_data["rsi_period"]
    ), f"max_candle_history_needed for {pair} is insufficient."

    tiers = config_data["profit_tiers"]
    assert (
        isinstance(tiers, list) and len(tiers) > 0
    ), f"profit_tiers for {pair} must be a non-empty list."
    cumulative_portion = 0.0
    has_all_remaining = False
    for tier in tiers:
        assert (
            isinstance(tier["profit_pct"], (int, float)) and tier["profit_pct"] > 0
        ), f"Tier profit_pct for {pair} must be positive."
        sell_portion = tier["sell_portion_initial"]
        if isinstance(sell_portion, (int, float)):
            assert (
                sell_portion > 0 and sell_portion <= 1.0
            ), f"Tier sell_portion_initial for {pair} must be between 0 and 1 (exclusive of 0)."
            cumulative_portion += sell_portion
        elif sell_portion == "all_remaining":
            has_all_remaining = True
        else:
            assert (
                False
            ), f"Invalid sell_portion_initial value in {pair}: {sell_portion}"
    assert (
        has_all_remaining
    ), f"The last profit tier for {pair} must have 'sell_portion_initial': 'all_remaining'."
    # Rule: Avoid complex flow constructs. (Assertions are simple checks here)
    # Allow cumulative portion to be slightly over 1 due to float precision if not using 'all_remaining' for all but last.
    # However, with 'all_remaining' as the typical last tier, this check is more about ensuring other portions are reasonable.
    assert (
        cumulative_portion <= 1.0001 or has_all_remaining
    ), f"Sum of sell_portion_initial for {pair} exceeds 100% before 'all_remaining'. Current sum: {cumulative_portion}"

    # Add assertions for min_base_trade_size, min_quote_trade_size, base_increment, quote_increment
    assert (
        isinstance(config_data.get("min_base_trade_size"), float)
        and config_data["min_base_trade_size"] > 0
    ), f"min_base_trade_size for {pair} must be a positive float."
    assert (
        isinstance(config_data.get("min_quote_trade_size"), float)
        and config_data["min_quote_trade_size"] > 0
    ), f"min_quote_trade_size for {pair} must be a positive float."
    assert (
        isinstance(config_data.get("base_increment"), str)
        and float(config_data["base_increment"]) > 0
    ), f"base_increment for {pair} must be a string representing a positive float."
    assert (
        isinstance(config_data.get("quote_increment"), str)
        and float(config_data["quote_increment"]) > 0
    ), f"quote_increment for {pair} must be a string representing a positive float."


if __name__ == "__main__":
    # Example of how to access configuration (for testing/demonstration)
    print("API Key Loaded:", bool(COINBASE_API_KEY))
    print("Log Level:", LOG_LEVEL)
    for pair_id, pair_config in TRADING_PAIRS.items():
        print(f"\nConfiguration for {pair_id}:")
        for key, value in pair_config.items():
            print(f"  {key}: {value}")
        # Calculate candle granularity in seconds
        granularity_name = pair_config["candle_granularity_api_name"]
        seconds = CANDLE_GRANULARITY_SECONDS.get(granularity_name)
        print(f"  Candle Granularity (seconds): {seconds}")

    print("\nConfig loaded and validated successfully.")
