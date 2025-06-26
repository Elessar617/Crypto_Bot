"""Refactored logging setup for the v6 crypto trading bot.

This module provides a function to explicitly configure and create a logger.
It removes import-time side effects and dependencies, making it testable.
"""

import logging
import os
import sys
from typing import Final, Optional


# Custom exception for logger directory issues
class LoggerDirectoryError(Exception):
    """Custom exception for errors related to the logger directory."""

    pass


# The root logger name for the application
APP_LOGGER_NAME: Final[str] = "CryptoBotV6"

# Global variable to hold the configured logger instance.
# This is checked to ensure setup_logging is called only once.
_logger_instance: Optional[logging.Logger] = None


def setup_logging(
    level: str, log_file: str, persistence_dir: str
) -> logging.Logger:
    """
    Configures and returns the application's root logger.

    This function should be called once at the beginning of the application's
    lifecycle. It is idempotent; subsequent calls will return the existing
    logger instance without reconfiguring.

    Args:
        level (str): The desired logging level (e.g., "DEBUG", "INFO").
        log_file (str): The name of the log file (e.g., "bot.log").
        persistence_dir (str): The base directory for logs and other data.

    Returns:
        logging.Logger: The configured logger instance.

    Raises:
        LoggerDirectoryError: If the log directory cannot be created or is not writable.
        ValueError: If the provided log level is invalid.
    """
    global _logger_instance
    if _logger_instance is not None:
        return _logger_instance

    # 1. Validate and convert log level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level provided: {level}")

    # 2. Create log directory
    log_directory = os.path.join(persistence_dir, "logs")
    try:
        os.makedirs(log_directory, exist_ok=True)
        if not os.access(log_directory, os.W_OK):
            raise LoggerDirectoryError(
                f"Log directory '{log_directory}' is not writable."
            )
    except OSError as e:
        raise LoggerDirectoryError(
            f"Failed to create log directory '{log_directory}': {e}"
        ) from e

    # 3. Configure the logger instance
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(numeric_level)
    logger.propagate = False

    # Clear any existing handlers to prevent duplicate logs in test environments
    if logger.hasHandlers():
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 4. Create and add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 5. Create and add file handler
    log_file_path = os.path.join(log_directory, log_file)
    try:
        file_handler = logging.FileHandler(log_file_path, mode="a")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except IOError as e:
        logger.error(
            f"Could not open log file '{log_file_path}': {e}. File logging will be disabled."
        )

    _logger_instance = logger
    logger.info(
        f"Logger initialized with level {level}. Logging to console and '{log_file_path}'."
    )
    return logger


def get_logger() -> logging.Logger:
    """
    Retrieves the configured logger instance.

    Raises:
        RuntimeError: If setup_logging() has not been called yet.

    Returns:
        logging.Logger: The application logger instance.
    """
    if _logger_instance is None:
        raise RuntimeError(
            "Logger not initialized. Please call setup_logging() before requesting a logger."
        )
    return _logger_instance
