"""Retry utilities with exponential backoff."""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional


class RetryError(Exception):
    """Raised when all retry attempts fail."""


def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    logger: Optional[logging.Logger] = None,
    raise_on_failure: bool = True,
) -> Callable:
    """Decorator for retrying a function with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            delay = base_delay
            last_exc = None
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt >= max_attempts:
                        if logger:
                            logger.error(
                                "Function %s failed after %d attempts: %s",
                                func.__name__, max_attempts, exc
                            )
                        if raise_on_failure:
                            raise RetryError(
                                f"Function {func.__name__} failed after {max_attempts} attempts"
                            ) from exc
                        return None
                    if logger:
                        logger.warning(
                            "Function %s attempt %d/%d failed: %s. Retrying in %.2fs",
                            func.__name__, attempt, max_attempts, exc, delay
                        )
                    time.sleep(delay)
                    attempt += 1
                    delay *= backoff
        return wrapper
    return decorator
