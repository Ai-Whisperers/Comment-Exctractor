"""Facebook Base Page Object extending shared BasePage."""

import logging
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

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
        except (PlaywrightTimeout, TimeoutError):
            pass

        # Try Escape key
        try:
            dialog = self.page.locator(Selectors.Popups.DIALOG).first
            if dialog.is_visible(timeout=300):
                self.page.keyboard.press("Escape")
                self.wait(300)
                logger.debug("POPUP DISMISSED | escape key")
        except (PlaywrightTimeout, TimeoutError):
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
            except (PlaywrightTimeout, TimeoutError):
                continue

        return self

    # =========================================================================
    # SMART WAIT STRATEGY
    # =========================================================================

    def smart_wait_for_content(
        self,
        max_wait_ms: int = 5000,
        check_interval_ms: int = 100,
        stability_checks: int = 3
    ) -> bool:
        """
        Wait until page content stabilizes or timeout.

        Returns True if content stabilized, False if timeout.
        """
        previous_height = self.evaluate("document.body.scrollHeight")
        stable_count = 0
        elapsed = 0

        while elapsed < max_wait_ms:
            self.wait(check_interval_ms)
            elapsed += check_interval_ms

            current_height = self.evaluate("document.body.scrollHeight")

            if current_height == previous_height:
                stable_count += 1
                if stable_count >= stability_checks:
                    logger.debug(f"Content stabilized after {elapsed}ms")
                    return True
            else:
                stable_count = 0
                previous_height = current_height

        logger.debug(f"Content wait timeout after {max_wait_ms}ms")
        return False

    def save_debug_html(
        self,
        reason: str,
        context: str = "",
        additional_info: dict = None,
        max_size_kb: int = 500
    ) -> Optional[str]:
        """Save current page HTML for debugging with size limit."""
        import json
        from pathlib import Path
        from datetime import datetime

        try:
            debug_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_{context}_{timestamp}.html"
            filepath = debug_dir / filename

            html = self.page.content()

            # Truncate if too large
            max_bytes = max_size_kb * 1024
            truncated = False
            if len(html.encode('utf-8')) > max_bytes:
                html = html[:max_bytes] + "\n\n<!-- TRUNCATED: exceeded size limit -->"
                truncated = True
                logger.debug(f"DEBUG HTML | truncated to {max_size_kb}KB")

            filepath.write_text(html, encoding='utf-8')

            # Save metadata
            if additional_info:
                meta_path = filepath.with_suffix('.json')
                meta_path.write_text(json.dumps({
                    "reason": reason,
                    "context": context,
                    "info": additional_info,
                    "timestamp": timestamp,
                    "truncated": truncated
                }, indent=2))

            logger.debug(f"DEBUG HTML | saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.warning(f"Failed to save debug HTML: {e}")
            return None

    # url_contains(), press_key(), and query_selector() are inherited from SharedBasePage
