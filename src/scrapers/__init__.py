"""Platform scrapers."""

from .base import BaseScraper
from .registry import ScraperRegistry

# Import platform scrapers
from .facebook.scraper import FacebookScraper
from .instagram.scraper import InstagramScraper
from .twitter.scraper import TwitterScraper
from .linkedin.scraper import LinkedInScraper
from .google.scraper import GoogleScraper

# Shared components
from .shared.browser_manager import BrowserManager, BrowserConfig
from .shared.rate_limiting import (
    RateLimitDetector,
    RateLimitHandler,
    get_rate_limit_detector,
)

__all__ = [
    # Base
    "BaseScraper",
    "ScraperRegistry",
    # Scrapers
    "FacebookScraper",
    "InstagramScraper",
    "TwitterScraper",
    "LinkedInScraper",
    "GoogleScraper",
    # Browser management
    "BrowserManager",
    "BrowserConfig",
    # Rate limiting
    "RateLimitDetector",
    "RateLimitHandler",
    "get_rate_limit_detector",
]
