"""Tests for custom exception types."""

import pytest

from src.core.exceptions import (
    # Base exceptions
    ExtractionError,
    ScraperError,
    StorageError,
    ExportError,
    ValidationError,
    ConfigurationError,
    # Rate limiting
    RateLimitError,
    # Authentication
    AuthenticationError,
    AccountNotFoundError,
    PrivateAccountError,
    # Network and Browser
    NetworkError,
    TimeoutError,
    BrowserError,
    ElementNotFoundError,
    NavigationError,
    # Parsing
    ParsingError,
    DateParsingError,
    NumberParsingError,
    # Session
    SessionError,
    SessionExpiredError,
    SessionCorruptedError,
    # Content
    ContentUnavailableError,
    PostNotFoundError,
    CommentsDisabledError,
    # Proxy
    ProxyError,
    # Checkpoint
    CheckpointError,
    # Helper functions
    is_retryable_error,
    get_error_context,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_scraper_error_inherits_from_extraction_error(self):
        """Test ScraperError inherits from ExtractionError."""
        error = ScraperError("test")
        assert isinstance(error, ExtractionError)

    def test_network_error_inherits_from_scraper_error(self):
        """Test NetworkError inherits from ScraperError."""
        error = NetworkError("test")
        assert isinstance(error, ScraperError)
        assert isinstance(error, ExtractionError)

    def test_browser_error_inherits_from_scraper_error(self):
        """Test BrowserError inherits from ScraperError."""
        error = BrowserError("test")
        assert isinstance(error, ScraperError)

    def test_parsing_error_inherits_from_extraction_error(self):
        """Test ParsingError inherits from ExtractionError."""
        error = ParsingError("test")
        assert isinstance(error, ExtractionError)

    def test_session_error_inherits_from_scraper_error(self):
        """Test SessionError inherits from ScraperError."""
        error = SessionError("test")
        assert isinstance(error, ScraperError)


class TestNetworkErrors:
    """Tests for network-related exceptions."""

    def test_network_error_stores_url(self):
        """Test NetworkError stores URL."""
        error = NetworkError(
            "Connection failed",
            url="https://example.com",
            status_code=500
        )
        assert error.url == "https://example.com"
        assert error.status_code == 500

    def test_timeout_error_stores_details(self):
        """Test TimeoutError stores timeout details."""
        error = TimeoutError(
            "Request timed out",
            platform="instagram",
            timeout_seconds=30.0,
            operation="page_load"
        )
        assert error.timeout_seconds == 30.0
        assert error.operation == "page_load"
        assert error.platform == "instagram"

    def test_proxy_error_masks_credentials(self):
        """Test ProxyError masks proxy credentials."""
        error = ProxyError(
            "Proxy failed",
            proxy_url="http://user:password@proxy.com:8080"
        )
        assert "password" not in error.proxy_url
        assert "***@proxy.com:8080" in error.proxy_url

    def test_proxy_error_preserves_url_without_credentials(self):
        """Test ProxyError preserves URL without credentials."""
        error = ProxyError(
            "Proxy failed",
            proxy_url="http://proxy.com:8080"
        )
        assert error.proxy_url == "http://proxy.com:8080"


class TestBrowserErrors:
    """Tests for browser automation exceptions."""

    def test_element_not_found_stores_selector(self):
        """Test ElementNotFoundError stores selector info."""
        error = ElementNotFoundError(
            "Element not found",
            selector="div.post-content",
            page_url="https://instagram.com/p/123"
        )
        assert error.selector == "div.post-content"
        assert error.page_url == "https://instagram.com/p/123"

    def test_navigation_error_stores_url(self):
        """Test NavigationError stores URL."""
        error = NavigationError(
            "Navigation failed",
            url="https://instagram.com/test"
        )
        assert error.url == "https://instagram.com/test"


class TestParsingErrors:
    """Tests for parsing exceptions."""

    def test_parsing_error_truncates_raw_data(self):
        """Test ParsingError truncates long raw data."""
        long_data = "x" * 1000
        error = ParsingError(
            "Parse failed",
            raw_data=long_data
        )
        assert len(error.raw_data) == 500

    def test_date_parsing_error_stores_string(self):
        """Test DateParsingError stores date string."""
        error = DateParsingError(
            "Invalid date",
            date_string="not-a-date"
        )
        assert error.date_string == "not-a-date"
        assert error.data_type == "date"

    def test_number_parsing_error_stores_string(self):
        """Test NumberParsingError stores number string."""
        error = NumberParsingError(
            "Invalid number",
            number_string="1,234K"
        )
        assert error.number_string == "1,234K"
        assert error.data_type == "number"


class TestContentErrors:
    """Tests for content-related exceptions."""

    def test_post_not_found_stores_post_id(self):
        """Test PostNotFoundError stores post ID."""
        error = PostNotFoundError(
            "Post not found",
            post_id="ABC123"
        )
        assert error.post_id == "ABC123"
        assert error.content_type == "post"

    def test_comments_disabled_stores_details(self):
        """Test CommentsDisabledError stores details."""
        error = CommentsDisabledError(
            "Comments disabled",
            post_id="XYZ789"
        )
        assert error.post_id == "XYZ789"
        assert error.reason == "disabled"
        assert error.content_type == "comments"


class TestSessionErrors:
    """Tests for session-related exceptions."""

    def test_session_error_stores_file_path(self):
        """Test SessionError stores session file path."""
        error = SessionError(
            "Session error",
            session_file="/path/to/session.json"
        )
        assert error.session_file == "/path/to/session.json"

    def test_session_expired_inherits_from_session_error(self):
        """Test SessionExpiredError inherits from SessionError."""
        error = SessionExpiredError("Session expired")
        assert isinstance(error, SessionError)

    def test_session_corrupted_inherits_from_session_error(self):
        """Test SessionCorruptedError inherits from SessionError."""
        error = SessionCorruptedError("Session corrupted")
        assert isinstance(error, SessionError)


class TestHelperFunctions:
    """Tests for exception helper functions."""

    def test_is_retryable_network_error(self):
        """Test NetworkError is retryable."""
        error = NetworkError("Connection failed")
        assert is_retryable_error(error) is True

    def test_is_retryable_timeout_error(self):
        """Test TimeoutError is retryable."""
        error = TimeoutError("Timed out")
        assert is_retryable_error(error) is True

    def test_is_retryable_rate_limit_error(self):
        """Test RateLimitError is retryable."""
        error = RateLimitError("Rate limited")
        assert is_retryable_error(error) is True

    def test_is_retryable_proxy_error(self):
        """Test ProxyError is retryable."""
        error = ProxyError("Proxy failed")
        assert is_retryable_error(error) is True

    def test_is_not_retryable_auth_error(self):
        """Test AuthenticationError is not retryable."""
        error = AuthenticationError("Auth failed")
        assert is_retryable_error(error) is False

    def test_is_not_retryable_validation_error(self):
        """Test ValidationError is not retryable."""
        error = ValidationError("Invalid data")
        assert is_retryable_error(error) is False

    def test_get_error_context_basic(self):
        """Test get_error_context returns basic info."""
        error = ExtractionError("Test error")
        context = get_error_context(error)

        assert context["error_type"] == "ExtractionError"
        assert context["message"] == "Test error"

    def test_get_error_context_with_platform(self):
        """Test get_error_context includes platform."""
        error = ScraperError("Test", platform="instagram")
        context = get_error_context(error)

        assert context["platform"] == "instagram"

    def test_get_error_context_with_network_details(self):
        """Test get_error_context includes network details."""
        error = NetworkError(
            "Failed",
            url="https://example.com",
            status_code=404
        )
        context = get_error_context(error)

        assert context["url"] == "https://example.com"
        assert context["status_code"] == 404

    def test_get_error_context_with_browser_details(self):
        """Test get_error_context includes browser details."""
        error = BrowserError(
            "Element not found",
            selector="div.content"
        )
        context = get_error_context(error)

        assert context["selector"] == "div.content"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_default_retry_after(self):
        """Test default retry_after value."""
        error = RateLimitError("Rate limited")
        assert error.retry_after == 60

    def test_rate_limit_custom_retry_after(self):
        """Test custom retry_after value."""
        error = RateLimitError("Rate limited", retry_after=120)
        assert error.retry_after == 120


class TestCheckpointError:
    """Tests for CheckpointError."""

    def test_checkpoint_error_stores_details(self):
        """Test CheckpointError stores details."""
        error = CheckpointError(
            "Checkpoint failed",
            checkpoint_path="/path/to/checkpoint.json",
            operation="save"
        )
        assert error.checkpoint_path == "/path/to/checkpoint.json"
        assert error.operation == "save"

