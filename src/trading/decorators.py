"""Custom decorators for the trading bot."""

import time
import logging
from functools import wraps
from typing import Any, Callable, Type, Tuple

from requests.exceptions import HTTPError, RequestException

from . import logger


def retry_on_exception(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (RequestException, HTTPError),
) -> Callable:
    """
    A decorator to retry a function call upon specific exceptions with exponential backoff.

    Args:
        max_retries (int): The maximum number of retries.
        base_delay (float): The base delay in seconds for backoff.
        exceptions (Tuple[Type[Exception], ...]): A tuple of exception types to catch and retry on.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func: Callable) -> Callable:
        """The actual decorator."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            log = logger.get_logger()
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        log.error(
                            f"Function {func.__name__} failed after {max_retries} retries.",
                            exc_info=True,
                        )
                        raise

                    delay = base_delay * (2**retries)
                    log.warning(
                        f"Retry {retries + 1}/{max_retries} for {func.__name__} due to {e}. Waiting {delay}s."
                    )
                    time.sleep(delay)

        return wrapper

    return decorator
