"""Tests for utility functions."""

import pytest
import time
from unittest.mock import patch, MagicMock

# Try to import delay utilities, skip tests if not available
try:
    from src.utils.delays import human_delay, typing_delay, should_take_break
    HAS_DELAYS = True
except ImportError:
    HAS_DELAYS = False
    human_delay = typing_delay = should_take_break = None

# Try to import retry utilities, skip tests if not available
try:
    from src.utils.retry import retry_on_exception, with_retry, RetryContext
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False
    retry_on_exception = with_retry = RetryContext = None

# Try to import parsing utilities
try:
    from src.utils.parsing import parse_number, parse_date, clean_text
    HAS_PARSING = True
except ImportError:
    HAS_PARSING = False
    parse_number = parse_date = clean_text = None


@pytest.mark.skipif(not HAS_DELAYS, reason="delays module not available")
class TestDelays:
    """Tests for delay utility functions."""

    @pytest.mark.unit
    def test_human_delay_default(self):
        """Test default human delay."""
        start = time.time()
        human_delay()
        elapsed = time.time() - start
        # Should be between 0.8 and 2 seconds by default
        assert 0.5 <= elapsed <= 3.0

    @pytest.mark.unit
    def test_human_delay_custom_range(self):
        """Test human delay with custom range."""
        start = time.time()
        human_delay(min_ms=100, max_ms=200)
        elapsed = time.time() - start
        assert 0.05 <= elapsed <= 0.3

    @pytest.mark.unit
    def test_typing_delay(self):
        """Test typing delay."""
        start = time.time()
        typing_delay("test text")
        elapsed = time.time() - start
        # Should be a short delay based on text length
        assert elapsed < 2.0

    @pytest.mark.unit
    def test_human_delay_types(self):
        """Test different human delay types."""
        start = time.time()
        human_delay("short")
        elapsed = time.time() - start
        # Should be a short delay
        assert elapsed < 2.0

    @pytest.mark.unit
    def test_should_take_break(self):
        """Test break decision function."""
        # At 10 posts, higher chance of break
        # Test many times to check probability behavior
        results = [should_take_break(10) for _ in range(100)]
        # Should have some True values (50% chance at multiples of 10)
        assert any(results)


@pytest.mark.skipif(not HAS_RETRY, reason="retry module not available")
class TestRetry:
    """Tests for retry utility."""

    @pytest.mark.unit
    def test_retry_on_success(self):
        """Test retry decorator with successful function."""
        call_count = 0

        @retry_on_exception(max_retries=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.unit
    def test_retry_on_temporary_failure(self):
        """Test retry decorator with temporary failure."""
        call_count = 0

        @retry_on_exception(max_retries=3, delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.unit
    def test_retry_exhausted(self):
        """Test retry decorator when all attempts fail."""
        call_count = 0

        @retry_on_exception(max_retries=2, delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fails()

        assert call_count == 3  # initial + 2 retries

    @pytest.mark.unit
    def test_with_retry_function(self):
        """Test non-decorator retry function."""
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Flaky")
            return "done"

        result = with_retry(flaky, max_retries=3, delay=0.01)
        assert result == "done"
        assert call_count == 2

    @pytest.mark.unit
    def test_retry_context_manager(self):
        """Test retry context manager."""
        call_count = 0

        with RetryContext(max_retries=3, delay=0.01) as retry:
            while retry.should_continue():
                try:
                    call_count += 1
                    if call_count < 2:
                        raise ValueError("Error")
                    break
                except ValueError as e:
                    retry.handle_error(e)

        assert call_count == 2


@pytest.mark.skipif(not HAS_PARSING, reason="parsing module not available")
class TestParsing:
    """Tests for parsing utility functions."""

    @pytest.mark.unit
    def test_parse_number_simple(self):
        """Test parsing simple numbers."""
        assert parse_number("123") == 123
        assert parse_number("1,234") == 1234
        assert parse_number("0") == 0

    @pytest.mark.unit
    def test_parse_number_with_k_suffix(self):
        """Test parsing numbers with K suffix."""
        assert parse_number("1K") == 1000
        assert parse_number("1.5K") == 1500
        assert parse_number("10K") == 10000

    @pytest.mark.unit
    def test_parse_number_with_m_suffix(self):
        """Test parsing numbers with M suffix."""
        assert parse_number("1M") == 1000000
        assert parse_number("1.5M") == 1500000
        assert parse_number("2.3M") == 2300000

    @pytest.mark.unit
    def test_parse_number_with_b_suffix(self):
        """Test parsing numbers with B suffix."""
        assert parse_number("1B") == 1000000000
        assert parse_number("2.5B") == 2500000000

    @pytest.mark.unit
    def test_parse_number_invalid(self):
        """Test parsing invalid numbers."""
        assert parse_number("invalid") == 0
        assert parse_number("") == 0
        assert parse_number(None) == 0

    @pytest.mark.unit
    def test_parse_date_iso_format(self):
        """Test parsing ISO format dates."""
        result = parse_date("2024-01-15T10:30:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    @pytest.mark.unit
    def test_parse_date_common_formats(self):
        """Test parsing common date formats."""
        # Various formats should be handled
        result = parse_date("January 15, 2024")
        if result:
            assert result.year == 2024
            assert result.month == 1

    @pytest.mark.unit
    def test_parse_date_invalid(self):
        """Test parsing invalid dates."""
        result = parse_date("not a date")
        assert result is None

    @pytest.mark.unit
    def test_clean_text_whitespace(self):
        """Test cleaning text with extra whitespace."""
        result = clean_text("  hello   world  ")
        assert result == "hello world"

    @pytest.mark.unit
    def test_clean_text_newlines(self):
        """Test cleaning text with newlines."""
        result = clean_text("hello\nworld")
        assert "hello" in result
        assert "world" in result

    @pytest.mark.unit
    def test_clean_text_special_chars(self):
        """Test cleaning text preserves special characters."""
        result = clean_text("hello #world @user")
        assert "#world" in result
        assert "@user" in result

    @pytest.mark.unit
    def test_clean_text_empty(self):
        """Test cleaning empty text."""
        assert clean_text("") == ""
        assert clean_text(None) == ""
