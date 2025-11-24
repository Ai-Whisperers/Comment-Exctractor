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
    ValidationError,
)
from .validation import DataValidator, ValidationResult, validate_results
from .events import (
    EventBus,
    EventType,
    Event,
    ProgressTracker,
    ConsoleHandler,
    get_event_bus,
    reset_event_bus,
)

# Lazy imports for container to avoid circular dependencies
def __getattr__(name):
    """Lazy import for Container-related exports."""
    if name in ("Container", "get_container", "reset_container", "configure_container"):
        from .container import Container, get_container, reset_container, configure_container
        globals()["Container"] = Container
        globals()["get_container"] = get_container
        globals()["reset_container"] = reset_container
        globals()["configure_container"] = configure_container
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
    "ValidationError",
    # Validation
    "DataValidator",
    "ValidationResult",
    "validate_results",
    # Container
    "Container",
    "get_container",
    "reset_container",
    "configure_container",
    # Events
    "EventBus",
    "EventType",
    "Event",
    "ProgressTracker",
    "ConsoleHandler",
    "get_event_bus",
    "reset_event_bus",
]
