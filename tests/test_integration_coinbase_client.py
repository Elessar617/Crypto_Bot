"""
Integration tests for the CoinbaseClient.

NOTE: These tests are mocked to avoid dependency on the live Coinbase Sandbox API.
"""

import os
import sys
import unittest
import importlib
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
import pytest
from typing import TYPE_CHECKING

# Add the project root to sys.path to allow for absolute imports of project modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# The TYPE_CHECKING block is for static analysis and avoids circular imports
if TYPE_CHECKING:
    from coinbase_client import CoinbaseClient
    import config


# --- Test Fixtures and Conditions ---

# Condition to skip tests if API credentials are not set
credentials_not_set = not (
    os.getenv("COINBASE_API_KEY") and os.getenv("COINBASE_API_SECRET")
)
skip_reason = "Coinbase API credentials are not set in the environment."


# --- Integration Test Class ---

@pytest.mark.skipif(credentials_not_set, reason=skip_reason)
class TestIntegrationCoinbaseClient(unittest.TestCase):
    """Contains integration tests for the CoinbaseClient."""

    def setUp(self):
        """Set up the test client before each test."""
        # Remove potentially mocked modules from other tests before importing.
        if 'config' in sys.modules:
            del sys.modules['config']
        if 'coinbase_client' in sys.modules:
            del sys.modules['coinbase_client']

        # Load environment variables from .env file
        load_dotenv()

        # Now import the modules fresh.
        import config
        import coinbase_client

        # Patch the RESTClient to avoid actual API calls
        self.patcher = patch("coinbase_client.RESTClient")
        self.mock_rest_client_class = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.mock_rest_client_instance = self.mock_rest_client_class.return_value

        # This test is designed for a sandbox environment.
        self.client = coinbase_client.CoinbaseClient(api_url=config.COINBASE_SANDBOX_API_URL)
        self.assertIsNotNone(
            self.client, "CoinbaseClient instance could not be created."
        )

    def test_get_accounts_sandbox(self):
        """
        Tests that get_accounts() can successfully retrieve a list of accounts.
        """
        # Arrange: Configure the mock RESTClient instance
        expected_accounts = [
            {
                "uuid": "f4d7e406-8e6a-4b6a-8c1a-2b3c4d5e6f7g",
                "name": "BTC Wallet",
                "currency": "BTC",
                "balance": "1.00000000",
                "available": "1.00000000",
                "hold": "0.00000000",
                "type": "ACCOUNT_TYPE_CRYPTO",
                "ready": True,
            }
        ]
        self.mock_rest_client_instance.get_accounts.return_value = {
            "accounts": expected_accounts
        }

        # Act: Call the method on our client instance
        accounts = self.client.get_accounts()

        # Assertions
        self.assertIsNotNone(accounts, "get_accounts() should return a list, not None.")
        self.assertIsInstance(
            accounts, list, "get_accounts() should return a list of accounts."
        )
        self.assertEqual(accounts, expected_accounts)
        if accounts:
            self.assertIn("uuid", accounts[0])


if __name__ == "__main__":
    # This allows the test to be run from the command line
    unittest.main()
