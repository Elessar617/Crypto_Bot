"""Tests for the logger.py module."""

import os
import sys
import logging
import unittest
import tempfile
import shutil
import atexit
from unittest.mock import patch, MagicMock
import importlib

# Since logger is a module we want to test in isolation, we need to manage its imports carefully
# We will mock the 'config' module before importing the logger

# Create a secure temporary directory for the test run
_temp_dir = tempfile.mkdtemp()
# Register a cleanup function to remove the directory at exit
atexit.register(shutil.rmtree, _temp_dir)

# A mock config object that our tests can control
mock_config = MagicMock()
mock_config.PERSISTENCE_DIR = _temp_dir
mock_config.LOG_FILE = "test_bot.log"
mock_config.LOG_LEVEL = "DEBUG"

# Mock the config module in sys.modules before importing the logger
sys.modules["trading.config"] = mock_config

# Now, import the logger module. It will bind to our mock config.
from trading import logger as logger_module  # noqa: E402


class TestLogger(unittest.TestCase):
    """Test suite for the logger module."""

    def setUp(self):
        """Set up for each test."""
        # Reload the logger module to reset its state for each test
        importlib.reload(logger_module)
        # Ensure the log directory exists
        self.log_dir = os.path.join(mock_config.PERSISTENCE_DIR, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, mock_config.LOG_FILE)

    def tearDown(self):
        """Clean up after each test."""
        # Reset the logger's internal state
        logger_module._reset_logger()
        # Clean up the log file if it was created
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def test_successful_initialization(self):
        """Test that a logger can be initialized successfully."""
        logger = logger_module.setup_logging(
            level=mock_config.LOG_LEVEL,
            log_file=mock_config.LOG_FILE,
            persistence_dir=mock_config.PERSISTENCE_DIR,
        )
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, logger_module.APP_LOGGER_NAME)
        self.assertEqual(logger.level, logging.DEBUG)

        # Check that handlers are present
        self.assertTrue(
            any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        )
        self.assertTrue(
            any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        )

        # Check that the log file was created
        self.assertTrue(os.path.isfile(self.log_file))

    def test_get_logger_before_setup(self):
        """Test that get_logger raises an error if called before setup."""
        with self.assertRaisesRegex(RuntimeError, "Logger not initialized"):
            logger_module.get_logger()

    def test_logging_to_file(self):
        """Test that messages are written to the log file."""
        logger = logger_module.setup_logging(
            level=mock_config.LOG_LEVEL,
            log_file=mock_config.LOG_FILE,
            persistence_dir=mock_config.PERSISTENCE_DIR,
        )
        test_message = "This is a test message for file logging."
        logger.info(test_message)

        with open(self.log_file, "r") as f:
            content = f.read()
        self.assertIn(test_message, content)

    @patch("trading.logger.os.path.exists", return_value=False)
    @patch("trading.logger.os.makedirs", side_effect=OSError("Permission denied"))
    def test_log_directory_creation_failure(self, mock_makedirs, mock_exists):
        """Test logger raises LoggerDirectoryError when directory creation fails."""
        # We must use logger_module.LoggerDirectoryError because the module is reloaded,
        # creating a new class object for the exception.
        with self.assertRaises(logger_module.LoggerDirectoryError) as cm:
            logger_module.setup_logging(
                level=mock_config.LOG_LEVEL,
                log_file=mock_config.LOG_FILE,
                persistence_dir=mock_config.PERSISTENCE_DIR,
            )
        self.assertIn("Failed to create log directory", str(cm.exception))

    @patch("logging.FileHandler", side_effect=IOError("Permission denied"))
    def test_file_handler_creation_io_error(self, mock_file_handler):
        """Test behavior when creating the FileHandler raises an IOError."""
        # This call should handle the error gracefully and not raise an exception
        logger_module.setup_logging(
            level=mock_config.LOG_LEVEL,
            log_file=mock_config.LOG_FILE,
            persistence_dir=mock_config.PERSISTENCE_DIR,
        )

        # Verify that only the StreamHandler was added.
        app_logger = logger_module.get_logger()
        self.assertEqual(len(app_logger.handlers), 1)
        self.assertIsInstance(app_logger.handlers[0], logging.StreamHandler)


if __name__ == "__main__":
    unittest.main()
