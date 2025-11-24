"""Event Bus for application-wide event handling and notifications.

This module provides a simple publish/subscribe pattern for:
- Progress updates during extraction
- Error notifications
- Rate limit warnings
- Completion notifications
- Custom event handling
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from weakref import WeakSet

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types for the application."""

    # Extraction lifecycle
    EXTRACTION_STARTED = "extraction.started"
    EXTRACTION_COMPLETED = "extraction.completed"
    EXTRACTION_FAILED = "extraction.failed"

    # Progress events
    POST_EXTRACTED = "post.extracted"
    COMMENTS_EXTRACTED = "comments.extracted"
    PROGRESS_UPDATE = "progress.update"

    # Rate limiting
    RATE_LIMIT_WARNING = "rate_limit.warning"
    RATE_LIMIT_DETECTED = "rate_limit.detected"
    RATE_LIMIT_RESUMED = "rate_limit.resumed"

    # Authentication
    LOGIN_STARTED = "auth.login_started"
    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILED = "auth.login_failed"

    # Storage events
    DATA_SAVED = "storage.saved"
    DATA_EXPORTED = "storage.exported"

    # Errors
    ERROR_OCCURRED = "error.occurred"
    WARNING_OCCURRED = "warning.occurred"


@dataclass
class Event:
    """Base event class containing event data."""

    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"Event({self.event_type.value}, source={self.source}, data={self.data})"


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """
    Central event bus for publish/subscribe pattern.

    Allows components to communicate without tight coupling.
    Supports both strong and weak references to handlers.

    Usage:
        bus = EventBus()

        # Subscribe to events
        def on_progress(event):
            print(f"Progress: {event.data}")

        bus.subscribe(EventType.PROGRESS_UPDATE, on_progress)

        # Publish events
        bus.publish(Event(
            event_type=EventType.PROGRESS_UPDATE,
            source="scraper",
            data={"posts": 10, "total": 100}
        ))
    """

    def __init__(self):
        """Initialize the event bus."""
        # Handlers per event type
        self._handlers: Dict[EventType, List[EventHandler]] = {}

        # Global handlers (receive all events)
        self._global_handlers: List[EventHandler] = []

        # Track subscriptions for cleanup
        self._subscription_count = 0

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> int:
        """
        Subscribe to a specific event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to handle the event

        Returns:
            Subscription ID for unsubscribing
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        self._subscription_count += 1

        logger.debug(f"Subscribed handler to {event_type.value}")
        return self._subscription_count

    def subscribe_all(self, handler: EventHandler) -> int:
        """
        Subscribe to all events.

        Args:
            handler: Callback function to handle all events

        Returns:
            Subscription ID
        """
        self._global_handlers.append(handler)
        self._subscription_count += 1

        logger.debug("Subscribed global handler")
        return self._subscription_count

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> bool:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove

        Returns:
            True if handler was found and removed
        """
        if event_type not in self._handlers:
            return False

        try:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Unsubscribed handler from {event_type.value}")
            return True
        except ValueError:
            return False

    def unsubscribe_all(self, handler: EventHandler) -> bool:
        """
        Unsubscribe a global handler.

        Args:
            handler: Handler to remove

        Returns:
            True if handler was found and removed
        """
        try:
            self._global_handlers.remove(handler)
            return True
        except ValueError:
            return False

    def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish

        Returns:
            Number of handlers that received the event
        """
        handlers_called = 0

        # Call specific handlers
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                try:
                    handler(event)
                    handlers_called += 1
                except Exception as e:
                    logger.error(f"Handler error for {event.event_type}: {e}")

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
                handlers_called += 1
            except Exception as e:
                logger.error(f"Global handler error: {e}")

        if handlers_called > 0:
            logger.debug(f"Published {event.event_type.value} to {handlers_called} handlers")

        return handlers_called

    def emit(
        self,
        event_type: EventType,
        source: str = "",
        **data
    ) -> int:
        """
        Convenience method to emit an event.

        Args:
            event_type: Type of event
            source: Source component
            **data: Event data as keyword arguments

        Returns:
            Number of handlers called
        """
        event = Event(
            event_type=event_type,
            source=source,
            data=data
        )
        return self.publish(event)

    def clear(self, event_type: Optional[EventType] = None) -> None:
        """
        Clear all handlers for an event type or all handlers.

        Args:
            event_type: Specific event type to clear, or None for all
        """
        if event_type:
            self._handlers[event_type] = []
            logger.debug(f"Cleared handlers for {event_type.value}")
        else:
            self._handlers.clear()
            self._global_handlers.clear()
            logger.debug("Cleared all handlers")

    def handler_count(self, event_type: Optional[EventType] = None) -> int:
        """
        Get the number of handlers for an event type.

        Args:
            event_type: Event type to count, or None for total

        Returns:
            Number of handlers
        """
        if event_type:
            return len(self._handlers.get(event_type, []))

        total = len(self._global_handlers)
        for handlers in self._handlers.values():
            total += len(handlers)
        return total


# =============================================================================
# CONVENIENCE CLASSES FOR COMMON PATTERNS
# =============================================================================

class ProgressTracker:
    """
    Convenience class for tracking extraction progress.

    Usage:
        tracker = ProgressTracker(bus, total_posts=100)

        for post in posts:
            process(post)
            tracker.increment()

        tracker.complete()
    """

    def __init__(
        self,
        bus: EventBus,
        total_posts: int,
        source: str = "scraper"
    ):
        """
        Initialize progress tracker.

        Args:
            bus: Event bus to publish to
            total_posts: Total number of posts expected
            source: Source component name
        """
        self.bus = bus
        self.total = total_posts
        self.current = 0
        self.source = source
        self.start_time = datetime.utcnow()

    def increment(self, count: int = 1) -> None:
        """Increment progress and emit event."""
        self.current += count
        self.bus.emit(
            EventType.PROGRESS_UPDATE,
            source=self.source,
            current=self.current,
            total=self.total,
            percentage=round((self.current / self.total) * 100, 1) if self.total > 0 else 0
        )

    def complete(self) -> None:
        """Mark extraction as complete."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        self.bus.emit(
            EventType.EXTRACTION_COMPLETED,
            source=self.source,
            total_extracted=self.current,
            elapsed_seconds=elapsed
        )

    def fail(self, error: str) -> None:
        """Mark extraction as failed."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        self.bus.emit(
            EventType.EXTRACTION_FAILED,
            source=self.source,
            extracted_before_failure=self.current,
            elapsed_seconds=elapsed,
            error=error
        )


class ConsoleHandler:
    """
    Simple handler that logs events to console.

    Useful for debugging and monitoring.
    """

    def __init__(self, event_types: Optional[List[EventType]] = None):
        """
        Initialize console handler.

        Args:
            event_types: Event types to handle (None for all)
        """
        self.event_types = set(event_types) if event_types else None

    def __call__(self, event: Event) -> None:
        """Handle event by logging to console."""
        if self.event_types and event.event_type not in self.event_types:
            return

        level = logging.INFO
        if event.event_type in (EventType.ERROR_OCCURRED, EventType.EXTRACTION_FAILED):
            level = logging.ERROR
        elif event.event_type == EventType.WARNING_OCCURRED:
            level = logging.WARNING

        logger.log(level, f"[{event.source}] {event.event_type.value}: {event.data}")


# =============================================================================
# GLOBAL EVENT BUS (optional singleton access)
# =============================================================================

_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get or create the global event bus.

    Returns:
        Global EventBus instance
    """
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def reset_event_bus() -> None:
    """Reset the global event bus (useful for testing)."""
    global _global_bus
    if _global_bus:
        _global_bus.clear()
    _global_bus = None
