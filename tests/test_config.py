"""Tests for the config.py module."""

import unittest
import os
from unittest import mock
import importlib
import sys

MODULE_NAME = "config"
# Determine project root assuming tests are in a subdirectory like 'tests'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestConfig(unittest.TestCase):
    """Test suite for configuration loading and validation."""

    @classmethod
    def setUpClass(cls):
        """Set up project root for module imports if necessary."""
        cls.original_sys_path = list(sys.path)
        cls.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if cls.project_root not in sys.path:
            sys.path.insert(0, cls.project_root)

    @classmethod
    def tearDownClass(cls):
        """Restore original sys.path."""
        sys.path = cls.original_sys_path

    def setUp(self):
        """Set up a clean environment for testing the config module."""
        self.original_environ = dict(os.environ)
        self.original_config_module_in_sys_modules = sys.modules.get(MODULE_NAME)

        # Remove any existing (potentially mocked) config module from sys.modules
        # to ensure a fresh import attempt in each test after env vars are set.
        if MODULE_NAME in sys.modules:
            del sys.modules[MODULE_NAME]

    def tearDown(self):
        """Restore the original environment and sys.modules state."""
        os.environ.clear()
        os.environ.update(self.original_environ)

        # Clean up the config module from sys.modules
        if MODULE_NAME in sys.modules:
            del sys.modules[MODULE_NAME]

        # Restore the original config module state in sys.modules if it existed
        if self.original_config_module_in_sys_modules:
            sys.modules[MODULE_NAME] = self.original_config_module_in_sys_modules
        # Ensure it's definitely gone if it wasn't there originally but got added by a test somehow
        elif MODULE_NAME in sys.modules:
            del sys.modules[MODULE_NAME]

    def _import_config(self):
        """Helper to import the config module, ensuring it's fresh."""
        if MODULE_NAME in sys.modules:
            # If a previous test in this class imported it and it wasn't cleaned perfectly,
            # or if some other part of the test runner imported it, reload for safety.
            return importlib.reload(sys.modules[MODULE_NAME])
        return importlib.import_module(MODULE_NAME)

    @mock.patch.dict(
        os.environ,
        {"COINBASE_API_KEY": "test_key", "COINBASE_API_SECRET": "test_secret"},
        clear=True,  # Clear other env vars to ensure isolation
    )
    def test_api_keys_loaded_successfully(self):
        """Test that API keys are loaded when environment variables are set."""
        try:
            config = self._import_config()
            self.assertEqual(config.COINBASE_API_KEY, "test_key")
            self.assertEqual(config.COINBASE_API_SECRET, "test_secret")
        except ImportError as e:
            self.fail(
                f"Failed to import config module '{MODULE_NAME}': {e}. Check PYTHONPATH or test execution directory."
            )
        except Exception as e:
            self.fail(f"Config loading failed with unexpected error: {e}")

    @mock.patch('dotenv.load_dotenv')
    @mock.patch.dict(os.environ, {"COINBASE_API_SECRET": "test_secret"}, clear=True)
    def test_api_key_missing(self, mock_load_dotenv):
        """Test AssertionError is raised if COINBASE_API_KEY is missing."""
        # Ensure COINBASE_API_KEY is not in the environment for this test
        if "COINBASE_API_KEY" in os.environ:
            del os.environ["COINBASE_API_KEY"]  # Should be redundant due to clear=True

        with self.assertRaisesRegex(
            AssertionError, "COINBASE_API_KEY environment variable not set or empty."
        ):
            self._import_config()

    @mock.patch('dotenv.load_dotenv')
    @mock.patch.dict(
        os.environ,
        {"COINBASE_API_KEY": "", "COINBASE_API_SECRET": "test_secret"},
        clear=True,
    )
    def test_api_key_empty(self, mock_load_dotenv):
        """Test AssertionError is raised if COINBASE_API_KEY is empty."""
        with self.assertRaisesRegex(
            AssertionError, "COINBASE_API_KEY environment variable not set or empty."
        ):
            self._import_config()

    @mock.patch('dotenv.load_dotenv')
    @mock.patch.dict(os.environ, {"COINBASE_API_KEY": "test_key"}, clear=True)
    def test_api_secret_missing(self, mock_load_dotenv):
        """Test AssertionError is raised if COINBASE_API_SECRET is missing."""
        if "COINBASE_API_SECRET" in os.environ:
            del os.environ["COINBASE_API_SECRET"]  # Redundant due to clear=True

        with self.assertRaisesRegex(
            AssertionError, "COINBASE_API_SECRET environment variable not set or empty."
        ):
            self._import_config()

    @mock.patch('dotenv.load_dotenv')
    @mock.patch.dict(
        os.environ,
        {"COINBASE_API_KEY": "test_key", "COINBASE_API_SECRET": ""},
        clear=True,
    )
    def test_api_secret_empty(self, mock_load_dotenv):
        """Test AssertionError is raised if COINBASE_API_SECRET is empty."""
        with self.assertRaisesRegex(
            AssertionError, "COINBASE_API_SECRET environment variable not set or empty."
        ):
            self._import_config()

    @mock.patch.dict(
        os.environ,
        {"COINBASE_API_KEY": "test_key", "COINBASE_API_SECRET": "test_secret"},
        clear=True,
    )
    def test_default_general_settings(self):
        """Test default values for general bot settings."""
        config = self._import_config()
        self.assertEqual(config.LOG_LEVEL, "INFO")
        self.assertEqual(config.LOG_FILE, "v6_trading_bot.log")
        expected_persistence_dir = os.path.join(config.PROJECT_ROOT, "bot_data")
        self.assertEqual(config.PERSISTENCE_DIR, expected_persistence_dir)

    @mock.patch.dict(
        os.environ,
        {"COINBASE_API_KEY": "test_key", "COINBASE_API_SECRET": "test_secret"},
        clear=True,
    )
    def test_trading_pairs_structure_and_defaults(self):
        """Test the structure and some default values in TRADING_PAIRS."""
        config = self._import_config()
        self.assertIn("ETH-USD", config.TRADING_PAIRS)
        self.assertIn("BTC-USD", config.TRADING_PAIRS)
        self.assertIn("LTC-USD", config.TRADING_PAIRS)

        eth_config = config.TRADING_PAIRS["ETH-USD"]
        self.assertEqual(eth_config["product_id"], "ETH-USD")
        self.assertEqual(eth_config["rsi_period"], 14)
        self.assertEqual(eth_config["fixed_buy_usd_amount"], 20.00)
        self.assertEqual(eth_config["candle_granularity_api_name"], "FIFTEEN_MINUTE")
        self.assertEqual(eth_config["max_candle_history_needed"], 18)  # 14 + 3 + 1
        self.assertEqual(len(eth_config["profit_tiers"]), 3)
        self.assertEqual(
            eth_config["profit_tiers"][2]["sell_portion_initial"], "all_remaining"
        )

    @mock.patch.dict(
        os.environ,
        {"COINBASE_API_KEY": "test_key", "COINBASE_API_SECRET": "test_secret"},
        clear=True,
    )
    def test_candle_granularity_seconds(self):
        """Test candle granularity mappings."""
        config = self._import_config()
        self.assertEqual(config.CANDLE_GRANULARITY_SECONDS["ONE_MINUTE"], 60)
        self.assertEqual(config.CANDLE_GRANULARITY_SECONDS["FIFTEEN_MINUTE"], 900)
        self.assertEqual(config.CANDLE_GRANULARITY_SECONDS["ONE_DAY"], 86400)

    @mock.patch.dict(
        os.environ,
        {"COINBASE_API_KEY": "test_key", "COINBASE_API_SECRET": "test_secret"},
        clear=True,
    )
    def test_config_module_main_block_runs(self):
        """Test that the __main__ block in config.py executes without error if module is run as script."""
        # This test primarily ensures the module can be imported and its top-level code runs
        # (which includes assertions for API keys). The actual __main__ block's print statements
        # are not captured here. A full test of __main__ output would use subprocess.
        try:
            config_module = self._import_config()
            # If import is successful, it means the assertions in config.py passed with the mocked env vars.
            self.assertIsNotNone(config_module)
            # Further check if the __main__ block can be conceptually run (it's part of module loading)
            # For a simple config.py, the __main__ often just prints some config values.
            # We are mainly concerned it doesn't crash due to missing keys if run as `python config.py`
            # (assuming .env or env vars are set in that scenario).
            # Here, we've ensured the module loads with mocked env vars.
            if (
                hasattr(config_module, "__file__")
                and config_module.__name__ == "config"
            ):
                # Simulate running the module's main block if it has one
                # by checking if it defines a main function or similar, or just rely on import success.
                # The current config.py's __main__ block just prints values, so import success is enough.
                pass  # Sufficient that import didn't fail
        except Exception as e:
            self.fail(
                f"Loading config.py (simulating __main__ context) failed with mocked env: {e}"
            )


if __name__ == "__main__":
    unittest.main()
