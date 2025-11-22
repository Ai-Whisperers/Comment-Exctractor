"""LinkedIn Profile Page Object."""

import logging
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class ProfilePage(BasePage):
    """Page object for LinkedIn profile scraping."""

    def __init__(self, page: Page):
        super().__init__(page)

    def navigate(self, username: str) -> "ProfilePage":
        """Navigate to profile - tries company page first, then personal profile."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        # Try company page first
        company_url = Selectors.URLs.company(username)
        logger.debug(f"NAVIGATE | trying company page={username}")

        try:
            # Use 'load' and longer timeout for reliable navigation
            super().navigate(company_url, wait_until="load", timeout=90000)
        except PlaywrightTimeout:
            logger.warning(f"NAVIGATE | timeout loading company page, retrying...")
            # Retry with a shorter wait
            try:
                super().navigate(company_url, wait_until="commit", timeout=60000)
            except PlaywrightTimeout:
                logger.warning(f"NAVIGATE | second timeout, continuing anyway")

        self.wait(3000)  # Give page time to load
        self.dismiss_popups()

        # Check if company page exists
        if '/company/' in self.page.url and self.is_profile_available():
            logger.debug(f"NAVIGATE | found company page={username}")
            self._is_company = True
            return self

        # Fall back to personal profile
        profile_url = Selectors.URLs.profile(username)
        logger.debug(f"NAVIGATE | trying personal profile={username}")
        try:
            super().navigate(profile_url, wait_until="load", timeout=90000)
        except PlaywrightTimeout:
            logger.warning(f"NAVIGATE | timeout loading profile, retrying...")
            try:
                super().navigate(profile_url, wait_until="commit", timeout=60000)
            except PlaywrightTimeout:
                logger.warning(f"NAVIGATE | second timeout, continuing anyway")

        self.wait(3000)
        self.dismiss_popups()
        self._is_company = False
        return self

    def navigate_to_posts(self, username: str) -> "ProfilePage":
        """Navigate to posts page - uses correct URL for company vs personal."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        # Check if we already know it's a company
        is_company = getattr(self, '_is_company', None)

        if is_company is None:
            # Determine by checking current URL or trying company first
            current_url = self.page.url
            is_company = '/company/' in current_url

        if is_company:
            url = Selectors.URLs.company_posts(username)
            logger.debug(f"NAVIGATE | company posts={username}")
        else:
            url = Selectors.URLs.profile_posts(username)
            logger.debug(f"NAVIGATE | profile posts={username}")

        try:
            super().navigate(url, wait_until="load", timeout=90000)
        except PlaywrightTimeout:
            logger.warning(f"NAVIGATE | timeout loading posts page, retrying...")
            try:
                super().navigate(url, wait_until="commit", timeout=60000)
            except PlaywrightTimeout:
                logger.warning(f"NAVIGATE | second timeout, continuing anyway")

        self.wait(3000)
        self.dismiss_popups()
        return self

    def is_profile_available(self) -> bool:
        if self.is_visible(Selectors.Profile.NOT_FOUND, timeout=2000):
            return False
        return True

    def get_display_name(self) -> str:
        return self.get_text(Selectors.Profile.DISPLAY_NAME, timeout=3000) or ""

    def get_headline(self) -> str:
        return self.get_text(Selectors.Profile.HEADLINE, timeout=2000) or ""

    def get_followers_count(self) -> int:
        text = self.get_text(Selectors.Profile.FOLLOWERS_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def get_connections_count(self) -> int:
        text = self.get_text(Selectors.Profile.CONNECTIONS_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def is_verified(self) -> bool:
        return self.is_visible(Selectors.Profile.VERIFIED_BADGE, timeout=2000)
