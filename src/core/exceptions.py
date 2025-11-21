"""Custom exceptions for the comment extractor."""

from typing import Optional


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
