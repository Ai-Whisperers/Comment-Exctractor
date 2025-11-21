"""Core models and protocols."""

from .models import (
    Platform,
    Author,
    Post,
    Comment,
    Profile,
    ExtractionResult,
    ExtractionStats,
    ClientConfig,
    SocialAccount,
    ExportMetadata,
)
from .protocols import ScraperProtocol, StorageProtocol, ExporterProtocol
from .exceptions import (
    ExtractionError,
    ScraperError,
    StorageError,
    ExportError,
    RateLimitError,
    AuthenticationError,
    ConfigurationError,
    PrivateAccountError,
)
from .validation import DataValidator, ValidationResult, validate_results

__all__ = [
    # Models
    "Platform",
    "Author",
    "Post",
    "Comment",
    "Profile",
    "ExtractionResult",
    "ExtractionStats",
    "ClientConfig",
    "SocialAccount",
    "ExportMetadata",
    # Protocols
    "ScraperProtocol",
    "StorageProtocol",
    "ExporterProtocol",
    # Exceptions
    "ExtractionError",
    "ScraperError",
    "StorageError",
    "ExportError",
    "RateLimitError",
    "AuthenticationError",
    "ConfigurationError",
    "PrivateAccountError",
    # Validation
    "DataValidator",
    "ValidationResult",
    "validate_results",
]
