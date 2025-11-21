"""Platform scrapers."""

from .base import BaseScraper
from .registry import ScraperRegistry

# Import Playwright-based scrapers
try:
    from .instagram_playwright import InstagramPlaywrightScraper
except ImportError:
    InstagramPlaywrightScraper = None

__all__ = [
    "BaseScraper",
    "ScraperRegistry",
    "InstagramPlaywrightScraper",
]
