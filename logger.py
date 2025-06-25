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


def _load_config() -> tuple[str, str, str, int]:
    """
    Loads logger configuration, providing fallbacks on error.

    This function encapsulates the logic for importing and validating configuration
    from `config.py`. If any step fails (import, validation), it logs a
    critical error and returns safe default values.

    Returns:
        A tuple containing:
        - Log level as a string (e.g., "DEBUG").
        - Log file name as a string.
        - Persistence directory path as a string.
        - Numeric log level (e.g., logging.DEBUG).
    """
    try:
        # Dynamically import to keep this function self-contained.
        from config import (
            LOG_LEVEL as CFG_LOG_LEVEL,
            LOG_FILE as CFG_LOG_FILE,
            PERSISTENCE_DIR as CFG_PERSISTENCE_DIR,
        )

        # Rule: Use a minimum of two runtime assertions per logical block.
        assert isinstance(CFG_LOG_LEVEL, str), "LOG_LEVEL must be a string."
        level_str = CFG_LOG_LEVEL.upper()
        numeric_level = getattr(logging, level_str, -1)
        assert numeric_level != -1, f"Invalid LOG_LEVEL '{level_str}' specified."

        assert isinstance(CFG_LOG_FILE, str), "LOG_FILE must be a string."
        assert len(CFG_LOG_FILE) > 0, "LOG_FILE cannot be empty."

        assert isinstance(
            CFG_PERSISTENCE_DIR, str
        ), "PERSISTENCE_DIR must be a string."
        assert len(CFG_PERSISTENCE_DIR) > 0, "PERSISTENCE_DIR cannot be empty."

        # Log success only if everything is valid.
        logging.getLogger(__name__).info("Successfully loaded logger configuration.")
        return level_str, CFG_LOG_FILE, CFG_PERSISTENCE_DIR, numeric_level

    except (ImportError, AssertionError) as e:
        # Log the specific error and return fallback values.
        logging.getLogger(__name__).critical(
            f"Logger config error: {e}. Using ERROR level fallback."
        )
        return "ERROR", "critical_error_logger_fallback.log", ".", logging.ERROR


# Load configuration at module level using the helper function.
# Rule: Restrict the scope of data to the smallest possible.
(LOG_LEVEL, LOG_FILE, PERSISTENCE_DIR, _log_level_numeric) = _load_config()

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

def setup_logger(
    level: int, file_path: str, file_logging_enabled: bool
) -> tuple[logging.Logger, bool]:
    """
    Configures and returns the application logger.

    This function is responsible for setting up the logger's handlers, formatter,
    and level. It is designed to be called once at module startup and can be
    re-called during testing to reconfigure the logger in a controlled way.

    Args:
        level (int): The numeric logging level (e.g., logging.DEBUG).
        file_path (str): The full path to the log file.
        file_logging_enabled (bool): Whether to enable file logging.

    Returns:
        tuple[logging.Logger, bool]: A tuple containing the configured logger
                                     and a boolean indicating if file logging
                                     was successfully enabled.
    """
    logger = logging.getLogger(APP_LOGGER_NAME)

    # Clear any existing handlers to ensure a clean configuration.
    if logger.hasHandlers():
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if file_logging_enabled:
        try:
            file_handler = logging.FileHandler(file_path, mode="a")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            return logger, True  # Return logger and True for success
        except IOError as e:
            logger.error(
                f"Could not create or open log file {file_path}: {e}. File logging disabled."
            )
            return logger, False  # Return logger and False for failure

    # If file logging was not enabled in the first place
    return logger, False


# Initial setup on module import
_logger, _file_logging_enabled = setup_logger(
    _log_level_numeric, LOG_FILE_PATH, _file_logging_enabled
)


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
