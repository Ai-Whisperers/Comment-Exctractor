"""Security utilities for credential masking, path validation, and sensitive data handling."""

import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.exceptions import ValidationError


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


# =============================================================================
# Path Validation and Sanitization
# =============================================================================

# Pattern for valid names (client, account, platform)
VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')

# Dangerous path patterns
DANGEROUS_PATH_PATTERNS = [
    '..',           # Parent directory traversal
    '~',            # Home directory expansion
    '//',           # UNC paths or root paths
    '\\\\',         # Windows UNC paths
]

# Reserved Windows filenames
WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}


def validate_safe_path(base_dir: Path, target_path: Path) -> bool:
    """
    Validate that target_path is safely within base_dir.

    Prevents path traversal attacks (e.g., ../../etc/passwd).

    Args:
        base_dir: Base directory that should contain the target
        target_path: Path to validate

    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve to absolute paths
        base_resolved = base_dir.resolve()
        target_resolved = target_path.resolve()

        # Check if target is within base using common path
        common = os.path.commonpath([str(base_resolved), str(target_resolved)])
        return common == str(base_resolved)
    except (ValueError, OSError):
        return False


def validate_name(value: str, field_name: str) -> None:
    """
    Validate client/account names to prevent path traversal and injection.

    Args:
        value: The value to validate
        field_name: Field name for error messages

    Raises:
        ValidationError: If value is invalid
    """
    if not value:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name)

    if len(value) > 100:
        raise ValidationError(
            f"{field_name} too long (max 100 characters)",
            field=field_name
        )

    if not VALID_NAME_PATTERN.match(value):
        raise ValidationError(
            f"Invalid {field_name}: '{value}'. "
            f"Only alphanumeric, underscore, hyphen, and dot allowed.",
            field=field_name
        )

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATH_PATTERNS:
        if pattern in value:
            raise ValidationError(
                f"Invalid characters in {field_name}: '{value}'",
                field=field_name
            )

    # Check for absolute paths
    if value.startswith('/') or value.startswith('\\'):
        raise ValidationError(
            f"{field_name} cannot start with path separator",
            field=field_name
        )

    # Check Windows reserved names
    name_upper = value.upper().split('.')[0]
    if name_upper in WINDOWS_RESERVED:
        raise ValidationError(
            f"{field_name} '{value}' is a reserved name",
            field=field_name
        )


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename to prevent path traversal and invalid characters.

    Args:
        name: Filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    # Replace .. with underscore
    sanitized = sanitized.replace('..', '_')
    # Prevent empty names
    if not sanitized:
        sanitized = 'unnamed'
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]

    # Check for reserved Windows names
    name_upper = sanitized.upper().split('.')[0]
    if name_upper in WINDOWS_RESERVED:
        sanitized = f"_{sanitized}"

    return sanitized


def sanitize_path_component(name: str) -> str:
    """
    Sanitize a single path component (directory or filename).

    More restrictive than sanitize_filename - only allows alphanumeric,
    underscore, hyphen, and dot.

    Args:
        name: Component name to sanitize

    Returns:
        Sanitized name
    """
    # Keep only safe characters
    sanitized = name.lower().strip()
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ', '..']:
        sanitized = sanitized.replace(char, '_')

    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')

    if not sanitized:
        sanitized = 'unnamed'

    # Check for reserved Windows names
    name_upper = sanitized.upper().split('.')[0]
    if name_upper in WINDOWS_RESERVED:
        sanitized = f"_{sanitized}"

    return sanitized


def validate_path_no_traversal(path: str, field_name: str = "path") -> None:
    """
    Validate that a path string contains no traversal attempts.

    Args:
        path: Path string to validate
        field_name: Field name for error messages

    Raises:
        ValidationError: If path contains traversal attempts
    """
    if not path:
        return

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATH_PATTERNS:
        if pattern in path:
            raise ValidationError(
                f"{field_name} cannot contain '{pattern}'",
                field=field_name
            )


def ensure_path_within_base(
    base_dir: Path,
    target_path: Path,
    field_name: str = "path"
) -> Path:
    """
    Ensure target path is within base directory, return resolved path.

    Args:
        base_dir: Base directory
        target_path: Target path to validate
        field_name: Field name for error messages

    Returns:
        Resolved safe path

    Raises:
        ValidationError: If path escapes base directory
    """
    if not validate_safe_path(base_dir, target_path):
        raise ValidationError(
            f"{field_name} escapes base directory: {target_path}",
            field=field_name
        )

    return target_path.resolve()


def create_safe_path(
    base_dir: Path,
    *components: str,
    ensure_exists: bool = False
) -> Path:
    """
    Create a safe path by sanitizing all components.

    Args:
        base_dir: Base directory
        *components: Path components to join
        ensure_exists: Create directories if True

    Returns:
        Safe, sanitized path

    Raises:
        ValidationError: If resulting path escapes base
    """
    # Sanitize all components
    safe_components = [sanitize_path_component(c) for c in components]

    # Build path
    result = base_dir
    for component in safe_components:
        result = result / component

    # Validate final path
    if not validate_safe_path(base_dir, result):
        raise ValidationError(
            f"Path escapes base directory: {result}",
            field="path"
        )

    # Create if requested
    if ensure_exists:
        result.parent.mkdir(parents=True, exist_ok=True)

    return result
