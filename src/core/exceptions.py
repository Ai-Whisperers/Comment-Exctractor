"""Custom exceptions for the comment extractor."""

from typing import Optional, Dict, Any


class ExtractionError(Exception):
    """Base exception for extraction errors."""

    def __init__(self, message: str, platform: Optional[str] = None):
        self.message = message
        self.platform = platform
        super().__init__(self.message)


class ScraperError(ExtractionError):
    """Error during scraping."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        account_id: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, platform)
        self.account_id = account_id
        self.original_error = original_error


class StorageError(ExtractionError):
    """Error during storage operations."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.operation = operation
        self.original_error = original_error


class ExportError(ExtractionError):
    """Error during export."""

    def __init__(
        self,
        message: str,
        format: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.format = format
        self.original_error = original_error


class RateLimitError(ScraperError):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message, platform)
        self.retry_after = retry_after or 60


class AuthenticationError(ScraperError):
    """Authentication failed error."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None
    ):
        super().__init__(message, platform)


class AccountNotFoundError(ScraperError):
    """Account/page not found."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        account_id: Optional[str] = None
    ):
        super().__init__(message, platform, account_id)


class PrivateAccountError(ScraperError):
    """Account is private and cannot be scraped."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        account_id: Optional[str] = None
    ):
        super().__init__(message, platform, account_id)


class ConfigurationError(ExtractionError):
    """Configuration error."""

    def __init__(self, message: str, setting: Optional[str] = None):
        super().__init__(message)
        self.setting = setting


class ValidationError(ExtractionError):
    """Data validation error."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


# Network and Browser Errors

class NetworkError(ScraperError):
    """Network connectivity error."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, platform, original_error=original_error)
        self.url = url
        self.status_code = status_code


class TimeoutError(NetworkError):
    """Request or operation timed out."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None
    ):
        super().__init__(message, platform)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class BrowserError(ScraperError):
    """Browser automation error."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        selector: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, platform, original_error=original_error)
        self.selector = selector


class ElementNotFoundError(BrowserError):
    """Expected page element not found."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        selector: Optional[str] = None,
        page_url: Optional[str] = None
    ):
        super().__init__(message, platform, selector)
        self.page_url = page_url


class NavigationError(BrowserError):
    """Page navigation failed."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        url: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, platform, original_error=original_error)
        self.url = url


# Parsing and Data Errors

class ParsingError(ExtractionError):
    """Error parsing scraped data."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        data_type: Optional[str] = None,
        raw_data: Optional[str] = None
    ):
        super().__init__(message, platform)
        self.data_type = data_type
        self.raw_data = raw_data[:500] if raw_data and len(raw_data) > 500 else raw_data


class DateParsingError(ParsingError):
    """Error parsing date/timestamp."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        date_string: Optional[str] = None
    ):
        super().__init__(message, platform, data_type="date", raw_data=date_string)
        self.date_string = date_string


class NumberParsingError(ParsingError):
    """Error parsing numeric value."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        number_string: Optional[str] = None
    ):
        super().__init__(message, platform, data_type="number", raw_data=number_string)
        self.number_string = number_string


# Session and State Errors

class SessionError(ScraperError):
    """Session-related error."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        session_file: Optional[str] = None
    ):
        super().__init__(message, platform)
        self.session_file = session_file


class SessionExpiredError(SessionError):
    """Session has expired and needs refresh."""
    pass


class SessionCorruptedError(SessionError):
    """Session data is corrupted."""
    pass


# Content-Specific Errors

class ContentUnavailableError(ScraperError):
    """Content is unavailable (deleted, blocked, etc)."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        content_id: Optional[str] = None,
        reason: Optional[str] = None
    ):
        super().__init__(message, platform)
        self.content_type = content_type
        self.content_id = content_id
        self.reason = reason


class PostNotFoundError(ContentUnavailableError):
    """Post not found or deleted."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        post_id: Optional[str] = None
    ):
        super().__init__(message, platform, content_type="post", content_id=post_id)
        self.post_id = post_id


class CommentsDisabledError(ContentUnavailableError):
    """Comments are disabled on this content."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        post_id: Optional[str] = None
    ):
        super().__init__(
            message, platform, content_type="comments", content_id=post_id,
            reason="disabled"
        )
        self.post_id = post_id


# Proxy and Connection Errors

class ProxyError(NetworkError):
    """Proxy connection error."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        proxy_url: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, platform, original_error=original_error)
        # Mask credentials in proxy URL
        if proxy_url and "@" in proxy_url:
            parts = proxy_url.split("@")
            self.proxy_url = f"***@{parts[-1]}"
        else:
            self.proxy_url = proxy_url


# Checkpoint and Resume Errors

class CheckpointError(ExtractionError):
    """Error with checkpoint save/load."""

    def __init__(
        self,
        message: str,
        checkpoint_path: Optional[str] = None,
        operation: Optional[str] = None
    ):
        super().__init__(message)
        self.checkpoint_path = checkpoint_path
        self.operation = operation


# Helper functions for exception handling

def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error can be retried
    """
    retryable_types = (
        NetworkError,
        TimeoutError,
        RateLimitError,
        ProxyError,
    )
    return isinstance(error, retryable_types)


def get_error_context(error: Exception) -> Dict[str, Any]:
    """
    Extract context information from an exception.

    Args:
        error: The exception to extract context from

    Returns:
        Dictionary with error context
    """
    context = {
        "error_type": type(error).__name__,
        "message": str(error),
    }

    if isinstance(error, ExtractionError):
        if hasattr(error, 'platform') and error.platform:
            context["platform"] = error.platform
        if hasattr(error, 'original_error') and error.original_error:
            context["original_error"] = str(error.original_error)

    if isinstance(error, ScraperError):
        if hasattr(error, 'account_id') and error.account_id:
            context["account_id"] = error.account_id

    if isinstance(error, NetworkError):
        if hasattr(error, 'url') and error.url:
            context["url"] = error.url
        if hasattr(error, 'status_code') and error.status_code:
            context["status_code"] = error.status_code

    if isinstance(error, BrowserError):
        if hasattr(error, 'selector') and error.selector:
            context["selector"] = error.selector

    return context
