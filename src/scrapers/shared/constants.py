"""Shared constants for all scrapers."""

from typing import Dict, List


class TIMEOUTS:
    """Standard timeout values in milliseconds."""
    # Human-like interaction delays
    HUMAN_MIN = 500
    HUMAN_MAX = 1500

    # Quick checks (popup dismissal, visibility checks)
    QUICK = 300
    POPUP = 500

    # Standard waits
    SHORT_WAIT = 1000
    MEDIUM_WAIT = 2000
    LONG_WAIT = 3000

    # Element visibility
    ELEMENT_VISIBLE = 5000
    VERY_LONG_WAIT = 10000

    # Page loading
    PAGE_LOAD = 30000
    NAVIGATION = 60000

    # Rate limiting
    RATE_LIMIT_WAIT = 60000
    RATE_LIMIT_EXTRA_MIN = 60000   # 1 minute
    RATE_LIMIT_EXTRA_MAX = 180000  # 3 minutes

    # Retry delays
    RETRY_BASE = 2000
    RETRY_MAX = 60000

    # Content loading
    CONTENT_LOAD = 1500
    DYNAMIC_CONTENT = 3000


class RETRY_CONFIG:
    """Retry and failure tracking configuration."""
    NAV_RETRIES = 3
    MAX_CONSECUTIVE_FAILURES = 5
    CHECKPOINT_INTERVAL = 5


class VIEWPORTS:
    """Standard viewport configurations."""
    DEFAULT: Dict[str, int] = {"width": 1280, "height": 800}
    MOBILE: Dict[str, int] = {"width": 375, "height": 812}
    TABLET: Dict[str, int] = {"width": 768, "height": 1024}


USER_AGENTS: List[str] = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# Common Accept-Language headers
ACCEPT_LANGUAGES: List[str] = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "en-US,en;q=0.8",
    "es-PY,es;q=0.9,en;q=0.8",  # Paraguayan Spanish
]


BROWSER_ARGS: List[str] = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]
