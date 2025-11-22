"""Shared scraper components."""

from .base_page import BasePage
from .browser_factory import BrowserFactory
from .browser_manager import BrowserManager, BrowserConfig, create_browser_manager
from .constants import TIMEOUTS, USER_AGENTS, VIEWPORTS, ACCEPT_LANGUAGES, BROWSER_ARGS
from .rate_limiting import (
    RateLimitDetector,
    RateLimitHandler,
    FacebookRateLimitDetector,
    InstagramRateLimitDetector,
    TwitterRateLimitDetector,
    LinkedInRateLimitDetector,
    get_rate_limit_detector,
)

__all__ = [
    # Page objects
    "BasePage",
    # Browser management
    "BrowserFactory",
    "BrowserManager",
    "BrowserConfig",
    "create_browser_manager",
    # Constants
    "TIMEOUTS",
    "USER_AGENTS",
    "VIEWPORTS",
    "ACCEPT_LANGUAGES",
    "BROWSER_ARGS",
    # Rate limiting
    "RateLimitDetector",
    "RateLimitHandler",
    "FacebookRateLimitDetector",
    "InstagramRateLimitDetector",
    "TwitterRateLimitDetector",
    "LinkedInRateLimitDetector",
    "get_rate_limit_detector",
]
