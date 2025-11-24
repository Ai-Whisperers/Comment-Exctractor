"""Event handlers that bridge EventBus to notification systems.

This module connects the Event Bus to webhook notifiers, automatically
sending notifications when important events occur.
"""

import logging
from typing import Optional, Dict, Any, List

from ..core.events import Event, EventType, EventBus, get_event_bus
from .webhooks import (
    WebhookNotifier,
    NotificationConfig,
    NotificationLevel,
    create_notifier,
)

logger = logging.getLogger(__name__)


class NotificationHandler:
    """
    Event handler that sends notifications based on extraction events.

    Maps EventBus events to notifications and sends them via
    configured notifiers.

    Usage:
        config = NotificationConfig(
            slack_webhook_url="https://hooks.slack.com/...",
        )

        handler = NotificationHandler(config)
        handler.register(get_event_bus())

        # Now events will trigger notifications
    """

    def __init__(
        self,
        config: NotificationConfig,
        notifier: Optional[WebhookNotifier] = None,
    ):
        """
        Initialize notification handler.

        Args:
            config: Notification configuration
            notifier: Custom notifier (defaults to auto-created from config)
        """
        self.config = config
        self.notifier = notifier or create_notifier(config)

        # Event type to notification mapping
        self._event_mapping: Dict[EventType, Dict[str, Any]] = {
            # Success events
            EventType.EXTRACTION_COMPLETED: {
                "level": NotificationLevel.SUCCESS,
                "title": "Extraction Completed",
                "format": self._format_extraction_completed,
            },
            EventType.LOGIN_SUCCESS: {
                "level": NotificationLevel.INFO,
                "title": "Login Successful",
                "format": self._format_login_success,
            },
            EventType.DATA_EXPORTED: {
                "level": NotificationLevel.SUCCESS,
                "title": "Data Exported",
                "format": self._format_data_exported,
            },

            # Warning events
            EventType.RATE_LIMIT_WARNING: {
                "level": NotificationLevel.WARNING,
                "title": "Rate Limit Warning",
                "format": self._format_rate_limit,
            },
            EventType.RATE_LIMIT_DETECTED: {
                "level": NotificationLevel.WARNING,
                "title": "Rate Limit Detected",
                "format": self._format_rate_limit,
            },
            EventType.WARNING_OCCURRED: {
                "level": NotificationLevel.WARNING,
                "title": "Warning",
                "format": self._format_generic,
            },

            # Error events
            EventType.EXTRACTION_FAILED: {
                "level": NotificationLevel.ERROR,
                "title": "Extraction Failed",
                "format": self._format_extraction_failed,
            },
            EventType.LOGIN_FAILED: {
                "level": NotificationLevel.ERROR,
                "title": "Login Failed",
                "format": self._format_login_failed,
            },
            EventType.ERROR_OCCURRED: {
                "level": NotificationLevel.ERROR,
                "title": "Error Occurred",
                "format": self._format_error,
            },
        }

    def register(self, bus: EventBus) -> None:
        """
        Register this handler with an event bus.

        Args:
            bus: Event bus to register with
        """
        for event_type in self._event_mapping:
            bus.subscribe(event_type, self)

        logger.info(f"Notification handler registered for {len(self._event_mapping)} event types")

    def unregister(self, bus: EventBus) -> None:
        """
        Unregister this handler from an event bus.

        Args:
            bus: Event bus to unregister from
        """
        for event_type in self._event_mapping:
            bus.unsubscribe(event_type, self)

    def __call__(self, event: Event) -> None:
        """
        Handle an event by sending a notification.

        Args:
            event: Event to handle
        """
        if event.event_type not in self._event_mapping:
            return

        mapping = self._event_mapping[event.event_type]
        level = mapping["level"]
        title = mapping["title"]
        format_fn = mapping["format"]

        # Format the message and details
        message, details = format_fn(event)

        # Add source to details
        if event.source:
            details["Source"] = event.source

        # Send notification
        try:
            self.notifier.send(
                message=message,
                level=level,
                title=title,
                details=details,
            )
        except Exception as e:
            logger.error(f"Failed to send notification for {event.event_type}: {e}")

    # =========================================================================
    # MESSAGE FORMATTERS
    # =========================================================================

    def _format_extraction_completed(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format extraction completed message."""
        data = event.data
        message = f"Extraction completed successfully"

        details = {}
        if "total_extracted" in data:
            details["Posts Extracted"] = data["total_extracted"]
        if "elapsed_seconds" in data:
            elapsed = round(data["elapsed_seconds"], 1)
            details["Duration"] = f"{elapsed}s"
        if "client" in data:
            details["Client"] = data["client"]
        if "platform" in data:
            details["Platform"] = data["platform"]
        if "account" in data:
            details["Account"] = data["account"]

        return message, details

    def _format_extraction_failed(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format extraction failed message."""
        data = event.data
        error = data.get("error", "Unknown error")
        message = f"Extraction failed: {error}"

        details = {}
        if "extracted_before_failure" in data:
            details["Extracted Before Failure"] = data["extracted_before_failure"]
        if "elapsed_seconds" in data:
            details["Duration"] = f"{round(data['elapsed_seconds'], 1)}s"
        if "client" in data:
            details["Client"] = data["client"]
        if "platform" in data:
            details["Platform"] = data["platform"]

        return message, details

    def _format_login_success(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format login success message."""
        data = event.data
        message = "Successfully logged in"

        details = {}
        if "platform" in data:
            details["Platform"] = data["platform"]

        return message, details

    def _format_login_failed(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format login failed message."""
        data = event.data
        error = data.get("error", "Unknown error")
        message = f"Login failed: {error}"

        details = {}
        if "platform" in data:
            details["Platform"] = data["platform"]
        if "reason" in data:
            details["Reason"] = data["reason"]

        return message, details

    def _format_rate_limit(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format rate limit message."""
        data = event.data
        message = "Rate limiting detected, slowing down requests"

        details = {}
        if "wait_seconds" in data:
            details["Wait Time"] = f"{data['wait_seconds']}s"
        if "platform" in data:
            details["Platform"] = data["platform"]

        return message, details

    def _format_data_exported(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format data exported message."""
        data = event.data
        message = "Data export completed"

        details = {}
        if "path" in data:
            details["Output Path"] = data["path"]
        if "format" in data:
            details["Format"] = data["format"]
        if "count" in data:
            details["Records"] = data["count"]

        return message, details

    def _format_error(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format generic error message."""
        data = event.data
        error = data.get("error", data.get("message", "Unknown error"))
        message = f"Error: {error}"

        details = {}
        if "type" in data:
            details["Error Type"] = data["type"]
        if "traceback" in data:
            details["Traceback"] = data["traceback"][:500]  # Truncate

        return message, details

    def _format_generic(self, event: Event) -> tuple[str, Dict[str, Any]]:
        """Format generic message."""
        data = event.data
        message = data.get("message", str(data))

        details = {k: v for k, v in data.items() if k != "message"}

        return message, details


def create_notification_handler(
    slack_webhook_url: Optional[str] = None,
    email_config: Optional[Dict[str, Any]] = None,
    min_level: NotificationLevel = NotificationLevel.INFO,
) -> NotificationHandler:
    """
    Create a notification handler with common configuration.

    Args:
        slack_webhook_url: Slack webhook URL
        email_config: Email configuration dict with smtp_host, email_to, etc.
        min_level: Minimum notification level

    Returns:
        Configured NotificationHandler

    Example:
        handler = create_notification_handler(
            slack_webhook_url="https://hooks.slack.com/...",
            min_level=NotificationLevel.WARNING,
        )
        handler.register(get_event_bus())
    """
    config = NotificationConfig(
        slack_webhook_url=slack_webhook_url,
        min_level=min_level,
    )

    if email_config:
        config.smtp_host = email_config.get("smtp_host")
        config.smtp_port = email_config.get("smtp_port", 587)
        config.smtp_username = email_config.get("smtp_username")
        config.smtp_password = email_config.get("smtp_password")
        config.smtp_use_tls = email_config.get("smtp_use_tls", True)
        config.email_from = email_config.get("email_from")
        config.email_to = email_config.get("email_to", [])

    return NotificationHandler(config)
