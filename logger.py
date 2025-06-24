"""Logging setup and utility functions for the v6 crypto trading bot.

This module configures a root logger for the application, directing log output
to both the console and a log file. It uses settings defined in config.py.
"""

import logging
import os
import sys
from typing import Final, Optional


# Custom exception for logger directory issues
class LoggerDirectoryError(Exception):
    pass


# Temporary variables to hold config values before Final declaration
_log_level_str: str
_log_file_str: str
_persistence_dir_str: str

# Rule: Restrict the scope of data to the smallest possible.
# Attempt to import configuration settings
try:
    # Ensure that config is imported and used locally to avoid polluting namespace if not needed
    from config import (
        LOG_LEVEL as CFG_LOG_LEVEL,
        LOG_FILE as CFG_LOG_FILE,
        PERSISTENCE_DIR as CFG_PERSISTENCE_DIR,
    )

    # Validate and cast imported config values
    # Rule: Check the return value of all non-void functions.
    # Rule: Use a minimum of two runtime assertions per function (or logical block).
    assert isinstance(CFG_LOG_LEVEL, str), "LOG_LEVEL from config must be a string."
    _log_level_str = CFG_LOG_LEVEL.upper()
    assert _log_level_str in [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ], f"Invalid LOG_LEVEL '{_log_level_str}' from config."

    assert isinstance(CFG_LOG_FILE, str), "LOG_FILE from config must be a string."
    _log_file_str = CFG_LOG_FILE
    assert len(_log_file_str) > 0, "LOG_FILE from config cannot be empty."

    assert isinstance(
        CFG_PERSISTENCE_DIR, str
    ), "PERSISTENCE_DIR from config must be a string."
    _persistence_dir_str = CFG_PERSISTENCE_DIR
    assert len(_persistence_dir_str) > 0, "PERSISTENCE_DIR from config cannot be empty."

    # Log successful import and usage of config values
    # This initial logging will go to stderr if logger isn't fully set up yet.
    logging.getLogger(__name__).info(
        "Successfully imported and validated logger configuration from config.py."
    )

except ImportError as e:
    # Log that config import failed and we are using defaults
    logging.getLogger(__name__).critical(
        f"Failed to import config: {e}. Using basic stderr logging and default paths."
    )
    # Use default fallback values
    _log_level_str = "ERROR"
    _log_file_str = "critical_error_logger_fallback.log"
    _persistence_dir_str = "."

except AssertionError as e:
    logging.getLogger(__name__).critical(
        f"Configuration validation error: {e}. Using basic stderr logging and default paths."
    )
    # Use default fallback values on assertion error as well
    _log_level_str = "ERROR"
    _log_file_str = "critical_error_logger_fallback.log"
    _persistence_dir_str = "."

# Now, define the Final constants for the logger module
LOG_LEVEL: Final[str] = _log_level_str
LOG_FILE: Final[str] = _log_file_str
PERSISTENCE_DIR: Final[str] = _persistence_dir_str

# Define the root logger name for the application
APP_LOGGER_NAME: Final[str] = "CryptoBotV6"

# Construct log directory path
# Rule: Restrict the scope of data to the smallest possible.
LOG_DIRECTORY: Final[str] = os.path.join(PERSISTENCE_DIR, "logs")
LOG_FILE_PATH: Final[str] = os.path.join(LOG_DIRECTORY, LOG_FILE)

# Ensure log directory exists
# Rule: Avoid heap memory allocation after initialization (os.makedirs is an init step).
# Rule: Check the return value of all non-void functions (not directly applicable here, but good practice for os calls).
try:
    os.makedirs(LOG_DIRECTORY, exist_ok=True)
    # Custom checks for directory creation/accessibility
    if not os.path.exists(LOG_DIRECTORY):
        raise LoggerDirectoryError(
            f"Log directory {LOG_DIRECTORY} was not created or is not accessible after makedirs."
        )
    if not os.access(LOG_DIRECTORY, os.W_OK):
        raise LoggerDirectoryError(
            f"Log directory {LOG_DIRECTORY} is not writable after makedirs."
        )
except (OSError, LoggerDirectoryError) as e:
    # If directory creation or validation fails, log to stderr and use a basic logger configuration
    # This is a critical failure for file logging.
    print(
        f"CRITICAL: Could not create log directory {LOG_DIRECTORY}: {e}",
        file=sys.stderr,
    )
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger(__name__).critical(
        f"Failed to create log directory {LOG_DIRECTORY}: {e}. File logging disabled."
    )
    # Fallback to console-only logging if directory fails
    _file_logging_enabled = False
else:
    _file_logging_enabled = True

# Configure the logger instance
_logger = logging.getLogger(APP_LOGGER_NAME)

# Clear any existing handlers from a previous load/configuration.
# This is crucial for testing scenarios involving module reloads to ensure a clean state.
# Iterate over a copy of the handlers list for safe removal.
if _logger.hasHandlers():
    for handler in list(_logger.handlers):
        _logger.removeHandler(handler)
        handler.close()  # Important to close handlers to release resources

# Reset propagation to default (False, as set later) in case it was modified by a previous configuration.
_logger.propagate = False

# Set the logging level from config (ensure it's a valid level)
# Rule: All loops must have fixed bounds (not applicable here).
# Rule: Avoid complex flow constructs (simple if/else for level setting).
log_level_numeric = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
assert isinstance(
    log_level_numeric, int
), f"Invalid LOG_LEVEL '{LOG_LEVEL}' from config. Defaulting to INFO."
if not isinstance(log_level_numeric, int):
    print(
        f"WARNING: Invalid LOG_LEVEL '{LOG_LEVEL}' from config. Defaulting to INFO.",
        file=sys.stderr,
    )
    log_level_numeric = logging.INFO  # Fallback to INFO if invalid

_logger.setLevel(log_level_numeric)

# Create a standard formatter
# Rule: Use the preprocessor only for header files and simple macros (not applicable to Python logging format strings).
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Create and configure console handler
console_handler = logging.StreamHandler(sys.stdout)  # Log to stdout
console_handler.setFormatter(formatter)
_logger.addHandler(console_handler)

# Create and configure file handler if directory creation was successful
if _file_logging_enabled:
    try:
        file_handler = logging.FileHandler(LOG_FILE_PATH, mode="a")  # Append mode
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
        # Two assertions for file handler setup
        assert any(
            isinstance(h, logging.FileHandler) for h in _logger.handlers
        ), "FileHandler not added to logger."
        # Check if file was created or is writable (this is a bit harder to assert directly post-handler-add without logging something)
        # For now, the try/except for FileHandler creation is the primary check.
    except IOError as e:
        _logger.error(
            f"Could not create or open log file {LOG_FILE_PATH}: {e}. File logging will be disabled."
        )
        # No need to remove console_handler, it's already added and useful.

# Prevent log propagation to avoid duplicate messages if root logger is also configured by another library
_logger.propagate = False


# Function to provide the logger instance
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns the centrally configured application logger.

    Args:
        name (Optional[str]): The name of the logger, typically __name__ of the calling module.
                              This is accepted for compatibility but the function currently
                              returns the main application logger instance.

    Returns:
        logging.Logger: The configured application logger.
    """
    if name:
        _logger.debug(f"Logger instance being provided to: {name}")

    return _logger


# Example usage (and basic test of logger setup)
if __name__ == "__main__":
    # This block will only run if logger.py is executed directly.
    # It demonstrates how to use the logger.
    try:
        local_logger = get_logger()
        local_logger.debug("This is a debug message.")
        local_logger.info("Logger initialized successfully. This is an info message.")
        local_logger.warning("This is a warning message.")
        local_logger.error("This is an error message.")
        local_logger.critical("This is a critical message.")
        if not _file_logging_enabled:
            print("File logging was disabled due to an earlier error.", file=sys.stderr)
        else:
            print(f"Log messages also written to: {LOG_FILE_PATH}")

    except Exception as e:
        # Fallback print if logger itself fails catastrophically during this test run
        print(f"Error during logger self-test: {e}", file=sys.stderr)
