"""Webhook notifiers for Slack and Email.

This module provides notifiers that send messages to external services
when extraction events occur.
"""

import json
import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class NotificationConfig:
    """Configuration for notification services."""

    # Slack configuration
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_username: str = "Comment Extractor"

    # Email configuration
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)

    # General settings
    enabled: bool = True
    min_level: NotificationLevel = NotificationLevel.INFO


class WebhookNotifier(ABC):
    """Base class for webhook notifiers."""

    @abstractmethod
    def send(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a notification.

        Args:
            message: Main message text
            level: Notification severity level
            title: Optional title/subject
            details: Additional details to include

        Returns:
            True if sent successfully
        """
        pass


class SlackNotifier(WebhookNotifier):
    """Send notifications to Slack via webhook."""

    def __init__(self, config: NotificationConfig):
        """
        Initialize Slack notifier.

        Args:
            config: Notification configuration
        """
        self.webhook_url = config.slack_webhook_url
        self.channel = config.slack_channel
        self.username = config.slack_username
        self.enabled = config.enabled and bool(self.webhook_url)
        self.min_level = config.min_level

    def send(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send notification to Slack."""
        if not self.enabled:
            return False

        # Check minimum level
        level_order = [NotificationLevel.INFO, NotificationLevel.SUCCESS,
                       NotificationLevel.WARNING, NotificationLevel.ERROR]
        if level_order.index(level) < level_order.index(self.min_level):
            return False

        # Build Slack message
        color = self._get_color(level)
        emoji = self._get_emoji(level)

        attachment = {
            "color": color,
            "title": title or f"{emoji} {level.value.upper()}",
            "text": message,
            "ts": datetime.utcnow().timestamp(),
        }

        # Add fields for details
        if details:
            attachment["fields"] = [
                {"title": k, "value": str(v), "short": True}
                for k, v in details.items()
            ]

        payload = {
            "username": self.username,
            "attachments": [attachment],
        }

        if self.channel:
            payload["channel"] = self.channel

        return self._send_webhook(payload)

    def _send_webhook(self, payload: Dict[str, Any]) -> bool:
        """Send payload to Slack webhook."""
        try:
            data = json.dumps(payload).encode('utf-8')
            request = Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            with urlopen(request, timeout=10) as response:
                if response.status == 200:
                    logger.debug("Slack notification sent successfully")
                    return True
                else:
                    logger.warning(f"Slack webhook returned status {response.status}")
                    return False

        except HTTPError as e:
            logger.error(f"Slack webhook HTTP error: {e.code} - {e.reason}")
            return False
        except URLError as e:
            logger.error(f"Slack webhook URL error: {e.reason}")
            return False
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    def _get_color(self, level: NotificationLevel) -> str:
        """Get Slack attachment color for level."""
        colors = {
            NotificationLevel.INFO: "#2196F3",      # Blue
            NotificationLevel.SUCCESS: "#4CAF50",   # Green
            NotificationLevel.WARNING: "#FFC107",   # Amber
            NotificationLevel.ERROR: "#F44336",     # Red
        }
        return colors.get(level, "#9E9E9E")

    def _get_emoji(self, level: NotificationLevel) -> str:
        """Get emoji for notification level."""
        emojis = {
            NotificationLevel.INFO: "info",
            NotificationLevel.SUCCESS: "white_check_mark",
            NotificationLevel.WARNING: "warning",
            NotificationLevel.ERROR: "x",
        }
        return f":{emojis.get(level, 'bell')}:"


class EmailNotifier(WebhookNotifier):
    """Send notifications via email."""

    def __init__(self, config: NotificationConfig):
        """
        Initialize email notifier.

        Args:
            config: Notification configuration
        """
        self.smtp_host = config.smtp_host
        self.smtp_port = config.smtp_port
        self.smtp_username = config.smtp_username
        self.smtp_password = config.smtp_password
        self.use_tls = config.smtp_use_tls
        self.email_from = config.email_from
        self.email_to = config.email_to
        self.min_level = config.min_level

        self.enabled = (
            config.enabled and
            bool(self.smtp_host) and
            bool(self.email_from) and
            len(self.email_to) > 0
        )

    def send(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send notification via email."""
        if not self.enabled:
            return False

        # Check minimum level
        level_order = [NotificationLevel.INFO, NotificationLevel.SUCCESS,
                       NotificationLevel.WARNING, NotificationLevel.ERROR]
        if level_order.index(level) < level_order.index(self.min_level):
            return False

        # Build email
        subject = title or f"[{level.value.upper()}] Comment Extractor Notification"

        # Create HTML body
        body_html = self._build_html_body(message, level, details)
        body_text = self._build_text_body(message, level, details)

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = ', '.join(self.email_to)

        msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        return self._send_email(msg)

    def _send_email(self, msg: MIMEMultipart) -> bool:
        """Send email via SMTP."""
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.sendmail(
                self.email_from,
                self.email_to,
                msg.as_string()
            )
            server.quit()

            logger.debug(f"Email notification sent to {self.email_to}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    def _build_html_body(
        self,
        message: str,
        level: NotificationLevel,
        details: Optional[Dict[str, Any]]
    ) -> str:
        """Build HTML email body."""
        color = self._get_color(level)

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 15px;">
                <h2 style="color: {color}; margin-top: 0;">
                    {level.value.upper()}
                </h2>
                <p style="font-size: 16px;">{message}</p>
        """

        if details:
            html += """
                <table style="border-collapse: collapse; margin-top: 15px;">
            """
            for key, value in details.items():
                html += f"""
                    <tr>
                        <td style="padding: 5px 10px 5px 0; font-weight: bold;">{key}:</td>
                        <td style="padding: 5px 0;">{value}</td>
                    </tr>
                """
            html += "</table>"

        html += f"""
            </div>
            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                Sent by Comment Extractor at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </p>
        </body>
        </html>
        """

        return html

    def _build_text_body(
        self,
        message: str,
        level: NotificationLevel,
        details: Optional[Dict[str, Any]]
    ) -> str:
        """Build plain text email body."""
        text = f"{level.value.upper()}\n\n{message}\n"

        if details:
            text += "\nDetails:\n"
            for key, value in details.items():
                text += f"  {key}: {value}\n"

        text += f"\nSent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"

        return text

    def _get_color(self, level: NotificationLevel) -> str:
        """Get color for notification level."""
        colors = {
            NotificationLevel.INFO: "#2196F3",
            NotificationLevel.SUCCESS: "#4CAF50",
            NotificationLevel.WARNING: "#FFC107",
            NotificationLevel.ERROR: "#F44336",
        }
        return colors.get(level, "#9E9E9E")


class CompositeNotifier(WebhookNotifier):
    """Composite notifier that sends to multiple channels."""

    def __init__(self, notifiers: List[WebhookNotifier]):
        """
        Initialize composite notifier.

        Args:
            notifiers: List of notifiers to use
        """
        self.notifiers = notifiers

    def send(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send notification to all configured channels."""
        success = False

        for notifier in self.notifiers:
            try:
                if notifier.send(message, level, title, details):
                    success = True
            except Exception as e:
                logger.error(f"Notifier {type(notifier).__name__} failed: {e}")

        return success

    def add_notifier(self, notifier: WebhookNotifier) -> None:
        """Add a notifier to the composite."""
        self.notifiers.append(notifier)


def create_notifier(config: NotificationConfig) -> WebhookNotifier:
    """
    Create a composite notifier based on configuration.

    Args:
        config: Notification configuration

    Returns:
        Configured notifier (composite if multiple channels)
    """
    notifiers = []

    if config.slack_webhook_url:
        notifiers.append(SlackNotifier(config))

    if config.smtp_host and config.email_to:
        notifiers.append(EmailNotifier(config))

    if len(notifiers) == 0:
        logger.warning("No notification channels configured")
        return CompositeNotifier([])
    elif len(notifiers) == 1:
        return notifiers[0]
    else:
        return CompositeNotifier(notifiers)
