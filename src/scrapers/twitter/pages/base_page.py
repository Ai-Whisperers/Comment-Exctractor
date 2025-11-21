"""Twitter-specific Base Page Object extending shared BasePage."""

import logging
from playwright.sync_api import Page

from ...shared import BasePage as SharedBasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class BasePage(SharedBasePage):
    """Twitter-specific base page object with platform-specific popup handling."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.selectors = Selectors

    def dismiss_popups(self) -> "BasePage":
        """Dismiss Twitter-specific popups."""
        popup_selectors = [
            Selectors.Popups.NOT_NOW,
            Selectors.Popups.DISMISS,
        ]
        super().dismiss_popups(popup_selectors)
        return self
