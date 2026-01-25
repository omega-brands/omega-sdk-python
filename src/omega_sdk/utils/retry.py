"""
Retry policy for OMEGA SDK.

Implements bounded retries with exponential backoff for transient errors.
"""

from typing import Any, Callable, TypeVar
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    RetryError,
)

from omega_sdk.errors import OmegaError


T = TypeVar("T")


def is_retryable_error(exception: BaseException) -> bool:
    """
    Determine if an exception should be retried.

    Args:
        exception: Exception to check

    Returns:
        True if the exception is retryable
    """
    if isinstance(exception, OmegaError):
        return exception.retryable
    # Network errors, timeouts, etc are retryable
    return isinstance(exception, (ConnectionError, TimeoutError))


def create_retry_decorator(max_attempts: int = 3) -> Callable:
    """
    Create a retry decorator with SDK retry policy.

    Args:
        max_attempts: Maximum number of attempts (including initial)

    Returns:
        Retry decorator

    Example:
        >>> @create_retry_decorator(max_attempts=3)
        ... async def call_api():
        ...     # API call that may fail transiently
        ...     pass
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
