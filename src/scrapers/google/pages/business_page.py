"""Google Maps Business Page Object."""

import logging
import re
from typing import Dict, Any, Optional
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class BusinessPage(BasePage):
    """Page object for Google Maps business profile scraping."""

    def __init__(self, page: Page):
        super().__init__(page)

    def navigate_to_place(self, place_id: str) -> "BusinessPage":
        """Navigate to a business by place ID."""
        url = Selectors.URLs.place(place_id)
        logger.debug(f"NAVIGATE | place_id={place_id}")
        super().navigate(url, wait_until="domcontentloaded")
        self.wait(3000)
        self.dismiss_popups()
        return self

    def navigate_to_search(self, query: str) -> "BusinessPage":
        """Navigate to a business search."""
        url = Selectors.URLs.search(query)
        logger.debug(f"NAVIGATE | search={query}")
        super().navigate(url, wait_until="domcontentloaded")
        self.wait(3000)
        self.dismiss_popups()
        return self

    def is_business_available(self) -> bool:
        """Check if business page loaded successfully."""
        # Check for not found message
        if self.is_visible(Selectors.Business.NOT_FOUND, timeout=2000):
            return False
        # Check for business name
        return self.is_visible(Selectors.Business.NAME, timeout=3000) or \
               self.is_visible(Selectors.Business.NAME_ALT, timeout=1000)

    def get_business_name(self) -> str:
        """Get the business name."""
        name = self.get_text(Selectors.Business.NAME, timeout=3000)
        if not name:
            name = self.get_text(Selectors.Business.NAME_ALT, timeout=2000)
        return name or ""

    def get_category(self) -> str:
        """Get the business category."""
        return self.get_text(Selectors.Business.CATEGORY, timeout=2000) or ""

    def get_address(self) -> str:
        """Get the business address."""
        return self.get_text(Selectors.Business.ADDRESS, timeout=2000) or ""

    def get_phone(self) -> str:
        """Get the business phone number."""
        return self.get_text(Selectors.Business.PHONE, timeout=2000) or ""

    def get_website(self) -> str:
        """Get the business website URL."""
        return self.get_attribute(Selectors.Business.WEBSITE, "href", timeout=2000) or ""

    def get_hours(self) -> str:
        """Get business hours text."""
        return self.get_text(Selectors.Business.HOURS, timeout=2000) or ""

    def get_rating(self) -> float:
        """Get the business rating (0-5)."""
        # Try primary selector
        rating_text = self.get_text(Selectors.Business.RATING, timeout=2000)
        if not rating_text:
            rating_text = self.get_text(Selectors.Business.RATING_ALT, timeout=1000)

        if rating_text:
            try:
                # Extract number from text like "4.5"
                match = re.search(r'[\d,.]+', rating_text)
                if match:
                    return float(match.group().replace(',', '.'))
            except (ValueError, AttributeError):
                pass
        return 0.0

    def get_total_reviews(self) -> int:
        """Get total number of reviews."""
        # Try primary selector
        reviews_text = self.get_text(Selectors.Business.TOTAL_REVIEWS, timeout=2000)
        if not reviews_text:
            reviews_text = self.get_text(Selectors.Business.TOTAL_REVIEWS_ALT, timeout=1000)

        if reviews_text:
            return self.parse_count(reviews_text)
        return 0

    def get_price_level(self) -> str:
        """Get price level (e.g., '$', '$$', '$$$')."""
        price_text = self.get_text(Selectors.Business.PRICE_LEVEL, timeout=2000)
        if price_text:
            # Extract $ symbols
            match = re.search(r'\$+', price_text)
            if match:
                return match.group()
        return ""

    def get_photo_count(self) -> int:
        """Get the number of photos."""
        text = self.get_text(Selectors.Business.PHOTO_COUNT, timeout=2000)
        if text:
            return self.parse_count(text)
        return 0

    def extract_business_data(self) -> Dict[str, Any]:
        """Extract all business data from the page."""
        return {
            "name": self.get_business_name(),
            "category": self.get_category(),
            "address": self.get_address(),
            "phone": self.get_phone(),
            "website": self.get_website(),
            "hours": self.get_hours(),
            "rating": self.get_rating(),
            "total_reviews": self.get_total_reviews(),
            "price_level": self.get_price_level(),
            "photo_count": self.get_photo_count(),
        }

    def click_reviews_tab(self) -> bool:
        """Click on the reviews tab to open reviews section."""
        # Try primary selector
        if self.click(Selectors.Reviews.REVIEWS_TAB, timeout=3000):
            self.wait(2000)
            return True
        # Try alternative selector
        if self.click(Selectors.Reviews.REVIEWS_TAB_ALT, timeout=2000):
            self.wait(2000)
            return True
        return False

    def extract_place_id_from_url(self) -> Optional[str]:
        """Extract place ID from current URL."""
        url = self.current_url
        # Google Maps URLs contain place_id or data parameter
        if 'place_id:' in url:
            match = re.search(r'place_id:([^/&?]+)', url)
            if match:
                return match.group(1)
        # Try to extract from data parameter
        if '!1s' in url:
            match = re.search(r'!1s([^!]+)', url)
            if match:
                return match.group(1)
        return None
