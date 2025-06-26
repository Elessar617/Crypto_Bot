"""
Configuration and fixtures for the pytest test suite.

This file provides shared fixtures to avoid code duplication and improve
the maintainability of the tests.
"""

import pytest
import os
from typing import Dict, Any

# Added imports for logger setup
from logger import setup_logging, LoggerDirectoryError
import config as app_config  # Use alias to avoid pytest 'config' fixture conflict


def pytest_configure(config):
    """Initializes the logger once before any tests are collected."""
    try:
        # Ensure the persistence directory exists for logging
        if not os.path.exists(app_config.PERSISTENCE_DIR):
            os.makedirs(app_config.PERSISTENCE_DIR)

        setup_logging(
            level=app_config.LOG_LEVEL,
            log_file=app_config.LOG_FILE,
            persistence_dir=app_config.PERSISTENCE_DIR,
        )
    except (LoggerDirectoryError, ValueError) as e:
        pytest.fail(f"Failed to initialize logger for tests: {e}")


@pytest.fixture
def valid_product_details() -> Dict[str, Any]:
    """Provides a fixture for a valid product details dictionary."""
    return {
        "product_id": "ETH-USD",
        "base_increment": "0.00001",
        "quote_increment": "0.01",
        "base_min_size": "0.001",
        "min_quote_trade_size": "1.0",
    }


@pytest.fixture
def sample_trading_pair_config() -> Dict[str, Any]:
    """
    Provides a fixture for a sample trading pair configuration dictionary.
    This structure is specifically for testing `determine_sell_orders_params`.
    """
    return {
        "sell_profit_tiers": [
            {"percentage": 2.0, "quantity_percentage": 50.0},
            {"percentage": 4.0, "quantity_percentage": 50.0},
        ]
    }


@pytest.fixture
def set_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sets dummy environment variables for testing."""
    monkeypatch.setenv("COINBASE_API_KEY", "test_api_key")
    monkeypatch.setenv("COINBASE_API_SECRET", "test_api_secret")
