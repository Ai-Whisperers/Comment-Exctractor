"""Twitter Profile Page Object."""

import logging
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class ProfilePage(BasePage):
    """Page object for Twitter profile scraping."""

    def __init__(self, page: Page):
        super().__init__(page)

    def navigate(self, username: str) -> "ProfilePage":
        url = Selectors.URLs.profile(username)
        logger.debug(f"NAVIGATE | profile={username}")
        super().navigate(url, wait_until="domcontentloaded")
        self.wait(2000)
        self.dismiss_popups()
        return self

    def is_profile_available(self) -> bool:
        if self.is_visible(Selectors.Profile.NOT_FOUND, timeout=2000):
            return False
        return True

    def get_display_name(self) -> str:
        return self.get_text(Selectors.Profile.DISPLAY_NAME, timeout=3000) or ""

    def get_followers_count(self) -> int:
        text = self.get_text(Selectors.Profile.FOLLOWERS_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def get_following_count(self) -> int:
        text = self.get_text(Selectors.Profile.FOLLOWING_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def is_verified(self) -> bool:
        return self.is_visible(Selectors.Profile.VERIFIED_BADGE, timeout=2000)
