"""Google Maps-specific Base Page Object extending shared BasePage."""

import logging
from playwright.sync_api import Page

from ...shared import BasePage as SharedBasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class BasePage(SharedBasePage):
    """Google Maps-specific base page object with platform-specific popup handling."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.selectors = Selectors

    def dismiss_popups(self) -> "BasePage":
        """Dismiss Google-specific popups like cookie consent."""
        popup_selectors = [
            Selectors.Popups.COOKIE_ACCEPT,
            Selectors.Popups.CLOSE_BUTTON,
            Selectors.Popups.DISMISS,
        ]
        super().dismiss_popups(popup_selectors)
        return self

    def _get_platform_name(self) -> str:
        """Return platform name for debug logging."""
        return "google"
