"""
Integration tests for the CoinbaseClient that make live API calls.

NOTE: These tests require valid COINBASE_API_KEY and COINBASE_API_SECRET environment
variables to be set in the .env file. They are designed to run against the
Coinbase Sandbox API and will be skipped if credentials are not available.
"""

import os
import sys
import unittest
from pathlib import Path
import pytest

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "Active/Single-File/v6"))

# Now we can import our modules
try:
    from coinbase_client import CoinbaseClient
    import config
except ImportError as e:
    print(f"Failed to import modules: {e}")
    # If imports fail, we can't run tests, so we'll have a dummy test that fails.
    CoinbaseClient = None
    config = None


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
        self.assertIsNotNone(
            CoinbaseClient, "CoinbaseClient class could not be imported."
        )
        self.assertIsNotNone(config, "config module could not be imported.")

        # Rule: Use the latest stable version of the operating system
        # This test is designed for a sandbox environment.
        self.client = CoinbaseClient(api_url=config.COINBASE_SANDBOX_API_URL)
        self.assertIsNotNone(
            self.client, "CoinbaseClient instance could not be created."
        )

    def test_get_accounts_sandbox(self):
        """
        Tests that get_accounts() can successfully connect to the sandbox
        and retrieve a list of accounts.
        """
        # Rule: Check the return value of all non-void functions.
        accounts = self.client.get_accounts()

        # Assertions
        self.assertIsNotNone(accounts, "get_accounts() should return a list, not None.")
        self.assertIsInstance(
            accounts, list, "get_accounts() should return a list."
        )
        # Sandbox may or may not have accounts, so we don't assert list is non-empty,
        # but we can check the structure if it is.
        if accounts:
            self.assertIsInstance(
                accounts[0], dict, "Items in the accounts list should be dictionaries."
            )
            self.assertIn("id", accounts[0], "Account dictionary should have an 'id' key.")


if __name__ == "__main__":
    # This allows the test to be run from the command line
    unittest.main()
