"""
Configuration and fixtures for the pytest test suite.

This file provides shared fixtures to avoid code duplication and improve
the maintainability of the tests.
"""

import pytest
import os
from typing import Dict, Any
from decimal import Decimal
import logging
from unittest.mock import MagicMock

# Added imports for logger setup
from trading.logger import setup_logging, LoggerDirectoryError
from trading import config as app_config


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


@pytest.fixture(scope="session")
def eth_product_details() -> Dict[str, Any]:
    """Provides a fixture for ETH-USD product details."""
    return {
        "product_id": "ETH-USD",
        "base_increment": "0.00001",
        "quote_increment": "0.01",
        "base_min_size": "0.001",
        "min_quote_trade_size": "1.0",
    }


@pytest.fixture
def set_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sets dummy environment variables for testing."""
    monkeypatch.setenv("COINBASE_API_KEY", "test_api_key")
    monkeypatch.setenv("COINBASE_API_SECRET", "test_api_secret")


@pytest.fixture
def mock_logger() -> MagicMock:
    """Provides a fixture for a mock logger."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def btc_product_details() -> Dict[str, Any]:
    """Provides a fixture for BTC-USD product details."""
    return {
        "product_id": "BTC-USD",
        "quote_increment": "0.01",
        "base_increment": "0.0001",
        "base_min_size": "0.001",
    }


@pytest.fixture(scope="session")
def btc_config_asset_params() -> Dict[str, Any]:
    """Provides a fixture for BTC-USD configuration parameters."""
    return {
        "profit_tiers": [
            {"label": "Tier 1", "profit_pct": 0.02, "sell_portion_initial": 0.5},
            {
                "label": "Tier 2",
                "profit_pct": 0.04,
                "sell_portion_initial": "all_remaining",
            },
        ]
    }


@pytest.fixture
def buy_amount_usd() -> Decimal:
    """Provides a sample buy amount in USD."""
    return Decimal("1000")


@pytest.fixture
def last_close_price() -> Decimal:
    """Provides a sample last close price."""
    return Decimal("50000")
