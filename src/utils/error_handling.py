"""
Error categorization and handling utilities.
"""

import logging
import time
import random
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    NOT_FOUND = "not_found"
    BROWSER = "browser"
    UNKNOWN = "unknown"


def categorize_error(error: Exception) -> ErrorCategory:
    """Categorize an exception for appropriate handling."""
    error_msg = str(error).lower()
    error_type = type(error).__name__.lower()

    # Timeout errors
    if "timeout" in error_msg or "timeout" in error_type:
        return ErrorCategory.TIMEOUT

    # Rate limiting
    if any(term in error_msg for term in ["rate limit", "too many", "429", "throttl"]):
        return ErrorCategory.RATE_LIMIT

    # Network errors
    if any(term in error_msg for term in ["net::", "connection", "network", "dns", "socket"]):
        return ErrorCategory.NETWORK

    # Authentication
    if any(term in error_msg for term in ["login", "auth", "credential", "password", "401", "403"]):
        return ErrorCategory.AUTH

    # Not found
    if any(term in error_msg for term in ["not found", "404", "does not exist", "no such"]):
        return ErrorCategory.NOT_FOUND

    # Browser issues
    if any(term in error_msg for term in ["browser", "page", "context", "target closed", "crashed"]):
        return ErrorCategory.BROWSER

    return ErrorCategory.UNKNOWN


class RetryStrategy:
    """Smart retry with error-specific strategies."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._strategies = {
            ErrorCategory.NETWORK: self._retry_network,
            ErrorCategory.TIMEOUT: self._retry_timeout,
            ErrorCategory.RATE_LIMIT: self._retry_rate_limit,
            ErrorCategory.BROWSER: self._retry_browser,
        }

    def should_retry(self, error: Exception, attempt: int) -> tuple:
        """
        Determine if should retry and how long to wait.

        Returns: (should_retry, wait_seconds)
        """
        if attempt >= self.max_retries:
            return False, 0

        category = categorize_error(error)
        strategy = self._strategies.get(category)

        if strategy:
            return strategy(attempt)

        # Default: no retry for unknown errors
        return False, 0

    def _retry_network(self, attempt: int) -> tuple:
        """Network errors: exponential backoff."""
        wait = min(5 * (2 ** attempt), 60)
        logger.info(f"Network error, retrying in {wait}s (attempt {attempt + 1})")
        return True, wait

    def _retry_timeout(self, attempt: int) -> tuple:
        """Timeout: longer waits."""
        wait = min(10 * (attempt + 1), 60)
        logger.info(f"Timeout, retrying in {wait}s (attempt {attempt + 1})")
        return True, wait

    def _retry_rate_limit(self, attempt: int) -> tuple:
        """Rate limit: long wait with jitter."""
        base_wait = 60 * (attempt + 1)
        jitter = random.uniform(0, 30)
        wait = min(base_wait + jitter, 300)
        logger.warning(f"Rate limited, waiting {wait:.0f}s (attempt {attempt + 1})")
        return True, wait

    def _retry_browser(self, attempt: int) -> tuple:
        """Browser issues: moderate wait."""
        wait = 5 * (attempt + 1)
        logger.warning(f"Browser error, retrying in {wait}s (attempt {attempt + 1})")
        return True, wait


def with_retry(max_retries: int = 3):
    """Decorator for automatic retry with smart strategy."""
    strategy = RetryStrategy(max_retries)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    should_retry, wait_time = strategy.should_retry(e, attempt)

                    if should_retry:
                        time.sleep(wait_time)
                    else:
                        break

            raise last_error

        return wrapper
    return decorator
