"""Text parsing utilities."""

import re
import logging
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)


def parse_iso_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse ISO 8601 timestamp string to datetime object.

    Handles common variations including:
    - Z suffix (UTC): '2024-01-15T10:30:00Z'
    - Timezone offset: '2024-01-15T10:30:00+00:00'
    - With/without milliseconds

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        datetime object or None if parsing fails

    Examples:
        >>> parse_iso_timestamp('2024-01-15T10:30:00Z')
        datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> parse_iso_timestamp('2024-01-15T10:30:00.123+00:00')
        datetime(2024, 1, 15, 10, 30, 0, 123000, tzinfo=timezone.utc)
    """
    if not timestamp_str:
        return None

    try:
        # Handle Z suffix (UTC)
        normalized = timestamp_str.replace('Z', '+00:00')
        return datetime.fromisoformat(normalized)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse ISO timestamp '{timestamp_str}': {e}")
        return None


def parse_datetime_flexible(timestamp_str: str) -> Optional[datetime]:
    """
    Parse datetime from various formats.

    Tries multiple common formats in order:
    - ISO 8601 with Z suffix
    - ISO 8601 with timezone
    - ISO 8601 basic
    - Date only

    Args:
        timestamp_str: Timestamp string in various formats

    Returns:
        datetime object or None if parsing fails
    """
    if not timestamp_str:
        return None

    # Try ISO format first (most common)
    result = parse_iso_timestamp(timestamp_str)
    if result:
        return result

    # Try other common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse timestamp: {timestamp_str}")
    return None


def parse_count(text: str) -> int:
    """
    Parse follower/like counts from text (handles K, M suffixes).

    Args:
        text: Text containing a number (e.g., '1.2K', '5M', '1,234')

    Returns:
        Parsed integer count

    Examples:
        >>> parse_count('1.2K likes')
        1200
        >>> parse_count('5M followers')
        5000000
        >>> parse_count('1,234 comments')
        1234
    """
    if not text:
        return 0

    # Clean the text
    text = text.strip().lower()

    # Extract number and suffix
    match = re.search(r'([\d,.]+)\s*([kmb])?', text, re.IGNORECASE)
    if not match:
        return 0

    number_str = match.group(1).replace(',', '')
    suffix = match.group(2)

    try:
        number = float(number_str)

        # Apply multiplier based on suffix
        if suffix:
            suffix = suffix.lower()
            if suffix == 'k':
                number *= 1000
            elif suffix == 'm':
                number *= 1000000
            elif suffix == 'b':
                number *= 1000000000

        return int(number)

    except (ValueError, TypeError):
        logger.debug(f"Failed to parse count from: {text}")
        return 0


def extract_numbers(text: str) -> List[int]:
    """
    Extract all numbers from text.

    Args:
        text: Text containing numbers

    Returns:
        List of extracted integers
    """
    if not text:
        return []

    # Find all number patterns
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and special characters.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def extract_username(text: str) -> Optional[str]:
    """
    Extract username from text (handles @ prefix).

    Args:
        text: Text containing username

    Returns:
        Username without @ prefix, or None
    """
    if not text:
        return None

    # Remove @ prefix if present
    text = text.strip()
    if text.startswith('@'):
        text = text[1:]

    # Basic validation
    if re.match(r'^[\w.]+$', text):
        return text

    return None


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text.

    Args:
        text: Text containing hashtags

    Returns:
        List of hashtags without # prefix
    """
    if not text:
        return []

    hashtags = re.findall(r'#(\w+)', text)
    return hashtags


def extract_mentions(text: str) -> List[str]:
    """
    Extract @mentions from text.

    Args:
        text: Text containing mentions

    Returns:
        List of usernames without @ prefix
    """
    if not text:
        return []

    mentions = re.findall(r'@([\w.]+)', text)
    return mentions


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def parse_timestamp(text: str) -> Optional[str]:
    """
    Parse relative timestamps (e.g., '2h', '3d', '1w').

    Args:
        text: Timestamp text

    Returns:
        Standardized timestamp string or None
    """
    if not text:
        return None

    text = text.strip().lower()

    # Match patterns like '2h', '3d', '1w', '2mo'
    match = re.match(r'^(\d+)\s*(s|m|h|d|w|mo|y)', text)
    if match:
        return f"{match.group(1)}{match.group(2)}"

    return None
