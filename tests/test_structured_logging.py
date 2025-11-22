"""Tests for structured logging with correlation IDs."""

import pytest
import logging
import json
import threading
from io import StringIO

from src.utils.structured_logging import (
    get_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    correlation_context,
    StructuredFormatter,
    CorrelationFormatter,
    ContextLogger,
    get_logger,
    log_operation,
    log_scraping_activity,
    log_storage_operation,
    setup_structured_logging,
)


class TestCorrelationId:
    """Tests for correlation ID management."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_get_correlation_id_generates_new(self):
        """Test get_correlation_id generates new ID if none exists."""
        cid = get_correlation_id()
        assert cid is not None
        assert len(cid) == 8

    def test_get_correlation_id_returns_same(self):
        """Test get_correlation_id returns same ID on repeated calls."""
        cid1 = get_correlation_id()
        cid2 = get_correlation_id()
        assert cid1 == cid2

    def test_set_correlation_id_custom(self):
        """Test setting custom correlation ID."""
        custom_id = "test1234"
        result = set_correlation_id(custom_id)
        assert result == custom_id
        assert get_correlation_id() == custom_id

    def test_set_correlation_id_generates(self):
        """Test set_correlation_id generates new ID when None."""
        result = set_correlation_id(None)
        assert len(result) == 8
        assert get_correlation_id() == result

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test")
        clear_correlation_id()
        # Should generate new ID
        new_id = get_correlation_id()
        assert new_id != "test"

    def test_correlation_id_thread_isolation(self):
        """Test correlation IDs are thread-local."""
        results = {}

        def thread_func(thread_id):
            cid = set_correlation_id(f"thread{thread_id}")
            # Small delay to ensure overlap
            import time
            time.sleep(0.01)
            results[thread_id] = get_correlation_id()

        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_func, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread should have its own ID
        assert results[0] == "thread0"
        assert results[1] == "thread1"
        assert results[2] == "thread2"


class TestCorrelationContext:
    """Tests for correlation_context context manager."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_correlation_context_sets_id(self):
        """Test context manager sets correlation ID."""
        with correlation_context("context1") as cid:
            assert cid == "context1"
            assert get_correlation_id() == "context1"

    def test_correlation_context_generates_id(self):
        """Test context manager generates ID when None."""
        with correlation_context() as cid:
            assert len(cid) == 8
            assert get_correlation_id() == cid

    def test_correlation_context_restores_previous(self):
        """Test context manager restores previous ID."""
        set_correlation_id("original")

        with correlation_context("nested"):
            assert get_correlation_id() == "nested"

        assert get_correlation_id() == "original"

    def test_correlation_context_clears_when_no_previous(self):
        """Test context manager clears ID when no previous."""
        with correlation_context("temp") as cid:
            assert cid == "temp"

        # Should generate new ID since none was set before
        new_id = get_correlation_id()
        assert new_id != "temp"

    def test_nested_correlation_contexts(self):
        """Test nested correlation contexts work correctly."""
        with correlation_context("outer") as outer_id:
            assert outer_id == "outer"

            with correlation_context("inner") as inner_id:
                assert inner_id == "inner"
                assert get_correlation_id() == "inner"

            assert get_correlation_id() == "outer"


class TestStructuredFormatter:
    """Tests for StructuredFormatter."""

    def test_basic_format(self):
        """Test basic structured log formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert "correlation_id" in data
        assert data["location"]["file"] == "test.py"
        assert data["location"]["line"] == 42

    def test_format_with_args(self):
        """Test formatting with message arguments."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Value is %d",
            args=(42,),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "Value is 42"

    def test_format_without_timestamp(self):
        """Test formatting without timestamp."""
        formatter = StructuredFormatter(include_timestamp=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "timestamp" not in data

    def test_format_without_correlation(self):
        """Test formatting without correlation ID."""
        formatter = StructuredFormatter(include_correlation=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "correlation_id" not in data

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.custom_field = "custom_value"
        record.numeric_field = 123

        output = formatter.format(record)
        data = json.loads(output)

        assert data["extra"]["custom_field"] == "custom_value"
        assert data["extra"]["numeric_field"] == 123


class TestCorrelationFormatter:
    """Tests for CorrelationFormatter."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_format_with_correlation(self):
        """Test formatting includes correlation ID."""
        set_correlation_id("test123")
        formatter = CorrelationFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        assert "[test123]" in output
        assert "Test message" in output

    def test_format_without_correlation(self):
        """Test formatting without correlation ID."""
        formatter = CorrelationFormatter(include_correlation=False)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        assert "correlation_id" not in output


class TestContextLogger:
    """Tests for ContextLogger."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_context_logger_creation(self):
        """Test creating a context logger."""
        logger = get_logger("test", key="value")
        assert isinstance(logger, ContextLogger)

    def test_context_logger_adds_context(self):
        """Test context logger adds context to messages."""
        base_logger = logging.getLogger("test")
        context_logger = ContextLogger(base_logger, {"platform": "instagram"})

        # Should have platform in extra
        assert context_logger.extra["platform"] == "instagram"

    def test_with_context_creates_new_logger(self):
        """Test with_context creates new logger with additional context."""
        logger1 = get_logger("test", key1="value1")
        logger2 = logger1.with_context(key2="value2")

        assert logger1.extra["key1"] == "value1"
        assert "key2" not in logger1.extra

        assert logger2.extra["key1"] == "value1"
        assert logger2.extra["key2"] == "value2"


class TestLogOperation:
    """Tests for log_operation decorator."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_log_operation_basic(self):
        """Test log_operation decorator basic usage."""
        @log_operation()
        def test_func():
            return "result"

        result = test_func()
        assert result == "result"

    def test_log_operation_with_name(self):
        """Test log_operation decorator with custom name."""
        @log_operation(operation="custom_operation")
        def test_func():
            return "result"

        result = test_func()
        assert result == "result"

    def test_log_operation_with_args(self):
        """Test log_operation decorator logging arguments."""
        @log_operation(log_args=True)
        def test_func(a, b, c=None):
            return a + b

        result = test_func(1, 2, c=3)
        assert result == 3

    def test_log_operation_with_exception(self):
        """Test log_operation decorator handles exceptions."""
        @log_operation()
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError) as exc:
            failing_func()
        assert "Test error" in str(exc.value)


class TestLoggingHelpers:
    """Tests for logging helper functions."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_log_scraping_activity(self):
        """Test log_scraping_activity function."""
        # Should not raise
        log_scraping_activity(
            platform="instagram",
            account="testuser",
            activity="Extracted 10 posts"
        )

    def test_log_storage_operation(self):
        """Test log_storage_operation function."""
        # Should not raise
        log_storage_operation(
            operation="save",
            storage_type="json",
            record_count=100
        )


class TestSetupStructuredLogging:
    """Tests for setup_structured_logging function."""

    def test_setup_basic(self):
        """Test basic logging setup."""
        setup_structured_logging(log_level="DEBUG")

        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1

    def test_setup_structured(self):
        """Test structured logging setup."""
        setup_structured_logging(log_level="INFO", structured=True)

        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)

    def test_setup_with_correlation(self):
        """Test setup with correlation formatter."""
        setup_structured_logging(log_level="INFO", structured=False)

        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, CorrelationFormatter)


class TestIntegration:
    """Integration tests for structured logging."""

    def setup_method(self):
        """Clear correlation ID and setup logging."""
        clear_correlation_id()

    def test_full_workflow(self):
        """Test complete logging workflow."""
        # Setup
        set_correlation_id("workflow1")

        # Create context logger
        logger = get_logger("test.integration", platform="instagram")

        # Use within operation
        @log_operation(operation="fetch_posts")
        def fetch_posts():
            return ["post1", "post2"]

        # Execute
        with correlation_context("workflow1"):
            posts = fetch_posts()

        assert posts == ["post1", "post2"]

    def test_nested_contexts_with_logging(self):
        """Test logging in nested correlation contexts."""
        captured = []

        # Custom handler to capture logs
        handler = logging.Handler()
        handler.emit = lambda record: captured.append(record)

        logger = logging.getLogger("test.nested")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            with correlation_context("outer"):
                logger.info("Outer start")

                with correlation_context("inner"):
                    logger.info("Inner")

                logger.info("Outer end")

            # Verify correlation IDs were correct
            assert len(captured) == 3
        finally:
            logger.removeHandler(handler)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_empty_correlation_id(self):
        """Test handling of empty string correlation ID."""
        # Empty string is allowed but unusual
        set_correlation_id("")
        assert get_correlation_id() == ""

    def test_unicode_correlation_id(self):
        """Test handling of unicode in correlation ID."""
        unicode_id = "test-\u2603"
        set_correlation_id(unicode_id)
        assert get_correlation_id() == unicode_id

    def test_large_extra_data(self):
        """Test formatter handles large extra data."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.large_list = list(range(1000))

        output = formatter.format(record)
        data = json.loads(output)

        assert len(data["extra"]["large_list"]) == 1000

    def test_non_serializable_extra(self):
        """Test formatter handles non-JSON-serializable extras."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.non_serializable = object()

        output = formatter.format(record)
        data = json.loads(output)

        # Should be converted to string
        assert "object at" in data["extra"]["non_serializable"]

    def test_concurrent_correlation_ids(self):
        """Test concurrent access to correlation IDs."""
        results = {}
        barrier = threading.Barrier(5)

        def worker(thread_id):
            barrier.wait()  # Synchronize start
            set_correlation_id(f"t{thread_id}")

            # Verify our ID wasn't overwritten
            for _ in range(100):
                if get_correlation_id() != f"t{thread_id}":
                    results[thread_id] = False
                    return

            results[thread_id] = True

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should have maintained their own ID
        assert all(results.values())
