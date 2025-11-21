"""Facebook Profile Page Object."""

import logging
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class ProfilePage(BasePage):
    """Page object for Facebook profile/page scraping."""

    def __init__(self, page: Page):
        """
        Initialize profile page.

        Args:
            page: Playwright page instance
        """
        super().__init__(page)

    def navigate(self, page_name: str) -> "ProfilePage":
        """
        Navigate to a Facebook page/profile.

        Args:
            page_name: Facebook page name or ID

        Returns:
            Self for chaining
        """
        url = Selectors.URLs.profile(page_name)
        logger.debug(f"NAVIGATE | profile={page_name} | url={url}")
        super().navigate(url, wait_until="domcontentloaded")
        self.wait(2000)
        self.dismiss_popups()
        return self

    def is_page_available(self) -> bool:
        """
        Check if the page/profile is available.

        Returns:
            True if available
        """
        # Check for not found message
        if self.is_visible(Selectors.Profile.PAGE_NOT_FOUND, timeout=2000):
            return False

        # Check page title
        if "Page Not Found" in self.page.title():
            return False

        return True

    def get_display_name(self) -> str:
        """
        Get the display name of the page/profile.

        Returns:
            Display name or empty string
        """
        return self.get_text(Selectors.Profile.PAGE_NAME, timeout=3000) or ""

    def get_followers_count(self) -> int:
        """
        Get the follower count.

        Returns:
            Number of followers
        """
        text = self.get_text(Selectors.Profile.FOLLOWERS_LINK, timeout=2000)
        if text:
            return self.parse_count(text)
        return 0

    def get_likes_count(self) -> int:
        """
        Get the page likes count.

        Returns:
            Number of likes
        """
        text = self.get_text(Selectors.Profile.LIKES_COUNT, timeout=2000)
        if text:
            return self.parse_count(text)
        return 0

    def is_verified(self) -> bool:
        """
        Check if the page/profile is verified.

        Returns:
            True if verified
        """
        return self.is_visible(Selectors.Profile.VERIFIED_BADGE, timeout=2000)
