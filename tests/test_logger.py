"""Tests for the logger.py module."""

import unittest
import os
import logging
import shutil  # For cleaning up test directories
import sys
from unittest import mock
import importlib

from types import ModuleType
from typing import Optional
import tempfile

# Determine the actual logger module name (e.g., 'logger' if logger.py is in the same dir or PYTHONPATH)
# Assuming logger.py is in the parent directory of tests, or accessible via PYTHONPATH
# For this project structure, it's likely 'logger'
LOGGER_MODULE_NAME = "trading.logger"  # The actual name of the logger module as Python knows it
CONFIG_MODULE_NAME = "trading.config"  # The actual name of the config module

# Try to import the actual logger and config modules to get their spec for MagicMock
# This helps create more accurate mocks.
try:
    logger_module_actual: Optional[ModuleType] = importlib.import_module(
        LOGGER_MODULE_NAME
    )
    config_module_actual: Optional[ModuleType] = importlib.import_module(
        CONFIG_MODULE_NAME
    )
except ImportError as e:
    # Fallback if direct import fails (e.g. path issues not resolved for test runner)
    # This might lead to less specific mocks if spec cannot be determined.
    print(f"Could not import logger/config for spec: {e}. Using basic MagicMock.")
    logger_module_actual = None
    config_module_actual = None


class TestLogger(unittest.TestCase):
    def setUp(self):
        """Set up a clean environment for each logger test."""
        # Save original modules to restore them later. This is critical for isolation.
        self.original_modules = {
            "trading.config": sys.modules.pop("trading.config", None),
            "trading.logger": sys.modules.pop("trading.logger", None),
        }
        self.addCleanup(self._restore_modules)

        # Create a temporary directory for logs
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

        # Create and inject a mock config module
        self.mock_config = mock.MagicMock(spec=config_module_actual)
        self.mock_config.PERSISTENCE_DIR = self.test_dir
        self.mock_config.LOG_FILE = "test_app.log"
        self.mock_config.LOG_LEVEL = "DEBUG"
        sys.modules["trading.config"] = self.mock_config

        # Import a fresh copy of the logger for each test
        self.logger_module = importlib.import_module(LOGGER_MODULE_NAME)

    def _restore_modules(self):
        """Cleanup function to restore sys.modules."""
        for name, module in self.original_modules.items():
            if module:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)

    def test_successful_initialization(self):
        """Test that a logger can be initialized successfully."""
        self.logger_module.setup_logging(
            level=self.mock_config.LOG_LEVEL,
            log_file=self.mock_config.LOG_FILE,
            persistence_dir=self.mock_config.PERSISTENCE_DIR,
        )
        logger = self.logger_module.get_logger()
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, self.logger_module.APP_LOGGER_NAME)
        self.assertEqual(logger.level, logging.DEBUG)

        # Check that handlers are present
        has_stream_handler = any(
            isinstance(h, logging.StreamHandler) for h in logger.handlers
        )
        has_file_handler = any(
            isinstance(h, logging.FileHandler) for h in logger.handlers
        )
        self.assertTrue(has_stream_handler, "No StreamHandler found.")
        self.assertTrue(has_file_handler, "No FileHandler found.")

        # Check that the log directory and file were created
        log_dir = os.path.join(self.test_dir, "logs")
        log_file = os.path.join(log_dir, self.mock_config.LOG_FILE)
        self.assertTrue(os.path.isdir(log_dir), "Log directory was not created.")
        self.assertTrue(
            os.path.isfile(log_file), f"Log file was not created at {log_file}."
        )

    def test_logging_to_file(self):
        """Test that messages are written to the log file."""
        self.logger_module.setup_logging(
            level=self.mock_config.LOG_LEVEL,
            log_file=self.mock_config.LOG_FILE,
            persistence_dir=self.mock_config.PERSISTENCE_DIR,
        )
        logger = self.logger_module.get_logger()
        test_message = "This is a test message for file logging."
        logger.info(test_message)

        log_file_path = os.path.join(self.test_dir, "logs", self.mock_config.LOG_FILE)
        with open(log_file_path, "r") as f:
            content = f.read()
        self.assertIn(test_message, content)

    def test_log_directory_creation_failure(self):
        """Test logger raises LoggerDirectoryError when directory creation fails."""
        self.logger_module._reset_logger()

        # Patch os.makedirs just for this test to simulate failure
        with mock.patch(
            f"{LOGGER_MODULE_NAME}.os.makedirs",
            side_effect=OSError("Permission denied"),
        ):
            with self.assertRaises(self.logger_module.LoggerDirectoryError) as cm:
                self.logger_module.setup_logging(
                    level=self.mock_config.LOG_LEVEL,
                    log_file=self.mock_config.LOG_FILE,
                    persistence_dir=self.mock_config.PERSISTENCE_DIR,
                )
            self.assertIn("Failed to create log directory", str(cm.exception))

    def test_file_handler_creation_io_error(self):
        """Test behavior when creating the FileHandler raises an IOError."""
        self.logger_module._reset_logger()

        # Patch FileHandler just for this test to simulate failure
        with mock.patch(
            f"{LOGGER_MODULE_NAME}.logging.FileHandler",
            side_effect=IOError("Permission denied"),
        ):
            # This call should handle the error gracefully and not raise an exception
            self.logger_module.setup_logging(
                level=self.mock_config.LOG_LEVEL,
                log_file=self.mock_config.LOG_FILE,
                persistence_dir=self.mock_config.PERSISTENCE_DIR,
            )

        # Verify that no FileHandler was actually added to the logger
        app_logger = self.logger_module.get_logger()
        has_file_handler = any(
            isinstance(h, logging.FileHandler) for h in app_logger.handlers
        )
        self.assertFalse(
            has_file_handler, "FileHandler should not be added on IOError."
        )


if __name__ == "__main__":
    # Ensure config is importable if run directly, by setting up env vars
    os.environ["COINBASE_API_KEY"] = os.environ.get(
        "COINBASE_API_KEY", "dummy_key_main"
    )
    os.environ["COINBASE_API_SECRET"] = os.environ.get(
        "COINBASE_API_SECRET", "dummy_secret_main"
    )
    unittest.main()
