"""Centralized constants and configuration values."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TimeoutConfig:
    """Timeout configurations for browser operations."""

    # Navigation timeouts
    PAGE_LOAD: int = 30000
    NETWORK_IDLE: int = 10000
    DOM_CONTENT_LOADED: int = 15000

    # Element timeouts
    ELEMENT_VISIBLE: int = 5000
    ELEMENT_CLICK: int = 3000
    ELEMENT_FILL: int = 2000

    # Wait timeouts
    SHORT_WAIT: int = 1000
    MEDIUM_WAIT: int = 3000
    LONG_WAIT: int = 5000
    EXTENDED_WAIT: int = 10000

    # Scraping specific
    LOGIN_WAIT: int = 5000
    POST_LOAD: int = 5000
    COMMENTS_LOAD: int = 3000
    MODAL_OPEN: int = 10000
    SCROLL_DELAY: int = 2000

    # Rate limiting
    BETWEEN_POSTS: int = 2000
    BETWEEN_COMMENTS: int = 1000
    EXTENDED_BREAK: int = 30000


@dataclass
class HumanDelayConfig:
    """Human-like delay configurations."""

    # Typing delays (ms)
    TYPING_MIN: int = 50
    TYPING_MAX: int = 150

    # Action delays (ms)
    SHORT_MIN: int = 300
    SHORT_MAX: int = 700
    MEDIUM_MIN: int = 500
    MEDIUM_MAX: int = 1500
    LONG_MIN: int = 1000
    LONG_MAX: int = 3000

    # Extended breaks
    BREAK_MIN: int = 5000
    BREAK_MAX: int = 15000
    EXTENDED_BREAK_MIN: int = 30000
    EXTENDED_BREAK_MAX: int = 60000


@dataclass
class BrowserConfig:
    """Browser configuration constants."""

    # Viewport
    DEFAULT_WIDTH: int = 1280
    DEFAULT_HEIGHT: int = 800
    MOBILE_WIDTH: int = 375
    MOBILE_HEIGHT: int = 667

    # User agents
    DESKTOP_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    MOBILE_USER_AGENT: str = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    )

    # Anti-detection args
    CHROMIUM_ARGS: list = None

    def __post_init__(self):
        if self.CHROMIUM_ARGS is None:
            self.CHROMIUM_ARGS = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]


@dataclass
class ScrapingConfig:
    """Scraping behavior configuration."""

    # Limits
    MAX_POSTS_DEFAULT: int = 100
    MAX_COMMENTS_PER_POST: int = 500
    MAX_CONSECUTIVE_FAILURES: int = 5
    MAX_SAME_POST_COUNT: int = 5

    # Scroll settings
    SCROLL_INCREMENT: int = 500
    MAX_SCROLLS: int = 50

    # Extended break settings
    POSTS_BEFORE_BREAK: int = 10
    BREAK_PROBABILITY: float = 0.1


# Default instances
TIMEOUTS = TimeoutConfig()
HUMAN_DELAYS = HumanDelayConfig()
BROWSER = BrowserConfig()
SCRAPING = ScrapingConfig()


# Platform URLs
class URLs:
    """Platform URL constants."""

    class Instagram:
        BASE = "https://www.instagram.com"
        LOGIN = "https://www.instagram.com/accounts/login/"
        HOME = "https://www.instagram.com/"
        ACCOUNTS_LOGIN = "/accounts/login/"
        ACCOUNTS_SIGNUP = "/accounts/signup/"
        CHALLENGE = "/challenge/"
        CHECKPOINT = "/checkpoint/"

        @staticmethod
        def profile(username: str) -> str:
            return f"https://www.instagram.com/{username}/"

        @staticmethod
        def post(post_id: str) -> str:
            return f"https://www.instagram.com/p/{post_id}/"

    class Facebook:
        BASE = "https://www.facebook.com"
        LOGIN = "https://www.facebook.com/login"
        HOME = "https://www.facebook.com/"

        @staticmethod
        def profile(username: str) -> str:
            return f"https://www.facebook.com/{username}"

        @staticmethod
        def post(post_id: str) -> str:
            return f"https://www.facebook.com/{post_id}"
