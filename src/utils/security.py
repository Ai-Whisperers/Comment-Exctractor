"""Security utilities for credential masking and sensitive data handling."""

import re
import logging
from typing import Any, Dict, Optional


# Patterns to detect sensitive fields
SENSITIVE_PATTERNS = [
    re.compile(r'password', re.IGNORECASE),
    re.compile(r'secret', re.IGNORECASE),
    re.compile(r'token', re.IGNORECASE),
    re.compile(r'api_key', re.IGNORECASE),
    re.compile(r'apikey', re.IGNORECASE),
    re.compile(r'auth', re.IGNORECASE),
    re.compile(r'credential', re.IGNORECASE),
    re.compile(r'private', re.IGNORECASE),
]


def mask_credential(value: str, visible_chars: int = 3) -> str:
    """
    Mask a credential value, showing only first few characters.

    Args:
        value: The credential value to mask
        visible_chars: Number of characters to show at start

    Returns:
        Masked string like "abc***"
    """
    if not value:
        return ""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "***"


def mask_email(email: str) -> str:
    """
    Mask an email address.

    Args:
        email: Email address to mask

    Returns:
        Masked email like "use***@gma***.com"
    """
    if not email or "@" not in email:
        return mask_credential(email)

    local, domain = email.rsplit("@", 1)
    masked_local = mask_credential(local, 3)

    # Mask domain but keep TLD
    if "." in domain:
        domain_parts = domain.split(".")
        masked_domain = mask_credential(domain_parts[0], 3) + "." + domain_parts[-1]
    else:
        masked_domain = mask_credential(domain, 3)

    return f"{masked_local}@{masked_domain}"


def mask_url_credentials(url: str) -> str:
    """
    Mask credentials in URLs (proxy URLs, API endpoints).

    Args:
        url: URL that may contain credentials

    Returns:
        URL with masked credentials
    """
    if not url:
        return ""

    # Pattern: protocol://user:pass@host:port
    if "@" in url:
        # Split on @ to get credentials part
        parts = url.split("@")
        host_part = parts[-1]

        # Get protocol
        if "://" in parts[0]:
            protocol, creds = parts[0].split("://", 1)
            return f"{protocol}://***@{host_part}"

        return f"***@{host_part}"

    return url


def mask_dict_secrets(data: Dict[str, Any], depth: int = 0, max_depth: int = 5) -> Dict[str, Any]:
    """
    Recursively mask sensitive values in a dictionary.

    Args:
        data: Dictionary that may contain sensitive data
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        Dictionary with sensitive values masked
    """
    if depth >= max_depth:
        return data

    result = {}
    for key, value in data.items():
        # Check if key matches sensitive patterns
        is_sensitive = any(pattern.search(key) for pattern in SENSITIVE_PATTERNS)

        if is_sensitive and isinstance(value, str):
            result[key] = mask_credential(value)
        elif isinstance(value, dict):
            result[key] = mask_dict_secrets(value, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = [
                mask_dict_secrets(item, depth + 1, max_depth)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result


class SensitiveFilter(logging.Filter):
    """
    Logging filter that masks sensitive data in log messages.

    Usage:
        handler.addFilter(SensitiveFilter())
    """

    # Patterns to find and mask in log messages
    PASSWORD_PATTERNS = [
        re.compile(r'password[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r'secret[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r'token[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r'api_key[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and mask sensitive data in log record."""
        message = str(record.getMessage())

        for pattern in self.PASSWORD_PATTERNS:
            message = pattern.sub(
                lambda m: m.group(0).replace(m.group(1), mask_credential(m.group(1))),
                message
            )

        record.msg = message
        record.args = ()

        return True


def setup_secure_logging(logger_name: Optional[str] = None) -> None:
    """
    Add sensitive data filter to logger(s).

    Args:
        logger_name: Specific logger name, or None for root logger
    """
    target_logger = logging.getLogger(logger_name)
    sensitive_filter = SensitiveFilter()

    for handler in target_logger.handlers:
        handler.addFilter(sensitive_filter)

    # Also add to root logger handlers if this is the root
    if logger_name is None:
        root = logging.getLogger()
        for handler in root.handlers:
            if sensitive_filter not in handler.filters:
                handler.addFilter(sensitive_filter)
