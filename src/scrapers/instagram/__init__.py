"""Instagram scraper package with Page Object Model architecture."""

from .scraper import InstagramScraper
from .selectors import Selectors

__all__ = ["InstagramScraper", "Selectors"]
