"""Facebook scraper package with Page Object Model architecture."""

from .scraper import FacebookScraper
from .selectors import Selectors

__all__ = ["FacebookScraper", "Selectors"]
