"""Tests for the logger.py module."""

import unittest
import os
import logging
import shutil  # For cleaning up test directories
import sys
from unittest import mock
import importlib
import types
from types import ModuleType
from typing import Optional
import tempfile

# Determine the actual logger module name (e.g., 'logger' if logger.py is in the same dir or PYTHONPATH)
# Assuming logger.py is in the parent directory of tests, or accessible via PYTHONPATH
# For this project structure, it's likely 'logger'
LOGGER_MODULE_NAME = "logger"  # The actual name of the logger module as Python knows it
CONFIG_MODULE_NAME = "config"  # The actual name of the config module

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
        """Set up test environment for each test."""
        self.test_log_dir = tempfile.mkdtemp(prefix="test_logs_")
        self.addCleanup(shutil.rmtree, self.test_log_dir)

        # Create a mock config object
        # Use spec=config_module_actual if available for a more accurate mock
        self.mock_config = mock.MagicMock(
            spec=config_module_actual if config_module_actual else object
        )
        self.mock_config.PERSISTENCE_DIR = self.test_log_dir
        self.mock_config.LOG_FILE = "test_app.log"
        self.mock_config.LOG_LEVEL = "DEBUG"  # Default for tests

        # 1. Replace the 'config' module in sys.modules with our mock_config.
        #    This must be done *before* logger.py is re-imported so that its
        #    'from config import ...' statement picks up the mock.
        #    Store the original config module if it exists, to restore in tearDown/addCleanup.
        self.original_config_module = sys.modules.get(CONFIG_MODULE_NAME)
        self.sys_modules_patcher = mock.patch.dict(
            sys.modules, {CONFIG_MODULE_NAME: self.mock_config}
        )
        self.sys_modules_patcher.start()

        def stop_sys_modules_patch():
            self.sys_modules_patcher.stop()
            # Restore original config module if it existed, otherwise remove the mock
            if self.original_config_module:
                sys.modules[CONFIG_MODULE_NAME] = self.original_config_module
            elif (
                CONFIG_MODULE_NAME in sys.modules
                and sys.modules[CONFIG_MODULE_NAME] is self.mock_config
            ):
                del sys.modules[CONFIG_MODULE_NAME]

        self.addCleanup(stop_sys_modules_patch)

        # 2. Remove the original logger module from sys.modules to force a full re-import.
        #    This is crucial if logger.py has module-level constants derived from config.
        if LOGGER_MODULE_NAME in sys.modules:
            del sys.modules[LOGGER_MODULE_NAME]

        # 3. Re-import the logger module. It will now execute its top-level statements
        #    (including 'from config import ...') using the patched config.
        self.logger_module = importlib.import_module(LOGGER_MODULE_NAME)

        # The _logger_configured flag logic is removed as logger.py's current structure
        # reconfigures itself at module level on import by clearing existing handlers.

        # Mock os.makedirs to control its behavior if needed, though with tempfile it might not be necessary
        # unless testing specific failure paths of directory creation itself.
        self.mock_makedirs = mock.patch("os.makedirs").start()
        self.addCleanup(
            mock.patch.stopall
        )  # Stops all patches started with patch().start()

        # Get a logger instance for tests to use, it should now be configured with mocks
        self.logger = self.logger_module.get_logger()

    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches started with patch() or self.config_patcher.start()
        # self.addCleanup handles this, but explicit stopall can be here too if preferred.
        # mock.patch.stopall() # This is now handled by addCleanup

        # Reset logger configuration state if necessary, though setUp should handle it for next test.
        # Clear any handlers that might have been added to the root logger directly or by other means
        # to prevent interference between tests.
        root_logger = logging.getLogger()
        if hasattr(root_logger, "handlers"):
            for handler in list(root_logger.handlers):
                root_logger.removeHandler(handler)
            root_logger.handlers.clear()

        # Also specifically for the app logger if it's different and might persist handlers
        app_logger = logging.getLogger(self.logger_module.APP_LOGGER_NAME)
        if hasattr(app_logger, "handlers"):
            for handler in list(app_logger.handlers):
                app_logger.removeHandler(handler)
            app_logger.handlers.clear()

        # Ensure _logger_configured is reset for the actual module if it was reloaded
        # This is more robustly handled in setUp by removing from sys.modules and re-importing.
        # if logger_module_actual and hasattr(logger_module_actual, '_logger_configured'):
        #     logger_module_actual._logger_configured = False

    def test_get_logger_instance(self):
        """Test that get_logger() returns a configured logger instance."""
        logger = self.logger_module.get_logger()
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, self.logger_module.APP_LOGGER_NAME)
        self.assertEqual(logger.level, logging.DEBUG)

    def test_log_directory_and_file_creation(self):
        """Test that the log directory and file are created."""
        self.assertTrue(
            os.path.isdir(self.test_log_dir), "Log directory was not created."
        )
        logger = self.logger_module.get_logger()
        logger.info("Test message for file creation.")
        # Adjusted path to include 'logs' subdirectory
        expected_log_file_path = os.path.join(self.test_log_dir, "logs", "test_app.log")
        self.assertTrue(
            os.path.isfile(expected_log_file_path),
            f"Log file was not created at {expected_log_file_path}.",
        )

    def test_logging_to_file(self):
        """Test that messages are written to the log file."""
        logger = self.logger_module.get_logger()
        test_message = "This is a unique test message for file logging."
        logger.info(test_message)

        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()

        # Adjusted path to include 'logs' subdirectory
        expected_log_file_path = os.path.join(self.test_log_dir, "logs", "test_app.log")
        with open(expected_log_file_path, "r") as f:
            log_content = f.read()
        self.assertIn(test_message, log_content)
        self.assertIn("INFO", log_content)

    def test_console_handler_present(self):
        """Test that a console handler (StreamHandler) is present."""
        logger = self.logger_module.get_logger()
        has_stream_handler = any(
            isinstance(h, logging.StreamHandler) for h in logger.handlers
        )
        self.assertTrue(
            has_stream_handler, "No StreamHandler found for console logging."
        )

    @mock.patch(f"{LOGGER_MODULE_NAME}.os.access")
    @mock.patch(f"{LOGGER_MODULE_NAME}.os.path.exists")
    def test_log_directory_creation_failure(
        self, mock_logger_os_path_exists, mock_logger_os_access
    ):
        """Test logger behavior when log directory creation fails or is not writable."""
        # Stop the global makedirs mock from setUp for this specific test
        self.mock_makedirs.stop()

        # Scenario 1: os.makedirs raises OSError
        with mock.patch(
            f"{LOGGER_MODULE_NAME}.os.makedirs",
            side_effect=OSError("Permission denied"),
        ) as mock_failing_makedirs:  # noqa: F841
            # Ensure config is re-evaluated by removing and re-importing logger module
            if LOGGER_MODULE_NAME in sys.modules:
                del sys.modules[LOGGER_MODULE_NAME]
            temp_logger_module_fail_create = importlib.import_module(LOGGER_MODULE_NAME)

            # Assert that _file_logging_enabled is False in the re-imported module
            self.assertFalse(
                temp_logger_module_fail_create._file_logging_enabled,
                "_file_logging_enabled should be False when makedirs fails.",
            )

            # Assert that no FileHandler was added to the logger instance
            logger_instance = temp_logger_module_fail_create._logger
            has_file_handler = any(
                isinstance(h, logging.FileHandler) for h in logger_instance.handlers
            )
            self.assertFalse(
                has_file_handler,
                "FileHandler should not be present if directory creation failed.",
            )

        # Restart the global makedirs mock for subsequent tests.
        self.mock_makedirs.start()

        # Scenario 2: Directory exists but is not writable (os.access returns False)
        # Configure mocks for this scenario
        mock_logger_os_path_exists.return_value = True  # Directory exists
        mock_logger_os_access.return_value = False  # Directory not writable

        if LOGGER_MODULE_NAME in sys.modules:
            del sys.modules[LOGGER_MODULE_NAME]
        temp_logger_module_not_writable = importlib.import_module(LOGGER_MODULE_NAME)

        self.assertFalse(
            temp_logger_module_not_writable._file_logging_enabled,
            "_file_logging_enabled should be False when dir not writable.",
        )
        logger_instance_not_writable = temp_logger_module_not_writable._logger
        has_file_handler_not_writable = any(
            isinstance(h, logging.FileHandler)
            for h in logger_instance_not_writable.handlers
        )
        self.assertFalse(
            has_file_handler_not_writable,
            "FileHandler should not be present if dir not writable.",
        )

    def _get_actual_config(self):
        """Helper to get a fresh import of the config module with current env vars."""
        # Temporarily remove config from sys.modules to ensure fresh import
        original_config = sys.modules.pop(CONFIG_MODULE_NAME, None)
        try:
            config_module = importlib.import_module(CONFIG_MODULE_NAME)
            return config_module
        finally:
            # Restore original config module if it existed, otherwise remove the new one
            if original_config:
                sys.modules[CONFIG_MODULE_NAME] = original_config
            elif CONFIG_MODULE_NAME in sys.modules:
                del sys.modules[CONFIG_MODULE_NAME]

    def _load_logger_module(self):
        """Helper to load/reload the logger module for a test."""
        if LOGGER_MODULE_NAME in sys.modules:
            # If entry exists but is not a module type, remove it to force fresh import
            if not isinstance(sys.modules[LOGGER_MODULE_NAME], types.ModuleType):
                del sys.modules[LOGGER_MODULE_NAME]
                # After deletion, it will definitely go to the 'else' block of the next check

        if LOGGER_MODULE_NAME in sys.modules:  # Re-check condition
            self.logger_module = importlib.reload(sys.modules[LOGGER_MODULE_NAME])
        else:
            self.logger_module = importlib.import_module(LOGGER_MODULE_NAME)
        return self.logger_module


if __name__ == "__main__":
    # Ensure config is importable if run directly, by setting up env vars
    os.environ["COINBASE_API_KEY"] = os.environ.get(
        "COINBASE_API_KEY", "dummy_key_main"
    )
    os.environ["COINBASE_API_SECRET"] = os.environ.get(
        "COINBASE_API_SECRET", "dummy_secret_main"
    )
    unittest.main()
