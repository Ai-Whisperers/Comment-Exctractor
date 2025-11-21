"""Facebook Base Page Object extending shared BasePage."""

import logging
from typing import Optional

from playwright.sync_api import Page

from ...shared.base_page import BasePage as SharedBasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class BasePage(SharedBasePage):
    """Base class for Facebook page objects, extending shared functionality."""

    def __init__(self, page: Page):
        """
        Initialize Facebook base page.

        Args:
            page: Playwright page instance
        """
        super().__init__(page)
        self.selectors = Selectors

    # =========================================================================
    # FACEBOOK POPUP HANDLING (overrides shared version)
    # =========================================================================

    def dismiss_popups(self) -> "BasePage":
        """
        Dismiss common Facebook popups.

        Returns:
            Self for chaining
        """
        # Try to close dialog with Close button
        try:
            close_button = self.page.locator(Selectors.Popups.CLOSE_BUTTON).first
            if close_button.is_visible(timeout=500):
                close_button.click()
                self.wait(500)
                logger.debug("POPUP DISMISSED | close button")
        except Exception:
            pass

        # Try Escape key
        try:
            dialog = self.page.locator(Selectors.Popups.DIALOG).first
            if dialog.is_visible(timeout=300):
                self.page.keyboard.press("Escape")
                self.wait(300)
                logger.debug("POPUP DISMISSED | escape key")
        except Exception:
            pass

        # Try common dismiss buttons
        dismiss_selectors = [
            Selectors.Popups.NOT_NOW,
            Selectors.Popups.NOT_NOW_LOWER,
            Selectors.Popups.DISMISS,
            Selectors.Popups.OK,
        ]

        for selector in dismiss_selectors:
            try:
                button = self.page.locator(selector).first
                if button.is_visible(timeout=500):
                    button.click()
                    self.wait(500)
                    logger.debug(f"POPUP DISMISSED | selector={selector}")
                    break
            except Exception:
                continue

        return self

    # =========================================================================
    # URL / PAGE STATE
    # =========================================================================

    def url_contains(self, pattern: str) -> bool:
        """Check if current URL contains pattern."""
        return pattern in self.page.url

    # =========================================================================
    # KEYBOARD
    # =========================================================================

    def press_key(self, key: str) -> "BasePage":
        """
        Press a keyboard key.

        Args:
            key: Key to press (e.g., "ArrowRight", "Escape")

        Returns:
            Self for chaining
        """
        self.page.keyboard.press(key)
        return self
