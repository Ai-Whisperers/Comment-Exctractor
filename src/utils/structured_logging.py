"""Structured logging with correlation IDs for request tracking."""

import logging
import json
import uuid
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager
from functools import wraps

# Thread-local storage for correlation ID
_context = threading.local()


def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one."""
    if not hasattr(_context, 'correlation_id'):
        _context.correlation_id = str(uuid.uuid4())[:8]
    return _context.correlation_id


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set a new correlation ID.

    Args:
        correlation_id: Optional ID to set, or generate new one if None

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    _context.correlation_id = correlation_id
    return correlation_id


def clear_correlation_id():
    """Clear the current correlation ID."""
    if hasattr(_context, 'correlation_id'):
        delattr(_context, 'correlation_id')


@contextmanager
def correlation_context(correlation_id: Optional[str] = None):
    """
    Context manager for correlation ID scope.

    Args:
        correlation_id: Optional ID to use, or generate new one if None

    Yields:
        The correlation ID for this context
    """
    old_id = getattr(_context, 'correlation_id', None)
    new_id = set_correlation_id(correlation_id)
    try:
        yield new_id
    finally:
        if old_id is not None:
            _context.correlation_id = old_id
        else:
            clear_correlation_id()


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""

    def __init__(self, include_timestamp: bool = True, include_correlation: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_correlation = include_correlation

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if self.include_timestamp:
            log_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        if self.include_correlation:
            log_data["correlation_id"] = get_correlation_id()

        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'thread', 'threadName', 'exc_info', 'exc_text',
                'message', 'taskName',
            }:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    extra_fields[key] = value
                except (TypeError, ValueError):
                    extra_fields[key] = str(value)

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data)


class CorrelationFormatter(logging.Formatter):
    """Standard text formatter with correlation ID support."""

    def __init__(
        self,
        fmt: str = None,
        datefmt: str = None,
        include_correlation: bool = True
    ):
        if fmt is None:
            if include_correlation:
                fmt = "%(asctime)s | %(levelname)-8s | [%(correlation_id)s] | %(name)s:%(lineno)d | %(message)s"
            else:
                fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"

        if datefmt is None:
            datefmt = "%Y-%m-%d %H:%M:%S"

        super().__init__(fmt, datefmt)
        self.include_correlation = include_correlation

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with correlation ID."""
        if self.include_correlation:
            record.correlation_id = get_correlation_id()
        return super().format(record)


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that adds context to all log messages."""

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        super().__init__(logger, extra or {})

    def process(self, msg, kwargs):
        """Add context to log message."""
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        extra['correlation_id'] = get_correlation_id()
        kwargs['extra'] = extra
        return msg, kwargs

    def with_context(self, **context) -> 'ContextLogger':
        """Create a new logger with additional context."""
        new_extra = {**self.extra, **context}
        return ContextLogger(self.logger, new_extra)


def get_logger(name: str, **context) -> ContextLogger:
    """
    Get a context-aware logger.

    Args:
        name: Logger name
        **context: Additional context to include in all log messages

    Returns:
        ContextLogger instance
    """
    return ContextLogger(logging.getLogger(name), context)


def log_operation(operation: str = None, log_args: bool = False, log_result: bool = False):
    """
    Decorator to log function entry, exit, and timing.

    Args:
        operation: Operation name (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
    """
    def decorator(func):
        op_name = operation or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()

            # Log entry
            log_data = {"operation": op_name, "event": "start"}
            if log_args:
                log_data["args_count"] = len(args)
                log_data["kwargs_keys"] = list(kwargs.keys())

            logger.debug(f"Starting {op_name}", extra=log_data)

            try:
                result = func(*args, **kwargs)

                # Log success
                duration = time.time() - start_time
                log_data = {
                    "operation": op_name,
                    "event": "complete",
                    "duration_ms": round(duration * 1000, 2)
                }
                if log_result and result is not None:
                    log_data["result_type"] = type(result).__name__

                logger.debug(f"Completed {op_name} in {duration:.3f}s", extra=log_data)
                return result

            except Exception as e:
                # Log failure
                duration = time.time() - start_time
                log_data = {
                    "operation": op_name,
                    "event": "error",
                    "duration_ms": round(duration * 1000, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
                logger.error(f"Failed {op_name}: {e}", extra=log_data)
                raise

        return wrapper
    return decorator


def log_scraping_activity(
    platform: str,
    account: str,
    activity: str,
    **extra
):
    """
    Log scraping activity with standard fields.

    Args:
        platform: Platform name (instagram, facebook, etc.)
        account: Account being scraped
        activity: Activity description
        **extra: Additional context
    """
    logger = get_logger(__name__, platform=platform, account=account)
    logger.info(activity, extra={
        "activity_type": "scraping",
        **extra
    })


def log_storage_operation(
    operation: str,
    storage_type: str,
    record_count: int = 0,
    **extra
):
    """
    Log storage operation with standard fields.

    Args:
        operation: Operation name (save, load, export)
        storage_type: Storage backend type
        record_count: Number of records affected
        **extra: Additional context
    """
    logger = get_logger(__name__, storage_type=storage_type)
    logger.info(f"Storage {operation}: {record_count} records", extra={
        "activity_type": "storage",
        "operation": operation,
        "record_count": record_count,
        **extra
    })


def setup_structured_logging(
    log_level: str = "INFO",
    structured: bool = False,
    log_file: str = None,
    include_correlation: bool = True
):
    """
    Configure logging with structured output and correlation ID support.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use JSON structured output
        log_file: Optional file to write logs to
        include_correlation: Include correlation IDs in logs
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []  # Clear existing handlers

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))

    if structured:
        console_handler.setFormatter(
            StructuredFormatter(include_correlation=include_correlation)
        )
    else:
        console_handler.setFormatter(
            CorrelationFormatter(include_correlation=include_correlation)
        )

    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        # Always use structured format for file logs
        file_handler.setFormatter(
            StructuredFormatter(include_correlation=include_correlation)
        )
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# Convenience exports
__all__ = [
    'get_correlation_id',
    'set_correlation_id',
    'clear_correlation_id',
    'correlation_context',
    'StructuredFormatter',
    'CorrelationFormatter',
    'ContextLogger',
    'get_logger',
    'log_operation',
    'log_scraping_activity',
    'log_storage_operation',
    'setup_structured_logging',
]
