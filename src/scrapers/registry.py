"""Registry for platform scrapers."""

import logging
from typing import Dict, Type, Optional, Any

from .base import BaseScraper
from ..core.models import Platform
from ..core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ScraperRegistry:
    """Registry for managing platform scrapers."""

    _scrapers: Dict[str, Type[BaseScraper]] = {}

    @classmethod
    def register(cls, platform: Platform, scraper_class: Type[BaseScraper]) -> None:
        """
        Register a scraper for a platform.

        Args:
            platform: Platform enum value
            scraper_class: Scraper class to register
        """
        cls._scrapers[platform.value] = scraper_class
        logger.debug(f"Registered scraper for {platform.value}: {scraper_class.__name__}")

    @classmethod
    def get(cls, platform: str, config: Optional[Dict[str, Any]] = None) -> BaseScraper:
        """
        Get a scraper instance for a platform.

        Args:
            platform: Platform name
            config: Platform-specific configuration

        Returns:
            Scraper instance

        Raises:
            ConfigurationError: If platform is not supported
        """
        # Normalize platform name
        platform_lower = platform.lower()

        if platform_lower not in cls._scrapers:
            available = ", ".join(cls._scrapers.keys())
            raise ConfigurationError(
                f"Unsupported platform: {platform}. Available: {available}",
                setting="platform"
            )

        scraper_class = cls._scrapers[platform_lower]

        try:
            return scraper_class(config)
        except ImportError as e:
            raise ConfigurationError(
                f"Scraper for {platform} requires additional dependencies: {e}",
                setting="platform"
            )

    @classmethod
    def list_available(cls) -> list[str]:
        """
        List available platforms.

        Returns:
            List of platform names
        """
        return list(cls._scrapers.keys())

    @classmethod
    def is_available(cls, platform: str) -> bool:
        """
        Check if a platform is available.

        Args:
            platform: Platform name

        Returns:
            True if platform is available
        """
        return platform.lower() in cls._scrapers


# Auto-register scrapers on import
def _register_default_scrapers():
    """Register default POM-based scrapers."""
    try:
        from .facebook import FacebookScraper
        ScraperRegistry.register(Platform.FACEBOOK, FacebookScraper)
        logger.info("Registered Facebook scraper")
    except ImportError as e:
        logger.warning(f"Facebook scraper not available: {e}")

    try:
        from .instagram import InstagramScraper
        ScraperRegistry.register(Platform.INSTAGRAM, InstagramScraper)
        logger.info("Registered Instagram scraper")
    except ImportError as e:
        logger.warning(f"Instagram scraper not available: {e}")

    try:
        from .twitter import TwitterScraper
        ScraperRegistry.register(Platform.TWITTER, TwitterScraper)
        logger.info("Registered Twitter scraper")
    except ImportError as e:
        logger.warning(f"Twitter scraper not available: {e}")

    try:
        from .linkedin import LinkedInScraper
        ScraperRegistry.register(Platform.LINKEDIN, LinkedInScraper)
        logger.info("Registered LinkedIn scraper")
    except ImportError as e:
        logger.warning(f"LinkedIn scraper not available: {e}")


# Register scrapers when module is imported
_register_default_scrapers()
